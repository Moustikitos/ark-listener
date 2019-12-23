# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import sys
import future
import hashlib

from builtins import int


int_from_bytes = \
    (lambda i: int.from_bytes(i)) if sys.version_info[0] < 3 else \
    (lambda i: int(i))


def createBase(secret, encoding="utf-8"):
    secret = secret if isinstance(secret, bytes) else secret.encode(encoding)
    unused = list(range(256))
    result = bytearray()

    while len(result) < 255:
        result += bytearray(
            [
                unused.pop(int_from_bytes(i) % len(unused))
                for i in hashlib.sha512(secret).digest()
            ]
        )
        secret = result[:]
    return result


def encrypt(msg, base, encoding="utf-8"):
    msg = msg if isinstance(msg, bytes) else msg.encode(encoding, "replace")
    encrypted = bytearray()
    n = len(base)
    for i in bytearray(msg):
        a = int.from_bytes(hashlib.md5(encrypted).digest(), "big")
        encrypted.append(base[(int_from_bytes(i)+a) % n])
        if a % 5:
            encrypted.append(a % n)
    return encrypted


def decrypt(encrypted, base, encoding="utf-8"):
    msg, _enc = bytearray(), bytearray()
    base = list(base)
    n = len(base)
    jump = False
    for e in encrypted:
        if jump:
            _enc.append(e)
            jump = False
        else:
            a = int.from_bytes(hashlib.md5(_enc).digest(), "big")
            msg.append((base.index(int_from_bytes(e))-a) % n)
            _enc.append(e)
            if a % 5:
                jump = True
    return msg.decode(encoding, "replace")


# https://fr.m.wikipedia.org/wiki/Indice_de_co%C3%AFncidence
from collections import Counter
import functools

def computeIc(encrypted):
    n = len(encrypted)
    d = n*(n-1)
    result = 0
    for v in Counter(list(encrypted)).values():
        result += v*(v-1)/d
    return result
