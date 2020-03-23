# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import base64
import lystener
from lystener import loadJson, rest


def freemobile_sendmsg(title, body):
    freemobile = loadJson("freemobile.notify", lystener.DATA)
    if freemobile != {}:
        return rest.GET.sendmsg(
            peer="https://smsapi.free-mobile.fr",
            msg=title + b":\n" + body,
            **freemobile
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
    title = title.encode("utf-8") if not isinstance(title, bytes) else title
    body = body.encode("utf-8") if not isinstance(body, bytes) else body

    for func in [
        freemobile_sendmsg,
        pushbullet_pushes,
        pushover_messages,
        twilio_messages
    ]:
        response = func(title, body)
        if response is not None:
            return response


# slack notification
# https://api.slack.com/methods/chat.postMessage
