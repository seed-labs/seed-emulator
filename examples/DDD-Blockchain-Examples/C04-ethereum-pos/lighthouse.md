# PoS - The merge (By manual - step by step)

# Environment :

- execution-chain software : geth
- beacon-chain software : lighthouse

# Requirements

## Lighthouse Installation – Build from source

• Reference : https://lighthouse-book.sigmaprime.io/installation-source.html

1. Install Rust

- curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

2. Install following packages

- sudo apt install -y git gcc g++ make cmake pkg-config llvm-dev libclang-dev clang

3. Build lighthouse & lcli

- git clone https://github.com/sigp/lighthouse.git
- cd lighthouse
- git checkout stable
- make
- make install-lcli

# Using Beacon Setup Node

## Beacon Setup Node Requirements

1. For Debug purpose, the setup node should independant from the Ethereum Network so that we do not have to re-build whole ethereum node again and again.

2. When the setup node distributes validator key resources, it should be done by ethereum Id.
   => the setup node should know 1) How many validatory keys to create. 2) Which ethereum nodes will request a key resource.

3. Setup node will run geth as well to deploy a deposit contract.
   => The setup node should know geth bootnodes' ip to bootstrap with other gethnodes.
   However, while meeting requirement 1, to know a geth bootnode is quite complicate.
   So I chose not to run geth node inside the setup node. Instead, I use ethreum node from the network to deploy the contract.

## How to Run

1. Run blockchain-pos.py

- before running the script, need to change one argument at line 131.
- update the LIGHTHOUSE_BIN_PATH value
  `LIGHTHOUSE_BIN_PATH="/home/won/.cargo/bin/lighthouse"`

- after running the script, it will generate `beacon-setup-node.sh` which runs the beacon-setup-node.py with arguments.

2. Run `beacon-setup-node.sh`

- This composes beacon-setup-node.

3. Run ethereum containers

```
cd output
dcbuild
dcup
```

4. Run beacon setup node

```
cd beacon-node
dcbuild
dcup
```

## Design

Design 1) Create an Independant Beacon Setup Node manually (Current Design)

Satisfy Requirement 1,2

As this node is seperated from the Ethereum Network, we should specify some information about the Ethereum Network to compose this node. The needed information is as below.

- TERMINAL_TOTAL_DIFFICULTY
- VALIDATOR_IDS
- BOOTNODE_IP

Design 2) Create a Server class for a Beacon Setup Node (Implemented But Not Using)

Satisfy Requirement 2,3

As the server class is a part of EthereumService class, it is dependant to Ethereum Network. And it is not suitable for debugging purpose.

# How to run Geth and Lighthouse on Seedchain. (Manual Steps)

## 1. Run geth nodes with SEED Emulator

```
# Generate docker compose files
./blockchain-poa.py
# Build docker
cd output && dcbuild
# Up docker containers
dcup or ./z_start.sh
```

## 2. Run lighthouse nodes and validator nodes using lighthouse and lcli software.

- reference : https://github.com/sigp/lighthouse/tree/stable/scripts/local_testnet

- cd $HOME/lighthouse/scripts/local_testnet

### 1) Deploy deposit contract

`lcli deploy-deposit-contract --eth1-http http://localhost:8545 --confirmations 1 --validator-count 5`

: deploys a deposit contract and send deposit transaction through `--eth1-http` endpoint which is an interface of one of the geth nodes. The node's coinbase should have enough `Eth` to deposit for validators.

Expected Result

```
Deposit contract address: "0x46d84b6f6633c3aac117d4d906ea13795a140fd7"
Submitting deposit for validator 0...
Submitting deposit for validator 1...
Submitting deposit for validator 2...
Submitting deposit for validator 3...
Submitting deposit for validator 4...
```

## 2) Create a beacon chain config files.

```
lcli new-testnet --spec mainnet --deposit-contract-address  46d84b6f6633c3aac117d4d906ea13795a140fd7 --deposit-contract-deploy-block 2 --testnet-dir ~/.lighthouse/local-testnet/testnet --min-genesis-active-validator-count 3 --min-genesis-time `date +%s` --genesis-delay 0 --genesis-fork-version 0x42424242 --altair-fork-epoch 1 --eth1-id 10 --eth1-follow-distance 1 --seconds-per-slot 3 --seconds-per-eth1-block 15 --merge-fork-epoch 3 --force
```

