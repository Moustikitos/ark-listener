# ark-listener

## Concept

Ark core webhooks triggers POST requests containing data as JSON object to a
targeted peer. This one then have to parse this data to trigger code execution.

`ark-listener` uses a Flask application parsing every POST requests received with
the pattern : `http://0.0.0.0:5001/module/function`.

for example, a POST to `http://0.0.0.0:5001/hyperledger/executeInsurancePolicy`
will be understand as : execute `executeInsurancePolicy` function from `hyperledger`
module with JSON found in request. In this particular case, the python code
triggered have to send data to hyperledger according to the targeted smart
contract specification.

## Supported blockchain

 * [X] Ark-v2

## Install

```bash
wget https://raw.githubusercontent.com/Moustikitos/ark-listener/master/bash/lys-install.sh
bash install.sh
```

## `lys` commands

```bash
cd ~
./lys --help
```

```
Usage:
   lys deploy-listener <event> <function> (<regexp> | -f <field> -c <condition> -v <value>) [-l <listener> -w <webhook>]
   lys destroy-listener [<function>]
   lys start-server
   lys stop-server

Options:
-f --field=<field>         : the transaction field to be checked by the node
-c --condition=<condition> : the condition operator used to check the field
-v --value=<value>         : the value triggering the webhook
-l --listener=<listener>   : the peer receiving whebhook POST request
-w --webhook=<webhook>     : the peer registering the webhook

Subcommands:
   deploy-listener  : link a webhook <event> with a python <function> 
   destroy-listener : unlink webhook <event> from python <function>
   start-server     : start/restart listener server
   stop-server      : stop listener server
```

## Example

Link a `transaction.applied` event to executeInsurancePolicy function from
`hyperledger.py` python module parsing vendorField content (4 ways).

```bash
./lys deploy-listener transaction.applied hyperledger.executeInsurancePolicy ^sc:.*$
```
```python
>>> from lys import deploy_listener
>>> deploy_listener(
...     event=transaction.applied",
...     function="hyperledger.executeInsurancePolicy",
...     regexp=r"^sc:.*$")
```

or

```bash
./lys deploy-listener transaction.applied hyperledger.executeInsurancePolicy -f vendorField -c regexp -v ^sc:.*$
```
```python
>>> from lys import deploy_listener
>>> deploy_listener(
...     event="transaction.applied",
...     function="hyperledger.executeInsurancePolicy",
...     field="vendorField",
...     condition="regexp",
...     value=r"^sc:.*$")
```

Now each transaction with vendorField starting with `sc:` will trigger
`executeInsurancePolicy`. Webhook peer is `http://127.0.0.1:4004` and listener
one is `http://127.0.0.1:5001`. Lystener server and webhook-api-enabled
ark-core-relay instance have to be running on the node then.
