# -*- encoding:utf-8 -*-

from lystener import rest, logMsg


def executeInsurancePolicy(data):
	
	params = data["vendorField"].split(':')
	endpoint = params[2]
	assetId = params[3]
	body = dict(
		policy = "resource:io.arklabs.InsurancePolicy#" + assetId,
		amountPaid = data["amount"],
		arkTransaction = json.dumps(data, indent=5),
		**{"$class": "io.arklabs." + endpoint}
	)

	req = rest.POST.api(endpoint, peer="http://159.89.146.143:3000", **body)
	if req.status == 200:
		logMsg('Transaction sent to hyperledger : ["SUCCESS"]')
	else:
		logMsg('Transaction sent to hyperledger : ["FAIL"]')

	return req.json()
