from servers.BASE import ResponderServer, Result, LogEntry
import socket
import threading
import multiprocessing
import selectors
import enum
import logging
import logging.config
import logging.handlers
multiprocessing.freeze_support()
multiprocessing.allow_connection_pickling()

class TaskCmd(enum.Enum):
	STOP = 0
	PROCESS = 1

class Server():
	def __init__(self, ip, port, handler, settings = None):
		self.bind_addr = ip
		self.bind_port = port
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

class SocketServer(multiprocessing.Process):
	def __init__(self, severs, processQ, resultQ, stopEvent):
		multiprocessing.Process.__init__(self)
		self.servers = servers
		self.processQ  = processQ
		self.resultQ   = resultQ
		self.stopEvent = stopEvent
		self.sockets = []
		self.sel     = selectors.DefaultSelector()
		self.handleLookupDict = {}

	def log(self, level, message):
		self.resultQ.put(LogEntry(level, self.name, message))

	def setup(self):
		for server in self.servers:
			if server.bind_port in self.handleLookupDict:
				self.log(logging.INFO,'ERROR! Multiple server wants to use the same port!!!')
				return
			self.handleLookupDict[server.bind_port] = server
			soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			soc.setblocking(False)
			soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			soc.bind(server.getaddr())
			soc.listen(1000)
			self.sel.register(soc, selectors.EVENT_READ, self.accept)

	def run(self):
		self.setup()
		while not self.stopEvent.is_set():
			events = self.sel.select()
			for key, mask in events:
				callback = key.data
				callback(key.fileobj, mask)

	def accept(self, sock, mask):
		conn, addr = sock.accept()  # Should be ready
		self.log(logging.INFO, 'Connection accepted from %s:%d' % (addr),)
		ip, port = conn.getsockname()
		if port not in self.handleLookupDict:
			self.log(logging.INFO,'Error! This is not possible')
			raise Exception('Got a socket to a port we did not open!')
		server = self.handleLookupDict[port]
		handler = type(server.handler())
		self.processQ.put(Task(TaskCmd.PROCESS, conn, handler, server.settings))


class CommProcessor(multiprocessing.Process):
	def __init__(self, threadCnt, processQ, resultQ, stopEvent):
		multiprocessing.Process.__init__(self)
		self.threadCnt = threadCnt
		self.processQ  = processQ
		self.resultQ   = resultQ
		self.stopEvent = stopEvent

		self.processThreads = []

	def log(self, level, message):
		self.resultQ.put(LogEntry(level, self.name, message))

	def setup(self):
		for i in range(self.threadCnt):
			processThread = threading.Thread(target = self.processorThread, args = ())
			processThread.daemon = True
			self.processThreads.append(processThread)
			processThread.start()

	def run(self):
		self.log(logging.INFO,'Starting CommProcessor')
		self.setup()
		self.log(logging.INFO,'setup done')
		while not self.stopEvent.is_set():
			for processThread in self.processThreads:
				processThread.join()

	def processorThread(self):
		while not self.stopEvent.is_set():
			task = self.processQ.get()
			if task.cmd == TaskCmd.STOP:
				print('Exiting!')
				return

			elif task.cmd == TaskCmd.PROCESS:
				self.process(task)


	def process(self, task):
		self.log(logging.INFO,'Processign socket!')
		
		a = task.handler()
		a.setup(task.soc, self.resultQ, task.settings)
		a.handle()

class LogProcessor(multiprocessing.Process):
	def __init__(self, logsettings, resultQ, stopEvent):
		multiprocessing.Process.__init__(self)
		self.resultQ     = resultQ
		self.stopEvent   = stopEvent
		self.logsettings = logsettings

		self.logger = None

	def log(self, level, message):
		self.handleLog(LogEntry(level, self.name, message))

	def setup(self):
		#TODO do proper log settings
		#self.logger = logging.getLogger(__name__)
		#self.logger.setLevel(logging.DEBUG)
		logging.config.dictConfig(self.logsettings)




	def run(self):
		self.setup()		
		self.log(logging.INFO,'setup done')
		while not self.stopEvent.is_set():
			resultObj = self.resultQ.get()
			if isinstance(resultObj, Result):
				self.handleResult(resultObj)
			elif isinstance(resultObj, LogEntry):
				self.handleLog(resultObj)
			else:
				raise Exception('Unknown object in queue!')

	def handleLog(self, log):
		logging.log(log.level, str(log))

	def handleResult(self, result):
		print(result.d)


if __name__ == '__main__':
	import time
	from servers.FTP3 import FTP
	from servers.HTTP3 import HTTP

	bind_ip = ''

	logsettings = {
		'version': 1,
		'formatters': {
			'detailed': {
				'class': 'logging.Formatter',
					'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
			}
		},
		'handlers': {
			'console': {
				'class': 'logging.StreamHandler',
				'level': 'DEBUG',
			}
		},
		'root': {
			'level': 'DEBUG',
			'handlers': ['console']
		}
	}

	httpsettings = {
		'Force_WPAD_Auth': False,
		'WPAD_Script': '',
		'NumChal' : "random",
		'Challenge' : '',
		'Serve_Always': False,
		'Serve_Exe': False,
		'Serve_Html': False,
		'Html_Filename': '',
		'Exe_Filename': '',
		'Exe_DlName': '',
		'Force_WPAD_Auth': False,
		'HtmlToInject': 'aaaa',
		'Basic' : False

	}

	threadCnt = 10
	severs    = []
	processQ  = multiprocessing.Queue()
	resultQ   = multiprocessing.Queue()
	stopEvent = multiprocessing.Event()

	lp = LogProcessor(logsettings, resultQ, stopEvent)
	lp.daemon = True
	lp.start()
	

	ftpserver = Server(bind_ip, 21, FTP)
	httpserver = Server(bind_ip, 80, HTTP, httpsettings)
	
	servers = [ftpserver, httpserver]

	cp = CommProcessor(threadCnt, processQ, resultQ, stopEvent)
	cp.daemon = True
	cp.start()

	ss = SocketServer(severs, processQ, resultQ, stopEvent)
	ss.daemon = True
	ss.start()

	print('Started everything!')
	ss.join()

