# -*- encoding:utf-8 -*-
# © THOORENS Bruno

"""
[requirements]
hbmqtt

[dependencies]
mosquitto
"""

import os
import sys
import json
import lystener
import traceback
import subprocess

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
    hbmqtt_pub command in a python subprocess where a virtualenv folder can be
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
        activate = os.path.expanduser(os.path.join(venv, "activate"))
        if os.path.exists(activate):
            cmd = (". %s\n" % activate) + cmd

    output, errors = subprocess.Popen(
        [],
        executable='/bin/bash',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).communicate(cmd.encode('utf-8'))

    return (
        output.decode("utf-8") if isinstance(output, bytes) else output,
        errors.decode("utf-8") if isinstance(errors, bytes) else errors
    )


def forward(data):
    lystener.logMsg('data received :\n%s' % json.dumps(data, indent=2))
    params = lystener.loadJson("iot.param", folder=lystener.DATA)

    try:
        output = "\n".join(
            publish(
                params.get("broker", "mqtt://127.0.0.1"),
                params.get(
                    "topic",
                    "%s/event" % NETWORK.get(data.get("network", 23), "ark")
                ),
                json.dumps(data, separators=(',', ':')),
                params.get("qos", 1),
                params.get("venv", os.path.dirname(sys.executable))
            )
        )

        if "MQTT connection failed" in output or \
           "command not found" in output or \
           "Usage:" in output or \
           "Traceback" in output:
            return {"success": False, "errors": output}
        else:
            return {"success": True, "msg": output}

    except Exception as error:
        lystener.logMsg(traceback.format_exc())
        return {"success": False, "error": "%r" % error}
