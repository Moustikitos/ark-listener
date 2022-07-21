# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import os
import sys
import json
import queue
import sqlite3
import hashlib
import datetime
import traceback
import threading
import importlib

from lystener import dumpJson, logMsg, loadJson, DATA, JSON


def initDB():
    database = os.path.join(DATA, "database.db")
    if not os.path.exists(DATA):
        os.makedirs(DATA)
    sqlite = sqlite3.connect(database)
    cursor = sqlite.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS "
        "fingerprint(hash TEXT UNIQUE, token TEXT);"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS "
        "history(signature TEXT UNIQUE, token TEXT);"
    )
    sqlite.row_factory = sqlite3.Row
    sqlite.commit()
    return sqlite


def vacuumDB():
    sqlite = sqlite3.connect(
        os.path.join(DATA, "database.db"),
        isolation_level=None
    )
    sqlite.row_factory = sqlite3.Row

    token = [
        row["token"] for row in
        sqlite.execute(
            "SELECT DISTINCT token FROM history"
        ).fetchall()
    ]

    for tok in [
        loadJson(name).get("token", None) for name in os.listdir(JSON)
        if name.endswith(".json")
    ]:
        if tok not in token:
            cleanDB(sqlite, tok)

    sqlite.execute("VACUUM")
    sqlite.commit()
    sqlite.close()


def cleanDB(sqlite, token):
    logMsg("removing hitory of token %s..." % token)
    sqlite.execute("DELETE FROM fingerprint WHERE token=?", (token,))
    sqlite.execute("DELETE FROM history WHERE token=?", (token,))


def trace(sqlite, token, content):
    sqlite.execute(
        "INSERT INTO fingerprint(hash, token) VALUES(?, ?);",
        (jsonHash(content), token)
    )


def untrace(sqlite, token, content):
    sqlite.execute(
        "DELETE FROM fingerprint WHERE hash=? AND token=?",
        (jsonHash(content), token)
    )


def webhookName(auth, mod, func):
    return "%s.json" % hashlib.sha256(
        f"whk://{auth}.{mod}.{func}".encode("utf-8")
    ).hexdigest()


def isGenuineWebhook(auth, webhhook={}):
    token = auth + webhhook.get("token", "")
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest() == webhhook.get("hash", "")


def jsonHash(data):
    raw = json.dumps(data, sort_keys=True, separators=(',', ':'))
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return h.decode() if isinstance(h, bytes) else h


def setInterval(interval):
    """
    threaded decorator.

    >>> @setInterval(10)
    ... def tick():
    ...     print("Tick")
    >>> event = tick() # print 'Tick' every 10 sec
    >>> type(event)
    <class 'threading.Event'>
    >>> event.set() # stop printing 'Tick' every 10 sec
    """
    def decorator(function):
        """Main decorator function."""

        def wrapper(*args, **kwargs):
            """Helper function to create thread."""
            stopped = threading.Event()

            # executed in another thread
            def loop():
                """Thread entry point."""
                # until stopped
                while not stopped.wait(interval):
                    function(*args, **kwargs)

            t = threading.Thread(target=loop)
            # stop if the program exits
            t.daemon = True
            t.start()
            return stopped
        return wrapper
    return decorator


class Task(threading.Thread):
    STOP = threading.Event()
    LOCK = threading.Lock()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()


class MessageLogger(Task):
    JOB = queue.Queue()

    def run(self):
        logMsg("MessageLogger is running in background...")
        while not Task.STOP.is_set():
            msg = MessageLogger.JOB.get()
            try:
                Task.LOCK.acquire()
                logMsg(msg)
            except Exception as exception:
                msg = "log error:\n%r\n%s" % \
                      (exception, traceback.format_exc())
            finally:
                Task.LOCK.release()
        logMsg("exiting MessageLogger...")

    @staticmethod
    def log(msg):
        MessageLogger.JOB.put(msg)


class FunctionCaller(Task):
    JOB = queue.Queue()

    def run(self):
        logMsg("FunctionCaller is running in background...")
        while not Task.STOP.is_set():
            func, args, kwargs = FunctionCaller.JOB.get()
            try:
                Task.LOCK.acquire()
                response = func(*args, **kwargs)
            except Exception as exception:
                msg = "%s response:\n%r\n%s" % \
                      (func, exception, traceback.format_exc())
            else:
                msg = "%s response:\n%r" % (func, response)
            finally:
                Task.LOCK.release()
            # push msg
            MessageLogger.JOB.put(msg)
        logMsg("exiting FunctionCaller...")

    @staticmethod
    def call(func, *args, **kwargs):
        FunctionCaller.JOB.put([func, args, kwargs])


