# ark-listener

### Support this project
 
 [![Liberapay receiving](https://img.shields.io/liberapay/goal/Toons?logo=liberapay)](https://liberapay.com/Toons/donate)
 
 [Buy &#1126;](https://bittrex.com/Account/Register?referralCode=NW5-DQO-QMT) and:
 
   * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
   * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://dpos.arky-delegate.info/arky)

## Supported blockchain

  * [X] Ark-v2
  * [ ] Ark-v3

## Concept

Ark core webhooks trigger POST requests containing blockchain data to a targeted peer. This one then have to parse data and trigger code execution. `ark-listener` uses lite python json server listening every POST requests received with the pattern : `http://{ip}:{port}/module/function`. 
If found, `module.function` will be executed with data embeded in the POST request.

### Python script triggered

Any peace of python code found in `lystener.__path__` can be triggered. 
`lystener` package provides a `plugins` folder where custom code to execute can be stored. If another place is needed, simply add the path to the `package.pth` file.

Python script environnement can be set using docstring. Requirements are checked and installed if missing with `./lys start-listening` or `./lys restart-listeners` commands.

Here an example of script (`module.py`):
```python
# -*- coding:utf-8 -*-

# python script environnement:
#  - elements listed in [requirements] will be installed with pip
#  - elements listed in [dependencies] will be installed with apt-get
#  - elements listed in [commands] will be executed with /bin/bash
"""
[requirements]
pytz
[dependencies]
python3
[commands]
echo "Simple script ready !"
"""

import sys
import pytz
from datetime import datetime as time


def function(data):
   # data is the blockchain content sent via webhook.
   # Script have to return ditctionary containing at least "success" key:
   #    {"success": True, ...} : execution will be stored in database
   #    {"success": False, ...} : execution will not be stored in database
   sys.stdout.write(
      "%s: %r" % (pytz.timezone('US/Eastern').localize(time.now()), data)
   )
   sys.stdout.flush()
   return {"success": True}
```

## Install

```
~$ bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-listener/master/bash/lys-install.sh)
```

Install script will copy two scripts in home folder: `lys-venv` and `lys`.

Listener server ip have to be white-listed on blockchain node (see `./lys public-ip`).

## Use

First read [`ARK doc`](https://ark.dev/docs/api/webhook-api/endpoints) about webhook endpoints.

Activate `lys` virtual environnement:
```
~$ ./lys-venv
(venv) ~$
```

Use `lys` command:
```
(venv) ~$ ./lys --help
Usage:
   lys deploy-listener <event> <function> (<regexp> | (<field> <condition> <value>)...) [-n <node>]
   lys update-listener <webhook-id> (<regexp> | (<field> <condition> <value>)...)
   lys destroy-listener
   lys show-listeners
   lys start-listening [-p <port>]
   lys restart-listeners
   lys stop-listening
   lys show-log
   lys public-ip
   lys grant <public-key>...

Options:
-n --node=<node> : the node registering the webhook
-p --port=<port> : the port used for listening srv [default: 5001]

Subcommands:
   deploy-listener    : link a webhook <event> with a python <function>
   update-listener    : change <event> trigger conditions
   destroy-listener   : unlink webhook <event> from python <function>
   lys show-listeners : print a sumary of registered <event>
   start-listening    : start/restart listener server
   restart-listeners  : restart listener server
   stop-listening     : stop listener server
   show-log           : show server log
   public-ip          : get public ip
   grant              : allow remote controle to <public-key> owner
```

### Examples

Execute `dummy.logSomething` on `transaction.applied` event:
```bash
cd ~
~$ ./lys-venv
# if vendorField starts with `sc:` using default webhook peer (http://127.0.0.1:4004)
(venv) ~$ ./lys deploy-listener transaction.applied dummy.logSomething ^sc:.*$
# or
(venv) ~$ ./lys deploy-listener transaction.applied dummy.logSomething vendorField regexp ^sc:.*$
# if amount >= 25 arks using a custom webhook peer
(venv) ~$ ./lys deploy-listener transaction.applied dummy.logSomething amount gte 2500000000 -n http://dpos.arky-delegate.info:4004
# if amount >= 25 arks or vendorField starting with `sc:` using a custom webhook peer
(venv) ~$ ./lys deploy-listener transaction.applied dummy.logSomething amount gte 2500000000 vendorField regexp ^sc:.*$ -n http://dpos.arky-delegate.info:4004
```

