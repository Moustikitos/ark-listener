__requirement__ = [
	"dposlib"
]

import os
import json

import lystener
import dposlib
from dposlib import rest
from lystener import loadJson

rest.use("ark")


def _notify(title, body):
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


def voteRefund(data):
	params = loadJson("voteRefund.param", folder=lystener.DATA)
	if not len(params):
		return json.dumps({"success": False, "message": "Not enough info to proceed"})

	voter_address = dposlib.core.crypto.getAddress(data["senderPublicKey"])
	dposlib.core.Transaction._publicKey = params["publicKey"]
	dposlib.core.Transaction._privateKey = params["privateKey"]
	if "secondPrivateKey" in params:
		dposlib.core.Transaction._secondPrivateKey = params["secondPrivateKey"]

	# create a refund transaction
	refund = dposlib.core.Transaction(
		type = 0,
		amount = data["fee"],
		recipientId = voter_address,
		vendorField = params.get("vendorField", "Thanks ! Here is vote fee refund")
	)
	refund.useDynamicFee(params.get("feeLevel", "minFee"))
	refund.finalize()
	# response = dposlib.core.api.broadcastTransactions(refund)

	vote = data["asset"]["votes"][0]
	_notify("Vote notification", "%(address)s %(action)s %(delegate)s\n%(weight)s ark weight" % {
		"address": voter_address,
		"action": "upvoted" if vote[0] == "+" else "downvoted",
		"delegate": rest.GET.api.wallets.__getattr__(vote[1:])(returnKey="data")["username"],
		"weight": rest.GET.api.wallets.__getattr__(voter_address)(returnKey="data")["balance"]
	})
	return json.dumps(refund)

	#return json.dumps(response)
