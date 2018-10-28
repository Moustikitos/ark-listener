# -*- encoding:utf-8 -*-

import json
import requests
import sys


def executeInsurancePolicy(data):

	head, namespace, endpoint, assetId = data["vendorField"].split(':')

	body = {
		"policy": "resource:io.arklabs.InsurancePolicy#" + assetId,
		"amountPaid": int(data["amount"]),
		"arkTransaction": data,
		"$class": "io.arklabs." + endpoint
	}

	headers = {
          "Content-Type": "application/json",
	}

	# POST body to http://159.89.146.143:3000/api/endpoint using requests
	try: 
		sys.stdout.write('Sending content to %s: %s\n' % (
			"http://159.89.146.143:3000/api/"+endpoint,
			json.dumps(body, indent=2)
		))
		result = requests.post(
			"http://159.89.146.143:3000/api/"+endpoint,
			data=json.dumps(body),
			headers=headers,
			verify=True
		)
		msg = json.dumps(result.json(), indent=2)
		sys.stdout.write('>>> Transaction sent to hyperledger...\n')
	except Exception as error:
		msg = "%r" % error
	sys.stdout.flush()
	
	return msg
