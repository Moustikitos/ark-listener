# ark-listener

## Support this project

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://dpos.arky-delegate.info/arky)

## Supported blockchain

 * [X] Ark-v2

## Concept

Ark core webhooks trigger POST requests containing data to a targeted peer. This one then have to parse data and trigger code execution.

`ark-listener` uses python server app listening every POST requests received with the pattern : `http://{ip}:{port}/module/function`.

If found, `module.function` will be executed with data embeded in the POST request.

## Install development version

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-listener/master/bash/lys-install.sh)
```

### Deploy listener

Execute `forger.logSomething` on `transaction.applied` event

```bash
cd ~
ark-listener/bash/activate
# if vendorField starts with `sc:`
# using default webhook peer (http://127.0.0.1:4004)
./lys deploy-listener transaction.applied forger.logSomething ^sc:.*$
# or
./lys deploy-listener transaction.applied forger.logSomething vendorField regexp ^sc:.*$

# if amount >= 25 arks
# using a custom webhook peer
./lys deploy-listener transaction.applied forger.logSomething amount gte 2500000000 -w http://dpos.arky-delegate.info:4004

# if amount >= 25 arks or vendorField starting with `sc:`
# using a custom webhook peer
./lys deploy-listener transaction.applied forger.logSomething amount gte 2500000000 vendorField regexp ^sc:.*$ -w http://dpos.arky-delegate.info:4004
```

## Launch listener

Your listener server ip have to be white-listed on blockchain relay. Execute `./lys public-ip` to find ip address.

```bash
~/ark-listener/bash/activate
~/lys start-listening
```

## Where is stored code to execute ?

The ark-listener tree contains a `plugins` folder where you can save your custom code to execute. If another place is needed, simply add the path to the `package.pth` file and `lystener` will be able to find it.

There are two way for the plugin to be loaded :
  * when event is triggered, once execution finished plugin is cleaned from memory. A plugin can be updated without server restart
  * on server start. The plugin name have to be added to `startup.import` file.

`plugin` dependencies are installed via `pip` using docstring as ini file format:

```python
# -*- encoding:utf-8 -*-
"""
[requirements]
git+https://github.com/Moustikitos/dpos#egg=dposlib
configparser
"""

from dposlib import rest
[...]
```

## How can I check deployed listeners ?

The listening server redirects browser to listener details page.

## `lys` commands

```bash
~/ark-listener/bash/activate
~/lys --help
```

```
Usage:
   lys deploy-listener <event> <function> (<regexp> | (<field> <condition> <value>)...) [-w <webhook>]
   lys destroy-listener
   lys start-listening [-p <port>]
   lys restart-listeners
   lys stop-listening
   lys show-log
   lys public-ip

Options:
-w --webhook=<webhook> : the peer registering the webhook
-p --port=<port>       : the port used for listening srv [default: 5001]

Subcommands:
   deploy-listener   : link a webhook <event> with a python <function>
   destroy-listener  : unlink webhook <event> from python <function>
   start-listening   : start/restart listener server
   restart-listeners : restart listener server
   stop-listening    : stop listener server
   show-log          : show server log
   public-ip         : get public ip
```
