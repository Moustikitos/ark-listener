# -*- encoding:utf-8 -*-
# (c) THOORENS Bruno

import future
import hashlib

from builtins import int


def createBase(secret, encoding="utf-8"):
	secret = secret if isinstance(secret, bytes) else secret.encode(encoding)
	unused = list(range(256))
	result = bytearray()
	while len(result) < 255:
		result.append(unused.pop(i%len(unused)) for i in hashlib.sha512(secret).digest())
		secret = result[:]
	return result


def encrypt(msg, base, encoding="utf-8", salt_size=256):
	msg = msg if isinstance(msg, bytes) else msg.encode(encoding, "replace")
	result = bytearray()
	n = len(base)
	for i in bytearray(msg):
		a = int.from_bytes(result[-salt_size:], "big")
		result.append(base[(i+a)%n])
	return result


def decrypt(encrypted, base, encoding="utf-8", salt_size=256):
	result = bytearray()
	base = list(base)
	n = len(base)
	for e in encrypted:
		a = int.from_bytes(encrypted[:len(result)][-salt_size:], "big")
		result.append((base.index(e)-a)%n)
	return result.decode(encoding, "replace")
