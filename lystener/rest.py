# -*- coding: utf-8 -*-
# © Toons

"""
>>> from lystener import rest
>>> # 'http://127.0.0.1:4002/api/delegates/get?username=arky'
>>> rest.GET.api.delegates.get(username="arky")
{'success': True, 'delegate': {'vote': '142348239372385', 'producedblocks': 107\
856, 'productivity': 98.63, 'address': 'ARfDVWZ7Zwkox3ZXtMQQY1HYSANMB88vWE', 'r\
ate': 42, 'publicKey': '030da05984d579395ce276c0dd6ca0a60140a3c3d964423a04e7abe\
110d60a15e9', 'approval': 1.05, 'username': 'arky', 'missedblocks': 1499}}

>>> # 'http://explorer.ark.io:8443/api/delegates/get?username=arky'
>>> rest.GET.api.delegates.get(peer="http://explorer.ark.io:8443", username="arky")
{'success': True, 'delegate': {'vote': '142348239372385', 'producedblocks': 107\
856, 'productivity': 98.63, 'address': 'ARfDVWZ7Zwkox3ZXtMQQY1HYSANMB88vWE', 'r\
ate': 42, 'publicKey': '030da05984d579395ce276c0dd6ca0a60140a3c3d964423a04e7abe\
110d60a15e9', 'approval': 1.05, 'username': 'arky', 'missedblocks': 1499}}

>>> # 'http://127.0.0.1:4004/api/webhooks/1 # need underscore if path element starts with a number
>>> rest.GET.api.webhooks._1(peer="http://127.0.0.1:4004").get("data")
{'data': [{'target': 'http://127.0.0.1:5000/block/forged', 'enabled': True, 'ev\
ent': 'block.forged', 'token': '61a4c809726a408702198d83c16c2d34', 'conditions'\
: [{'key': 'generatorPublicKey', 'condition': 'eq', 'value': '03a02b9d5fdd1307c\
2ee4652ba54d492d1fd11a7d1bb3f3a44c4a05e79f19de933'}], 'id': 1}]}
"""

import re
import json
import requests
import lystener

# default peer configuration
LISTENER_PEER = {"protocol": "http", "ip": "127.0.0.1", "port": 5001}
WEBHOOK_PEER = {"protocol": "http", "ip": "127.0.0.1", "port": 4004}
# global var used by REST requests
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 7

# generate defaults peers
peers = lystener.loadJson("peer.json", folder=lystener.__path__[0])
LISTENER_PEER.update(peers.get("listener", {}))
WEBHOOK_PEER.update(peers.get("webhook", {}))
# dump peer.json on first import
lystener.dumpJson(
	{"listener":LISTENER_PEER, "webhook":WEBHOOK_PEER},
	"peer.json",
	folder=lystener.__path__[0]
)


class EndPoint(object):

	@staticmethod
	def _manageResponse(req):
		try:
			return req.json()
		except:
			return req.text

	@staticmethod
	def _GET(*args, **kwargs):
		peer = kwargs.pop('peer', "%(protocol)s://%(ip)s:%(port)s" % LISTENER_PEER)
		try:
			req = requests.get(
				peer + "/".join(args),
				params=dict([k.replace('and_', 'AND:'), v] for k,v in kwargs.items()),
				headers=HEADERS,
				timeout=TIMEOUT,
				verify=True
			)
			data = EndPoint._manageResponse(req)
		except Exception as error:
			data = {"success": False, "error": error}
		return data

	@staticmethod
	def _POST(*args, **kwargs):
		peer = kwargs.pop('peer', "%(protocol)s://%(ip)s:%(port)s" % LISTENER_PEER)
		try:
			req = requests.post(
				peer + "/".join(args),
				data=json.dumps(kwargs),
				headers=HEADERS,
				timeout=TIMEOUT,
				verify=True
			)
			data = EndPoint._manageResponse(req)
		except Exception as error:
			data = {"success": False, "error": error}
		return data

	@staticmethod
	def _PUT(*args, **kwargs):
		peer = kwargs.pop('peer', "%(protocol)s://%(ip)s:%(port)s" % LISTENER_PEER)
		try:
			req = requests.put(
				peer + "/".join(args),
				data=json.dumps(kwargs),
				headers=HEADERS,
				timeout=TIMEOUT,
				verify=True
			)
			data = EndPoint._manageResponse(req)
		except Exception as error:
			data = {"success": False, "error": error}
		return data

	@staticmethod
	def _DELETE(*args, **kwargs):
		peer = kwargs.pop('peer', "%(protocol)s://%(ip)s:%(port)s" % LISTENER_PEER)
		try:
			req = requests.delete(
				peer + "/".join(args),
				data=json.dumps(kwargs),
				headers=HEADERS,
				timeout=TIMEOUT,
				verify=True
			)
			data = EndPoint._manageResponse(req)
		except Exception as error:
			data = {"success": False, "error": error}
		return data

	def __init__(self, elem=None, parent=None, method=None):
		if method not in [EndPoint._GET, EndPoint._POST, EndPoint._PUT, EndPoint._DELETE]:
			raise Exception("REST method %s not implemented" % method)
		self.elem = elem
		self.parent = parent
		self.method = method

	def __getattr__(self, attr):
		startswith_ = re.compile(r"^_[0-9A-Fa-f].*")
		if attr not in ["elem", "parent", "method", "chain"]:
			if startswith_.match(attr):
				attr = attr[1:]
			return EndPoint(attr, self, self.method)
		else:
			return object.__getattr__(self, attr)

	def __call__(self, *args, **kwargs):
		return self.method(*self.chain()+list(args), **kwargs)

	def chain(self):
		return (self.parent.chain() + [self.elem]) if self.parent!=None else [""]


GET = EndPoint(method=EndPoint._GET)
POST = EndPoint(method=EndPoint._POST)
PUT = EndPoint(method=EndPoint._PUT)
DELETE = EndPoint(method=EndPoint._DELETE)
