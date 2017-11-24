from abc import abstractmethod


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

class ResponderServer():
	def __init__(self):
		self.soc   = None #socket comes here
		self.logQ  = None
		self.settings = None

	def setup(self, soc, logQ, settings = None):
		self.soc  = soc
		self.logQ = logQ
		self.settings = settings

	def log(self, level, message):
		self.logQ.put(LogEntry(level, self.modulename(), message))

	def logResult(self, resultd):
		self.logQ.put(Result(resultd))

	@abstractmethod
	def modulename(self):
		pass

	@abstractmethod
	def handle(self):
		return 1