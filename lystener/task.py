# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import os
import sys
import json
import sqlite3
import hashlib
import traceback
import threading
import importlib

try:
    import queue
except ImportError:
    import Queue as queue

from lystener import logMsg, loadJson, DATA


def initDB():
    database = os.path.join(DATA, "database.db")
    if not os.path.exists(DATA):
        os.makedirs(DATA)
    sqlite = sqlite3.connect(database)
    cursor = sqlite.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS "
        "history(signature TEXT, authorization TEXT);"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "history_index ON history(signature);"
    )
    sqlite.row_factory = sqlite3.Row
    sqlite.commit()
    return sqlite


def vacuumDB():
    pass


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


class FunctionCaller(Task):
    JOB = queue.Queue()

    def run(self):
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


class TaskChecker(Task):
    JOB = queue.Queue()
    DB = None

    def run(self):
        # sqlite db opened within thread
        TaskChecker.DB = initDB()
        # run until Task.killall() called
        while not Task.STOP.is_set():
            skip = True
            # wait until a job is given
            module, name, data = TaskChecker.JOB.get()
            headers = data.get("headers", {})
            body = data.get("data", {})
            # get authorization from headers
            auth = headers.get("authorization", "")
            # recreate the security token and check if authorized
            webhook = loadJson("%s.json" % auth)
            token = auth + webhook.get("token", "")
            if loadJson("token").get(
                "%s.%s" % (module, name), False
            ) != token:
                msg = "not authorized here\n%s" % json.dumps(data, indent=2)
            # check sender IP
            elif webhook.get("node-ip", "127.0.0.1") != headers.get(
                "x-forward-for",
                headers.get("remote-addr", "127.0.0.1")
            ):
                msg = "sender not genuine\n%s" % json.dumps(data, indent=2)
            else:
                # build a signature
                signature = body.get("signature", False)
                if not signature:
                    signature = jsonHash(body)
                signature = "%s.%s[%s]" % (module, name, signature)

                # ATOMIC ACTION -----------------------------------------------
                Task.LOCK.acquire()
                # check if signature already in database
                req = TaskChecker.DB.execute(
                    "SELECT count(*) FROM history WHERE signature = ?",
                    (signature,)
                )
                # exit if signature found in database
                if req.fetchone()[0] != 0:
                    msg = "data already parsed"
                elif signature in TaskExecutioner.ONGOING:
                    msg = "data is being parsed"
                else:
                    TaskExecutioner.ONGOING.add(signature)
                    skip = False
                Task.LOCK.release()
                # END ATOMIC ACTION -------------------------------------------

            if not skip:
                # import asked module
                try:
                    obj = importlib.import_module("lystener." + module)
                except Exception as exception:
                    msg = "%r\ncan not import python module %s" % \
                        (exception, module)
                else:
                    # try to get function by name
                    TaskExecutioner.MODULES.add(obj)
                    func = getattr(obj, name, False)
                    if callable(func):
                        TaskExecutioner.JOB.put([func, body, auth, signature])
                        msg = "forwarded: " + signature
                    else:
                        msg = "python definition %s not found in %s or is " \
                              "not callable" % (name, module)

            # push msg
            MessageLogger.JOB.put(msg)


class TaskExecutioner(Task):
    JOB = queue.Queue()
    MODULES = set([])
    ONGOING = set([])
    DB = None

    def run(self):
        TaskExecutioner.DB = initDB()
        while not Task.STOP.is_set():
            error = True
            response = {}
            # wait until a job is given
            func, data, auth, sig = TaskExecutioner.JOB.get()
            try:
                response = func(data)
            except Exception as exception:
                msg = "%s response:\n%s\n%s" % \
                      (func, "%r" % exception, traceback.format_exc())
            else:
                error = False
                msg = "%s response:\n%s" % (func, response)

            # push msg
            MessageLogger.JOB.put(msg)

            # daemon waits here to log results, update database and clean
            # memory
            try:
                # ATOMIC ACTION -----------------------------------------------
                Task.LOCK.acquire()

                if not error and response.get("success", False):
                    TaskExecutioner.DB.execute(
                        "INSERT OR REPLACE INTO "
                        "history(signature, authorization) "
                        "VALUES(?,?);", (sig, auth)
                    )
                    TaskExecutioner.DB.commit()

                # remove the module if all jobs done so if code is modified it
                # will be updated without a listener restart
                if TaskExecutioner.JOB.empty():
                    TaskExecutioner.ONGOING.clear()
                    error = False
                    while not error:
                        try:
                            obj = TaskExecutioner.MODULES.pop()
                        except Exception:
                            error = True
                        else:
                            sys.modules.pop(obj.__name__, False)
                            del obj

            except Exception as error:
                MessageLogger.JOB.put(
                    "Internal error occured:\n%s\n%s" %
                    ("%r" % error, traceback.format_exc())
                )

            finally:
                Task.LOCK.release()
                # END ATOMIC ACTION -------------------------------------------


def killall():
    Task.STOP.set()
    MessageLogger.JOB.put("kill signal sent !")
    FunctionCaller.JOB.put([lambda n: n, {"Exit": True}, {}])
    TaskChecker.JOB.put(["", "", {}])
    TaskExecutioner.JOB.put([lambda n: n, {"success": False}, "", ""])
