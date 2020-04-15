# -*- encoding:utf-8 -*-
# © THOORENS Bruno
"""
[requirements]
hbmqtt

[dependencies]
mosquitto
"""

import json
import shlex
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


def forward(data):
    lystener.logMsg('data received :\n%s' % json.dumps(data, indent=2))
    params = lystener.loadJson("iot.param", folder=lystener.DATA)

    try:
        cmd = (
            "hbmqtt_pub --url %(broker)s -t %(topic)s "
            "-m '%(message)s' --qos %(qos)s"
        ) % {
            "broker": params.get("broker", "mqtt://127.0.0.1"),
            "topic": params.get(
                "topic", "%s/event" % NETWORK[data.get("network", 23)]
            ),
            "message": json.dumps(data, separators=(',', ':')),
            "qos": params.get("qos", 2)
        }

        output = subprocess.check_output(
            shlex.split(cmd), stderr=subprocess.STDOUT
        )
        output = output.decode("utf-8") if isinstance(output, bytes) else output

        if "MQTT connection failed" in output or \
           "Usage:" in output or \
           "Traceback" in output:
            return {"success": False, "msg": output}
        else:
            return {"success": True, "msg": output}

    except Exception as error:
        lystener.logMsg(traceback.format_exc())
        return {"success": False, "error": "%r" % error}
