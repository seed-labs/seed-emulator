# Kubo Service
The Kubo service is the most widely-used implementation of the InterPlanetary Filesystem (IPFS), written in Go and well-maintained.

## Table of Contents
- [What is a distributed filesystem?](#what-is-a-distributed-filesystem)
- [Bootstrapping](#bootstrapping)
- [Getting Started](#getting-started)
    - [Manual Installation](#manual-installation)
    - [Dynamic Installation](#dynamic-installation)
- [Emulation](#emulation)
- [Usage](#usage)
- [Technical Implementation](#technical-implementation)

## What is a distributed filesystem?
A distributed filesystem such as IPFS allows users to store data accross multiple hosts, typically under no central authority. Data is hosted on one or more peers in a distributed network, and its presence is advertised to others through P2P networking and a distributed hash table (DHT).

## Bootstrapping
Kubo uses a list of bootstrap nodes with which it communicates upon initializaton. A bootstrap node is nothing more than a well-connected peer within the IPFS network. A new peer uses the nodes specified in its bootstrap list to learn about other adjacent nodes, as well as to learn about what data is available.

Kubo is packaged with a default bootstrap list of peers that are maintained by the Kubo development team, and are publically accessible. This is what allows a new Kubo node to immediately become a part of the public Kubo network.

However, in the Emulator we typically do not want Kubo nodes to interact with the outside world by default. In order to prevent this, we automatically delete all default nodes from this bootstrap list upon initialization. We then replace these default bootstrap nodes with a list of bootstrap nodes as configured in the Emulator. This allows us to inform new nodes of other Kubo nodes that are not local to this new instance, for example, new peers in completely different stub AS's.

**We therefore recommend that you configure at least one Kubo node as a bootstrap node.**

## Getting Started
This service is implemented in a non-intrusive manner by giving API access only to configuration parameters that one might want to change before initialization of the server.
Further configuration may be done on each Kubo node using the [Kubo CLI](https://docs.ipfs.tech/reference/kubo/cli/#ipfs) or [RPC API](https://docs.ipfs.tech/reference/kubo/rpc/#api-v0-get) which are automatically installed on each Kubo node.

Getting started in the Emulator is as simple as initializing the Kubo Service and installing Kubo on a virtual node.

### Manual Installation
The most basic way of getting started with Kubo is to manually install Kubo on a particular node. This is done as follows:

  1. Create an instance of the `Emulator`.
  2. Create an instance of the `KuboService`.
  3. Install Kubo on a given virtual node (see [installing a component](./component.md#a-simple-component)).
  4. Bind the virtual node to a physical node within the emulator (see [binding a component](./component.md#binding-and-filter)).
  5. Add the `KuboService` layer to the emulator.

### Dynamic Installation
If you have a large number of nodes that you would like to install Kubo on, you may want to do this more dynamically. This can be done with iteration, and is used in the [Kubo example](../../examples/internet/B26_ipfs_kubo/README.md).

## Emulation
Kubo may be installed on a node within the Emulator, alongside most other components. Once the simulation is running, you can connect through any node running Kubo, and use the Kubo CLI to interact with Kubo (see command reference [here](https://docs.ipfs.tech/reference/kubo/cli/)).

## Usage
This section contains usage notes on aspects of the Kubo implementation which may not be adequately explained through API documentation alone.

### Custom Config
IPFS Kubo automatically generates a configuration file upon initialization. This implements a
set of default settings, and/or the settings associated with a particular profile (if specified).

The `replaceConfig()` method and the public `initConfig` attribute of the `KuboServer` allow you to specify
your own custom configuration for Kubo. This essentially builds a JSON file from the
configuration that you specify, and Kubo uses this on initialization instead of generating
its own configuration file. Please note:
  - If you have specified all necessary sections of the configuration file, the node will function normally.
  - If you have not specified all sections of the configuration file, the node's behavior may be unpredictable.

The `importConfig()` and `setConfig()` methods, and the public `startConfig` attribute of the `KuboServer` allows you to specify your own custom configuration for Kubo which is applied on startup instead of initialization.
This automatically modifies the Kubo configuration after it has been initialized with either the default configuration values, or a user-defined configuration file (see above). **This is the best way to selectively alter the Kubo configuration of a node.**

If you would like to make modifications to the configuration of a set of nodes after initialization with default values, you may do so using the [IPFS CLI](https://docs.ipfs.tech/reference/kubo/cli/#ipfs-config).

For more information on the Kubo configuration file, please check the most [current documentation](https://github.com/ipfs/kubo/blob/master/docs/config.md).
