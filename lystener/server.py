# -*- coding: utf-8 -*-
# © THOORENS Bruno

import re
import os
import time
import json
import hashlib
import binascii
import lystener
import traceback

from lystener import rest
from lystener.secp256k1 import ecdsa, schnorr
from collections import OrderedDict

if lystener.PY3:
    from http.server import HTTPServer, BaseHTTPRequestHandler

    def getHeader(http_msg, key, alt=False):
        return http_msg.get(key, alt)

else:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

    def getHeader(http_msg, key, alt=False):
        http_msg.getheader(key, alt)

PATTERN = re.compile(r"^/([0-9a-zA-Z_]*)/([0-9a-zA-Z_]*)$")
CURSOR = None


class Seed:

    FILENAME = os.path.join(lystener.JSON, "salt")

    @staticmethod
    def dump():
        if not os.path.exists(Seed.FILENAME) or (
            os.path.exists(Seed.FILENAME) and
            time.time() - os.path.getmtime(Seed.FILENAME) > 30
        ):
            h = hashlib.sha256(binascii.hexlify(os.urandom(32))).hexdigest()
            lystener.dumpJson(
                {"salt": h.decode("utf-8") if isinstance(h, bytes) else h},
                "salt"
            )
            lystener.logMsg("New salt dumped !")

    @staticmethod
    def start():
        Seed.dump()
        lystener.logMsg("Seed manager started")
        lystener.setInterval(16)(Seed.dump)()

    @staticmethod
    def get(pin=False):
        try:
            value = lystener.loadJson("salt")["salt"]
        except KeyError:
            if not os.path.exists(Seed.FILENAME):
                Seed.start()
            value = lystener.loadJson("salt")["salt"]
        else:
            if time.time() - os.path.getmtime(Seed.FILENAME) > 60:
                Seed.start()
        return int(value[:5], 16) if pin else value

    @staticmethod
    def check(value):
        return value == Seed.get()


class WebhookApp:

    DB = None

    def __init__(self, host="127.0.0.1", port=5000):
        global CURSOR
        self.host = host
        self.port = port
        WebhookApp.DB = lystener.initDB()
        if CURSOR is None:
            CURSOR = WebhookApp.DB.cursor()
        Seed.start()

    def __call__(self, environ, start_response):
        """
        Web Server Gateway Interface for deployment.
        https://www.python.org/dev/peps/pep-3333
        """
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "/")

        if method == "POST":
            match = PATTERN.match(path)
            if match is not None:
                authorization = environ.get("HTTP_AUTHORIZATION", "?")
                module, name = match.groups()
                value, resp, payload = extractPayload(
                    environ["wsgi.input"].read()
                )
                if payload != {}:
                    resp = callListener(payload, authorization, module, name)
            else:
                resp = {"success": False, "msg": "invalid listener endpoint"}
                value = 403

        elif method == "GET":
            if path == "/":
                resp = {"success": True, "data": listenerState()}
                value = 200
            elif path == "/salt":
                resp = {"success": True, "salt": Seed.get()}
                value = 200
            elif path == "/pin":
                resp = {"success": True, "pin": Seed.get(pin=True)}
                value = 200
            else:
                resp = {"success": False, "msg": "invalid endpoint"}
                value = 403

        elif method in ["PUT", "DELETE"]:
            value, resp = managePutDelete(
                method, path, environ["wsgi.input"].read(), {
                    "Public-key": environ.get("HTTP_PUBLIC_KEY", "?"),
                    "Signature": environ.get("HTTP_SIGNATURE", "?"),
                    "Method": environ.get("HTTP_METHOD", "ecdsa"),
                    "Salt": environ.get("HTTP_SALT", "")
                }
            )

        else:
            resp = {"success": False, "msg": "invalid method"}
            value = 403

        data = json.dumps(resp)
        statuscode = "%d" % value
        write = start_response(
           statuscode.decode("latin-1") if isinstance(statuscode, bytes)
           else statuscode,
           (["Content-type", "application/json"],)
        )
        write(data.encode("latin-1") if not isinstance(data, bytes) else data)
        return b""

    def run(self):
        """
        For testing purpose only.
        """
        self.httpd = HTTPServer((self.host, self.port), WebhookHandler)
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass


