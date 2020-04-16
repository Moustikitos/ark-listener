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

Execute `dummy.logSomething` on `transaction.applied` event :

```bash
cd ~
ark-listener/bash/activate
# if vendorField starts with `sc:`
# using default webhook peer (http://127.0.0.1:4004)
./lys deploy-listener transaction.applied dummy.logSomething ^sc:.*$
# or
./lys deploy-listener transaction.applied dummy.logSomething vendorField regexp ^sc:.*$

# if amount >= 25 arks
# using a custom webhook peer
./lys deploy-listener transaction.applied dummy.logSomething amount gte 2500000000 -w http://dpos.arky-delegate.info:4004

# if amount >= 25 arks or vendorField starting with `sc:`
# using a custom webhook peer
./lys deploy-listener transaction.applied dummy.logSomething amount gte 2500000000 vendorField regexp ^sc:.*$ -w http://dpos.arky-delegate.info:4004
```

`lystener` also allows remote deployement using `secp256k1` cryptographic security. The autorized public keys have to be stored in `auth` file as json format in `.json` folder (use `./lys grant`). See below a valid `auth` file :

```json
[
  "030da05984d579395ce276c0dd6ca0a60140a3c3d964423a04e7abe110d60a15e9",
  "02c232b067bf2eda5163c2e187c1b206a9f876d8767a0f1a3f6c1718541af3bd4d"
]
```

Associated private keys are then granted to send PUT and DELETE calls to listener server using `client` module. The private key is never broadcasted.

```python
>>> from lystener import client, rest
>>> # connection to listener is mandatory for security check
>>> rest.connect("http://{ip_0}:{port_0}")
>>> client.link()
... Type or paste your secret>
>>> # once private key generated, security headers are used to sent PUT or
>>> # DELETE call (add or remove listener remotly), emitter is the blockchain
>>> # node sending the webhook, it is not mandatory if listener is installed 
>>> # on blockchain node. Listener server public ip will be used if no
>>> # receiver is defined.
>>>
>>> # /listener/deploy endpoint
>>> client.PUT.listener.deploy(
...    function="dummy.logSomething",
...    event="block.forged",
...    conditions=[("totalFee", "gte", 100000000)],
...    emitter="http://{ip_2}{port_2}",  # blockchain node {ip}:{port}
...    receiver="http://{ip_1}:{port_1}",  # listener {ip}:{port} listening 
... )
>>> # /listener/destroy endpoint
>>> client.DELETE.listener.destroy(
...    id="fa67d0c3-4d88-4038-9818-573d9beac84b",
... )
```

If `client` module not to be used, HTTP request must provide elements below in the headers :

```raw
Public-key: <secp256k1-public-key>
Signature: <[der-stringder]|64-length-hex-string>
Method: <[ecdsa]|schnorr>
Salt: <hex-string>
```

Signature is issued on concatenation of client public-ip with a random `Salt` string (provided in the header) and another one from listener `/salt` endpoint. If `Method` omitted, `ecdsa` signature check is used.

## Launch listener

```bash
~/ark-listener/bash/activate
~/lys start-listening
```

Listener server ip have to be white-listed on blockchain relay. Execute `./lys public-ip` to find ip address.

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

Requirements are checked, and installed if missing, on each startup from `./lys start-listening` command.

## IOT bridge plugin

`lystener` bundles `iot` plugin. It configures a `mosquitto` server at startup and provides a simple `forward` module to send webhook data from blockchain to a specific topic. default configuration is :

```json
{
  "broker": "mqtt://127.0.0.1",
  "topic": "ark/event",
  "qos": 2
}
```

Those defaults can be changed using json-formated file `iot.param` stored in `lystener/.data` folder.

You can listen [binance market](https://www.binance.com/en/trade/ARK_BTC) noise from webhook id [`55cd34c2-0e77-4b91-a0d8-48da6f2a8a64`](http://listen.arky-delegate.info) at `mqtt://listen.arky-delegate.info` on `ark/event` topic. 

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
   lys grant <public-key>...
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
   grant             : allow remote controle to public key owner
   show-log          : show server log
   public-ip         : get public ip
```
