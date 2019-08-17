import json
from lystener import logMsg

def logSomething(data):
	logMsg('Data received :\n%s' % json.dumps(data, indent=2))
	return json.dumps({"success": True})
