# -*- coding: utf-8 -*-
# © Toons

import os
import hashlib
import getpass
import binascii

from lystener import rest, secp256k1
from lystener.server import jsonHash
from lystener.secp256k1 import ecdsa, schnorr

PRIVKEY = None


def link(secret=None):
    global PRIVKEY
    if secret is None:
        secret = getpass.getpass(prompt="Type or paste your secret> ")
    PRIVKEY = binascii.hexlify(
        secp256k1.hash_sha256(
            secret if isinstance(secret, bytes) else secret.encode("utf-8")
        )
    )


def unlink():
    global PRIVKEY
    PRIVKEY = None


def schnorr_sign(msg, privateKey):
    msg = hashlib.sha256(msg.encode("utf-8")).digest()
    return binascii.hexlify(
        schnorr.sign(msg, binascii.unhexlify(privateKey))
    )


def ecdsa_sign(msg, privateKey):
    msg = hashlib.sha256(msg.encode("utf-8")).digest()
    return binascii.hexlify(
        ecdsa.sign(msg, binascii.unhexlify(privateKey))
    )


def create_header(privateKey, payload, method="ecdsa"):
    salt = binascii.hexlify(os.urandom(32))
    salt = salt.decode("utf-8") if isinstance(salt, bytes) else salt

    msg = (jsonHash(payload) + salt + rest.GET.salt().get("salt", "?"))

    headers = {"Salt": salt}
    publicKey = secp256k1.PublicKey.from_seed(binascii.unhexlify(privateKey))
    headers["Public-key"] = binascii.hexlify(
        secp256k1.encoded_from_point(publicKey)
    )

    if method == "ecdsa":
        headers["Ecdsa-sig"] = ecdsa_sign(msg, privateKey)
    elif method == "schnorr":
        headers["Schnorr-sig"] = schnorr_sign(msg, privateKey)
    return headers


def secp256k1_filter(**kwargs):
    privateKey = kwargs.pop("privateKey", PRIVKEY)
    headers = kwargs.pop("headers", {"Content-type": "application/json"})
    method = kwargs.pop("method", "ecdsa")
    to_jsonify = kwargs.pop("jsonify", None)

    if privateKey is not None:
        if to_jsonify is not None:
            headers.update(**create_header(privateKey, to_jsonify, method))
        else:
            headers.update(**create_header(privateKey, kwargs, method))
        kwargs["headers"] = headers

    return kwargs


PUT = rest.EndPoint(
    method=lambda *a, **kw:
        rest.EndPoint._call("PUT", *a, **secp256k1_filter(**kw))
)
DELETE = rest.EndPoint(
    method=lambda *a, **kw:
        rest.EndPoint._call("DELETE", *a, **secp256k1_filter(**kw))
)
