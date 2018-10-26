# -*- encoding:utf-8 -*-

import io
import os
import re
import sys
import json
import datetime

# save python familly
PY3 = True if sys.version_info[0] >= 3 else False
input = input if PY3 else raw_input

# configuration pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
JSON = os.path.abspath(os.path.join(ROOT, ".json"))
DATA = os.path.abspath(os.path.join(ROOT, "app", ".data"))
LOG = os.path.abspath(os.path.join(ROOT, "app", ".log"))


# add the modules folder to the package path
__path__.append(os.path.abspath(os.path.join(ROOT, "modules")))
# add custom modules pathes from modules.pth file
pathfile = os.path.join(ROOT, "modules.pth")
if os.path.exists(pathfile):
	with io.open(pathfile) as pathes:
		comment = re.compile(r"^[\s]*#.*")
		for path in [p.strip() for p in pathes.read().split("\n") if not comment.match(p)]:
			if p != "":
				__path__.append(os.path.abspath(path))


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


def loadEnv(pathname):
	with io.open(pathname, "r") as environ:
		lines = [l.strip() for l in environ.read().split("\n")]
	result = {}
	for line in [l for l in lines if l != ""]:
		key,value = [l.strip() for l in line.split("=")]
		try:
			result[key] = int(value)
		except:
			result[key] = value
	return result


def dumpEnv(env, pathname):
	try:
		shutil.copy(pathname, pathname+".bak")
	except:
		pass
	with io.open(pathname, "wb") as environ:
		for key,value in sorted([(k,v) for k,v in env.items()], key=lambda e:e[0]):
			environ.write(b"%s=%s\n" % (key, value))


def logMsg(msg, logname=None):
	if logname:
		logfile = os.path.join(LOG, logname)
		try:
			os.makedirs(os.path.dirname(logfile))
		except OSError:
			pass
		stdout = io.open(logfile, "a")
	else:
		stdout = sys.stdout
	stdout.write(">>> [%s] %s\n" % (datetime.datetime.now().strftime("%x %X"), msg))
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

