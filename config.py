pidfile = "/var/run/responder.pid"

logsettings = {
	'webview' : {
		'URL':'https://creds.56k.io:8081',
		'AgentId' : 'localagent',
		'SSLAuth' : False,
		'SSLServerCert' : '',
		'SSLClientCert' : '',
		'SSLClientKey'  : ''

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
	'certfile' : '/etc/letsencrypt/live/creds.56k.io/fullchain.pem',
	'keyfile'  : '/etc/letsencrypt/live/creds.56k.io/privkey.pem'
	#'certfile' : '/home/garage/Desktop/Responder-asyncio/certs/responder.crt',
	#'keyfile'  : '/home/garage/Desktop/Responder-asyncio/certs/responder.key'
}