- Need to change `--deposit-contract-address` and `--deposit-contract-deploy-block` value.
  (Have to find it manually at this point.)
- This will create config files under ~/.lighthouse/local-testnet/testnet
- Update `TERMINAL_TOTAL_DIFFICULTY` to `"100"` in config.yaml file to make it run on SEED chain.

## 3) Create validators

```
lcli \
        insecure-validators \
        --count 3 \
        --base-dir ~/.lighthouse/local-testnet \
        --node-count 3
```

- It will generate 3 nodes configs each of which will runs one validator.

## 4) Building a genesis state. (genesis.ssz)

```
lcli \
        interop-genesis \
        --spec mainnet \
        --genesis-time $GENESIS_TIME \
        --testnet-dir ~/.lighthouse/local-testnet/testnet \
        3
```

- `$GENESIS_TIME` should be same value with `--min-genesis-time` value in step 2) Create a beacon chain config files.

## 5) Run beacon nodes.

In this example, we will run 3 beacon nodes.

### create jwt.hex

Currently, geth nodes use a hard-coded jwt.hex which is `0xae7177335e3d4222160e08cecac0ace2cecce3dc3910baada14e26b11d2009fc`.
Create jwt.hex file.

`echo '0xae7177335e3d4222160e08cecac0ace2cecce3dc3910baada14e26b11d2009fc' > ~/jwt.hex`

- node1

```
lighthouse --debug-level info bn --datadir ~/.lighthouse/local-testnet/node_1 --testnet-dir ~/.lighthouse/local-testnet/testnet --enable-private-discovery --staking --enr-address 127.0.0.1         --enr-udp-port 9000 --enr-tcp-port 9000 --port 9000 --http-port 8000 --disable-packet-filter --target-peers 2 --execution-endpoint http://127.0.0.1:8551 --execution-jwt ~/jwt.hex
```

- node2

```
lighthouse --debug-level info bn --datadir ~/.lighthouse/local-testnet/node_2 --testnet-dir ~/.lighthouse/local-testnet/testnet --enable-private-discovery --staking --enr-address 127.0.0.1 --enr-udp-port 9001 --enr-tcp-port 9001 --port 9001 --http-port 8001 --disable-packet-filter --target-peers 2 --execution-endpoint http://127.0.0.1:8551 --execution-jwt ~/jwt.hex
```

- node3

```
lighthouse --debug-level info bn --datadir ~/.lighthouse/local-testnet/node_3 --testnet-dir ~/.lighthouse/local-testnet/testnet --enable-private-discovery --staking --enr-address 127.0.0.1 --enr-udp-port 9002 --enr-tcp-port 9002 --port 9002 --http-port 8002 --disable-packet-filter --target-peers 2 --execution-endpoint http://127.0.0.1:8551 --execution-jwt ~/jwt.hex
```

## 6) Run validator nodes

- `--suggested-fee-recipient` value should be changed.

- validator node1

```
lighthouse --debug-level info vc --datadir ~/.lighthouse/local-testnet/node_1 --testnet-dir ~/.lighthouse/local-testnet/testnet --init-slashing-protection --beacon-nodes http://localhost:8000 --suggested-fee-recipient 0xd07cd97f7f749f27133da19cff6de4da8b8e8cd5
```

- validator node2

```
lighthouse --debug-level info vc --datadir ~/.lighthouse/local-testnet/node_2 --testnet-dir ~/.lighthouse/local-testnet/testnet --init-slashing-protection --beacon-nodes http://localhost:8001 --suggested-fee-recipient 0xd07cd97f7f749f27133da19cff6de4da8b8e8cd5
```

- validator node3

```
lighthouse --debug-level info vc --datadir ~/.lighthouse/local-testnet/node_3 --testnet-dir ~/.lighthouse/local-testnet/testnet --init-slashing-protection --beacon-nodes http://localhost:8002 --suggested-fee-recipient 0xd07cd97f7f749f27133da19cff6de4da8b8e8cd5
```
