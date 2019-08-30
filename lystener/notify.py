import os

import lystener
from lystener import loadJson, rest


def send(title, body):
	pushover = loadJson("pushover.notify", lystener.DATA)
	if pushover != {}:
		pushover["body"] = body
		pushover["title"] = title
		os.system('''
curl -s -F "token=%(token)s" \
	-F "user=%(user)s" \
	-F "title=%(title)s" \
	-F "message=%(body)s" \
	--silent --output /dev/null \
	https://api.pushover.net/1/messages.json
''' % pushover)

	pushbullet = loadJson("pushbullet.notify", lystener.DATA)
	if pushbullet != {}:
		pushbullet["body"] = body
		pushbullet["title"] = title
		os.system('''
curl --header 'Access-Token: %(token)s' \
	--header 'Content-Type: application/json' \
	--data-binary '{"body":"%(body)s","title":"a%(title)s","type":"note"}' \
	--request POST \
	--silent --output /dev/null \
	https://api.pushbullet.com/v2/pushes
''' % pushbullet)

	twilio = loadJson("twilio.notify", lystener.DATA)
	if twilio != {}:
		twilio["body"] = body
		os.system('''
curl -X "POST" "https://api.twilio.com/2010-04-01/Accounts/%(sid)s/Messages.json" \
	--data-urlencode "From=%(sender)s" \
	--data-urlencode "Body=%(body)s" \
	--data-urlencode "To=%(receiver)s" \
	--silent --output /dev/null \
	-u "%(sid)s:%(auth)s"
''' % twilio)

	freemobile = loadJson("freemobile.notify", lystener.DATA)
	if freemobile != {}:
		freemobile["msg"] = title + ":\n" + body
		rest.GET.sendmsg(peer="https://smsapi.free-mobile.fr", **freemobile)
