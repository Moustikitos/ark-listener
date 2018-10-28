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

### Deploy a simple trigger

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

### Send a transaction with appropriate vendorField
```
{
  "amount": 100000000,
  "asset": {},
  "fee": 10000000,
  "id": "e7c4d70e837df92f90212503c8204e44bc080b3a1ccfe1c923816d4692ce3e31",
  "recipientId": "DFyUhQW52sNB5PZdS7VD9HknwYrSNHPQDq",
  "senderId": "D7seWn8JLVwX4nHd9hh2Lf7gvZNiRJ7qLk",
  "senderPublicKey": "03a02b9d5fdd1307c2ee4652ba54d492d1fd11a7d1bb3f3a44c4a05e79f19de933",
  "signSignature": "3045022100a83fa3bd7bde02a44594b5c8ed5aa372508b4db360a207066fb7fbab9b22a67802206e6411b583b26e25d168a2742bf6e2fbf59b15bef9a27de4f7c2afa26a992e08",
  "signature": "3045022100d8ff38c891f5c3cd2267b6da13000807b38db81074cf15567f1b6a809377ec430220606f2ba1505a822a1946203c3d1a0b34314b34f35612c4bb10813049374eaf3b",
  "timestamp": 50646949,
  "type": 0,
  "vendorField": "sc:ins:PolicyPaymentTransaction:0123"
}
```
```
2018-10-28 17:36 +00:00: Sending content to http://159.89.146.143:3000/api/PolicyPaymentTransaction: {
2018-10-28 17:36 +00:00:   "policy": "resource:io.arklabs.InsurancePolicy#0123", 
2018-10-28 17:36 +00:00:   "$class": "io.arklabs.PolicyPaymentTransaction", 
2018-10-28 17:36 +00:00:   "amountPaid": "100000000", 
2018-10-28 17:36 +00:00:   "arkTransaction": "{\"signSignature\": \"3045022100a83fa3bd7bde02a44594b5c8ed5aa372508b4db360a207066fb7fbab9b22a67802206e6411b583b26e25d168a2742bf6e2fbf59b15bef9a27de4f7c2afa26a992e08\", \"fee\": \"10000000\", \"network\": 30, \"timestamp\": 50646949, \"signature\": \"3045022100d8ff38c891f5c3cd2267b6da13000807b38db81074cf15567f1b6a809377ec430220606f2ba1505a822a1946203c3d1a0b34314b34f35612c4bb10813049374eaf3b\", \"recipientId\": \"DFyUhQW52sNB5PZdS7VD9HknwYrSNHPQDq\", \"senderPublicKey\": \"03a02b9d5fdd1307c2ee4652ba54d492d1fd11a7d1bb3f3a44c4a05e79f19de933\", \"vendorField\": \"sc:ins:PolicyPaymentTransaction:0123\", \"amount\": \"100000000\", \"version\": 1, \"expiration\": 0, \"vendorFieldHex\": \"73633a696e733a506f6c6963795061796d656e745472616e73616374696f6e3a30313233\", \"id\": \"e7c4d70e837df92f90212503c8204e44bc080b3a1ccfe1c923816d4692ce3e31\", \"type\": 0, \"secondSignature\": \"3045022100a83fa3bd7bde02a44594b5c8ed5aa372508b4db360a207066fb7fbab9b22a67802206e6411b583b26e25d168a2742bf6e2fbf59b15bef9a27de4f7c2afa26a992e08\"}"
2018-10-28 17:36 +00:00: }
2018-10-28 17:36 +00:00: >>> Transaction sent to hyperledger...
2018-10-28 17:36 +00:00: >>> executeInsurancePolicy response:
```
**hyperledger response**
```
2018-10-28 17:36 +00:00: {
2018-10-28 17:36 +00:00:   "policy": "resource:io.arklabs.InsurancePolicy#0123", 
2018-10-28 17:36 +00:00:   "$class": "io.arklabs.PolicyPaymentTransaction", 
2018-10-28 17:36 +00:00:   "amountPaid": "100000000", 
2018-10-28 17:36 +00:00:   "transactionId": "e68e87b897618b7008f110e145ef2ff48687a9da783dbb82884ed2574c46ca2a", 
2018-10-28 17:36 +00:00:   "arkTransaction": "{\"signSignature\": \"3045022100a83fa3bd7bde02a44594b5c8ed5aa372508b4db360a207066fb7fbab9b22a67802206e6411b583b26e25d168a2742bf6e2fbf59b15bef9a27de4f7c2afa26a992e08\", \"fee\": \"10000000\", \"network\": 30, \"timestamp\": 50646949, \"signature\": \"3045022100d8ff38c891f5c3cd2267b6da13000807b38db81074cf15567f1b6a809377ec430220606f2ba1505a822a1946203c3d1a0b34314b34f35612c4bb10813049374eaf3b\", \"recipientId\": \"DFyUhQW52sNB5PZdS7VD9HknwYrSNHPQDq\", \"senderPublicKey\": \"03a02b9d5fdd1307c2ee4652ba54d492d1fd11a7d1bb3f3a44c4a05e79f19de933\", \"vendorField\": \"sc:ins:PolicyPaymentTransaction:0123\", \"amount\": \"100000000\", \"version\": 1, \"expiration\": 0, \"vendorFieldHex\": \"73633a696e733a506f6c6963795061796d656e745472616e73616374696f6e3a30313233\", \"id\": \"e7c4d70e837df92f90212503c8204e44bc080b3a1ccfe1c923816d4692ce3e31\", \"type\": 0, \"secondSignature\": \"3045022100a83fa3bd7bde02a44594b5c8ed5aa372508b4db360a207066fb7fbab9b22a67802206e6411b583b26e25d168a2742bf6e2fbf59b15bef9a27de4f7c2afa26a992e08\"}"
2018-10-28 17:36 +00:00: }
```
