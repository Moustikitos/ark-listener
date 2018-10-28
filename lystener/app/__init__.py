# -*- encoding:utf-8 -*-

import os
import re
import sys
import imp
import json
import flask
import hashlib


import requests
import lystener
from collections import OrderedDict
from importlib import import_module
from lystener import logMsg, loadJson, initDB, loadEnv, configparser


# create the application instance 
app = flask.Flask(__name__) 
app.config.update(
	# 300 seconds = 5 minutes lifetime session
	PERMANENT_SESSION_LIFETIME = 300,
	# used to encrypt cookies
	# secret key is generated each time app is restarted
	SECRET_KEY = os.urandom(24),
	# JS can't access cookies
	SESSION_COOKIE_HTTPONLY = True,
	# update cookies on each request
	# cookie are outdated after PERMANENT_SESSION_LIFETIME seconds of idle
	SESSION_REFRESH_EACH_REQUEST = True,
	# 
	TEMPLATES_AUTO_RELOAD = True
)
# redirect commn http errors to index
app.register_error_handler(404, lambda *a,**kw: flask.redirect(flask.url_for("index")))
app.register_error_handler(500, lambda *a,**kw: flask.redirect(flask.url_for("index")))

# pass
app.config.ini = configparser.ConfigParser(allow_no_value=True)
inifile = os.path.join(lystener.DATA, "listener.ini")
if os.path.exists(inifile):
	app.config.ini.read(inifile)


@app.route("/")
def index():
	if os.path.exists(os.path.join(lystener.ROOT, ".json")):
		json_list = [loadJson(name) for name in os.listdir(os.path.join(lystener.ROOT, ".json")) if name.endswith(".json")]
	else:
		json_list = []
	cursor = connect()
	return flask.render_template("listener.html",
		counts=dict(cursor.execute("SELECT autorization, count(*) FROM history GROUP BY autorization").fetchall()),
		webhooks=json_list
	)


@app.route("/<module>/<name>", methods=["POST"])
def execute(module, name):

	if flask.request.method == "POST":
		raw = flask.request.data
		data = json.loads(raw).get("data", False)
		path_module = "%s.%s" % (module, name)
		autorization = flask.request.headers["Authorization"]

		# check the data sent by webhook
		if not data:
			logMsg("no data provided")
			return json.dumps({"success": False, "message": "no data provided"})

		# check autorization and exit if bad one
		webhook = loadJson("%s.json" % path_module)
		if not webhook.get("token", "").startswith(autorization) and \
		   not app.config.ini.get("Autorization", autorization, fallback=False):
			logMsg("not autorized here")
			return json.dumps({"success": False, "message": "not autorized here"})

		# use sqlite database to check if data already parsed once
		cursor = connect()
		signature = data.get("signature", False)
		if not signature:
			# remove all trailing spaces, new lines, tabs etc...
			# and generate sha 256 hash as signature
			raw = re.sub(r"[\s]*", "", sameDataSort(data))
			h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
			signature = h.decode() if isinstance(h, bytes) else h
		# check if signature already in database
		cursor.execute("SELECT count(*) FROM history WHERE signature = ?", (signature,))
		if cursor.fetchone()[0] == 0:
			# insert signature if no one found in database
			cursor.execute("INSERT OR REPLACE INTO history(signature, autorization) VALUES(?,?);", (signature, autorization))
		else:
			# exit if signature found in database
			logMsg("data already parsed")
			return json.dumps({"success": False, "message": "data already parsed"})
	
		# act as a hub if asked
		endpoints = webhook.get("hub", [])
		if app.config.ini.has_section("Hub"):
			endpoints.extend([item[0] for item in app.config.ini.items("Hub", vars={})])
		if len(endpoints):
			result = []
			for endpoint in endpoints:
				try:
					req = request.post(endpoint, data=flask.request.data, headers=flask.request.headers, timeout=rest.TIMEOUT, verify=True)
				except Exception as error:
					result.append({"success":False,"error":error,"except":True})
				else:
					result.append(req.text)
			msg = "event broadcasted to hub :\n%s" % json.dumps(dic(zip(endpoints, result)), indent=2)
			logMsg(msg)
			# if node is used as a hub, should not have to execute something
			# so exit here
			return json.dumps({"success": True, "message": msg})

		# import asked module
		try:
			obj = import_module("lystener." + module)
		except ImportError as error:
			msg = "%r\ncan not import python element %s" % (error, module)
			logMsg(msg)
			return json.dumps({"success": False, "message": msg})

		# get asked function and execute with data provided by webhook
		func = getattr(obj, name, False)
		if func:
			response = func(data)
			logMsg("%s response:\n%s" % (name, response))
		else:
			msg = "python definition %s not found in %s" % (name, module)
			logMsg(msg)
			return json.dumps({"success": False, "message": msg})

		# remove the module so if code is modified it will be updated without
		# a listener restart
		sys.modules.pop(obj.__name__, False)
		del obj
		return json.dumps({"success": True, "message": response})


@app.teardown_appcontext
def close(*args, **kw):
	if hasattr(flask.g, "database"):
		flask.g.database.commit()
		flask.g.database.close()


def sameDataSort(data, reverse=False):
	if isinstance(data, (list,tupple)):
		return sorted(data, reverse=reverse)
	elif isintace(data, dict):
		result = OrderedDict()
		for key,value in sorted([(k,v) for k,v in data.items()], key=lambda e:e[0], reverse=reverse):
			result[k] = sameDataSort(value, reverse)
	else:
		return data


def connect():
	if not hasattr(flask.g, "database"):
		setattr(flask.g, "database", initDB())
	return getattr(flask.g, "database").cursor()


# css reload bugfix...

@app.context_processor
def override_url_for():
	return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
	if endpoint == 'static':
		filename = values.get("filename", False)
		if filename:
			file_path = os.path.join(app.root_path, endpoint, filename)
			values["q"] = int(os.stat(file_path).st_mtime)
	return flask.url_for(endpoint, **values)
