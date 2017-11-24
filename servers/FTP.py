import logging
import traceback
from servers.BASE import ResponderServer, Result, LogEntry
from packets3 import FTPPacket



class FTP(ResponderServer):
	def modulename(self):
		return 'FTP'

	def handle(self):
		try:
			self.send(FTPPacket().getdata())
			data = self.recv()

			if data[0:4] == b"USER":
				User = data[5:].strip().decode()

				Packet = FTPPacket(Code=b"331",Message=b"User name okay, need password.")
				self.send(Packet.getdata())
				data = self.recv()

			if data[0:4] == b"PASS":
				Pass = data[5:].strip().decode()

				Packet = FTPPacket(Code=b"530",Message=b"User not logged in.")
				self.send(Packet.getdata())
				

				self.logResult({
					'module': 'FTP', 
					'type': 'Cleartext', 
					'client': self.soc.getpeername()[0], 
					'user': User, 
					'cleartext': Pass, 
					'fullhash': User + ':' + Pass
				})

				data = self.recv()

			else:
				Packet = FTPPacket(Code=b"502",Message=b"Command not implemented.")
				self.send(Packet.getdata())
				data = self.recv()

		except Exception as e:
			self.log(logging.INFO,'Exception! %s' % (str(e),))
			pass

		finally:
			self.soc.close()

	def send(self, data):
		self.soc.sendall(data)

	def recv(self):
		"""
		incorrect buffering, but works for capturing logon creds
		"""
		maxdata = 5 * 1024
		buff = b''
		while True:
			t = self.soc.recv(1024)
			if t == b'':
				break
			buff += t
			if len(buff) > maxdata:
				break
			if buff.find(b'\r\n') != -1:
				break

		return buff

