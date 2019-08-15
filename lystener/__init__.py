# -*- encoding:utf-8 -*-

import io
import os
import re
import sys
import imp
import json
import socket
import sqlite3
import datetime
import threading

# save python familly
PY3 = True if sys.version_info[0] >= 3 else False
if PY3:
	import queue
	import configparser
	input = input 
else:
	import Queue as queue
	import ConfigParser as configparser
	input = raw_input


# configuration pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
JSON = os.path.abspath(os.path.join(ROOT, ".json"))
DATA = os.path.abspath(os.path.join(ROOT, "app", ".data"))
LOG = os.path.abspath(os.path.join(ROOT, "app", ".log"))


# add the modules folder to the package path
__path__.append(os.path.abspath(os.path.join(ROOT, "modules")))

# add custom modules pathes from modules.pth file
# targeted python code could be anywhere where user can access
pathfile = os.path.join(ROOT, "modules.pth")
if os.path.exists(pathfile):
	with io.open(pathfile) as pathes:
		comment = re.compile(r"^[\s]*#.*")
		for path in [p.strip() for p in pathes.read().split("\n") if not comment.match(p)]:
			if path != "":
				__path__.append(os.path.abspath(path))


def getPublicIp():
	"""Store the public ip of server in PUBLIC_IP global var"""
	global PUBLIC_IP
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		# doesn't even have to be reachable
		s.connect(('10.255.255.255', 1))
		PUBLIC_IP = s.getsockname()[0]
	except:
		PUBLIC_IP = '127.0.0.1'
	finally:
		s.close()
	return PUBLIC_IP
# getPublicIp()


def loadJson(name, folder=None):
	filename = os.path.join(JSON, name if not folder else os.path.join(folder, name))
	if os.path.exists(filename):
		with io.open(filename) as in_:
			return json.load(in_)
	else:
		return {}


def dumpJson(data, name, folder=None):
	filename = os.path.join(JSON, name if not folder else os.path.join(folder, name))
	try: os.makedirs(os.path.dirname(filename))
	except OSError: pass
	with io.open(filename, "w" if PY3 else "wb") as out:
		json.dump(data, out, indent=4)


def logMsg(msg, logname=None, dated=False):
	if logname:
		logfile = os.path.join(LOG, logname)
		try:
			os.makedirs(os.path.dirname(logfile))
		except OSError:
			pass
		stdout = io.open(logfile, "a")
	else:
		stdout = sys.stdout

	stdout.write(
		">>> " + \
		("[%s] " % datetime.datetime.now().strftime("%x %X") if dated else "") + \
		"%s\n" % msg
	)
	stdout.flush()

	if logname:
		return stdout.close()


def chooseItem(msg, *elem):
	n = len(elem)
	if n > 1:
		sys.stdout.write(msg + "\n")
		for i in range(n):
			sys.stdout.write("    %d - %s\n" % (i + 1, elem[i]))
		sys.stdout.write("    0 - quit\n")
		i = -1
		while i < 0 or i > n:
			try:
				i = input("Choose an item: [1-%d]> " % n)
				i = int(i)
			except ValueError:
				i = -1
			except KeyboardInterrupt:
				sys.stdout.write("\n")
				sys.stdout.flush()
				return False
		if i == 0:
			return None
		return elem[i - 1]
	elif n == 1:
		return elem[0]
	else:
		sys.stdout.write("Nothing to choose...\n")
		return False


def initDB():
	database = os.path.join(DATA, "database.db")
	if not os.path.exists(DATA):
		os.makedirs(DATA)
	sqlite = sqlite3.connect(database)
	cursor = sqlite.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS history(signature TEXT, autorization TEXT);")
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS history_index ON history(signature);")
	sqlite.row_factory = sqlite3.Row
	sqlite.commit()
	return sqlite


# class UrlBroadcaster(threading.Thread):

# 	JOB = queue.Queue()
# 	LOCK = threading.Lock()
# 	STOP = threading.Event()

# 	@staticmethod
# 	def killall():
# 		UrlBroadcaster.STOP.set()

# 	def __init__(self, *args, **kwargs):
# 		threading.Thread.__init__(self)
# 		self.daemon = True
# 		self.start()

# 	def run(self):
# 		while not UrlBroadcaster.STOP.is_set():
# 			endpoint, data, headers = UrlBroadcaster.JOB.get()
# 			try:
# 				requests.post(endpoint, data=data, headers=headers, timeout=5, verify=True)
# 			except Exception as error:
# 				UrlBroadcaster.LOCK.aquire()
# 				logMsg("%r" % json.dumps({"endpoint":endpoint,"success":False,"error":"%r"%error,"except":True}, indent=2))
# 			else:
# 				UrlBroadcaster.LOCK.aquire()
# 				logMsg("%r" % json.dumps({"endpoint":endpoint,"success":True}, indent=2))
# 			finally:
# 				UrlBroadcaster.LOCK.release()


class TaskExecutioner(threading.Thread):

	JOB = queue.Queue()
	LOCK = threading.Lock()
	STOP = threading.Event()

	@staticmethod
	def killall():
		TaskExecutioner.STOP.set()

	def __init__(self, *args, **kwargs):
		threading.Thread.__init__(self)
		self.daemon = True
		self.start()

	def run(self):
		while not TaskExecutioner.STOP.is_set():
			name, func, data = TaskExecutioner.JOB.get()
			try:
				response = func(data)
			except Exception as error:
				TaskExecutioner.LOCK.aquire()
				logMsg("%s response:\n%s" % (name, "%r"%error))
			else:
				TaskExecutioner.LOCK.aquire()
				logMsg("%s response:\n%s" % (name, response))
			finally:
				TaskExecutioner.LOCK.release()

