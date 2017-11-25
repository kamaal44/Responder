#!/usr/bin/python3

if __name__ == '__main__':
	import os
	import time
	from pathlib import Path
	from core import *
	from servers.FTP import FTP
	from servers.HTTP import HTTP, HTTPS

	#### DEBUG ONLY!!
	os.environ['PYTHONASYNCIODEBUG'] = 'aaaa'

	current_path = Path(__file__)
	basedir = Path(str(current_path.parents[0]))

	bind_ip = ''


	logsettings = {
		'webview' : {
			'settings_file': str(basedir.joinpath('webview_config.py').resolve()),
			'useDB':True, 
			'useWeb':True
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
		'certfile' : '/home/garage/Desktop/Responder-asyncio/certs/responder.crt',
		'keyfile'  : '/home/garage/Desktop/Responder-asyncio/certs/responder.key'
	}

	httpssettings = httpsettings
	httpssettings['SSL'] = sslsettings

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
	httpsserver = Server('', 443, HTTPS, proto = ServerProtocol.SSL, settings = httpssettings)
	servers.append(httpsserver)

	for server in servers:
		ss = AsyncSocketServer(server, resultQ)
		ss.daemon = True
		ss.start()

	print('Started everything!')
	ss.join()

