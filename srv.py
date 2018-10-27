#! /usr/bin/env python
# -*- encoding:utf-8 -*-

"""
Usage:
   srv [-i <ip> -p <port>]

Options:
-i --ip=<ip>     : the IP address you want to listen [default: 127.0.0.1]
-p --port=<port> : the port you want to use          [default: 5001]
"""

import sys
import docopt

if __name__ == "__main__":
	from lystener import rest
	from lystener.app import app

	args = docopt.docopt(__doc__, argv=sys.argv[1:])
	app.run(host=args["--ip"], port=int(args["--port"]))
