# How to run Ethereum PoS private network - The Merge

In this example, we show how the SEED Emulator to emulate
The Merge that is an upgrade to proof-of-stake.
In the real world, consensus transition occurs from proof-of-work
to proof-of-stake. However, in the emulation, we starts the
blockchain with proof-of-authority and then transits to proof-of-stake.
With proof-of-authority, we can allocate a balance to specific accounts
and we do not need to wait for miner to accumulate enough Ethereum to
stake for proof-of-stake consensus.

![](pics/POS-1.png)

## Table of contents

### [1. Emulate The Merge](#1-emulate-the-merge-1)

#### [1.1 Internet Emulator Base](#11-internet-emulator-base-1)

#### [1.2 Creating Ethereum POS Node](#12-creating-ethereum-pos-node-1)

#### [1.3 Creating Beacon Setup Node ](#13-creating-beacon-setup-node-1)

#### [1.4 Set a node as a bootnode](#14-set-a-node-as-a-bootnode-1)

#### [1.5 Add Validator](#15-add-validator-1)

### [2. Introduction to PoS](#2-introduction-to-pos-1)

# 1. Emulate `The Merge`

## 1.1 Internet Emulator Base

In this example, we emulate the internet with 10 stub ASes.

ASes : [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]

Each stub AS has 3 hosts, and the emulator has 30 hosts in total

For example, the ips of 3 hosts in each AS 150 and AS 151 will be assigned as below

- 10.150.0.71
- 10.150.0.72
- 10.150.0.73
- 10.151.0.71
- 10.151.0.72
- 10.151.0.73

```python
# Create the Internat Emulator Base with 10 Stub AS (150-154, 160-164) using the Makers utility tool.
# hosts_per_stub_as=3 : create 3 hosts per one stub AS.
#  It will create hosts(physical node) named `host_{}`.format(counter), counter starts from 0.
hosts_per_stub_as = 3
emu = Makers.makeEmulatorBaseWith10StubASAndHosts(hosts_total_per_as)
```

## 1.2 Creating Ethereum POS Node

We create the POS blockchain sub-layer in the Ethereum layer and
creates the POS ethereum nodes using the Blockchain::createNode() method.

```python
# Create the Ethereum layer
eth = EthereumService()

# Create the Blockchain layer which is a sub-layer of Ethereum layer.
# chainName="pos": set the blockchain name as "pos"
# consensus="ConsensusMechnaism.POS" : set the consensus of the blockchain as "ConsensusMechanism.POS".
# supported consensus option: ConsensusMechanism.POA, ConsensusMechanism.POW, ConsensusMechanism.POS
blockchain = eth.createBlockchain(chainName="pos", consensus=ConsensusMechanism.POS)

# set `terminal_total_difficulty`, which is the value to designate when the Merge is happen.
# The default value is 20.
# In this example, a block is sealed for every 15 seconds. If we set `terminal_total_difficulty` to 20,
# the Ethereum blockchain will keep POA for approximately 150 sec (20/2\*15)
# and then conduct the Merge to change the consensus mechanism to POS.
blockchain.setTerminalTotalDifficulty(20)

asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]

i = 1
for asn in asns:
    for id in range(hosts_per_stub_as):
        # Create a blockchain virtual node named "eth{}".format(i)
        e:EthereumServer = blockchain.createNode("eth{}".format(i))

        # Create Docker Container Label named 'Ethereum-POS-i'
        e.appendClassName('Ethereum-POS-{}'.format(i))

        # Enable Geth to communicate with geth node via http
        e.enableGethHttp()
```

## 1.3 Creating Beacon Setup Node

In order to run Ethereum PoS, you need to run not only the mainnet (execution layer) but also the beacon chain (consensus layer). In this example, we use Geth software to run execution layer and Lighthouse to run consensus layer.
To run a beacon node, config information is needed.  
Like we set genesis.yaml when running Geth, genesis configurations is needed when running Lighthouse. A Beacon Setup Node take care of configuration files which is needed to run Beacon Node. The following code shows how we set beacon setup node.
The Beacon Setup Node is essential to run POS.

```python
# Set host in asn 150 with id 0 (ip : 10.150.0.71) as BeaconSetupNode.
if asn == 150 and id == 0:
        e.setBeaconSetupNode()
```

The role of a Beacon Setup Node

- generate config files for beaconchain
- create validator keys
- deposit for validators that is enabled at the point of Genesis.
- distributes all those data to the other nodes.

A Beacon Setup Node does not run any ethereum node. It's only role is to generate
and distribute data for beacon nodes. To deposit for validators, it makes an api request to the Geth node and send transactions. By default, it will connect to one of node that runs the bootnode.

# 1.4 Set a node as a bootnode

