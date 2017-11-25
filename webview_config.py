import urllib

###### DB CONFIG
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + sqlite_file.replace('\\','\\\\')
SQLALCHEMY_TRACK_MODIFICATIONS = False

###### LOGGING CONFIG
LOGLEVEL = 'DEBUG'

###### WEBSERVER CONFIG
HOST = ''
PORT = 8081

