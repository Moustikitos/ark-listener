# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import lystener
from lystener import loadJson, task
from usrv import notify


def send(title, body):
    title = title.decode("utf-8") if isinstance(title, bytes) else title
    body = body.decode("utf-8") if isinstance(body, bytes) else body

    for func in [
        notify.freemobile_sendmsg,
        notify.pushbullet_pushes,
        notify.pushover_messages,
        notify.twilio_messages,
    ]:
        response = func(
            title, body,
            **loadJson(f"{func.__name__.split('_')[0]}.notify", lystener.DATA)
        )
        if isinstance(response, dict):
            if response.get("status", 1000) < 300:
                task.MessageLogger.log(
                    "%s notice:\n[%s]\n%s" % (func, title, body)
                )
                return response
    return {"msg": "nothing seems to be sent correctly"}
