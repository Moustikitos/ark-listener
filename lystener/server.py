# -*- coding: utf-8 -*-
# © Toons

import re
import os
import json
import hashlib
import lystener
import traceback

from collections import OrderedDict

if lystener.PY3:
    from http.server import HTTPServer, BaseHTTPRequestHandler
else:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

PATTERN = re.compile(r"^/([0-9a-zA-Z_]*)/([0-9a-zA-Z_]*)$")
CURSOR = None


class WebhookApp:

    def __init__(self, host="127.0.0.1", port=5000):
        global CURSOR
        if CURSOR is None:
            CURSOR = lystener.initDB().cursor()
        self.host = host
        self.port = port

    def __call__(self, environ, start_response):
        """
        Web Server Gateway Interface for deployment.
        https://www.python.org/dev/peps/pep-3333/
        """
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "/")
        match = PATTERN.match(path)

        if match is not None and method == "POST":
            authorization = environ.get("HTTP_AUTHORIZATION", "?")
            module, name = match.groups()
            value, resp, payload = extractPayload(
                environ["wsgi.input"].read()
            )
            if payload != {}:
                resp = managePayload(payload, authorization, module, name)

        elif path == "/" and method == "GET":
            resp = {"success": True, "data": listenerState()}
            value = 200

        else:
            resp = {"success": False, "msg": "invalid endpoint"}
            value = 403

        data = json.dumps(resp)
        data = data.encode("latin-1") if not isinstance(data, bytes) else data
        statuscode = "%d" % value
        write = start_response(
           statuscode.decode("latin-1") if isinstance(statuscode, bytes)
           else statuscode,
           (["Content-type", "application/json"],)
        )
        write(data)
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

    def do_GET(self):
        if self.path == "/":
            resp = {"success": True, "data": listenerState()}
            value = 200
        else:
            resp = {"success": False, "msg": "invalid endpoint"}
            value = 403
        data = json.dumps(resp)
        self.send_response(value)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(
            data if isinstance(data, bytes) else data.encode("utf-8")
        )

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
                resp = managePayload(payload, authorization, module, name)
        else:
            payload = {}
            resp = {"success": False, "msg": "invalid endpoint"}
            value = 403

        data = json.dumps(resp)
        data = data if isinstance(data, bytes) else data.encode("utf-8")
        self.send_response(value)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(data)


def getHeader(httpmsg, key, alt=False):
    if lystener.PY3:
        return httpmsg.get(key, alt)
    else:
        return httpmsg.getheader(key, alt)


def extractPayload(data):
    try:
        payload = json.loads(data)
    except Exception as error:
        payload = {}
        resp = {
            "success": False,
            "msg": "error processing data",
            "traceback": "%r:\n%s" %
            (error, traceback.format_exc())
        }
        value = 406
    else:
        resp = {"success": True}
        value = 200

    return value, resp, payload


def managePayload(payload, authorization, module, name):
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
        data = sameDataSort(data)
        # generate sha 256 hash as signature if no one found
        # remove all trailing spaces, new lines, tabs etc...
        raw = re.sub(r"[\s]*", "", json.dumps(data))
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        signature = h.decode() if isinstance(h, bytes) else h

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
        info["conditions"] = webhook["conditions"]
        info["peer"] = webhook["peer"]
        data.append(info)

    return data