class TaskChecker(Task):
    JOB = queue.Queue()
    DB = None

    def run(self):
        # sqlite db opened within thread
        TaskChecker.DB = initDB()
        logMsg("TaskChecker is running in background...")
        # run until Task.killall() called
        while not Task.STOP.is_set():
            skip = True
            # wait until a job is given
            module, name, auth, content = TaskChecker.JOB.get()
            # get webhook data
            webhook = loadJson(webhookName(auth, module, name))
            # compute security hash
            if not isGenuineWebhook(auth, webhook):
                msg = "not authorized here\n%s" % json.dumps(content, indent=2)
            else:
                # build a signature
                signature = "%s@%s.%s[%s]" % (
                    webhook["event"], module, name, jsonHash(content)
                )
                skip = False
            if not skip:
                # import asked module
                try:
                    obj = importlib.import_module("lystener." + module)
                except Exception as exception:
                    skip = True
                    msg = "%r\ncan not import python module %s" % \
                        (exception, module)
                else:
                    # try to get function by name
                    TaskExecutioner.MODULES.add(obj)
                    func = getattr(obj, name, False)
                    if callable(func):
                        TaskExecutioner.JOB.put(
                            [func, content, webhook["token"], signature]
                        )
                        msg = "forwarded: " + signature
                    else:
                        skip = True
                        msg = "python definition %s not found in %s or is " \
                              "not callable" % (name, module)
            if skip and "token" in webhook:
                Task.LOCK.acquire()
                # ATOMIC ACTION -----------------------------------------------
                untrace(TaskChecker.DB, webhook["token"], content)
                TaskChecker.DB.commit()
                # END ATOMIC ACTION -------------------------------------------
                Task.LOCK.release()
            # push msg
            MessageLogger.JOB.put(msg)
        logMsg("exiting TaskChecker...")


class TaskExecutioner(Task):
    JOB = queue.Queue()
    MODULES = set([])
    DB = None

    def run(self):
        logMsg("TaskExecutioner is running in background...")
        TaskExecutioner.DB = initDB()
        while not Task.STOP.is_set():
            error = True
            response = {}
            # wait until a job is given
            func, data, token, sig = TaskExecutioner.JOB.get()
            try:
                response = func(data)
            except Exception as exception:
                msg = "%s response:\n%s\n%s" % \
                      (func, "%r" % exception, traceback.format_exc())
                # dump data and message to manage it later
                dumpJson(
                    dict(data=data, msg=msg),
                    "%s.json" % datetime.datetime.now().strftime(
                        "%m-%d-%Y_%Hh%Mm%Ss"
                    )
                )
            else:
                error = False
                msg = "%s response:\n%s" % (func, response)
            # push msg
            MessageLogger.JOB.put(msg)
            # daemon waits here to log results, update database and clean
            # memory
            try:
                Task.LOCK.acquire()
                # ATOMIC ACTION -----------------------------------------------
                if not error and response.get("success", False):
                    TaskExecutioner.DB.execute(
                        "INSERT OR REPLACE INTO history(signature, token) "
                        "VALUES(?, ?);", (sig, token)
                    )
                # remove the module if all jobs done so if code is modified it
                # will be updated without a listener restart
                if TaskExecutioner.JOB.empty():
                    empty = False
                    while not empty:
                        try:
                            obj = TaskExecutioner.MODULES.pop()
                        except Exception:
                            empty = True
                        else:
                            sys.modules.pop(obj.__name__, False)
                            del obj
            except Exception as exception:
                MessageLogger.JOB.put(
                    "Internal error occured:\n%s\n%s" %
                    ("%r" % exception, traceback.format_exc())
                )
            finally:
                if error:
                    untrace(TaskExecutioner.DB, token, data)
                TaskExecutioner.DB.commit()
                # END ATOMIC ACTION -------------------------------------------
                Task.LOCK.release()
        logMsg("exiting TaskExecutioner...")
