#!/usr/bin/python3

if __name__ == '__main__':
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

	#### DEBUG ONLY!!
	os.environ['PYTHONASYNCIODEBUG'] = 'aaaa'

	current_path = Path(__file__)
	basedir = Path(str(current_path.parents[0]))

	bind_ip = ''


	logsettings = {
		'webview' : {
		#	'settings_file': '/var/www/responder-webview/config.py',
			'settings_file': '/home/garage/Desktop/Responder-asyncio/webview_config.py',
			'useDB':True, 
			'useWeb':False
		},
		'log' : {
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

	sslsettings = {
		'ciphers'  : 'ALL',
		#'certfile' : '/etc/letsencrypt/live/creds.56k.io/fullchain.pem',
		#'keyfile'  : '/etc/letsencrypt/live/creds.56k.io/privkey.pem'
		'certfile' : '/home/garage/Desktop/Responder-asyncio/certs/responder.crt',
		'keyfile'  : '/home/garage/Desktop/Responder-asyncio/certs/responder.key'
	}

	httpsettings2 = copy.deepcopy(httpsettings)
	httpsettings2['Basic'] = True

	httpssettings = httpsettings
	httpssettings['SSL'] = sslsettings

	impassettings = {}
	impassettings['SSL'] = sslsettings

	pop3ssettings = {}
	pop3ssettings['SSL'] = sslsettings


	servers    = []
	resultQ   = multiprocessing.Queue()
	stopEvent = multiprocessing.Event()

	lp = LogProcessor(logsettings, resultQ, stopEvent)
	lp.daemon = True
	lp.start()
	
	ftpserver = Server('', 21, FTP)
	servers.append(ftpserver)
	httpserver = Server('', 80, HTTP, settings = httpsettings)
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

