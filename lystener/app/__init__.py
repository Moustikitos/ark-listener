# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import io
import os
import re
import json
import flask
import hashlib
import lystener

from importlib import import_module
from collections import OrderedDict
from lystener import logMsg, loadJson, initDB, TaskExecutioner


# create the application instance
app = flask.Flask(__name__)
app.config.update(
    # 300 seconds = 5 minutes lifetime session
    PERMANENT_SESSION_LIFETIME=300,
    # used to encrypt cookies
    # secret key is generated each time app is restarted
    SECRET_KEY=os.urandom(24),
    # JS can't access cookies
    SESSION_COOKIE_HTTPONLY=True,
    # update cookies on each request
    # cookie are outdated after PERMANENT_SESSION_LIFETIME seconds of idle
    SESSION_REFRESH_EACH_REQUEST=True,
    #
    TEMPLATES_AUTO_RELOAD=True,
)

# import plugins on startup
with io.open(os.path.join(lystener.ROOT, "startup.import")) as in_:
    for name in [
        line for line in in_.read().split("\n")
        if line != "" and "#" not in line
    ]:
        logMsg("loading %s plugin..." % name)
        try:
            import_module("lystener."+name)
        except Exception as exception:
            logMsg("%r\nerror importing plugin %s" % (exception, name))
        else:
            logMsg("%s plugin loaded\n" % name)


@app.route("/")
def index():
    if os.path.exists(os.path.join(lystener.ROOT, ".json")):
        json_list = [
            loadJson(name) for name in os.listdir(
                os.path.join(lystener.ROOT, ".json")
            ) if name.endswith(".json")
        ]
    else:
        json_list = []

    cursor = connect()
    return flask.render_template(
        "listener.html",
        counts=dict(cursor.execute("SELECT authorization, count(*) FROM history GROUP BY authorization").fetchall()),
        webhooks=json_list,
    )


@app.route("/<module>/<name>", methods=["POST"])
def execute(module, name):

    if flask.request.method == "POST":

        # try to load data as json. If not possible then it is a junk POST
        # request. ValueError is raised when json can not decode data
        try:
            payload = json.loads(flask.request.data)
        except ValueError:
            return json.dumps(
                {"success": False, "message": "POST request not allowed here"}
            )

        # get the content of `data` field
        data = payload.get("data", False)
        # check the data sent by webhook
        if not data:
            logMsg("no data received")
            return json.dumps(
                {"success": False, "message": "no data provided"}
            )
        # sort data
        else:
            data = sameDataSort(data)

        # check authorization and exit if bad one
        authorization = flask.request.headers.get("Authorization", "?")
        webhook = loadJson("%s.json" % authorization)
        half_token = webhook.get("token", 32*" ")[:32]
        if authorization == "?" or half_token != authorization:
            msg = "not authorized here\n%s" % json.dumps(data, indent=2)
            logMsg(msg)
            return json.dumps({"success": False, "message": msg})

        # use sqlite database to check if data already parsed once
        cursor = connect()
        # try to get a signature from data
        signature = data.get("signature", False)
        if not signature:
            # generate sha 256 hash as signature if no one found
            # remove all trailing spaces, new lines, tabs etc...
            raw = re.sub(r"[\s]*", "", json.dumps(data))
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            signature = h.decode() if isinstance(h, bytes) else h

        # check if signature already in database
        cursor.execute(
            "SELECT count(*) FROM history WHERE signature = ?", (signature,)
        )

        # first get TaskExecutioner lock
        TaskExecutioner.LOCK.acquire()
        # exit if signature found in database
        if cursor.fetchone()[0] != 0:
            logMsg("data already parsed")
            TaskExecutioner.LOCK.release()
            return json.dumps(
                {"success": False, "message": "data already parsed"}
            )
        # else put the job to task execution
        elif signature not in TaskExecutioner.ONGOING:
            event = payload.get("event", "?")
            timestamp = payload.get("timestamp", "?")
            msg = "data authorized - %s\n    %s:%s --> %s.%s" % \
                  (authorization, timestamp, event, module, name)
            logMsg(msg)
            TaskExecutioner.ONGOING.add(signature)
            TaskExecutioner.JOB.put(
                [module, name, data, signature, authorization]
            )
            TaskExecutioner.LOCK.release()
            return json.dumps({"success": True, "message": msg})
        else:
            logMsg("data on going to be parsed")
            TaskExecutioner.LOCK.release()
            return json.dumps(
                {"success": False, "message": "data on going to be parsed"}
            )


@app.teardown_appcontext
def close(*args, **kw):
    if hasattr(flask.g, "database"):
        flask.g.database.commit()
        flask.g.database.close()


def sameDataSort(data, reverse=False):
    """return a sorted object from iterable data"""
    if isinstance(data, (list, tuple)):
        return sorted(data, reverse=reverse)
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


def connect():
    if not hasattr(flask.g, "database"):
        setattr(flask.g, "database", initDB())
    return getattr(flask.g, "database").cursor()


########################
# css reload bugfix... #
########################
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get("filename", False)
        if filename:
            file_path = os.path.join(app.root_path, endpoint, filename)
            values["q"] = int(os.stat(file_path).st_mtime)
    return flask.url_for(endpoint, **values)
########################
