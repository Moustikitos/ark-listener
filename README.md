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

## Install development version

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-listener/master/bash/lys-install.sh)
```
