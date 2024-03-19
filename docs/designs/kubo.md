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
Getting started in the Emulator is as simple as initializing the Kubo Service and installing Kubo on a virtual node.

### Manual Installation
The most basic way of getting started with Kubo is to manually install Kubo on a particular node. This is done as follows:

```python
from seedemu import *

# Set up Emulator:
emu = Emulator()

# Setting up Kubo:
ipfs = KuboService()
vnode = 'kubo_node_0'
ipfs.install(vnode)
emu.addBinding(Binding(vnode, filter = Filter(asn = 151, nodeName='host_0')))
emu.addLayer(ipfs)

# Render and compile:
emu.render()
emu.compile(Docker(), './output', override = True)
```

### Dynamic Installation
If you have a large number of nodes that you would like to install Kubo on, you may want to do this more dynamically. This can be done as follows:

```python
from seedemu import *

# Set up Emulator:
emu = Emulator()

# Setting up Kubo:
ipfs = KuboService()
numHosts = 1
i = 0
asns = [151, 152, 153, 154, 161, 162, 163, 171, 172]
# Install Kubo within each stub AS:
for asn in asns:
    # Install Kubo on the given number of nodes within the current AS:
    for h in range(numHosts):
        vnode = f'kubo-{i}'
        displayName = f'Kubo-{i}_'
        cur = ipfs.install(vnode)

        # Configure node as a boot node for a portion of the Kubo nodes:
        if i % 3 == 0:
            cur.setBootNode()
            displayName += 'Boot'
        else:
            displayName += 'Peer'
        
        emu.getVirtualNode(vnode).setDisplayName(displayName)
        emu.addBinding(Binding(vnode, filter = Filter(asn=asn, nodeName=f'host_{h}')))
        i += 1
emu.addLayer(ipfs)

# Render and compile:
emu.render()
emu.compile(Docker(), './output', override = True)
```

## Emulation
Kubo may be installed on a node within the Emulator, alongside most other components. Once the simulation is running, you can connect through any node running Kubo, and use the Kubo CLI to interact with Kubo (see command reference [here](https://docs.ipfs.tech/reference/kubo/cli/)).

For a visualization of the performance and status of a Kubo node, you may access the Web UI which is automatically forwarded from a running node to the host device. You may do this by accessing http://localhost:5001/webui/

Additionally, you may make requests to Kubo's RPC API which is automatically exposed to the host device at http://localhost:5001/api/v0/. Please see the [Kubo RPC API reference](https://docs.ipfs.tech/reference/kubo/rpc/) for more information and specific usage instructions.

## Usage
Notes on using the Kubo Service within an emulator configuration.
Config file reference [here](https://github.com/ipfs/kubo/blob/master/docs/config.md).

## Technical Implementation
Notes on the technical implementation.