__requirement__ = [
	"dposlib"
]
__json__ = "%s.param" % os.path.basename(__name__)

import os
import json
import getpass

import lystener
import dposlib
from dposlib import rest
from lystener import loadJson, notify

rest.use("ark")

KEYS = {}
SECOND_KEYS = {}

def loadKeys(username, params):
	params = loadJson(__json__, folder=lystener.DATA)
	secret = parameters.pop("secret", False)
	secondSecret = parameters.pop("secondSecret", False)
	dumpJson(params, __json__, folder=lystener.DATA)		

	try:
		INFO = rest.GET.api.delegates.__getattr__(username)()["data"]
		while KEYS.get("publicKey", None) != INFO["publicKey"]:
			KEYS = dposlib.core.crypto.getKeys(secret)
		while SECOND_KEYS.get("publicKey", None) != INFO.get("secondPublicKey", None):
			SECOND_KEYS = dposlib.core.crypto.getKeys(secondSecret)
	except KeyboardInterrupt:
		raise Exception("'%s' plugin initialization failed" % os.path.basename(__file__))
	else:
		dposlib.core.Transaction._publicKey = KEYS["publicKey"]
		dposlib.core.Transaction._privateKey = KEYS["privateKey"]
		dposlib.core.Transaction._secondPublicKey = SECOND_KEYS.get("publicKey", None)
		dposlib.core.Transaction._secondPrivateKey = SECOND_KEYS.get("privateKey", None)


def voteRefund(data):
	params = loadJson(__json__, folder=lystener.DATA)		
	voter_address = dposlib.core.crypto.getAddress(data["senderPublicKey"])
	vote = data["asset"]["votes"][0]
	sign, vote = vote[0], vote[1:]
	
	if vote == INFO["publicKey"]:
		if sign == "+":
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
		else:
			response = {}

		notify.send("Vote notification", "%(address)s %(action)s %(delegate)s\n%(weight)s ark weight" % {
			"address": voter_address,
			"action": "upvoted" if sign == "+" else "downvoted",
			"delegate": INFO["username"],
			"weight": rest.GET.api.wallets.__getattr__(voter_address)(returnKey="data")["balance"]
		})
		return json.dumps(refund)

		#return json.dumps(response)
