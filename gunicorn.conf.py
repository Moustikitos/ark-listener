# -*- coding:utf-8 -*-
from lystener import server, task


def post_worker_init(worker):
    server.DAEMONS = [
        task.TaskChecker(),
        task.TaskExecutioner(),
        task.MessageLogger(),
        task.FunctionCaller()
    ]


def on_exit(server):
    task.killall()
