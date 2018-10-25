# -*- encoding:utf-8 -*-

import os
import json
import flask

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
	SESSION_REFRESH_EACH_REQUEST = True
)


@app.route("/<module>/<name>", methods=["POST", "GET"])
def execute(module, name, **data):

	if flask.request.method == "POST":
		path_module = "%s.%s" % (module, name)
		data = json.loads(flask.request.data).get("data", False)

		# check the data sent by webhook
		if not data:
			Exception("no data provided")

		# check autorization and exit if bad one
		webhook = loadJson("%s.json" % path_module)
		if not webhook.get("token", "").startswith(flask.request.headers["Authorization"]):
			raise Exception("not autorized here")

	if not len(data):
		return json.dumps({"listening": True})

	# import asked module
	try:
		obj = import_module('lystener.{0}'.format(module))
	except ImportError as error:
		raise Exception("%r\ncan not import python module %s" % (error, module))

	# get asked function and execute with data provided by webhook
	print(obj)
	func = getattr(obj, name, False)
	if func:
		logMsg("%s" % func(data))
	else:
		raise Exception("python definition %s not found in %s" % (name, module))

	return json.dumps({"listening": True})
