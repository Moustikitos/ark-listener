# -*- coding: utf-8 -*-
# © THOORENS Bruno

import os
import io
import sys
import time
import hashlib
import binascii
import lystener
import traceback

import cSecp256k1 as secp256k1
from usrv import srv, req
from lystener import task

DAEMONS = None
CURSOR = None
FILENAME = os.path.join(lystener.JSON, "salt")


def deploy(host="0.0.0.0", port=5001):
    normpath = os.path.normpath
    executable = normpath(sys.executable)

    with io.open("./lys.service", "w") as unit:
        unit.write(u"""[Unit]
Description=Lys web server
After=network.target

[Service]
User=%(usr)s
WorkingDirectory=%(wkd)s
Environment=PYTHONPATH=%(path)s
ExecStart=%(bin)s/gunicorn 'lystener.server:WebhookApp()' \
--bind=%(host)s:%(port)s --workers=5 --access-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
""" % {
            "usr": os.environ.get("USER", "unknown"),
            "wkd": normpath(sys.prefix),
            "path": os.path.abspath(
                normpath(os.path.dirname(lystener.__path__[0]))
            ),
            "bin": os.path.dirname(executable),
            "port": port,
            "host": host
        })

    if os.system("%s -m pip show gunicorn" % executable) != "0":
        os.system(
            "%s -m pip install gunicorn%s" %
            (executable, "" if lystener.PY3 else "==19.10.0")
        )
    os.system("chmod +x ./lys.service")
    os.system("sudo mv --force ./lys.service /etc/systemd/system")
    os.system("sudo systemctl daemon-reload")
    if not os.system("sudo systemctl restart lys"):
        os.system("sudo systemctl start lys")


def dumpSeed():
    if not os.path.exists(FILENAME) or (
        os.path.exists(FILENAME) and
        time.time() - os.path.getmtime(FILENAME) > 30
    ):
        h = hashlib.sha256(binascii.hexlify(os.urandom(32))).hexdigest()
        lystener.dumpJson(
            {"salt": h.decode("utf-8") if isinstance(h, bytes) else h},
            "salt"
        )


def startSeed():
    dumpSeed()
    task.setInterval(16)(dumpSeed)()


def getSeed(pin=False):
    try:
        value = lystener.loadJson("salt")["salt"]
    except KeyError:
        if not os.path.exists(FILENAME):
            startSeed()
        value = lystener.loadJson("salt")["salt"]
    else:
        if time.time() - os.path.getmtime(FILENAME) > 60:
            startSeed()
    return str(int(value, 16))[:6] if pin else value


def checkSeed(value):
    return value == getSeed()


@srv.bind("/authorized", methods=["PUT", "DELETE"])
def checkRemoteAuth(**args):
    try:
        headers = args.get("headers", {})
        remote = headers.get(
            "x-forwarded-for",
            headers.get("remote-addr", "127.0.0.1")
        )
        task.MessageLogger.JOB.put(
            "received secured headers: %r" % headers
        )
        # check if publick key defined in header is an authorized one
        # auth is a list of public keys. Because loadJson returns a void
        # dict if no file found, the if condition acts same as if it was a list
        publicKey = headers.get("public-key", "?")
        if publicKey not in lystener.loadJson("auth"):
            return {"status": 401, "msg": "not authorized"}
        # Note that client has to define its own salt value and get a
        # 1-min-valid random seed from lystener server.
        # See /salt endpoint
        sig = secp256k1.HexSig.from_der(headers["signature"])
        puk = secp256k1.PublicKey.decode(publicKey)
        msg = secp256k1.hash_sha256(remote + headers["salt"] + getSeed())
        if not secp256k1._ecdsa.verify(msg, puk.x, puk.y, sig.r, sig.s):
            return {"status": 403, "msg": "bad signature"}
        return {"status": 200, "msg": "access granted"}

    except Exception as error:
        return {
            "status": 500,
            "msg": "checkPutDelete response: %s\n%s" %
            ("%r" % error, traceback.format_exc())
        }


class WebhookApp(srv.MicroJsonApp):

    def __init__(self, host="127.0.0.1", port=5000, loglevel=20):
        global DAEMONS, CURSOR
        srv.MicroJsonApp.__init__(self, host, port, loglevel)
        if CURSOR is None:
            CURSOR = task.initDB()
        if DAEMONS is None:
            DAEMONS = [
                task.TaskChecker(),
                task.TaskExecutioner(),
                task.MessageLogger()
            ]


# Bindings
# --------

@srv.bind("/")
def index():
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


@srv.bind("/salt")
def salt():
    return getSeed()


@srv.bind("/pin")
def pin():
    return getSeed(pin=True)


# catch webhook data #
@srv.bind("/<str:mod>/<str:func>", methods=["POST"])
def catch(mod, func, **kwargs):
    "Create a new job and return simple message."
    task.TaskChecker.JOB.put([mod, func, kwargs])
    return {
        "status": 200,
        "msg": "task set: %s.%s(%s)" %
        (mod, func, kwargs.get("data", {}))
    }


# send POST request to create webhook #
@srv.bind("/deploy", methods=["POST"])
def deploy_listener(**kwargs):
    chk = checkRemoteAuth(**kwargs)
    if chk.get("status", 0) >= 299:
        return chk
    return req.POST.api.webhook(**kwargs.get("data", {}))


# for test purpose only
if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(
        usage="usage: %prog [options] BINDINGS...",
        version="%prog 1.0"
    )
    parser.add_option(
        "-s", "--ssl", action="store_true", dest="ssl", default=False,
        help="activate ssl socket wraping"
    )
    parser.add_option(
        "-l", "--log-level", action="store", dest="loglevel", default=20,
        type="int",
        help="set log level from 1 to 50 [default: 20]"
    )
    parser.add_option(
        "-i", "--ip", action="store", dest="host", default="127.0.0.1",
        help="ip to run from             [default: 127.0.0.1]"
    )
    parser.add_option(
        "-p", "--port", action="store", dest="port", default=5000,
        type="int",
        help="port to use                [default: 5000]"
    )

    (options, args) = parser.parse_args()
    app = WebhookApp(options.host, options.port, loglevel=options.loglevel)
    app.run(ssl=options.ssl)
