import os
import struct
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

backend = default_backend()


def _derive_key(password, salt, iterations=100000):
	"""Derive a secret key from a given password and salt"""
	password = password if isinstance(password, bytes) else password.encode("utf-8")
	salt = salt if isinstance(salt, bytes) else salt.encode("utf-8")
	kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations, backend=backend)
	result = b64e(kdf.derive(password))
	return result if isinstance(result, bytes) else result.encode()


def encode(message, password, iterations=100000):
	message = message if isinstance(message, bytes) else message.encode("utf-8")
	salt = os.urandom(16)
	key = _derive_key(password, salt, iterations)
	return b64e(salt + struct.pack(">I", iterations) + b64d(Fernet(key).encrypt(message)))


def decode(token, password):
	password = password if isinstance(password, bytes) else password.encode("utf-8")
	decoded = b64d(token)
	salt, iter_, token = decoded[:16], decoded[16:20], b64e(decoded[20:])
	iterations = struct.unpack(">I", iter_)[0]
	key = _derive_key(password, salt, iterations)
	result = Fernet(key).decrypt(token)
	return result.decode("utf-8") if isinstance(result, bytes) else result
