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
  "fee": 10000000,
  "id": "3a070fcd16ae0e6214df9ea209e3091ee751808016bef5eca0e16453931be1f9",
  "recipientId": "DFyUhQW52sNB5PZdS7VD9HknwYrSNHPQDq",
  "senderId": "D7seWn8JLVwX4nHd9hh2Lf7gvZNiRJ7qLk",
  "senderPublicKey": "03a02b9d5fdd1307c2ee4652ba54d492d1fd11a7d1bb3f3a44c4a05e79f19de933",
  "signSignature": "304402204c23a6275b8ab56a5c77b10fe17036dc664ffda587f8a0356011676758ecc26602207af61465756c87f462afc568627051dedee67d9c74489684c4d64ea802a34f13",
  "signature": "3045022100a75fd350967e7524dc9fb66a490e814a408c79f8a3d44fe75f71299f8c6b65af02207313dd3f33d83700ad32a89d3de506e64cd81472c9b60e46b67f4d66c28117b3",
  "timestamp": 50645384,
  "type": 0,
  "vendorField": "sc:ins:PolicyPaymentTransaction:0123"
}
```
```
2018-10-28 17:30 +00:00: Sending content to http://159.89.146.143:3000/api/PolicyPaymentTransaction: {
2018-10-28 17:30 +00:00:   "policy": "resource:io.arklabs.InsurancePolicy#0123", 
2018-10-28 17:30 +00:00:   "$class": "io.arklabs.PolicyPaymentTransaction", 
2018-10-28 17:30 +00:00:   "amountPaid": 100000000, 
2018-10-28 17:30 +00:00:   "arkTransaction": {
2018-10-28 17:30 +00:00:     "signSignature": "3044022019bcd27d01b6223692f55e89989a63fdca64036ca7353bc0d4f77cde418763e30220604d8cd5fce89a1cba224526ea6ccfd7ac5f3eefff4a746df16cf6fd69832e65", 
2018-10-28 17:30 +00:00:     "fee": "10000000", 
2018-10-28 17:30 +00:00:     "network": 30, 
2018-10-28 17:30 +00:00:     "timestamp": 50646617, 
2018-10-28 17:30 +00:00:     "signature": "304302204a7cdf0aba4e03bcc4a609fd394834c7c4b6d970f0c52a7c1bddd38b94e100d2021f2a37cd38635e2ab4207cb3d22b55803553a955ed8318e006d6a04c954d4a06", 
2018-10-28 17:30 +00:00:     "recipientId": "DFyUhQW52sNB5PZdS7VD9HknwYrSNHPQDq", 
2018-10-28 17:30 +00:00:     "senderPublicKey": "03a02b9d5fdd1307c2ee4652ba54d492d1fd11a7d1bb3f3a44c4a05e79f19de933", 
2018-10-28 17:30 +00:00:     "vendorField": "sc:ins:PolicyPaymentTransaction:0123", 
2018-10-28 17:30 +00:00:     "amount": "100000000", 
2018-10-28 17:30 +00:00:     "version": 1, 
2018-10-28 17:30 +00:00:     "expiration": 0, 
2018-10-28 17:30 +00:00:     "vendorFieldHex": "73633a696e733a506f6c6963795061796d656e745472616e73616374696f6e3a30313233", 
2018-10-28 17:30 +00:00:     "id": "aede05e3113722f52c59f7456838e8ccc16d69f8e3467e325adf52a423f1a517", 
2018-10-28 17:30 +00:00:     "type": 0, 
2018-10-28 17:30 +00:00:     "secondSignature": "3044022019bcd27d01b6223692f55e89989a63fdca64036ca7353bc0d4f77cde418763e30220604d8cd5fce89a1cba224526ea6ccfd7ac5f3eefff4a746df16cf6fd69832e65"
2018-10-28 17:30 +00:00:   }
2018-10-28 17:30 +00:00: }
2018-10-28 17:30 +00:00: >>> Transaction sent to hyperledger...
2018-10-28 17:30 +00:00: >>> executeInsurancePolicy response:
2018-10-28 17:30 +00:00: {
2018-10-28 17:30 +00:00:   "policy": "resource:io.arklabs.InsurancePolicy#0123", 
2018-10-28 17:30 +00:00:   "$class": "io.arklabs.PolicyPaymentTransaction", 
2018-10-28 17:30 +00:00:   "amountPaid": "100000000", 
2018-10-28 17:30 +00:00:   "transactionId": "a3e7f5186ff8b049758fa91a2438da71b151c554b91f111411e50764a6b0e974", 
2018-10-28 17:30 +00:00:   "arkTransaction": "[object Object]"
2018-10-28 17:30 +00:00: }
```
