# -*- encoding:utf-8 -*-

import os
import re
import json
import flask
import hashlib

import lystener
from importlib import import_module
from lystener import logMsg, loadJson

# CURRENT_HASH = set()

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
	SESSION_REFRESH_EACH_REQUEST = True
)


@app.route("/<module>/<name>", methods=["POST", "GET"])
def execute(module, name):
	global CURRENT_HASH

	if flask.request.method == "POST":
		raw = flask.request.data
		data = json.loads(raw).get("data", False)
		raw = re.sub(r"[\s]*", "", raw) # strip all whitespaces

		# should add something to set a hook is happening
		# and prevent from execution of the same event with same data...
		# maybe hash the raw data and save it somewhere in a database
		# could be some history of parsed webhooks

		# h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
		# if h in CURRENT_HASH:
		# 	logMsg("already being processed")
		# 	return json.dumps({"success": False, "message": "already being processed"})
		# else:
		# 	CURRENT_HASH.add(h)

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

		# CURRENT_HASH.remove(h)
		return json.dumps({"success": True, "message": response})

	return flask.render_template(
		"listener.html",
		webhooks=[loadJson(name) for name in os.listdir(os.path.join(lystener.ROOT, ".json")) if name.endswith(".json")]
	)
