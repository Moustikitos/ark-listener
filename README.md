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

Ark core webhooks trigger POST requests containing data to a targeted peer. This one then have to parse data and trigger code execution.

`ark-listener` uses python server app listening every POST requests received with the pattern : `http://{ip}:{port}/module/function`.

If found, `module.function` will be executed with data embeded in the POST request.

## Command line

```
Usage:
   lys deploy-listener <event> <function> (<regexp> | (<field> <condition> <value>)...) [-w <webhook>]
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
-w --webhook=<webhook> : the peer registering the webhook
-p --port=<port>       : the port used for listening srv [default: 5001]

Subcommands:
   deploy-listener    : link a webhook <event> with a python <function>
   update-listener    : change <event> trigger conditions
   destroy-listener   : unlink webhook <event> from python <function>
   lys show-listeners : print a sumary of listeners
   start-listening    : start/restart listener server
   restart-listeners  : restart listener server
   stop-listening     : stop listener server
   show-log           : show server log
   public-ip          : get public ip
   grant              : allow remote controle to <public-key> owner
```