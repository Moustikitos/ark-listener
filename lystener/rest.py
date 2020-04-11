# -*- coding: utf-8 -*-
# © THOORENS Bruno

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


def connect(peer):
    return EndPoint.connect(peer)


class EndPoint(object):

    timeout = 5
    opener = None
    peer = "%(scheme)s://%(ip)s:%(port)s" % WEBHOOK_PEER
    startswith_ = re.compile(r"^_[0-9A-Fa-f].*")

    def __init__(self, elem=None, parent=None, method=lambda: None):
        self.elem = elem
        self.parent = parent
        self.method = method

        if EndPoint.opener is None:
            EndPoint.opener = OpenerDirector()
            for handler in [HTTPHandler, HTTPSHandler]:
                EndPoint.opener.add_handler(handler())

    def __getattr__(self, attr):
        if attr not in ["elem", "parent", "method", "chain"]:
            if EndPoint.startswith_.match(attr):
                attr = attr[1:]
            return EndPoint(attr, self, self.method)
        else:
            return object.__getattr__(self, attr)

    def __call__(self, *args, **kwargs):
        return self.method(*self.chain()+list(args), **kwargs)

    @staticmethod
    def _manage_response(res, error=None):
        text = res.read()
        try:
            data = json.loads(text)
        except Exception as err:
            data = {
                "success": True, "except": True,
                "raw":
                    text.decode("utf-8") if isinstance(text, bytes)
                    else text,
                "error": "%r" % err
            }
        data["status"] = res.getcode()
        return data

    @staticmethod
    def _open(req):
        try:
            res = EndPoint.opener.open(req, timeout=EndPoint.timeout)
        except Exception as error:
            return {"success": False, "error": "%r" % error, "except": True}
        else:
            return EndPoint._manage_response(res)

    @staticmethod
    def _call(method="GET", *args, **kwargs):
        return EndPoint._open(EndPoint.build_req(method, *args, **kwargs))

    @staticmethod
    def build_req(method="GET", *args, **kwargs):
        method = method.upper()
        headers = kwargs.pop("headers", {"Content-type": "application/json"})
        to_urlencode = kwargs.pop("urlencode", None)
        to_jsonify = kwargs.pop("jsonify", None)

        # construct base url
        chain = "/".join(args)
        if not chain.startswith("/"):
            chain = "/" + chain
        else:
            chain = chain.replace("//", "/")
        url = kwargs.pop('peer', EndPoint.peer) + chain

        if method == "GET":
            if len(kwargs):
                url += "?" + urlencode(kwargs)
            req = Request(url, None, headers)
        else:
            # if data provided other than kwargs use kwargs to build url
            if to_urlencode != to_jsonify:
                if len(kwargs):
                    url += "?" + urlencode(kwargs)
            # set content-type as json by default
            headers["Content-type"] = "application/json"
            # if explicitly asked to send data as urlencoded
            if to_urlencode is not None:
                data = urlencode(to_urlencode)
                headers["Content-type"] = "application/x-www-form-urlencoded"
            # if explicitly asked to send data as json
            elif to_jsonify is not None:
                data = json.dumps(to_jsonify)
            # else send kwargs as json
            elif len(kwargs):
                data = json.dumps(kwargs)
            # if nothing provided send void json as data
            else:
                data = json.dumps({})
            req = Request(url, data.encode('utf-8'), headers)

        # tweak request
        req.add_header("User-agent", "Mozilla/5.0")
        req.get_method = lambda: method
        return req

    @staticmethod
    def connect(peer):
        try:
            EndPoint.opener.open(peer, timeout=EndPoint.timeout)
        except Exception:
            EndPoint.peer = "%(scheme)s://%(ip)s:%(port)s" % WEBHOOK_PEER
            return False
        else:
            if peer.endswith("/"):
                peer = peer[:-1]
            EndPoint.peer = peer
            return True

    def add_handler(self, handler):
        if not isinstance(handler, BaseHandler):
            raise Exception(
                "%r have to be a %r instance" % (handler, BaseHandler)
            )
        if not isinstance(EndPoint.opener, OpenerDirector):
            EndPoint.opener = OpenerDirector()
        EndPoint.opener.add_handler(handler)

    def chain(self):
        return (self.parent.chain() + [self.elem]) if self.parent is not None \
               else [""]


GET = EndPoint(method=lambda *a, **kw: EndPoint._call("GET", *a, **kw))
POST = EndPoint(method=lambda *a, **kw: EndPoint._call("POST", *a, **kw))
PUT = EndPoint(method=lambda *a, **kw: EndPoint._call("PUT", *a, **kw))
DELETE = EndPoint(method=lambda *a, **kw: EndPoint._call("DELETE", *a, **kw))
