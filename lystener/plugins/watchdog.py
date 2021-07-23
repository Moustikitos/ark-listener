# -*- encoding:utf-8 -*-

"""
[requirements]
base58
"""

import json
import base58
import hashlib
import binascii
import lystener

from lystener import task, loadJson, notify


def getAddress(publicKey, marker):
    """
    Compute ARK address from publicKey.

    Args:
        publicKey (str): public key
        marker (int): network marker (optional)
    Returns:
        the address
    """
    b58 = base58.b58encode_check(
        binascii.unhexlify(hex(marker)[2:]) +
        hashlib.new(
            'ripemd160', binascii.unhexlify(publicKey)
        ).digest()[:20]
    )
    return b58.decode('utf-8') if isinstance(b58, bytes) else b58


def notifyWhaleMove(data):
    task.MessageLogger.log('data received :\n%s' % json.dumps(data, indent=2))
    params = loadJson("notifyWhaleMove.param", folder=lystener.DATA)

    sender = getAddress(data["senderPublicKey"], data["network"])
    receiver = data["recipientId"]
    task.MessageLogger.log('Big move from %s to %s!' % (sender, receiver))

    for exchange, wallets in params["hot wallets"].items():
        task.MessageLogger.log(
            '    checking %s wallets : %s...' % (exchange, wallets)
        )
        if receiver in wallets:
            task.FunctionCaller.call(
                notify.send,
                "Whale alert",
                "%s sent %.2f token to %s" %
                (sender, float(data["amount"])/100000000, exchange)
            )
            return {"success": True}
        elif sender in wallets:
            task.FunctionCaller.call(
                notify.send,
                "Whale alert",
                "%s sent %.2f token to %s" %
                (exchange, float(data["amount"])/100000000, receiver)
            )
            return {"success": True}

    return {"success": False, "response": "Nothing hapen !"}
