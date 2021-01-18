# -*- coding: utf-8 -*-
# © THOORENS Bruno

import lystener

from usrv import req

GET = req.GET
POST = req.POST
PUT = req.PUT
DELETE = req.DELETE

# default peer configuration
LISTENER_PEER = {"scheme": "http", "ip": lystener.getPublicIp(), "port": 5001}
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
