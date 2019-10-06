# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import json
from lystener import logMsg


def logSomething(data):
	logMsg('data received :\n%s' % json.dumps(data, indent=2))
	return json.dumps({"success": True})
