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
from lystener import logMsg, loadJson, initDB, configparser, TaskExecutioner #, UrlBroadcaster

# starting 2 threads 
DAEMONS = [TaskExecutioner(), TaskExecutioner()]

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
	TEMPLATES_AUTO_RELOAD = True,
)

# redirect common http errors to index
app.register_error_handler(404, lambda *a,**kw: flask.redirect(flask.url_for("index")))
app.register_error_handler(500, lambda *a,**kw: flask.redirect(flask.url_for("index")))

# load listener.ini config file if found
# EXAMPLE
# [Autorizations]
# cc89e79975ea6ce45aa3a2fd7a54d383=forger.logSomething
# 37124939c97757349fc2f632683ef44e=hyperledger.executeInsurancePolicy	
# app.config.ini = configparser.ConfigParser(allow_no_value=True)
# inifile = os.path.join(lystener.DATA, "listener.ini")
# if os.path.exists(inifile):
# 	app.config.ini.read(inifile)


@app.route("/listeners")
def index():
	if os.path.exists(os.path.join(lystener.ROOT, ".json")):
		json_list = [loadJson(name) for name in os.listdir(os.path.join(lystener.ROOT, ".json")) if name.endswith(".json")]
	else:
		json_list = []

	# if app.config.ini.has_section("Autorizations"):
	# 	tiny_list = dict(app.config.ini.items("Autorizations", vars={}))
	# else:
	# 	tiny_list = {}

	cursor = connect()
	return flask.render_template("listener.html",
		counts=dict(cursor.execute("SELECT autorization, count(*) FROM history GROUP BY autorization").fetchall()),
		webhooks=json_list,
		# tinies=tiny_list
		tinies={}
	)


@app.route("/<module>/<name>", methods=["POST"])
def execute(module, name):

	if flask.request.method == "POST":
		# parse data as json object and try to get the content of `data` field
		data = json.loads(flask.request.data).get("data", False)

		# check the data sent by webhook
		if not data:
			logMsg("no data provided")
			return json.dumps({"success": False, "message": "no data provided"})

		# check autorization and exit if bad one
		autorization = flask.request.headers.get("Authorization", "?")
		# get token-autorization from registered webhook
		webhook = loadJson("%s.%s.json" % (module, name))
		half_token = webhook.get("token", 32*" ")[:32]
		# get token-autorization list from listener.ini file
		# ini_autorizations = {}
		# if app.config.ini.has_section("Autorizations"):
		# 	ini_autorizations = app.config.ini.options("Autorizations")
		if autorization == "?" or (half_token != autorization): # and autorization not in ini_autorizations):
			logMsg("not autorized here\ngiven auth=%s" % autorization)
			return json.dumps({"success": False, "message": "not autorized here"})

		# use sqlite database to check if data already parsed once
		cursor = connect()
		# try to get a signature from data
		signature = data.get("signature", False)
		if not signature:
			# remove all trailing spaces, new lines, tabs etc...
			# and generate sha 256 hash as signature
			raw = re.sub(r"[\s]*", "", json.dumps(sameDataSort(data)))
			h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
			signature = h.decode() if isinstance(h, bytes) else h
		# check if signature already in database
		cursor.execute("SELECT count(*) FROM history WHERE signature = ?", (signature,))
		if cursor.fetchone()[0] != 0:
			# exit if signature found in database
			logMsg("data already parsed")
			return json.dumps({"success": False, "message": "data already parsed"})
		else:
			logMsg("data autorized")
			TaskExecutioner.JOB.put(module, name, data, signature, autorization)
			return json.dumps({"success": True, "message": "data autorized"})


@app.teardown_appcontext
def close(*args, **kw):
	if hasattr(flask.g, "database"):
		flask.g.database.commit()
		flask.g.database.close()


def sameDataSort(data, reverse=False):
	"""return a sorted object from iterable data"""
	if isinstance(data, (list, tuple)):
		return sorted(data, reverse=reverse)
	elif isinstance(data, dict):
		result = OrderedDict()
		for key,value in sorted([(k,v) for k,v in data.items()], key=lambda e:e[0], reverse=reverse):
			result[k] = sameDataSort(value, reverse)
		return result
	else:
		return data


def connect():
	if not hasattr(flask.g, "database"):
		setattr(flask.g, "database", initDB())
	return getattr(flask.g, "database").cursor()


########################
# css reload bugfix... #
########################
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
########################
