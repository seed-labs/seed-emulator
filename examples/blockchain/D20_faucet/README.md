# Faucet Server

Before sending a transaction to the blockchain, the user's account needs
to have some fund. In most test nets, a faucet server is provided to
fund user's accounts after receiving requests. We have implemented
such a faucet server in our emulator. This example demonstrates how to use it. 

## Table of Content

- [Create a faucet server](#create-faucet-server)
- [Fund accounts during the build time](#fund-account-build-time)
- [Fund accounts during the run time](#fund-account-run-time)
- [Advanced fund account for Developer](#fund-account-advanced)


<a id="create-faucet-server"></a>
## Create Faucet Server

We first need to add a faucet server to a blockchain using the `createFaucetServer` method.
We can specify 4 parameters: `vnode`, `port`, `linked_eth_node`, and `balance`.
- `vnode`: the virtual node name of the faucet server.
- `port`: a port number, used by the faucet server to set up a web server.
- `linked_eth_node`: the faucet server needs to link to an eth node, so it can
  sends out transactions to the blockchain. We just need to provide the name
  of an existing eth node, but we need to make sure that the eth node
  has enabled the http connection (otherwise, it cannot accept external requests). 
- `balance`: set the initial balance (ETH) of the account used by the faucet server.
  This account will be created during the build time and be added to the genesis block.

```python
e5 = blockchain.createNode("poa-eth5").enableGethHttp()

# Faucet Service
blockchain:Blockchain
faucet:FaucetServer = blockchain.createFaucetServer(
           vnode='faucet', 
           port=80, 
           linked_eth_node='poa-eth5',
           balance=1000)
```


## Fund Accounts Using Faucet

<a id="fund-account-build-time"></a>
### (1) Fund accounts during the build time

During the emulator build time, if we already know the account address,
we fund the account directly at the build time.

```python
faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
```

<a id="fund-account-run-time"></a>
### (2) Fund accounts during the run time

Very often, we do not know the account addresses during the build time, because
the accounts are created during the run time. In this case, during the run
time, the user can send a HTTP request to the faucet server to ask
the faucet server to fund a specified account. Data in the request
can be conveyed in two ways: form and json. Here are the examples
using `curl` to send HTTP requests to the faucet server (we can
do this from any host). 

```
curl -X POST -d "address=0x72943017a1fa5f255fc0f06625aec22319fcd5b3&amount=2" http://10.154.0.71:80/fundme 
```

```
curl -X POST -H "Content-Type: application/json" -d '{
  "address": "0x72943017a1fa5f255fc0f06625aec22319fcd5b3",
  "amount": 2
}' http://10.154.0.71:80/fundme
```


## Fund Accounts Using Python

If you want to create a service class that creates Ethereum accounts
dynamically (i.e., during the emulator run time),
you may want to fund the accounts in your service class. 
This `FaucetUserService` example shows you how to do that.

In this manual, we show how to use our `FaucetUserService`.
Detailed instructions on how this service is implemented can be found
in our [developer manual](../../../docs/developer_manual/blockchain/faucet-user-service.md)

To use the faucet, we need to specify the vnode name of the faucet server and the
port number. The `FaucetUserService` will use this information to set up
the script to interact with the faucet server. 

```python
faucetUserService = FaucetUserService()
faucetUserService.install('faucetUser')
faucetUserService.setFaucetServerInfo(vnode = 'faucet', port=80)
emu.addBinding(Binding('faucetUser', filter=Filter(asn=164, nodeName='host_0')))
```

In the example above, we hardcoded the faucet server's name and port number.
To make code more portable, we can get the faucet server information from
the blockchain service. 

```python
faucet_info = blockchain.getFaucetServerInfo()  # returns a list of dictionary
faucetUserService.setFaucetServerInfo(faucet_info[0]['name'], faucet_info[0]['port'])
```

After the emulator starts, we can log into the `faucetUser` container.
We will find a script called `fund.py` in the root folder.
This script is generated during the build time based on the parameters
provided. It sends a fund request for a newly created account.

