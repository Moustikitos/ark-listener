# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import json
import time
import requests

import lystener
from lystener import logMsg, loadJson, dumpJson, notify


def logSomething(data):
    logMsg('data received :\n%s' % json.dumps(data, indent=2))
    return {"success": True}


def checkIfForging(data):
    success = False
    ############################
    # load contract parameters #
    ############################
    params = loadJson("checkIfForging.param", folder=lystener.DATA)
    # get monitored delegates
    delegates = params.get("delegates", [])
    # exit if no delegate monitored
    if not len(delegates):
        return {"success": False}
    # get delegate informations
    usernames = params.get("usernames", {})
    delegate_number = params.get("active_delegates", 51)
    notification_delay = params.get("notification_delay", 10) * 60 # in minutes
    messages = []

    for pkey in delegates:
        # identify delegate by username or public key
        pkey = usernames.get(pkey, data["generatorPublicKey"])

        last_block = loadJson("%s.last.block" % pkey, folder=lystener.DATA)
        # if last forged block found
        if last_block != {}:
            # custom parameters
            missed = last_block.get("missed", 0)
            last_notification = last_block.get("notification", 0)
            # blockchain parameters
            last_round = last_block["height"] // delegate_number
            current_round = data["height"] // delegate_number
            diff = current_round - last_round
            now = time.time()
            delay = now - last_notification

            if diff > 1:
                rank = requests.get(
                    "https://explorer.ark.io:8443/api/delegates/%s" % pkey
                ).json().get("data", []).get("rank", [])
                send_notification = (rank <= delegate_number) and \
                                    (delay >= notification_delay)
                # do the possible checks
                if rank > delegate_number and delay >= notification_delay:
                    msg = "%s is not in forging position" % pkey
                    notify.send("[forging notification]", msg)
                    data["notification"] = now
                elif diff == 2:
                    msg = "%s just missed a block" % pkey
                    if send_notification:
                        notify.send("[forging notification]", msg)
                        data["notification"] = now
                    data["missed"] = missed + 1
                    success = True
                elif diff > 2:
                    msg = "%s is missing blocks (total %d)" % (pkey, missed + 1)
                    if send_notification:
                        notify.send("[forging notification]", msg)
                        data["notification"] = now
                    data["missed"] = missed + 1
                    success = True
            elif diff <= 1 and missed > 0:
                msg = "%s is forging again" % pkey
                notify.send("[forging notification]", msg)
                success = True
            else:
                # default message
                msg = "%s is forging (last round=%d | current round=%d)" % \
                      (pkey, last_round, current_round)

            messages.append(msg)

        # dump last forged block with additional data
        if usernames.get(data["generatorPublicKey"], False) == pkey:
            dumpJson(data, "%s.last.block" % pkey, folder=lystener.DATA)

    return {"success": success, "message": messages}
