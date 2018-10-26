# -*- encoding:utf-8 -*-
import json
from lystener import rest, logMsg


def executeInsurancePolicy(data):

	params = data["vendorField"].split(':')
	endpoint = params[2]
	assetId = params[3]
	body = {
		"policy": "resource:io.arklabs.InsurancePolicy#" + assetId,
		"amountPaid": data["amount"],
		"arkTransaction": json.dumps(data, indent=5),
		"$class": "io.arklabs." + endpoint
	}

	# POST body to http://159.89.146.143:3000/api/endpoint using rest:
	result = rest.POST.api(endpoint, peer="http://159.89.146.143:3000", **body)
	if result.status == 200:
		logMsg('Transaction sent to hyperledger : ["SUCCESS"]')
	else:
		logMsg('Transaction sent to hyperledger : ["FAIL"]')

	try: msg = json.dumps(result.json(), indent=2)
	except: msg = result.text
	else: msg = "executeInsurancePolicy finished"
	return msg
