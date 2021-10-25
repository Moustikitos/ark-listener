# -*- coding: utf-8 -*-
# © THOORENS Bruno

import os
import hashlib
import binascii
import traceback
import cSecp256k1 as secp256k1

from lystener import task, rest, dumpJson, logMsg

ECDSA = None


def link(secret=None):
    global ECDSA
    ECDSA = secp256k1.Ecdsa(secret)


def unlink():
    global ECDSA
    ECDSA = None


def create_header(peer=None):
    global ECDSA
    salt = binascii.hexlify(os.urandom(32))
    salt = salt.decode("utf-8") if isinstance(salt, bytes) else salt
    msg = salt + rest.GET.salt(peer=peer).get("result", "?")
    return {
        "Salt": salt,
        "Public-Key": ECDSA.puk().encode().decode("utf-8"),
        "Signature": ECDSA.sign(msg).der().decode("utf-8")
    }


def secp256k1_filter(**kwargs):
    global ECDSA
    headers = kwargs.pop("headers", {"Content-type": "application/json"})
    peer = kwargs.get("peer", None)
    if ECDSA is not None:
        headers.update(**create_header(peer))
        kwargs["headers"] = headers
    return kwargs


POST = rest.req.EndPoint(
    method=lambda *a, **kw:
        rest.req.EndPoint._call("POST", *a, **secp256k1_filter(**kw))
)
PUT = rest.req.EndPoint(
    method=lambda *a, **kw:
        rest.req.EndPoint._call("PUT", *a, **secp256k1_filter(**kw))
)
DELETE = rest.req.EndPoint(
    method=lambda *a, **kw:
        rest.req.EndPoint._call("DELETE", *a, **secp256k1_filter(**kw))
)


def deploy_listener(args={}, **options):
    """
    link blockchain event to a python function.
    """

    function = args.get("<function>", options.get("function", ""))
    regexp = args.get("<regexp>", options.get("regexp", None))
    event = args.get("<event>", options.get("event", "null"))

    target_url = \
        ("%(scheme)s://%(ip)s%(port)s" % rest.LISTENER_PEER) + \
        "/" + function.replace(".", "/")

    # compute listener condition
    # if only a regexp is givent compute condition on vendorField
    if regexp is not None:
        conditions = [{
            "key": "vendorField",
            "condition": "regexp",
            "value": regexp
        }]
    # else create a condition.
    # Ark webhook api will manage condition errors
    else:
        conditions = list(
            {"key": k, "condition": c, "value": v} for k, c, v in zip(
                args.get("<field>", options.get("field", [])),
                args.get("<condition>", options.get("condition", [])),
                args.get("<value>", options.get("value", []))
            )
        )

    # check if remotly called
    remotly = options.get("remote", False)
    if remotly:
        _POST = POST
        target_peer = options.get("peer", "http://127.0.0.1")
        link()
    else:
        _POST = rest.POST
        target_peer = args.get(
            "<node>", options.get("node", rest.req.EndPoint.peer)
        )

    # create the webhook
    req = _POST.api.webhooks(
        event=event,
        peer=target_peer,
        target=target_url,
        conditions=conditions
    )

    # parse request result if no error messages
    try:
        if req.get("status", req.get("statusCode", 500)) < 300:
            webhook = req["data"]
            # save the used peer to be able to delete it later
            webhook["peer"] = target_peer
            # build the security hash and keep only second token part
            webhook["hash"] = hashlib.sha256(
                webhook["token"].encode("utf-8")
            ).hexdigest()
            # create a unique name based on first token part and module.name
            # so when a content is received, authorisation in POST header can
            # be used with module and name mentioned in the url
            webhook_name = task.webhookName(
                webhook["token"][:32], *function.split(".")
            )
            logMsg("token: %s" % webhook["token"])
            webhook["token"] = webhook["token"][32:]
            dumpJson(webhook, webhook_name)
            logMsg("%s webhook set" % function)
        else:
            logMsg("%s webhook not set:\n%r" % (function, req))
    except Exception as error:
        logMsg("%s" % req)
        logMsg("%r\n%s" % (error, traceback.format_exc()))
