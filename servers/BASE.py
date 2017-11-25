from abc import ABC, abstractmethod
import asyncio
import logging

class Result():
	def __init__(self,d):
		self.d = d

class LogEntry():
	def __init__(self, level, name, msg):
		self.level = level
		self.name  = name
		self.msg   = msg

	def __str__(self):
		return "[%s] %s" % (self.name, self.msg)

class ResponderServer(ABC):
	def __init__(self):
		self.port     = None
		self.loop     = None
		self.logQ     = None
		self.settings = None
		self.peername = None #this is set when a connection is made!
		self.peerport = None

	def setup(self, port, loop, logQ, settings = None):
		self.port  = port
		self.loop  = loop
		self.logQ = logQ
		self.settings = settings

	def log(self, level, message):
		if self.peername == None:
			message = '[INIT] %s' %  message
		else:	
			message = '[%s:%d] %s' % (self.peername, self.peerport, message)
		self.logQ.put(LogEntry(level, self.modulename(), message))

	def logResult(self, resultd):
		self.logQ.put(Result(resultd))

	@abstractmethod
	def modulename(self):
		pass

	@abstractmethod
	def handle(self):
		pass



class ResponderProtocolTCP(asyncio.Protocol):
	
	def __init__(self, server):
		asyncio.Protocol.__init__(self)
		self._server = server
		self._buffer_maxsize = 10*1024
		self._request_data_size = self._buffer_maxsize
		self._transport = None
		self._buffer = ''


	def connection_made(self, transport):
		self._server.peername, self._server.peerport = transport.get_extra_info('peername')
		self._server.log(logging.INFO, 'New connection opened')
		self._transport = transport
		self._connection_made(transport)

	def data_received(self, raw_data):
		try:
			data = raw_data.decode('utf-8')
		except UnicodeDecodeError as e:
			self._transport._write(str(e).encode('utf-8'))
		
		else:
			self._buffer += data
			self._parsebuff()

	def connection_lost(self, exc):
		self._server.log(logging.INFO, 'Connection closed')
		self._connection_lost(exc)

	## Override this to access to connection lost function
	def _connection_lost(self, exc):
		return

	## Override this to start handling the buffer, the data is in self._buffer as a string!
	def _parsebuff():
		return

	## Override this to start handling the buffer
	def _connection_made():
		return