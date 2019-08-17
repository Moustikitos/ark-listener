# ark-listener

## Support this project

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://arky-delegate.info/arky)

## Supported blockchain

 * [X] Ark-v2

## Concept

Ark core webhooks trigger POST requests containing data to a targeted peer. This one then have to parse data and trigger code execution.

`ark-listener` uses a Flask application listening every POST requests received with the pattern : `http://{ip}:{port}/module/function`.

If found, `module.function` will be executed with data embeded in the POST request.

## Install

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
./lys deploy-listener transaction.applied forger.logSomething -f vendorField -c regexp -v ^sc:.*$

# if amount >= 25 arks
# using a custom webhook peer
./lys deploy-listener transaction.applied forger.logSomething -f amount -c gte -v 2500000000 -w http://dpos.arky-delegate.info:4004

# if amount >= 25 arks and vendorField starting with `sc:`
# using a custom webhook peer
./lys deploy-listener transaction.applied forger.logSomething -m amount|gte|2500000000,vendorField|regexp|^sc:.*$ -w http://dpos.arky-delegate.info:4004
```

## Launch listener

### For testing purposes

Your listener have to be white-listed on blockchain relay. Execute `./lys public-ip` to get your listener ip address.

```bash
cd ~
ark-listener/bash/activate
pm2 start app.json
```

### In production mode (still under developement)

```bash
cd ~
ark-listener/bash/activate
./lys start-listening
```

## Where is stored code to execute ?

The ark-listener tree contains a `modules` folder where you can save your custom code to execute. If another place is needed, simply add the path to the `modules.pth` file and `lystener` will be able to find it.

## How can I check deployed listeners ?

The listening server redirects browser to listener details page.

## `lys` commands

```bash
cd ~
ark-listener/bash/activate
./lys --help
```

```
Usage:
   lys deploy-listener <event> <function> (<regexp> | -f <field> -c <condition> -v <value> | -m <data>) [-w <webhook>]
   lys destroy-listener
   lys start-listening [-p <port>]
   lys stop-listening
   lys public-ip

Options:
-f --field=<field>         : the transaction field to be checked by the node
-c --condition=<condition> : the condition operator used to check the field
-v --value=<value>         : the value triggering the webhook
-m --multiple=<data>       : coma-separated list of key|operator|value terms
-w --webhook=<webhook>     : the peer registering the webhook
-p --port=<port>           : the port used for listening srv [default: 5001]

Subcommands:
   deploy-listener  : link a webhook <event> with a python <function> 
   destroy-listener : unlink webhook <event> from python <function>
   start-listening  : start/restart listener server
   stop-listening   : stop listener server
   public-ip        : get public ip
```
