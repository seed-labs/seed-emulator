# Kubo Service
The Kubo service is the most widely-used implementation of the InterPlanetary Filesystem (IPFS), written in Go and well-maintained.

## Table of Contents
- [What is a distributed filesystem?](#what-is-a-distributed-filesystem)
- [Getting Started](#getting-started)
    - [Manual Installation](#manual-installation)
    - [Dynamic Installation](#dynamic-installation)
- [Emulation](#emulation)
- [Usage](#usage)
    - [API Reference](#api-reference)
- [Technical Implementation](#technical-implementation)

## What is a distributed filesystem?
A distributed filesystem such as IPFS allows users to store data accross multiple hosts, typically under no central authority. Data is hosted on one or more peers in a distributed network, and its presence is advertised to others through P2P networking and a distributed hash table (DHT).

## Getting Started
Getting started in the Emulator is as simple as initializing the Kubo Service and installing Kubo on a virtual node.

### Manual Installation
The most basic way of getting started with Kubo is to manually install Kubo on a particular node, in this case a node with ASN 151. This is done as follows:

```python
from seedemu import *

# Set up Emulator:
emu = Emulator()

# Setting up Kubo:
ipfs = KuboService()
vnode = 'kubo_node_0'
ipfs.install(vnode)
emu.addBinding(Binding(vnode, filter = Filter(asn = 151)))
emu.addLayer(ipfs)

# Render and compile:
emu.render()
emu.compile(Docker(), './output', override = True)
```

### Dynamic Installation
Blah blah blah

## Emulation
Notes on using the Kubo Service as deployed in the emulator

## Usage
Notes on using the Kubo Service within an emulator configuration.

### API Reference
Class diagram and API documentation.

## Technical Implementation
Notes on the technical implementation not adequately described in API Documentation