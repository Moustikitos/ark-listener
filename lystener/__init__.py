# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import io
import os
import re
import sys
import ast
import json
import datetime
import traceback
import configparser

# save python familly
PY3 = sys.version_info[0] >= 3

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
