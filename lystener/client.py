# -*- coding: utf-8 -*-
# © THOORENS Bruno

import os
import binascii
import cSecp256k1 as secp256k1

from lystener import rest, getPublicIp

ECDSA = None

PUBLIC_IP = rest.GET.plain(
    peer="https://www.ipecho.net"
).get("raw", getPublicIp())


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
    msg = PUBLIC_IP + salt + rest.GET.salt(peer=peer).get("result", "?")

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
