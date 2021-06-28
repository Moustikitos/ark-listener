# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import base64
import lystener
from lystener import loadJson, rest


def freemobile_sendmsg(title, body):
    freemobile = loadJson("freemobile.notify", lystener.DATA)
    if freemobile != {}:
        freemobile["msg"] = title + ":\n" + body
        return rest.POST.sendmsg(
            peer="https://smsapi.free-mobile.fr",
            jsonify=freemobile
        )


def pushbullet_pushes(title, body):
    pushbullet = loadJson("pushbullet.notify", lystener.DATA)
    if pushbullet != {}:
        return rest.POST.v2.pushes(
            peer="https://api.pushbullet.com",
            body=body, title=title, type="note",
            headers={
                'Access-Token': pushbullet["token"],
            }
        )


def pushover_messages(title, body):
    pushover = loadJson("pushover.notify", lystener.DATA)
    if pushover != {}:
        return rest.POST(
            "1", "messages.json",
            peer="https://api.pushover.net",
            urlencode=dict(
                message=body,
                title=title,
                **pushover
            )
        )


def twilio_messages(title, body):
    twilio = loadJson("twilio.notify", lystener.DATA)
    if twilio != {}:
        authentication = base64.b64encode(
            ("%s:%s" % (twilio["sid"], twilio["auth"])).encode('utf-8')
        )
        return rest.POST(
            "2010-04-01", "Accounts", twilio["sid"], "Messages.json",
            peer="https://api.twilio.com",
            urlencode={
                "From": twilio["sender"],
                "To": twilio["receiver"],
                "Body": body,
            },
            headers={
                "Authorization": "Basic %s" % authentication.decode('ascii')
            }
        )


def send(title, body):
    title = title.decode("utf-8") if isinstance(title, bytes) else title
    body = body.decode("utf-8") if isinstance(body, bytes) else body

    for func in [
        freemobile_sendmsg,
        pushbullet_pushes,
        pushover_messages,
        twilio_messages
    ]:
        response = func(title, body)
        if isinstance(response, dict):
            lystener.logMsg("notification response:\n%s" % response)
            if response.get("status", 1000) < 300:
                return response
