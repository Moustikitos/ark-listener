# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import json
from lystener import task


def logSomething(data):
    task.MessageLogger.JOB.put(
        'data received :\n%s' % json.dumps(data, indent=2)
    )
    return {"success": True}
