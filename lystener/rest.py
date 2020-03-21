# -*- coding: utf-8 -*-
# © Toons

import re
import json
import lystener

if lystener.PY3:
    from urllib.request import Request, OpenerDirector, HTTPHandler
    from urllib.request import HTTPSHandler, BaseHandler
    from urllib.parse import urlencode
else:
    from urllib2 import Request, OpenerDirector, HTTPHandler, HTTPSHandler
    from urllib2 import BaseHandler
    from urllib import urlencode


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

# global var used by REST requests
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 7


class EndPoint(object):

    opener = None

    def __init__(self, elem=None, parent=None, method=lambda: None):
        self.elem = elem
        self.parent = parent
        self.method = method

        if EndPoint.opener is None:
            EndPoint.opener = OpenerDirector()
            for handler in [HTTPHandler, HTTPSHandler]:
                EndPoint.opener.add_handler(handler())

    def add_handler(self, handler):
        if not isinstance(handler, BaseHandler):
            raise Exception(
                "%r have to be a %r instance" % (handler, BaseHandler)
            )
        if not isinstance(EndPoint.opener, OpenerDirector):
            EndPoint.opener = OpenerDirector()
        EndPoint.opener.add_handler(handler)

    @staticmethod
    def _manage_response(res, error=None):
        text = res.read()
        try:
            data = json.loads(text)
        except Exception as err:
            data = {
                "success": True, "except": True,
                "raw": text, "error": "%r" % err
            }
        return data

    @staticmethod
    def _call(method="GET", *args, **kwargs):
        method = method.upper()
        headers = kwargs.pop("headers", dict(HEADERS))
        data = kwargs.pop("urlencode", None)
        # build request
        url = \
            kwargs.pop('peer', "%(scheme)s://%(ip)s:%(port)s" % WEBHOOK_PEER) \
            + "/".join(args)
        if method == "GET":
            if len(kwargs):
                url += "?" + urlencode(kwargs)
            req = Request(url, data, headers)
        else:
            if data is None:
                data = json.dumps(kwargs)
                headers["Content-type"] = "application/json"
            else:
                data = urlencode(data)
                headers["Content-type"] = "application/x-www-form-urlencoded"
            req = Request(url, data.encode('utf-8'), headers)
        # tweak request
        req.add_header("User-agent", "Mozilla/5.0")
        req.get_method = lambda: method
        # send request
        try:
            res = EndPoint.opener.open(req, timeout=TIMEOUT)
        except Exception as error:
            return {"success": False, "error": "%r" % error, "except": True}
        else:
            return EndPoint._manage_response(res)

    def __getattr__(self, attr):
        startswith_ = re.compile(r"^_[0-9A-Fa-f].*")
        if attr not in ["elem", "parent", "method", "chain"]:
            if startswith_.match(attr):
                attr = attr[1:]
            return EndPoint(attr, self, self.method)
        else:
            return object.__getattr__(self, attr)

    def __call__(self, *args, **kwargs):
        return self.method(*self.chain()+list(args), **kwargs)

    def chain(self):
        return (self.parent.chain() + [self.elem]) if self.parent is not None \
               else [""]


GET = EndPoint(method=lambda *a, **kw: EndPoint._call("GET", *a, **kw))
POST = EndPoint(method=lambda *a, **kw: EndPoint._call("POST", *a, **kw))
PUT = EndPoint(method=lambda *a, **kw: EndPoint._call("PUT", *a, **kw))
DELETE = EndPoint(method=lambda *a, **kw: EndPoint._call("DELETE", *a, **kw))
