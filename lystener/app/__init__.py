# -*- encoding:utf-8 -*-

import os
import re
import sys
import imp
import json
import flask
import hashlib
import sqlite3

import lystener
from collections import OrderedDict
from importlib import import_module
from lystener import logMsg, loadJson


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


@app.route("/")
def index():
	if os.path.exists(os.path.join(lystener.ROOT, ".json")):
		json_list = [loadJson(name) for name in os.listdir(os.path.join(lystener.ROOT, ".json")) if name.endswith(".json")]
	else:
		json_list = []
	cursor = connect()
	return flask.render_template("listener.html",
		counts=dict(cursor.execute("SELECT module, count(*) FROM history GROUP BY module").fetchall()),
		webhooks=json_list
	)


@app.route("/<module>/<name>", methods=["POST", "GET"])
def execute(module, name):

	if flask.request.method == "POST":
		raw = flask.request.data
		data = json.loads(raw).get("data", False)
		path_module = "%s.%s" % (module, name)

		# check the data sent by webhook
		if not data:
			logMsg("no data provided")
			return json.dumps({"success": False, "message": "no data provided"})

		# check autorization and exit if bad one
		webhook = loadJson("%s.json" % path_module)
		if not webhook.get("token", "").startswith(flask.request.headers["Authorization"]):
			logMsg("not autorized here")
			return json.dumps({"success": False, "message": "not autorized here"})

		# use sqlite database to check if data already parsed once
		cursor = connect()
		if "signature" in data:
			signature = data["signature"]
		else:
			# remove all trailling spaces, new lines, tabs etc...
			raw = re.sub(r"[\s]*", "", sameDataSort(data))
			h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
			signature = h.decode() if isinstance(h, bytes) else h
		cursor.execute("SELECT count(*) FROM history WHERE signature = ?", (signature,))
		if cursor.fetchone()[0] == 0:
			# insert signature
			cursor.execute("INSERT OR REPLACE INTO history(signature, module) VALUES(?,?);", (signature, path_module))
		else:
			logMsg("data already parsed")
			return json.dumps({"success": False, "message": "data already parsed"})
	
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

		# remove the module so if it is modified it will be updated
		sys.modules.pop(obj.__name__, False)
		del obj
		return json.dumps({"success": True, "message": response})

	return flask.redirect(flask.url_for("index"))


@app.teardown_appcontext
def close(*args, **kw):
	if hasattr(flask.g, "database"):
		flask.g.database.commit()
		flask.g.database.close()


@app.context_processor
def override_url_for():
	return dict(url_for=dated_url_for)


def sameDataSort(data, reverse=False):
	if isinstance(data, (list, tuple)):
		return list[sorted(elem, reverse=reverse)]
	elif isintace(data, dict):
		result = OrderedDict()
		for key,value in sorted([(k,v) for k,v in data.items()], key=lambda e:e[0], reverse=reverse):
			result[k] = sameDataSort(value, reverse)
	else:
		return data


def initDB():
	database = os.path.join(lystener.DATA, "database.db")
	if not os.path.exists(database):
		os.makedirs(lystener.DATA)
	sqlite = sqlite3.connect(database)
	cursor = sqlite.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS history(signature TEXT, module TEXT);")
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS history_index ON history(signature);")
	sqlite.row_factory = sqlite3.Row
	sqlite.commit()
	return sqlite


def connect():
	if not hasattr(flask.g, "database"):
		setattr(flask.g, "database", initDB())
	return getattr(flask.g, "database").cursor()


def dated_url_for(endpoint, **values):
	if endpoint == 'static':
		filename = values.get("filename", False)
		if filename:
			file_path = os.path.join(app.root_path, endpoint, filename)
			values["q"] = int(os.stat(file_path).st_mtime)
	return flask.url_for(endpoint, **values)
