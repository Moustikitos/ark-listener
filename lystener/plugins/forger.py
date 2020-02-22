# -*- encoding:utf-8 -*-
# © THOORENS Bruno

import json
import time

import lystener
from lystener import logMsg, loadJson, dumpJson, notify, rest


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
    peer = params.get("peer", "https://explorer.ark.io:8443")
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
                rank = rest.GET.api.delegates(
                    pkey, peer=peer
                ).get("data", {}).get("rank", -1)
                if not rank:
                    return {"success": False, "message": "delegate not found"}
                send_notification = (rank <= delegate_number) and \
                                    (delay >= notification_delay)
                # do the possible checks
                if rank > delegate_number:
                    msg = "%s is not in forging position" % pkey
                    if delay >= notification_delay:
                        notify.send("[forging notification]", msg)
                    last_block["notification"] = now
                elif diff == 2:
                    msg = "%s just missed a block" % pkey
                    if send_notification:
                        notify.send("[forging notification]", msg)
                        last_block["notification"] = now
                    last_block["missed"] = missed + 1
                    success = True
                elif diff > 2:
                    msg = "%s is missing blocks (total %d)" % (pkey, missed + 1)
                    if send_notification:
                        notify.send("[forging notification]", msg)
                        last_block["notification"] = now
                    last_block["missed"] = missed + 1
                    success = True
            elif diff <= 1 and (missed > 0 or last_notification > 0):
                msg = "%s is forging again" % pkey
                notify.send("[forging notification]", msg)
                last_block.pop("missed", False)
                last_block.pop("notification", False)
                success = True
            else:
                # default message
                msg = "%s is forging (last round=%d | current round=%d)" % \
                      (pkey, last_round, current_round)

            # dump last forged block info
            dumpJson(last_block, "%s.last.block" % pkey, folder=lystener.DATA)
            messages.append(msg)

        # update last forged block with data and dump it
        if usernames.get(data["generatorPublicKey"], False) == pkey:
            last_block.update(data)
            dumpJson(last_block, "%s.last.block" % pkey, folder=lystener.DATA)

    return {"success": success, "message": messages}
