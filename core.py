from servers.BASE import ResponderServer, Result, LogEntry, Connection
import os
import ssl
import socket
import threading
import multiprocessing
import selectors
import enum
import logging
import logging.config
import logging.handlers
import asyncio
import requests
import json
from copy import deepcopy
import datetime
import ipaddress

multiprocessing.freeze_support()

class TaskCmd(enum.Enum):
	STOP = 0
	PROCESS = 1

class ServerProtocol(enum.Enum):
	TCP = 0
	UDP = 1
	SSL = 2

class Server():
	def __init__(self, ip, port, handler, proto = ServerProtocol.TCP, settings = None):
		self.bind_addr = ip
		self.bind_port = port
		self.proto     = proto
		self.handler   = handler
		self.settings  = settings

	def getaddr(self):
		return ((self.bind_addr, self.bind_port))

class Task():
	def __init__(self, cmd, soc, handler, settings = None):
		self.cmd     = cmd
		self.soc     = soc
		self.handler = handler
		self.settings  = settings

class AsyncSocketServer(multiprocessing.Process):
	def __init__(self, server, resultQ):
		multiprocessing.Process.__init__(self)
		self.server    = server
		self.resultQ   = resultQ
		self.loop      = None


	def log(self, level, message):
		self.resultQ.put(LogEntry(level, self.name, message))

	def setup(self):
		self.loop = asyncio.get_event_loop()
		if self.server.proto == ServerProtocol.TCP:
			s = self.server.handler()
			s.setup(self.server.bind_port, self.loop, self.resultQ, self.server.settings)
			s.run()
		elif self.server.proto == ServerProtocol.SSL:
			context = self.create_ssl_context()
			s = self.server.handler()
			s.setup(self.server.bind_port, self.loop, self.resultQ, self.server.settings)
			s.run(context)
		else:
			raise Exception('Protocol not implemented!')

	def create_ssl_context(self):
		ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
		#ssl_context.options |= (ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION)
		#ssl_context.set_ciphers(self.server.settings['SSL']['ciphers'])
		ssl_context.load_cert_chain(certfile=self.server.settings['SSL']['certfile'], keyfile=self.server.settings['SSL']['keyfile'])
		#ssl_context.set_alpn_protocols(['http/1.1'])
		return ssl_context


	def run(self):
		self.log(logging.INFO,'Starting SocketServer')
		self.setup()
		self.log(logging.INFO,'SocketServer setup complete!')
		self.loop.run_forever()


class LogProcessor(multiprocessing.Process):
	def __init__(self, logsettings, resultQ, stopEvent):
		multiprocessing.Process.__init__(self)
		self.resultQ     = resultQ
		self.stopEvent   = stopEvent
		self.logsettings = logsettings

		self.logger = None
		self.resultHandlers = []
		self.extensionsQueue = multiprocessing.Queue()


	def log(self, level, message):
		self.handleLog(LogEntry(level, self.name, message))

	def setup(self):
		logging.config.dictConfig(self.logsettings['log'])
		self.resultHandlers.append(print)
		if 'webview' in self.logsettings:
			wv = WebViewHandler(self.extensionsQueue, self.resultQ, self.logsettings['webview'])
			wv.start()

	
	def run(self):
		self.setup()		
		self.log(logging.INFO,'setup done')
		while not self.stopEvent.is_set():
			resultObj = self.resultQ.get()
			if isinstance(resultObj, Result):
				self.handleResult(resultObj)
			elif isinstance(resultObj, LogEntry):
				self.handleLog(resultObj)
			elif isinstance(resultObj, Connection):
				self.handleConnection(resultObj)
			else:
				raise Exception('Unknown object in queue!')

	def handleLog(self, log):
		logging.log(log.level, str(log))

	def handleConnection(self, con):
		logging.log(logging.INFO, str(con))
		self.extensionsQueue.put(con)

	def handleResult(self, result):
		self.extensionsQueue.put(result)


class WebViewHandler(threading.Thread):
	def __init__(self, resQ, logQ, config):
		threading.Thread.__init__(self)
		self.sendInterval = 10
		self.resQ = resQ
		self.logQ = logQ
		self.url = config['URL']
		self.connectionEndpoint = '/connection/'
		self.resultsEndpoint    = '/result/'
		self.AgentId =  config['AgentId']
		self.isSSL =  config['SSLAuth']
		self.SSLServerCert =  config['SSLServerCert']
		self.SSLClientCert =  config['SSLClientCert']
		self.SSLClientKey  =  config['SSLClientKey']

		self.resbuff = []
		self.resbuffLock = threading.Lock()

		self.conbuff = []
		self.conbuffLock = threading.Lock()

	def log(self, level, message):
		self.logQ.put(LogEntry(level, 'WebViewHandler', message))

	def setup(self):
		t = threading.Timer(self.sendInterval, self.sendResults)
		t.daemon = True
		t.start()
		t = threading.Timer(self.sendInterval, self.sendConnections)
		t.daemon = True
		t.start()

	def run(self):
		self.setup()
		self.log(logging.DEBUG,'Started!')
		while True:
			resultObj = self.resQ.get()
			if isinstance(resultObj, Result):
				with self.resbuffLock:
					res = resultObj.d
					res['agent_id'] = self.AgentId
					self.resbuff.append(res)
			elif isinstance(resultObj, Connection):
				with self.conbuffLock:
					self.conbuff.append(resultObj.toDict())

			else:
				raise Exception('Unknown object in queue!')


	def sendConnections(self):
		self.log(logging.DEBUG,'sendConnections called')
		if len(self.conbuff) > 0:
			package = {}
			package['agent_id'] = self.AgentId
			package['connections'] = None
			with self.conbuffLock:
				package['connections'] = deepcopy(self.conbuff)
				self.conbuff = []


			t1 = threading.Thread(target = self.sendtoAPI, args = (package,self.connectionEndpoint))
			t1.daemon = True
			t1.start()
				

		threading.Timer(self.sendInterval, self.sendConnections).start()


	def sendResults(self):
		self.log(logging.DEBUG,'sendResults called')
		if len(self.resbuff) > 0:
			tempbuff = None
			with self.resbuffLock:
				tempbuff = deepcopy(self.resbuff)
				self.resbuff = []

			t1 = threading.Thread(target = self.sendtoAPI, args = (tempbuff,self.resultsEndpoint))
			t1.daemon = True
			t1.start()
				

		threading.Timer(self.sendInterval, self.sendResults).start()


	def sendtoAPI(self, data, endpoint):
		try:
			self.log(logging.DEBUG,'Sending results to URL')
			headers = {'content-type': 'application/json'}
			#processing SSL client auth
			if self.url[:5].lower() == 'https' and self.isSSL:
				if self.SSLServerCert == False:
					self.log(logging.WARNING,'SSL client certificate enabled, but server cert verification disabled. I also like to live dangerously.')
				
				response = requests.put(self.url+endpoint, 
										data=json.dumps(data, cls = UniversalEncoder), 
										headers=headers,
										cert=(self.SSLClientCert, self.SSLClientKey),
										verify=self.SSLServerCert
										)
			#just upload wihout cert
			else:		
				response = requests.put(self.url+endpoint, 
										data=json.dumps(data, cls = UniversalEncoder), 
										headers=headers)
		except Exception as e:
			self.log(logging.INFO,'Exception! %s' % (str(e),))

				

class UniversalEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, datetime.datetime):
			return obj.isoformat()
		elif isinstance(obj, enum.Enum):
			return obj.value
		else:
			return json.JSONEncoder.default(self, obj)