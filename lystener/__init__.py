# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import io
import os
import re
import sys
import ast
import json
import socket
import sqlite3
import datetime
import traceback
import threading
import importlib
import configparser

# save python familly
PY3 = True if sys.version_info[0] >= 3 else False
if PY3:
    import queue
    input = input
else:
    import Queue as queue
    input = raw_input

# configuration pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
JSON = os.path.abspath(os.path.join(ROOT, ".json"))
DATA = os.path.abspath(os.path.join(ROOT, ".data"))
LOG = os.path.abspath(os.path.join(ROOT, ".log"))
#
VALID_URL = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

# add the modules folder to the package path
__path__.append(os.path.abspath(os.path.join(ROOT, "plugins")))
__path__.append(os.path.abspath(os.path.join(ROOT, "_plugins")))

# add custom modules pathes from modules.pth file
# targeted python code could be anywhere where user can access
pathfile = os.path.join(ROOT, "package.pth")
if os.path.exists(pathfile):
    with io.open(pathfile) as pathes:
        comment = re.compile(r"^[\s]*#.*")
        for path in [
            p.strip() for p in pathes.read().split("\n")
            if not comment.match(p)
        ]:
            if path != "":
                __path__.append(os.path.abspath(path))


def checkPluginDependencies():
    """
    Walk trought all plugins and install dependencies according to docstrings
    """
    for path in [p for p in __path__[1:] if os.path.exists(p)]:
        for name in [os.path.join(path, name) for name in os.listdir(path)]:
            if os.path.isfile(name) and \
               (name.endswith(".py") or name.endswith(".pyw")):
                logMsg(
                    "%s - %s" % (path, os.path.basename(name.split(".")[0]))
                )
                with open(name, "r" if PY3 else "rb") as f:
                    tree = ast.parse(f.read())
                    docstring = ast.get_docstring(tree)
                    if docstring is not None:
                        cfg = configparser.ConfigParser(
                            allow_no_value=True,
                            delimiters="~"
                        )
                        try:
                            cfg.read_string(
                                docstring.decode("utf-8") if not PY3
                                else docstring
                            )
                        except Exception as error:
                            logMsg(
                                "docstring not exploited\n%r\n%s" %
                                (error, traceback.format_exc())
                            )
                        else:
                            sections = cfg.sections()
                            if "requirements" in sections:
                                os.system(
                                    "pip install %s" %
                                    " ".join(cfg["requirements"].keys())
                                )
                            if "dependencies" in sections:
                                os.system(
                                    "sudo apt-get install %s" %
                                    " ".join(cfg["dependencies"].keys())
                                )
                            if "commands" in sections:
                                for cmd in cfg["commands"].keys():
                                    os.system('/bin/bash -c "%s"' % cmd)
                            logMsg("docstring exploited")


def getPublicIp():
    """Store the public ip of server in PUBLIC_IP global var"""
    global PUBLIC_IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        PUBLIC_IP = s.getsockname()[0]
    except Exception:
        PUBLIC_IP = '127.0.0.1'
    finally:
        s.close()
    return PUBLIC_IP


def loadJson(name, folder=None):
    filename = os.path.join(JSON if not folder else folder, name)
    if os.path.exists(filename):
        with io.open(filename) as in_:
            data = json.load(in_)
    else:
        data = {}
    # hack to avoid "OSError: [Errno 24] Too many open files"
    # with pypy
    try:
        in_.close()
        del in_
    except Exception:
        pass
    #
    return data


def dumpJson(data, name, folder=None):
    filename = os.path.join(
        JSON, name if not folder else os.path.join(folder, name)
    )
    try:
        os.makedirs(os.path.dirname(filename))
    except OSError:
        pass
    with io.open(filename, "w" if PY3 else "wb") as out:
        json.dump(data, out, indent=4)
    # hack to avoid "OSError: [Errno 24] Too many open files"
    # with pypy
    try:
        out.close()
        del out
    except Exception:
        pass
    #


def logMsg(msg, logname=None, dated=False):
    if logname:
        logfile = os.path.join(LOG, logname)
        try:
            os.makedirs(os.path.dirname(logfile))
        except OSError:
            pass
        stdout = io.open(logfile, "a")
    else:
        stdout = sys.stdout

    stdout.write(
        ">>> " + (
            "[%s] " % datetime.datetime.now().strftime("%x %X") if dated else
            ""
        ) + "%s\n" % msg
    )
    stdout.flush()

    if logname:
        return stdout.close()


def chooseItem(msg, *elem):
    n = len(elem)
    if n > 1:
        sys.stdout.write(msg + "\n")
        for i in range(n):
            sys.stdout.write("    %d - %s\n" % (i + 1, elem[i]))
        sys.stdout.write("    0 - quit\n")
        i = -1
        while i < 0 or i > n:
            try:
                i = input("Choose an item: [1-%d]> " % n)
                i = int(i)
            except ValueError:
                i = -1
            except KeyboardInterrupt:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return False
        if i == 0:
            return None
        return elem[i - 1]
    elif n == 1:
        return elem[0]
    else:
        sys.stdout.write("Nothing to choose...\n")
        return False


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


def setInterval(interval):
    """ threaded decorator
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


class TaskExecutioner(threading.Thread):

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()
    ONGOING = set([])
    MODULES = set([])

    @staticmethod
    def killall():
        TaskExecutioner.STOP.set()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def run(self):
        while not TaskExecutioner.STOP.is_set():
            error = False
            # wait until a job is given
            module, name, data, sig, auth = TaskExecutioner.JOB.get()
            # import asked module
            try:
                obj = importlib.import_module("lystener."+module)
            except Exception as exception:
                error = True
                msg = "%r\ncan not import python module %s" % \
                      (exception, module)
            # get asked function and execute it with data
            else:
                TaskExecutioner.MODULES.add(obj)
                func = getattr(obj, name, False)
                if func:
                    try:
                        response = func(data)
                    except Exception as exception:
                        error = True
                        msg = "%s response:\n%s\n%s" % \
                              (name, "%r" % exception, traceback.format_exc())
                    else:
                        msg = "%s response:\n%s" % (name, response)
                else:
                    error = True
                    msg = "python definition %s not found in %s" % \
                          (name, module)
            # ATOMIC ACTION START
            # daemon waits here to log results, update database and clean
            # memory
            TaskExecutioner.LOCK.acquire()

            logMsg(msg)
            if not error and response.get("success", False):
                sqlite = initDB()
                cursor = sqlite.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO history(signature, authorization) "
                    "VALUES(?,?);", (sig, auth)
                )
                sqlite.commit()
                sqlite.close()

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

            TaskExecutioner.LOCK.release()
            # ATOMIC ACTION END
