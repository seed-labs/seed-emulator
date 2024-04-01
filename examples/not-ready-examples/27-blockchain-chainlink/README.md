# Table of Contents
[What is Chainlink?](#chainlink)

[Chainlink Initializer Node](#chainlink-initializer-node)

[Chainlink Normal Node](#chainlink-normal-node)


## Terms
Accounts:
- A : For chainlink initializer node to deploy link token contract
- B : Created by chainlink statup command to send transactions to oracle contract
- C : For chainlink normal node to deploy oracle contract

Contracts:
- X :   LINK token contract
- Y :   Oracle contract

## Chainlink

### What is Chainlink?
Chainlink is a decentralized oracle network that provides a critical service to the blockchain ecosystem. It securely and reliable connects smart contracts to external data sources, APIs, off-chain computation.


## Chainlink Service
Chainlink service on the seed emulator is based on two types of server. One is the Chainlink initalizer server and the other is the Chainlink normal server. In the upcoming section, we will discuss how Chainlink service is setup on the seed emulator.

### Chainlink Initializer Node
Chainlink initializer server is used to deploy the LINK token contract, and there is also a webserver running from where the users will be able to get the contract address of the LINK token, and oracle contracts deployed by the chainlink normal server.

### Flow of Chainlink Initializer Node
![Chainlink Initializer Server](./fig/Chainlink_Init_Service.jpeg)
1. The initializer node will wait for the blockchain to be ready.
2. Once the blockchain is ready, the initializer node will create a new web3 account (A).
3. Then it will request the faucet service to transfer some ether to the newly created account (A).
4. After receiving the ether, the initializer node will deploy the LINK token contract (X).
5. Once the LINK token contract is deployed, the initializer node will start a web server and a flask server. The LINK token address will be displayed on the web server for the users to use. The flask server will be used by Chainlink normal nodes to send a post request with the oracle contract address. This will be also displayed on the web server so the users can use it.

### Code for Chainlink Initializer Node
```python
chainlink = ChainlinkService()
cnode = 'chainlink_init_server'
# Install the Chainlink initializer service
c_init = chainlink.installInitializer(cnode)
# Set the faucet URL or node name
c_init.setFaucetUrl(vnode="faucet", port=3000)
# Set the RPC to connect to the blockchain
c_init.setRPCbyEthNodeName('eth2')
service_name = 'Chainlink-Init'
emu.getVirtualNode(cnode).setDisplayName(service_name)
# Bind the Chainlink initializer service to an asn
emu.addBinding(Binding(cnode, filter = Filter(asn=164, nodeName='host_2')))
```

### Chainlink Normal Node
Chainlink normal server is used to deploy the oracle contracts. The oracle contracts are used to get the data from the external world and send it to the smart contracts. The oracle contracts are deployed by the Chainlink normal server and the oracle contract address is sent to the Chainlink initializer server.

### Flow of Chainlink Normal Node
![Chainlink Normal Server](./fig/Chainlink_Normal_Service.jpeg)
1. The normal node will will start the chainlink servies which will create a new chainlink web3 account (B).
2. Then it will request the faucet service to transfer some ether to the newly created account (B).
3. After sending the faucet request the normal node will wait for the initializer node to deploy the LINK token contract, and from the web server it will get the LINK token address (X).
4. Once the LINK token address (X) is received, the normal node will create a new account (C), request faucet service to transfer some ether to the newly created account (C).
5. After receiving the ether, the normal node will deploy the oracle contract (Y).
6. Once the oracle contract is deployed, the normal node will invoke Y.setAuthorizedSenders([B]) to authorize the chainlink created account (B) to send data/transaction to the oracle contract (Y).
7. After this is done, the normal node will send a post request to the flask server running on the initializer node with the oracle contract address (Y).
8. Then using the oracle contract address (Y) the initializer node will configure generic jobs for the chainlink service.

### Code for Chainlink Normal Node
```python
# Install the Chainlink normal service
c_normal = chainlink.install(cnode)
# Set the RPC to connect to the blockchain
c_normal.setRPCbyEthNodeName('eth{}'.format(i))
c_normal.setInitNodeIP("chainlink_init_server")
# Set the faucet URL or node name
c_normal.setFaucetUrl(vnode="faucet", port=3000)
emu.getVirtualNode(cnode).setDisplayName(service_name)
emu.addBinding(Binding(cnode, filter = Filter(asn=asn, nodeName='host_2')))
```

## To-Do
- Add the user flow example for the chainlink service.