class WebhookHandler(BaseHTTPRequestHandler):

    def close_request(self, value, resp):
        data = json.dumps(resp)
        data = data if isinstance(data, bytes) else data.encode("latin-1")
        self.send_response(value)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            resp = {"success": True, "data": listenerState()}
            value = 200
        elif self.path == "/salt":
            resp = {"success": True, "salt": Seed.get()}
            value = 200
        elif self.path == "/pin":
            resp = {"success": True, "pin": Seed.get(pin=True)}
            value = 200
        else:
            resp = {"success": False, "msg": "invalid endpoint"}
            value = 403
        return self.close_request(value, resp)

    def do_POST(self):
        authorization = getHeader(self.headers, "Authorization", "?")
        match = PATTERN.match(self.path)
        if match is not None:
            module, name = match.groups()
            value, resp, payload = extractPayload(
                self.rfile.read(
                    int(getHeader(self.headers, 'content-length'))
                )
            )
            if payload != {}:
                resp = callListener(payload, authorization, module, name)
        else:
            payload = {}
            resp = {"success": False, "msg": "invalid listener endpoint"}
            value = 403

        return self.close_request(value, resp)

    def do_PUT(self):
        return self.close_request(
            *managePutDelete(
                "PUT", self.path, self.rfile.read(
                    int(getHeader(self.headers, 'content-length'))
                ),
                self.headers
            )
        )

    def do_DELETE(self):
        return self.close_request(
            *managePutDelete(
                "DELETE", self.path, self.rfile.read(
                    int(getHeader(self.headers, 'content-length'))
                ),
                self.headers
            )
        )


def extractPayload(data):
    try:
        payload = json.loads(data)
    except Exception as error:
        lystener.logMsg(traceback.format_exc())
        return 406, {
            "success": False,
            "msg": "error processing data: %r" % error
        }, {}
    return 200, {"success": True}, payload


def jsonHash(*args, **kwargs):
    data = sameDataSort(dict(*args, **kwargs))
    # remove all trailing spaces, new lines, tabs etc...
    raw = re.sub(r"[\s]*", "", json.dumps(data))
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return h.decode() if isinstance(h, bytes) else h


def managePutDelete(method, path, payload, headers):
    try:
        # check if endpoint defined
        func = ENDPOINT.get(method, {}).get(path, False)
        if not func:
            return 403, {"success": False, "msg": "invalid endpoint"}

        # check if publick key defined in header is an authorized one
        # auth is a list of public keys. Because loadJson returns a void
        # dict if no file found, the if condition acts same as if it was a list
        publicKey = headers.get("Public-key", "?")
        if publicKey not in lystener.loadJson("auth"):
            return 400, {"success": False, "msg": "not authorized"}

        # load payload as json, if value != 200 --> payload is not compliant with
        # application/json mime asked
        value, resp, payload = extractPayload(payload)
        if value != 200:
            return value, resp

        # get method as ecdsa or schnorr and generate msg used to issue
        # signature
        signature = headers["Signature"]
        method = headers.get("Method", "ecdsa")
        msg = headers["Salt"] + Seed.get()
        # Note that client has to define its own salt value and get a 1-min-valid
        # random seed from lystener server.
        # See /salt endpoint
        if not (schnorr.verify if method == "schnorr" else ecdsa.verify)(
            hashlib.sha256(msg.encode("utf-8")).digest(),
            binascii.unhexlify(publicKey),
            binascii.unhexlify(signature)
        ):
            return 400, {"success": False, "msg": "bad signature"}
        # execute endpoint
        return func(payload)
    except Exception as error:
        lystener.logMsg(traceback.format_exc())
        return 400, {"success": False, "error": "%r" % error}


def callListener(payload, authorization, module, name):
    # get the content of `data` field
    data = payload.get("data", False)
    # check the data sent by webhook
    if not data:
        lystener.logMsg("no data provided")
        return {"success": False, "message": "no data provided"}

    # check authorization and exit if bad one
    webhook = lystener.loadJson("%s.json" % authorization)
    half_token = webhook.get("token", 32*" ")[:32]
    if authorization == "?" or half_token != authorization:
        msg = "not authorized here\n%s" % json.dumps(data, indent=2)
        lystener.logMsg(msg)
        return {"success": False, "message": msg}

    # try to get a signature from data
    signature = data.get("signature", False)
    if not signature:
        signature = jsonHash(data)

    # check if signature already in database
    CURSOR.execute(
        "SELECT count(*) FROM history WHERE signature = ?", (signature,)
    )

    # exit if signature found in database
    if CURSOR.fetchone()[0] != 0:
        lystener.logMsg("data already parsed")
        return {"success": False, "message": "data already parsed"}
    # else put the job to task execution
    elif signature not in lystener.TaskExecutioner.ONGOING:
        lystener.TaskExecutioner.LOCK.acquire()
        event = payload.get("event", "?")
        timestamp = payload.get("timestamp", "?")
        msg = "data authorized - %s\n    %s:%s --> %s.%s\n    sig:%s" % \
            (authorization, timestamp, event, module, name, signature)
        lystener.logMsg(msg)
        lystener.TaskExecutioner.ONGOING.add(signature)
        lystener.TaskExecutioner.JOB.put(
            [module, name, data, signature, authorization]
        )
        lystener.TaskExecutioner.LOCK.release()
        return {"success": True, "message": msg}
    else:
        lystener.logMsg("data on going to be parsed")
        return {"success": False, "message": "data on going to be parsed"}


