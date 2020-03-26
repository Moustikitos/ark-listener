# -*- coding: utf-8 -*-
# © Toons

import re
import os
import cgi
import json
import hashlib
import lystener
import threading
import traceback

from collections import OrderedDict

if lystener.PY3:
    from http.server import HTTPServer, BaseHTTPRequestHandler
else:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

PATTERN = re.compile(r"^/([0-9a-zA-Z_]*)/([0-9a-zA-Z_]*)$")
CURSOR = lystener.initDB().cursor()


class WebhookApp:

    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        match = PATTERN.match(environ.get("PATH_INFO", ""))
        method = environ["REQUEST_METHOD"]

        if match is not None and method == "POST":
            module, name = match.groups()
            authorization = environ.get("HTTP_AUTHORIZATION", "?")

            try:
                payload = json.loads(environ["wsgi.input"].read())
            except Exception as error:
                payload = {}
                resp = {
                    "success": False,
                    "msg": "error processing data",
                    "traceback": "%r:\n%s" %
                    (error, traceback.format_exc())
                }
                value = b"406"
            else:
                resp = {"success": True}
                value = b"200"

            if payload != {}:
                resp = managePayload(payload, authorization, module, name)

        elif path == "/" and method == "GET":
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
                    "SELECT authorization, count(*) FROM history GROUP BY authorization"
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

            resp = {"success": True, "data": data}
            value = b"200"

        else:
            resp = {"success": False, "msg": "invalid endpoint"}
            value = b"403"

        data = json.dumps(resp)
        data = data.encode("utf-8") if not isinstance(data, bytes) else data
        write = start_response(value, (["Content-type", "application/json"],))
        write(data)

        return b""

    def run(self):
        self.httpd = HTTPServer((self.host, self.port), WebhookHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.setDaemon(True)
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class WebhookHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        match = PATTERN.match(self.path)

        # if somethin matched
        if match is not None:
            module, name = match.groups()
            ctype, pdict = cgi.parse_header(
                getHeader(self.headers, 'content-type')
            )
            if ctype == 'application/json':
                try:
                    length = int(getHeader(self.headers, 'content-length'))
                    payload = json.loads(self.rfile.read(length))
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
            else:
                payload = {}
                resp = {"success": False, "msg": "no valid jsons found"}
                value = 415

        else:
            payload = {}
            resp = {"success": False, "msg": "invalid endpoint"}
            value = 403

        self.send_response(value)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        if payload != {}:
            resp = managePayload(
                payload, getHeader(self.headers, "Authorization", "?"),
                module, name
            )

        data = json.dumps(resp)
        self.wfile.write(data.encode("utf-8") if lystener.PY3 else data)
        return


def getHeader(httpmsg, key, alt=False):
    if lystener.PY3:
        return httpmsg.get(key, alt)
    else:
        return httpmsg.getheader(key, alt)


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
