# Ethereum Layer2 Service

## Implementation

### Service components

The Ethereum layer2 service consists of following components:

- `EthereumLayer2Service` - This component interacts with the emulator and creates `EthereumLayer2Blockchain` instances.
- `EthereumLayer2Blockchain` - This component is an intermediate layer between `EthereumLayer2Service` and `EthereumLayer2Server`, it enables a centralized management and configuration for all nodes in a same blockchain.
- `EthereumLayer2Server` - This component implements the installation process of the layer2 service and provides a more fine-grained control on nodes than the `EthereumLayer2Blockchain`.
- `EthereumLayer2Template` - This component provides enums and templates for generating scripts of the installation process.

### Node categories

There are three types of node in the layer2 service:

- `sequencer` node executes layer2 txs, builds layer2 blocks, and uploads layer2 txs (as batches) and states to layer1.
- `non-sequencer` node is a client node that redirects txs to the sequencer node and syncs layer2 blockchain states (downloads the tx batches) via layer1.
- `deployer` node is responsible for deploying layer2 smart contracts on layer1 (Ethereum).

### Custom Docker Images

The layer2 nodes use following docker images:

- `deployer` node uses the `huagluck/seedemu-sc-deployer` image
- `sequencer` node and `non-sequencer` node use the `huagluck/seedemu-op-stack` image

## Design Choices

### Layer2 stack selection

The Ethereum layer2 service is implemented using the [Optimism stack](https://docs.optimism.io/), since it is the most popular optimistic ethereum layer2 implementation, with detailed [documentations](https://specs.optimism.io/).

### Config method

The configurations are set in an `.env` environment file, which enables unified management and avoids duplications.

## System Runtime Dependency

```txt
layer1 blockchain running
            |
            V
deployer deployed SC on layer1
            |
            V
deployer generated & hosted layer2 configs
            |
            V
other nodes downloaded configs
            |
            V
sequencer node running
            |
            V
non-sequencer node running
```

## Future Work

### A more comprehensive configuration

Current configurations for the node are simple and limited, to provide more customization for the layer2 blockchain, we can add more interfaces in the `EthereumLayer2Template` class.

#### Node software configuration

- `op-node` configs are defined in the `EthereumLayer2Template.__SUB_LAUNCHERS[EthereumLayer2Component.OP_NODE]` class property.
- `op-geth` configs are defined in the `EthereumLayer2Template.__SUB_LAUNCHERS[EthereumLayer2Component.OP_GETH]` class property.
- `op-batcher` configs are defined in the `EthereumLayer2Template.__SUB_LAUNCHERS[EthereumLayer2Component.OP_BATCHER` class property.
- `op-proposer` configs are defined in the `EthereumLayer2Template.__SUB_LAUNCHERS[EthereumLayer2Component.OP_PROPOSER` class property.

Configuration references:

- [op-node](https://docs.optimism.io/builders/node-operators/management/configuration#op-node)
- [op-geth](https://docs.optimism.io/builders/node-operators/management/configuration#op-geth)
- `op-batcher`: run `$ op-batcher -h` in the sequencer node docker container
- `op-proposer`: run `$ op-proposer -h` in the sequencer node docker container

### Chain configurations

Chain configs are defined in the `EthereumLayer2Template.CHAIN_CONFIG` class property.

[Chain configuration reference](https://docs.optimism.io/builders/chain-operators/management/configuration)

### Block explorer

Currently, we monitor the layer2 blockchain via the command line tool, which is not user friendly and lack of functionality.

Using open source block explorers (e.g. [blockscout](https://github.com/blockscout/blockscout)) can provide user a more insightful view of the blockchain.