def sameDataSort(data, reverse=False):
    """return a sorted object from iterable data"""
    if isinstance(data, (list, tuple)):
        return sorted(
            data,
            key=lambda e: list(e.values()) if isinstance(e, dict) else e,
            reverse=reverse,
        )
    elif isinstance(data, dict):
        result = OrderedDict()
        for key, value in sorted(
            [(k, v) for k, v in data.items()],
            key=lambda e: e[0],
            reverse=reverse
        ):
            result[key] = sameDataSort(value, reverse)
        return result
    else:
        return data


def listenerState():
    if os.path.exists(os.path.join(lystener.ROOT, ".json")):
        json_list = [
            lystener.loadJson(name) for name in os.listdir(
                os.path.join(lystener.ROOT, ".json")
            ) if name.endswith(".json")
        ]
    else:
        json_list = []

    counts = dict(
        CURSOR.execute(
            "SELECT authorization, count(*) "
            "FROM history GROUP BY authorization"
        ).fetchall()
    )

    data = []
    for webhook in json_list:
        info = {}
        info["counts"] = counts.get(webhook["token"][:32], 0)
        info["id"] = webhook["id"]
        info["event"] = webhook["event"]
        info["call"] = ".".join(webhook["target"].split("/")[-2:])
        info["conditions"] = webhook["conditions"]
        info["peer"] = webhook["peer"]
        data.append(info)

    return data


def deployListener(payload):
    function = payload["function"]
    emitter = payload.get(
        "emitter",
        "%(scheme)s://%(ip)s:%(port)s" % rest.WEBHOOK_PEER
    )
    receiver = payload.get(
        "receiver",
        ("%(scheme)s://%(ip)s:%(port)s" % rest.LISTENER_PEER) +
        "/" + function.replace(".", "/")
    )

    if "regexp" in payload:
        conditions = [{
            "key": "vendorField",
            "condition": "regexp",
            "value": payload["regexp"]
        }]
    elif "conditions" in payload:
        conditions = list(
            {"key": k, "condition": c, "value": v} for k, c, v in
            payload["conditions"]
        )

    resp = rest.POST.api.webhooks(
        event=payload["event"], target=receiver, conditions=conditions,
        peer=emitter
    )
    if "data" in resp:
        webhook = resp["data"]
        webhook["peer"] = emitter
        lystener.dumpJson(webhook, webhook["token"][:32] + ".json")
        lystener.logMsg("%s webhook set" % function)
        return 200, resp
    else:
        lystener.logMsg("%s webhook not set" % function)
        return 400, resp


def destroyListener(payload):

    id_ = payload.get("id", payload.get("_id", payload.get("id_", False)))
    webhook = {}
    for name in [n for n in os.listdir(lystener.JSON) if n.endswith(".json")]:
        data = lystener.loadJson(name)
        if data["id"] == id_:
            webhook = data
            break

    if not webhook:
        return 400, {"success": False, "msg": "webhook %s not found" % id_}

    # delete webhook using its id and parent peer
    rest.DELETE.api.webhooks("%s" % webhook["id"], peer=webhook["peer"])
    # delete the webhook configuration
    os.remove(os.path.join(lystener.JSON, name))
    msg = "webhook %s destroyed" % id_
    lystener.logMsg(msg)

    return 200, {"success": True, "msg": msg}


ENDPOINT = {
    "GET": {
        "/": lambda *a, **k: None,
        "/salt": lambda *a, **k: None,
        "/pin": lambda *a, **k: None,
    },
    "PUT": {
        "/listener/deploy": deployListener
    },
    "DELETE": {
        "/listener/destroy": destroyListener
    }
}
