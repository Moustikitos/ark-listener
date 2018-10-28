#! /usr/bin/env python
# -*- encoding:utf-8 -*-

"""
Usage:
   lys deploy-listener <event> <function> (<regexp> | -f <field> -c <condition> -v <value>) [-l <listener> -w <webhook> -e <endpoints>]
   lys destroy-listener [<function>]
   lys start-listening [-i <ip> -p <port>]
   lys stop-listening

Options:
-f --field=<field>         : the transaction field to be checked by the node
-c --condition=<condition> : the condition operator used to check the field
-v --value=<value>         : the value triggering the webhook
-l --listener=<listener>   : the peer receiving whebhook POST request
-w --webhook=<webhook>     : the peer registering the webhook
-e --endpoints=<endpoints> : the end points where to broadcast event
-i --ip=<ip>               : the ip used for listening server   [default: 0.0.0.0]
-p --port=<port>           : the port used for listening server [default: 5001]

Subcommands:
   deploy-listener  : link a webhook <event> with a python <function> 
   destroy-listener : unlink webhook <event> from python <function>
   start-listening  : start/restart listener server
   stop-listening   : stop listener server
"""

import os
import re
import sys
import docopt

# add git installation
sys.path.append(os.path.abspath(os.path.expanduser("~/ark-listener")))
# add parent path if executed from git structure
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import lystener
from lystener import rest, initDB


def _endpoints(value):
	# https://github.com/django/django/blob/master/django/core/validators.py#L74
	valid_url = re.compile(
		r'^https?://'  # http:// or https://
		r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
		r'localhost|'  # localhost...
		r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
		r'(?::\d+)?'  # optional port
		r'(?:/?|[/?]\S+)$', re.IGNORECASE)

	if os.path.exists(value):
		with io.open(value, "r") as data:
			result = [addr.strip() for addr in data.read().split("\n").split(",")]
	elif isinstance(value, str):
		result = value.split(",")
	else:
		return False

	result = [url for url in result if valid_url.match(url)]
	return False if not len(result) else result

def start_listening(args={}, **options):
	# persistent options effect
	# modifying the pm2 app.json configuration
	app_folder = os.path.abspath(os.path.dirname(lystener.__path__[0]))
	app = lystener.loadJson("app.json", folder=app_folder)
	app["apps"][0]["args"] = " ".join(["--{0:s}={1:s}".format(*item) for item in options.items()])
	lystener.dumpJson(app, "app.json", folder=app_folder)
	# execute pm2 command lines
	os.system("""
	if [ "$(pm2 id lystener-server) " = "[] " ]; then
		cd %(abspath)s
		pm2 start app.json
	else
		pm2 restart lystener-server
	fi
	""" % {"abspath": app_folder}
)


def stop_listening(args={}, **options):
	# execute pm2 command lines
	os.system("""
	if [ "$(pm2 id lystener-server) " != "[] " ]; then
		cd %(abspath)s
		pm2 stop lystener-server
	fi
	""" % {"abspath": os.path.abspath(os.path.dirname(lystener.__path__[0]))}
	)


def deploy_listener(args={}, **options):
	"""
	link ark blockchain event to a python function.
	"""

	function = args.get("<function>", options.get("function", False))
	regexp = args.get("<regexp>", options.get("regexp", False))
	event = args.get("<event>", options.get("event", False))
	json_name = "%s.json" % function

	# build peers and target url
	webhook_peer = options.get("webhook", "%(scheme)s://%(ip)s:%(port)s" % rest.WEBHOOK_PEER)
	listener_peer = options.get("listener", "%(scheme)s://%(ip)s:%(port)s" % rest.LISTENER_PEER)
	target_url = listener_peer +"/"+ function.replace(".", "/")

	# compute listener condition
	# if only a regexp is givent compute condition on vendorField
	if regexp:
		condition = {
			"key": "vendorField",
			"condition": "regexp",
			"value": args["<regexp>"]
		}
	# else create a condition.
	# Ark webhook api will manage condition errors
	elif len(options):
		condition = {
			"field": options["field"],
			"condition": options["condition"],
			"value": options["value"]
		}
	
	# load webhook configuration if already set
	webhook = lystener.loadJson(json_name)
	# lystener.loadJson returns void dict if json_name not found,
	# the if clause bellow will be true then
	if not webhook.get("token", False):
		# create the webhook
		req = rest.POST.api.webhooks(event=event, peer=webhook_peer, target=target_url, conditions=[condition])
		# parse request result if no error messages
		if not req.get("error", False):
			webhook = req["data"]
			# save the used peer to be able to delete it later
			webhook["peer"] = webhook_peer
			webhook["hub"] = _endpoints(options.get("endpoints", False))
			# save webhook configuration in JSON folder
			lystener.dumpJson(webhook, json_name)
			lystener.logMsg("%s webhook set" % function)
		else:
			lystener.logMsg("%r" % req)
			lystener.logMsg("%s webhook not set" % function)
	else:
		lystener.logMsg("webhook already set for %s" % function)


def destroy_listener(args={}, **options):
	"""
	unlink ark blockchain event from a python function.
	"""
	# # connect to database in order to remove 
	# sqlite = initDB()
	# cursor = sqlite.cursor()

	function = args.get("<function>", options.get("function", False))

	if not function:
		listeners = [name.replace(".json", "") for name in os.listdir(lystener.JSON) if name.endswith(".json")]
		function = lystener.chooseItem("Select listener to destroy:", *listeners)
		if not function: return

	json_name = "%s.json" % function
	# load webhook configuration
	webhook = lystener.loadJson(json_name)
	# condition bellow checks if webhook configurations is found
	if webhook.get("peer", False):
		# delete webhook usong its id and parent peer
		rest.DELETE.api.webhooks("%s"%webhook["id"], peer=webhook["peer"])
		# delete the webhook configuration
		os.remove(os.path.join(lystener.JSON, json_name))
		# cursor.execute("SELECT FROM history WHERE autorization = ?", (webhook["token"][:32],)).fetchall()
		lystener.logMsg("%s webhook destroyed" % function)
	else:
		lystener.logMsg("%s webhook not found" % function)

	# sqlite.commit()
	# sqlite.close()


# command line execution
########################
if __name__ == "__main__":

	FILTER = {
		"--condition": lambda value: value,
		"--field":     lambda value: value,
		"--listener":  lambda value: value,
		"--value":     lambda value: value,
		"--webhook":   lambda value: value,
		"<regexp>":    lambda value: getattr(value, "pattern", value)
	}

	# will get the first argument which is neither a value neither an option
	def getAction(args):
		for action in [k for k in args if k[0] not in ["-", "<"]]:
			if args[action] == True:
				return action
		return False

	# will rename --multi-word-option to multi_word_option
	def getOptions(args):
		options = {}
		for option,value in [(k,v) for k,v in args.items() if k.startswith("--") and v != None]:
			options[option[2:].replace("-", "_")] = value
		return dict((k,v) for k,v in options.items() if v != None)

	# see http://docopt.org
	args = docopt.docopt(__doc__, argv=sys.argv[1:])
	for key,cast in [(k,c) for k,c in FILTER.items() if k in args]:
		args[key] = cast(args[key])

	action = getAction(args)
	options = getOptions(args)

	if action:
		# rename multi-word-action to multi_word_action
		func = getattr(sys.modules[__name__], action.replace("-", "_"))
		if callable(func):
			func(args, **options)