We can set a node as a bootnode that bootstraps all blockchain nodes.
If a node is set as a bootnode, it will run a http server that sends
its blockchain node url so that the other nodes can connect to it.
When it is a POS blockchain, the node serves as a BootNode in both layers: execution layer and consensus layer.
If bootnode does not set to any node, we should specify
peer nodes urls manually.

```python
# Set host in asn 150 with id 1 (ip : 10.150.0.72) as BootNode.
# This node will serve as a BootNode in both execution layer (geth) and consensus layer (lighthouse).
if asn == 150 and id == 1:
        e.setBootNode(True)
```

# 1.5 Add Validator

There are 2 ways to add validator in this emulator

- Enable validator at genesis
- Enable validator at running

We can specifies which validators will be activated from the genesis state as well.
This way is to enable validator at genesis.
But once the beaconchain is initiated, there is no way to add validators in genesis configurations.
To be a validator, we need to stake 32 Ethereum and wait until the validator is activated.
The activation requires a specific amount of time to get the validator's stake information
from the execution layer, verify the data, and wait until the validator to be activated.
We emulate this by enable validator at running.

```python
# Set hosts in asn 152 and 162 with id 0 and 1 as validator node.
# Validator is added by deposit 32 Ethereum and is activated in realtime after the Merge.
# isManual=True : deposit 32 Ethereum by manual.
#                 Other than deposit part, create validator key and running a validator node is done by codes.
if asn in [152, 162]:
    if id == 0:
        e.enablePOSValidatorAtRunning()
    if id == 1:
        e.enablePOSValidatorAtRunning(is_manual=True)

# Set hosts in asn 152, 153, 154, and 160 as validator node.
# These validators are activated by default from genesis status.
# Before the Merge, when the consensus in this blockchain is still POA,
# these hosts will be the signer nodes.
if asn in [151,153,154,160]:
    e.enablePOSValidatorAtGenesis()
```

If we use the method: `enablePOSValidatorAtRunning()` with parameter `is_manual=False`,
A new validator will be added automatically once the emulator runs.
However, if `is_manual` is set to `True`, we need to run deposit.sh script by manual.
All other tasks will be executed but deposit action. It will create a validator key and
run validator node with lighthouse. But it will not be activated until we stake 32 Ethereum
by executing the `deposit.sh` script under `/tmp` folder. The following example shows how to
run the `deposit.sh`.

```
$ docker ps | grep -i 10.152.0.72
b127d8503f24   output_hnode_152_host_1       "/start.sh"      15 minutes ago   Up 15 minutes                                               as152h-Ethereum-POS-8-10.152.0.72

 <!-- docksh is a custom bash function : docksh() { docker exec -it $1 /bin/bash; } -->
$ docksh b127

===============================================================

root@b127d8503f24 / # ls
bin  boot  dev  etc  home  ifinfo.txt  interface_setup  lib  lib32  lib64  libx32  media  mnt  opt  proc  root  run  sbin  seedemu_sniffer  seedemu_worker  srv  start.sh  sys  tmp  usr  var

root@b127d8503f24 / # cd tmp
root@b127d8503f24 /tmp # ls
beacon-bootstrapper  beacon-setup-node  deposit.sh  eth-bootstrapper  eth-genesis.json  eth-nodes  eth-node-urls  eth-password  jwt.hex  keystore  local-testnet  seed.pass  testnet.tar.gz  tmp6i66iy80

root@b127d8503f24 /tmp # ./deposit.sh
"0xa162184cbc0515d7d4a65eb4341429ac765a95c06bac3496040c1840b7c6065a"
```

# 2. Introduction to PoS

A consensus mechanism is a system that blockchains use to validate the authenticity of transactions and maintain the security of the underlying blockchain. As one of the features of the blockchain, anyone can participate in maintaining block, which is called mining in proof-of-work and is called validating in proof-of-stake. However, the open membership can cause a security issue such as Sybil attacks. To prevent this attack and make the blockchain system more reliable, a participant should show some effort.

In proof-of-work consensus protocol, a participant needs to show computational efforts, which consumes a lot of energy. To mine a block, a miner should calculate the hash that satisfies a particular condition and do it faster than any other miners. And this consensus requires a computer with high performance and the waste of power was severe. The competitors in the world runs countless machines and consumes a lot of electricity to mine one block. Only one miner per one block can get rewards and the efforts from the other miners can only produce a waste of the power. This tremendous dissipation can cause the problem in eco system. That is why Ethereum has changed its consensus protocol to proof-of-stake from proof-of-work recently.

In proof-of-stake consensus protocol, a participant should stake a promised amount of money to be involved in maintaining blockchains. By staking some amount of money, a staker holds qualification to generate a block. The power dissipation problem is solved as only one staker (called validator instead of miner in proof-of-stake) will validate (called mine in proof-of-stake) a block and link it to the blockchain at each time. There is no unnecessary power consumption anymore.
