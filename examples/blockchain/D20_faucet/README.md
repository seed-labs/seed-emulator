# Faucet Server

Before sending a transaction to the blockchain, the user's account needs
to have some fund. In most test nets, a faucet server is provided to
fund user's accounts after receiving requests. We have implemented
such a faucet server in the SEED blockchain emulator.
This example demonstrates how to use it. 


## Table of Content

- [Create a faucet server](#create-faucet-server)
- [Fund accounts during the build time](#fund-account-build-time)
- [Fund accounts during the run time (using curl)](#fund-account-run-time-curl)
- [Fund accounts during the run time (using Python)](#fund-account-run-time-python)
- [Advanced fund account for Developer](#fund-account-advanced)


<a id="create-faucet-server"></a>
## Create Faucet Server

We first need to add a faucet server to a blockchain. This server
runs a web server, which can transfer the fund in its own account
to whoever requests for fund.  This example uses
a pre-built block component (`D00_ethereum_poa`), which already has a faucet server.
In the [D00_ethereum_poa](../D00_ethereum_poa/) example, these lines are
used to create a faucet server

```python
faucet:FaucetServer = blockchain.createFaucetServer(
           vnode='faucet',
           port=80,
           linked_eth_node='eth5',
           balance=10000,
           max_fund_amount=10)
faucet.setDisplayName('Faucet')
```

We can specify the following parameters: 
- `vnode`: the virtual node name of the faucet server.
- `port`: a port number, used by the faucet server to set up a web server.
- `linked_eth_node`: the faucet server needs to link to an eth node, so it can
  sends out transactions to the blockchain. We just need to provide the name
  of an existing eth node, but we need to make sure that the eth node
  has enabled the http connection (otherwise, it cannot accept external requests). 
- `balance`: set the initial balance (ETH) of the account used by the faucet server.
  This account will be created during the build time and be added to the genesis block.
- `max_fund_amount`: the maximal amount of fund (in Ethers) that can be transferred 
  in each request.

Because this server is already created in the base component,
we just need to get an instance of this object:

```python
eth         = emu.getLayer('EthereumService')
blockchain  = eth.getBlockchainByName(eth.getBlockchainNames()[0])
faucet_name = blockchain.getFaucetServerNames()[0]
faucet      = blockchain.getFaucetServerByName(faucet_name)
```


## Fund Accounts Using Faucet

<a id="fund-account-build-time"></a>
### (1) Fund accounts during the build time

During the emulator build time, if we already know the account address,
we can ask the faucet to fund it, so when the 
emulator starts, the faucet server will carry out the fund transfer. 

```python
faucet.fund('0x72943017a1fa5f255fc0f06625aec22319fcd5b3', 2)
```

<a id="fund-account-run-time-curl"></a>
### (2) Fund accounts during the run time (using curl)

Very often, we do not know the account addresses during the build time, because
the accounts are created during the run time. In this case, during the run
time, the user can send a HTTP request to the faucet server to ask
the faucet server to fund a specified account. Data in the request
can be conveyed in two ways: form and json. Here are the examples
that use `curl` to send HTTP requests to the faucet server (we can
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

<a id="fund-account-run-time-python"></a>
### (3) Fund accounts during the run time (using Python)

We can write Python programs to interact with the Faucet server.
A helper class
called [FaucetHelper.py](../../../library/blockchain/FaucetHelper.py)
is created to make writing such programs easier.



<a id="fund-account-advanced"></a>
## Advanced fund account for Developer

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

