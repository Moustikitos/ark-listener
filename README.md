# ark-listener

## Support this project

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://arky-delegate.info/arky)

## Supported blockchain

 * [X] Ark-v2

## Install

```bash
 bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-listener/master/bash/lys-install.sh)
```

## Concept

Ark core webhooks triggers POST requests containing data as JSON object to a targeted peer. This one then have to parse data and trigger code execution.

`ark-listener` uses a Flask application listening every POST requests received with the pattern : `http://0.0.0.0:5001/module/function`.

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
   lys deploy-listener <event> <function> (<regexp> | -f <field> -c <condition> -v <value>) [-l <listener> -w <webhook>]
   lys destroy-listener [<function>]
   lys start-listening [-i <ip> -p <port>]
   lys stop-listening
   lys public-ip

Options:
-f --field=<field>         : the transaction field to be checked by the node
-c --condition=<condition> : the condition operator used to check the field
-v --value=<value>         : the value triggering the webhook
-l --listener=<listener>   : the peer receiving whebhook POST request
-w --webhook=<webhook>     : the peer registering the webhook
-i --ip=<ip>               : the ip used for listening server   [default: 0.0.0.0]
-p --port=<port>           : the port used for listening server [default: 5001]

Subcommands:
   deploy-listener  : link a webhook <event> with a python <function> 
   destroy-listener : unlink webhook <event> from python <function>
   start-listening  : start/restart listener server
   stop-listening   : stop listener server
   public-ip        : get public ip (to be whitelisted on ark relay)
```
