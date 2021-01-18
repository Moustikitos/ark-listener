# -*- encoding:utf-8 -*-
# © THOORENS Bruno

"""
[commands]
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/hbmqtt/master/ark-broker/install-ark-broker.sh)
"""

import os
import sys
import json
import lystener
import traceback
import subprocess

from lystener import zjsn


NETWORK = {
    23: "ark",
    30: "dark",
    100: "iop",
    90: "diop",
    58: "qredit",
}


def publish(broker, topic, message, qos=1, venv=None):
    """
    Send message on a topic using a specific broker. This function calls
    hbmqtt_pub command in a python subprocess where a virtualenv can be
    specified if needed (folder where `activate` script is localized).

    Args:
        broker (:class:`str`): valid borker url (ie mqtt://127.0.0.1)
        topic (:class:`str`): topic to use
        message (:class:`str`): message to send
        qos (:class:`int`): quality of service [default: 2]
        venv (:class:`str`): virtualenv folder [default: None]
    Returns:
        :class:`str`: subprocess stdout and stderr
    """
    # build hbmqtt_pub command line
    # see ~ https://hbmqtt.readthedocs.io/en/latest/references/hbmqtt_pub.html
    cmd = (
        "hbmqtt_pub --url %(broker)s "
        "-t %(topic)s -m '%(message)s' --qos %(qos)s"
    ) % {
        "broker": broker,
        "topic": topic,
        "message": message,
        "qos": qos
    }

    if venv is not None:
        # check if venv exists and add venv activation in command line
        activate = os.path.expanduser(os.path.join(venv, "activate"))
        if os.path.exists(activate):
            # `.` is used instead of `source`
            cmd = (". %s\n" % activate) + cmd

    # build a python subprocess and send command
    output, errors = subprocess.Popen(
        [],
        executable='/bin/bash',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).communicate(cmd.encode('utf-8'))

    # return stdout and stderr as str
    return (
        output.decode("utf-8") if isinstance(output, bytes) else output,
        errors.decode("utf-8") if isinstance(errors, bytes) else errors
    )


def forward(data):
    lystener.logMsg('data received :\n%s' % json.dumps(data, indent=2))
    # if `iot.param` not found, param = {}
    params = lystener.loadJson("iot.param", folder=lystener.DATA)

    try:
        # launch subprocess and merge stdout and stderr in output
        output = "\n".join(
            publish(
                params.get("broker", "mqtt://127.0.0.1"),
                params.get(
                    "topic",
                    "%s/event" % NETWORK.get(data.get("network", 23), "ark")
                ),
                json.dumps(zjsn.zip(data)),
                params.get("qos", 1),
                params.get("venv", os.path.dirname(sys.executable))
            )
        )
        # do some basic error checks
        if "MQTT connection failed" in output:
            status = 500
        elif "command not found" in output:
            status = 400
        elif "Usage:" in output:
            status = 500
        elif "Traceback" in output:
            status = 500
        elif "syntax error" in output:
            status = 500
        else:
            status = 200

        return {"status": status, "success": status < 300, "message": output}

    except Exception as error:
        lystener.logMsg(traceback.format_exc())
        return {"status": 500, "success": False, "error": "%r" % error}
