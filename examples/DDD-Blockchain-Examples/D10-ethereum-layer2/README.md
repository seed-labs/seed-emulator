# Ethereum Layer2 Example

This an example showing how to install, configure, and interact with layer2 blockchain. The layer2 blockchain relies on the [ethereum layer](../B06-blockchain/README.md), and this example is using a POA blockchain.

## Table of Content

- [Building the Layer2 Blockchain](#building-the-layer2-blockchain)
- [Interacting with Layer2 Blockchain](#interacting-with-layer2-blockchain)

## Building the Layer2 Blockchain

### A.0 Generate the layer2 privileged & test accounts

Four accounts will be generated for the layer2 service:

- `GS_ADMIN` has the ability to upgrade layer2 system contracts and settings (e.g. layer2 gasprice, other privileged accounts) on layer1.
- `GS_BATCHER` publishes Sequencer transaction data to layer1.
- `GS_PROPOSER` publishes L2 transaction results (state roots) to L1.
- `GS_SEQUENCER` signs blocks on the layer2 p2p network (for a more rapid blockchain state synchronization).
- `GS_TEST` will be used by the [L2Util](./L2Util.py) to interact with layer2.

```python
# Generate privileged & test accounts for layer2
accs = generateAccounts()
```

### A.1 Create a layer1 (Ethereum) blockchain

This example is using a POA blockchain for simplicity.

```python
# Create the Ethereum layer
eth = EthereumService(override=True)

# Create the 1 Blockchain layers, which is a sub-layer of Ethereum layer
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create blockchain nodes (POA Ethereum)
e5 = blockchain.createNode("poa-eth5")
e6 = blockchain.createNode("poa-eth6")
e7 = blockchain.createNode("poa-eth7")
e8 = blockchain.createNode("poa-eth8")
...
# Start mining on e5,e6
e5.setBootNode(True).unlockAccounts().startMiner()
e6.unlockAccounts().startMiner()
...
# Binding virtual nodes to physical nodes
emu.addBinding(Binding("poa-eth5", filter=Filter(asn=160, nodeName="host_0")))
emu.addBinding(Binding("poa-eth6", filter=Filter(asn=161, nodeName="host_0")))
emu.addBinding(Binding("poa-eth7", filter=Filter(asn=162, nodeName="host_0")))
emu.addBinding(Binding("poa-eth8", filter=Filter(asn=163, nodeName="host_0")))

# Add the ethereum layer
emu.addLayer(eth)
```

### A.2 Customize layer1 genesis file

For the layer1 blockchain, some customizations are needed for layer2 blockchain deployment:

- Change the gaslimit to 30,000,000 (Default gaslimit is 4,700,000, not sufficient for deploying some layer2 smart contracts)
- Pre-deploy the smart contract factory (Need to be at the specific address)
- Fund the admin accounts (these accounts are used for deploying SC, submitting L2 batches/states, etc.)

```python
# Customize blockchain genesis file
initBal = 10**8
# Set the gas limit per block to 30,000,000 for layer2 smart contract deployment
blockchain.setGasLimitPerBlock(30_000_000)
# Pre-deploy the smart contract factory for layer2 smart contract deployment
blockchain.addLocalAccount(EthereumLayer2SCFactory.ADDRESS.value, 0)
blockchain.addCode(EthereumLayer2SCFactory.ADDRESS.value, EthereumLayer2SCFactory.BYTECODE.value)
# Funding accounts
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_ADMIN][0], initBal)
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_BATCHER][0], initBal)
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_PROPOSER][0], initBal)
blockchain.addLocalAccount(accs[EthereumLayer2Account.GS_TEST][0], initBal)
```

### A.3 Enable geth http of layer1 nodes

Layer2 nodes are required to connect to a layer1 node. At least one node in layer1 blockchain should enable geth http.

```python
# Enable ws and http connections
# Set geth ws port to 8541 (Default : 8546)
e5.enableGethWs().setGethWsPort(8541)
e5.enableGethHttp()
e6.enableGethHttp()
e7.enableGethHttp()
```

### A.4 Create and configure layer2 service & blockchain

The layer2 blockchain is required to configure an layer1 node (geth http enabled).  
Also, the four accounts funded in previous step should also be configured.

```python
# Create Layer2 service
l2 = EthereumLayer2Service()

# Create a Layer2 blockchain, name is required
l2Bkc = l2.createL2Blockchain("test")

# Set the layer1 node to be connected for all the nodes in this layer2 blockchain
# All the layer2 nodes are required to connect to a layer1 node
l2Bkc.setL1VNode("poa-eth5", e5.getGethHttpPort())

# Configure the admin accounts for layer2 blockchain
# Admin, batcher, proposer, and test must be funded in the layer1 blockchain
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_ADMIN, accs[EthereumLayer2Account.GS_ADMIN]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_BATCHER, accs[EthereumLayer2Account.GS_BATCHER]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_PROPOSER, accs[EthereumLayer2Account.GS_PROPOSER]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_SEQUENCER, accs[EthereumLayer2Account.GS_SEQUENCER]
)
l2Bkc.setAdminAccount(
    EthereumLayer2Account.GS_TEST, accs[EthereumLayer2Account.GS_TEST]
)
```

### A.5 Create layer2 nodes

There are three types of nodes in layer2 blockchain:

- `sequencer`: Must have only one sequencer node in a layer2 blockchain
- `deployer`: Must have only one deployer node in a layer2 blockchain
- `non-sequencer`: Can have an arbitrary amount of non-sequencer nodes in a layer2 blockchain

```python
# Create layer2 nodes
# Set l2-1 to be a sequencer node, only one sequencer node is allowed in a layer2 blockchain
l2_1 = l2Bkc.createNode("l2-1", EthereumLayer2Node.SEQUENCER)

# Each node can have a individual layer1 node to connect to,
# this setting will override the blockchain setting
l2_2 = l2Bkc.createNode("l2-2").setL1VNode("poa-eth6", e6.getGethHttpPort())

# Default type of the node is the non-sequencer node
l2_3 = l2Bkc.createNode("l2-3").setHttpPort(9545)
l2_4 = l2Bkc.createNode("l2-4").setWSPort(8547)

# Set the deployer node, which is used to deploy the smart contract
# Only one deployer node is allowed in a layer2 blockchain
deployer = l2Bkc.createNode("l2-deployer", EthereumLayer2Node.DEPLOYER)
```

### A.6 Bind layer2 service to the emulator

At the end, each layer2 virtual node should be bound with a physical node in the emulator.  
After binding the nodes, add layer2 service to the emulator.

```python
# Add the ethereum layer
emu.addLayer(eth)

emu.addBinding(Binding("l2-1", filter=Filter(asn=150, nodeName="host_0")))
emu.addBinding(Binding("l2-2", filter=Filter(asn=151, nodeName="host_0")))
emu.addBinding(Binding("l2-3", filter=Filter(asn=152, nodeName="host_0")))
emu.addBinding(Binding("l2-4", filter=Filter(asn=153, nodeName="host_0")))
emu.addBinding(Binding("l2-deployer", filter=Filter(asn=154, nodeName="host_0")))

emu.addLayer(l2)

emu.render()

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(docker, "./output", override=True)
```

### Optional settings

- `l2node.setL1VNode("poa-eth6", e6.getGethHttpPort())` override the blockchain l1vnode config for a node
- `l2node.createNode("l2-3").setHttpPort(9545)` change the node's geth http port (default 8545)
- `l2node.createNode("l2-3").setWSPort(8547)` change the node's geth ws port (default 8545)

## Interacting with Layer2 Blockchain

There are two ways to interact with a layer2 blockchain:

- Use geth inside the docker container
- Use the `L2Util.py` command line tool

### B.1 Using geth

To use geth inside the docker container please refer to the ethereum [documentation](../B06-blockchain/README.md#use-blockchain)

### B.2 Using L2Util

#### B.2.0 Save configs

These configs are required to set before using the cmd line tool:

- `l1Port`: a layer1 node's geth http port (need to be enabled and forwarded to the host)
- `l2Port`: a layer2 node's(sequencer/non-sequencer) geth http port (need to be forwarded to the host)
- `deployerPort`:the layer2 deployer node's web server port (need to be forwarded to the host)
- `l1ChainId`: the layer1 blockchain chain id
- `l2ChainId`: the layer2 blockchain chain id

For example, in `layer2.py`:

```python
# Configs for L2Util
L1_PORT = 12545
L2_PORT = 8545
DEPLOYER_PORT = 8888
...
emu.getVirtualNode("poa-eth7").setDisplayName("Ethereum-POA-7").addPortForwarding(
    L1_PORT, e7.getGethHttpPort()
)
...
# Generate privileged & test accounts for layer2
accs = generateAccounts()
...
# Save the configuration to interact with the layer2 blockchain
writeConfig(L1_PORT, L2_PORT, DEPLOYER_PORT, blockchain.getChainId(), l2Bkc.getChainID())
```

#### B.2.1 `monitor` monitor layer2 blockchain status

Monitor the layer2 blockchain blocks  

usage: `$ ./L2Util.py monitor <isL2: true/false> [custom RPC]`  
example: `$ ./L2Util.py monitor true` (the l2 geth http port must be forwarded)  
output:

```shell
Connected to RPC: http://localhost:8545
Current block number: 428
======================================================================
Block number: 429, timestamp: 1713327503, hash: 0xd69ed1d9507d4094e318ad38fbe4680f488f603a06262afd7bc3f1b05b2d9cb1, tx count: 1
----------------------------------------------------------------------
Transaction hashes:
......................................................................
  0xc9f6f02082648c78d7f5007a7e47d769df58128a71c3e0951a5e07b86e9ebf45
......................................................................
----------------------------------------------------------------------
======================================================================
Block number: 430, timestamp: 1713327505, hash: 0x70a185052cec1d91397687a6fd79aacae859f1ec93158bf49fc0878529d0dcdc, tx count: 1
----------------------------------------------------------------------
Transaction hashes:
......................................................................
  0xc659baf75ebf86168f9f04bbf0ebfbf59f8ba58f09aaed9d7be3d5968a79e2a6
......................................................................
----------------------------------------------------------------------
======================================================================
```

#### B.2.2 `deposit` deposit ETH from layer1 to layer2

Deposit test account's (defined in the example) ETH from layer1 to layer2.  

usage: `$ ./L2Util.py deposit [amount in ether (default=1)]`  
example: `$ ./L2Util.py deposit` (the l1, l2 geth http ports must be forwarded)  
output:

```shell
L1 balance before: 99999998993978000000000000
L2 balance before: 999978982765118528
L1 deposit transaction sent: 0xc854b390154c90dd991bce3b19e699dd722a3736f5bcadbdb97f86901ac681ee
Waiting for L2 transaction to be mined...
L1 balance after: 99999997988127000000000000
L2 balance after: 1999978982765118528
```

#### B.2.3 `sendTx` send a layer2 tx

This command can send a simple transaction using the test account (defined in the example).  
**Note: Must deposit before sending a layer2 tx**  

usage: `$ ./L2Util.py <to> [value in ether (default=0)] [data (default=0x)]`  
example: `$ ./L2Util.py sendTx 0x2DDAaA366dc75119A256C41b9bd483D13A64389d 0.1 0x10` (the l2 geth http port must be forwarded)  
output:

```shell
L2 transaction sent: 0x954146bd223102e9380b09fb4417301db3001016031e84ea44ac8551d826e434
Waiting for transaction to be mined...
Transaction receipt: AttributeDict({'blockHash': HexBytes('0xf78331202785c516c6402fc45eaf6c130081fb727249d4405a6d594b3ce452ab'), 'blockNumber': 481, 'contractAddress': None, 'cumulativeGasUsed': 84969, 'effectiveGasPrice': 1000000000, 'from': '0x2DDAaA366dc75119A256C41b9bd483D13A64389d', 'gasUsed': 21016, 'l1Fee': '0x499acbc0', 'l1FeeScalar': '1', 'l1GasPrice': '0x4ddce', 'l1GasUsed': '0xf20', 'logs': [], 'logsBloom': HexBytes('0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'), 'status': 1, 'to': '0x2DDAaA366dc75119A256C41b9bd483D13A64389d', 'transactionHash': HexBytes('0x954146bd223102e9380b09fb4417301db3001016031e84ea44ac8551d826e434'), 'transactionIndex': 1, 'type': '0x0'})
```