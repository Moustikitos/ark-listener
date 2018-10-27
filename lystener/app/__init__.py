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


@app.route("/")
def index():
	if os.path.exists(os.path.join(lystener.ROOT, ".json")):
		json_list = [loadJson(name) for name in os.listdir(os.path.join(lystener.ROOT, ".json")) if name.endswith(".json")]
	else:
		json_list = []
	return flask.render_template("listener.html", webhooks=json_list)


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
		# remove all trailling spaces, new lines, tabs etc...
		raw = re.sub(r"[\s]*", "", raw)
		# copute sha256 hash
		h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
		h = h.decode() if isinstance(h, bytes) else h
		# check if hash already exists
		cursor.execute("SELECT count(*) FROM history WHERE hash = ?", (h,))
		if cursor.fetchone()[0] == 0:
			# insert hash if 
			cursor.execute("INSERT OR REPLACE INTO history(hash, module) VALUES(?,?);", (h, path_module))
		else:
			logMsg("transaction already parsed")
			return json.dumps({"success": False, "message": "transaction already parsed"})
	
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
			logMsg("%s execution:\n%s" % (name, response))
		else:
			msg = "python definition %s not found in %s" % (name, module)
			logMsg(msg)
			return json.dumps({"success": False, "message": msg})

		# remove the module so if it is modified it will be updated
		sys.modules.pop(obj.__name__, False)
		del obj
		return json.dumps({"success": True, "message": response})

	return flask.redirect(flask.url_for("index"))


def initDB():
	database = os.path.join(lystener.DATA, "database.db")
	if not os.path.exists(database):
		os.makedirs(lystener.DATA)
	sqlite = sqlite3.connect(database)
	cursor = sqlite.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS history(hash TEXT, module TEXT);")
	cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS history_index ON history(hash);")
	sqlite.row_factory = sqlite3.Row
	sqlite.commit()
	return sqlite


def connect():
	if not hasattr(flask.g, "database"):
		setattr(flask.g, "database", initDB())
	return getattr(flask.g, "database").cursor()


@app.teardown_appcontext
def close(*args, **kw):
	if hasattr(flask.g, "database"):
		flask.g.database.commit()
		flask.g.database.close()
