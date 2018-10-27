# ark-listener

## Supported blockchain

 * [X] Ark-v2

## Install

```bash
wget https://raw.githubusercontent.com/Moustikitos/ark-listener/master/bash/lys-install.sh
bash lys-install.sh
```

## Concept

Ark core webhooks triggers POST requests containing data as JSON object to a
targeted peer. This one then have to parse data and trigger code execution.

`ark-listener` uses a Flask application listening every POST requests received
with the pattern : `http://0.0.0.0:5001/module/function`.

for example, a POST to `http://0.0.0.0:5001/hyperledger/executeInsurancePolicy`
will be understand as : execute `executeInsurancePolicy` function from `hyperledger`
module with JSON found in request. In this particular case, the python code
triggered have to send data to hyperledger according to the targeted smart
contract specification.

## Where is stored code to execute ?

The ark-listener tree contains a `modules` folder where you can save your
custom code to execute. If another place is needed, simply add the path to the
`modules.pth` file and `lystener` will be able to find it.

## How can I check deployed listeners ?

The listening server redirects browser to listener details page.

## `lys` commands

```bash
cd ~
./lys --help
```

```
Usage:
   lys deploy-listener <event> <function> (<regexp> | -f <field> -c <condition> -v <value>) [-l <listener> -w <webhook>]
   lys destroy-listener [<function>]
   lys start-listening [-i <ip> -p <port>]
   lys stop-listening

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
```

## Example

Link a `transaction.applied` event to `executeInsurancePolicy` function from
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

```
{
  "amount": 100000000,
  "asset": {},
  "fee": 5128149,
  "id": "79af5a0fa8ffdc166a3fceb4ae6fd4d80e53e57db2bb0eed849979fe45693bf2",
  "recipientId": "DGuuCwJYoEheBAC4PZTBSBasaDHxg2e6j7",
  "senderId": "D7seWn8JLVwX4nHd9hh2Lf7gvZNiRJ7qLk",
  "senderPublicKey": "03a02b9d5fdd1307c2ee4652ba54d492d1fd11a7d1bb3f3a44c4a05e79f19de933",
  "signSignature": "304402200d89ce33ffe5a89b70cec179ca80541380cd1e3b2c7332b6f69dd36f315ce5ba022022969c81184a1f8051b846bd8d41daafc92959229736dc6cb3a79995e92a95d3",
  "signature": "30450221008f19ec684b890464da23f18bcc741a1f5b46bb4a6b130c8b1d3c0078e2e89a7002207283460aa9ac1f0eb2ddf195a8f3ede6c7de4053652df76528322f608d0d2640",
  "timestamp": 50540092,
  "type": 0,
  "vendorField": "sc:ins:PolicyPaymentTransaction:2345"
}
```
```
2018-10-27 11:56 +00:00: >>> Transaction sent to hyperledger...
2018-10-27 11:56 +00:00: >>> [10/27/18 11:56:42] executeInsurancePolicy response:
2018-10-27 11:56 +00:00: ConnectionError(MaxRetryError("HTTPConnectionPool(host='159.89.146.143', port=3000): Max retries exceeded with url: /api/PolicyPaymentTransaction (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f30a680c050>: Failed to establish a new connection: [Errno 111] Connection refused',))",),)
```
