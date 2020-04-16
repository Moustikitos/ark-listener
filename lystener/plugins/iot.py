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


def iotPublish(
    broker, topic, message, qos=2, venv=os.path.dirname(sys.executable)
):
    """
    This function sends simple message using specific venv.
    """
    output, errors = subprocess.Popen(
        [". %s/activate" % venv],
        executable='/bin/bash',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).communicate(
        (
            "hbmqtt_pub --url %(broker)s "
            "-t %(topic)s -m '%(message)s' --qos %(qos)s" % {
                "broker": broker,
                "topic": topic,
                "message": message,
                "qos": qos
            }
        ).encode('utf-8')
    )

    return (
        output.decode("utf-8") if isinstance(output, bytes) else output,
        errors.decode("utf-8") if isinstance(errors, bytes) else errors
    )


def forward(data):
    lystener.logMsg('data received :\n%s' % json.dumps(data, indent=2))
    params = lystener.loadJson("iot.param", folder=lystener.DATA)

    try:
        output, errors = iotPublish(
            params.get("broker", "mqtt://127.0.0.1"),
            params.get("topic", "%s/event" % NETWORK[data.get("network", 23)]),
            json.dumps(data, separators=(',', ':')),
            params.get("qos", 2)
        )

        if "MQTT connection failed" in output or \
           "Usage:" in output or \
           "Traceback" in output:
            return {"success": False, "msg": output, "errors": errors}
        else:
            return {"success": True, "msg": output + errors}

    except Exception as error:
        lystener.logMsg(traceback.format_exc())
        return {"success": False, "error": "%r" % error}
