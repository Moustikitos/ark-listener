# -*- coding: utf-8 -*-
# © THOORENS Bruno

import socket
import lystener

from usrv import req


GET = req.GET
POST = req.POST
PUT = req.PUT
DELETE = req.DELETE


def getPublicIp():
    """Store the public ip of server in PUBLIC_IP global var"""
    global PUBLIC_IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        PUBLIC_IP = s.getsockname()[0]
    except Exception:
        PUBLIC_IP = '127.0.0.1'
    finally:
        s.close()
    return PUBLIC_IP


PUBLIC_IP = GET.plain(
    peer="https://www.ipecho.net"
).get("raw", getPublicIp())


# default peer configuration
LISTENER_PEER = {"scheme": "http", "ip": PUBLIC_IP, "port": 5001}
WEBHOOK_PEER = {"scheme": "http", "ip": "127.0.0.1", "port": 4004}

# generate defaults peers
peers = lystener.loadJson("peer.json", folder=lystener.ROOT)
LISTENER_PEER.update(peers.get("listener", {}))
WEBHOOK_PEER.update(peers.get("webhook", {}))

# dump peer.json on first import
lystener.dumpJson(
    {"listener": LISTENER_PEER, "webhook": WEBHOOK_PEER},
    "peer.json",
    folder=lystener.ROOT
)

req.EndPoint.peer = "%(scheme)s://%(ip)s:%(port)s" % WEBHOOK_PEER
