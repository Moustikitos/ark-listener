# -*- encoding:utf-8 -*-

import json
import requests
import sys


def executeInsurancePolicy(data):

	head, namespace, endpoint, assetId = data["vendorField"].split(':')

	body = {
		"policy": "resource:io.arklabs.InsurancePolicy#" + assetId,
		"amountPaid": data["amount"],
		"arkTransaction": json.dumps(data, indent=5),
		"$class": "io.arklabs." + endpoint
	}

	headers = {
          "Content-Type": "application/json",
          "os": "linux3.2.0-4-amd64",
          "version": "0.3.0",
          "port": "3000"
	}

	# POST body to http://159.89.146.143:3000/api/endpoint using requests
	result = requests.post(
		"http://159.89.146.143:3000/api/"+endpoint,
		data=json.dumps(body),
		headers=headers,
		verify=True
	)

	try: msg = json.dumps(result.json(), indent=2)
	except: msg = result
	sys.stdout.write('>>> Transaction sent to hyperledger...\n')
	sys.stdout.flush()
	
	return msg
