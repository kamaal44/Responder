#!/usr/bin/python3
import sys
import atexit
import copy
import os
import time
from pathlib import Path
from core import *
from servers.FTP import FTP
from servers.HTTP import HTTP, HTTPS
from servers.SMTP import SMTP
from servers.POP3 import POP3, POP3S
from servers.IMAP import IMAP, IMAPS
import config

def byealex(name_of_pid):
	pidfile = str(name_of_pid)
	os.remove(pidfile)

def handle_systemd():
	if os.path.isfile(config.pidfile):
		print ("%s already exists, exiting" % config.pidfile)
		sys.exit()

	pid = str(os.getpid())
	with open(config.pidfile, 'w') as f:
		f.write(pid)
	
	atexit.register(byealex,config.pidfile)
	

def main(argv):
	handle_systemd()
	try:
		current_path = Path(__file__)
		basedir = Path(str(current_path.parents[0]))

		bind_ip = ''

		httpsettings2 = copy.deepcopy(config.httpsettings)
		httpsettings2['Basic'] = True

		httpssettings = config.httpsettings
		httpssettings['SSL'] = config.sslsettings

		impassettings = {}
		impassettings['SSL'] = config.sslsettings

		pop3ssettings = {}
		pop3ssettings['SSL'] = config.sslsettings


		servers    = []
		resultQ   = multiprocessing.Queue()
		stopEvent = multiprocessing.Event()

		lp = LogProcessor(config.logsettings, resultQ, stopEvent)
		lp.daemon = True
		lp.start()
		
		ftpserver = Server('', 21, FTP)
		servers.append(ftpserver)
		httpserver = Server('', 80, HTTP, settings = config.httpsettings)
		servers.append(httpserver)
		httpserver2 = Server('', 81, HTTP, settings = httpsettings2)
		servers.append(httpserver2)
		httpsserver = Server('', 443, HTTPS, proto = ServerProtocol.SSL, settings = httpssettings)
		servers.append(httpsserver)
		smtpserver = Server('', 25, SMTP)
		servers.append(smtpserver)
		pop3server = Server('', 110, POP3)
		servers.append(pop3server)
		pop3sserver = Server('', 995, POP3S, proto = ServerProtocol.SSL, settings = pop3ssettings)
		servers.append(pop3sserver)
		imapserver = Server('', 143, IMAP)
		servers.append(imapserver)
		imapsserver = Server('', 993, IMAPS, proto = ServerProtocol.SSL, settings = impassettings)
		servers.append(imapsserver)

		for server in servers:
			ss = AsyncSocketServer(server, resultQ)
			ss.daemon = True
			ss.start()

		print('Started everything!')
		ss.join()

	except KeyboardInterrupt:
		sys.exit(0)


if __name__ == '__main__':
	main(sys.argv)