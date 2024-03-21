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
<!-- Notes on using the Kubo Service within an emulator configuration. -->
<!-- Config file reference [here](https://github.com/ipfs/kubo/blob/master/docs/config.md). -->
### Kubo Service

```python
# The below constructor shows all keyword arguments and their default values:
ipfs = KuboService(apiPort=5001, gatewayPort=8080, bootstrapIps=[], distro=Distribution.LINUX, arch=Architecture.X64)
```

You may initialize `KuboService` with no arguments to take default values that should be sufficient in most use-cases.

| Argument | Type | Description |
| --- | --- | --- |
| `apiPort` | `int` | This changes what TCP port the RPC API built into Kubo is bound to for all nodes that are created. |
| `gatewayPort` | `int` | This changes what TCP port the HTTP Gateway built into Kubo is bound to for all nodes that are created. |
| `bootstrapIps` | `list[str]` | This is used to provide additional predetermined IPv4 addresses to be added to the bootstrap list of all nodes. |
| `distro` | `KuboEnums.Distribution` | This is used to change what distribution Kubo will be run on (e.g. Linux or FreeBSD). |
| `arch` | `KuboEnums.Architecture` | This is used to change the CPU architecture Kubo will be run on (e.g. X64 or X86). |

---

The `KuboService` also provides an API to retrieve the current list of bootstrap nodes which can be used in more advanced scenarios, for example:

```python
kubo = KuboService()
bootstrapNodes:list = kubo.getBootstrapList()
print(bootstrapNodes)
```
Script Output:
```
['10.150.1.72', '10.150.1.73']
```

### KuboServer

After initializing `KuboService`, you may initialize as many instances of `KuboServer` as you need, for example:

```python
ipfs = KuboService()
vnode = 'kubo_node_0'
ipfs.install(vnode)  # This installs KuboServer on a node
emu.addBinding(Binding(vnode, filter = Filter(asn = 151, nodeName='host_0')))
```

You may chain API calls onto the `ipfs.install()` API call to modify the Kubo configuration on a particular node. The `ipfs.install()` API call returns an instance of `KuboServer`, with the following:

| Attribute | Type | Description |
| --- | --- | --- |
| `config` | `KuboUtils.DottedDict` | This contains the manually-set Kubo config file (empty if not set). It may be accessed like a normal dictionary, or using JSON dot notation. |

---

| Method | Return Type | Description |
| --- | --- | --- |
| `isBootNode()` | `bool` | Indicates whether the current server is a boot node or not. |
| `setBootNode(isBoot:bool=True)` | `Self` | Sets a node as a boot node to be included in the bootstrap list for all other nodes. |
| `setVersion(version:str)` | `Self` | Sets the version of Kubo to use on the current node. |
| `getVersion()` | `str` | Gets the version of Kubo that will be installed on the current node. |
| `setProfile(profile:str)` | `Self` | Sets the profile (configuration preset) used by Kubo on initialization. |
| `importConfig(config:dict)` | `Self` | Import a Kubo config JSON stored as a Python dict. **This will override the automatically generated config file, which could have unintended consequences.** |
| `setConfig(key:str, value:Any)` | `Self` | Set a single key-value pair in the Kubo config JSON. **This will override the automatically generated config file, which could have unintended consequences.** |
---

## Technical Implementation
The following includes some technical notes on the implementation, including aspects which might be improved or expanded on in the future.

### KuboService
- `self._distro` and `self._arch` are implemented at the service level, so will be the same for all nodes.
    - `self._distro` depends on `KuboServer._base_system` and should change dynamically based on that.
    - `self._arch` must be the same as the architecture given to the compiler, Kubo should determine dynamically based on compiler arch.
- `self._tmp_dir` is the location in which temporary setup files may be placed, right now just the bootstrap script.
    - Change `TEMPORARY_DIR` in `KuboService` to modify this.
- `self._first_installed` may be used to expose a single node's Web UI to the host VM. We should find a better way to expose all nodes' Web UIs without individual port forwarding (which also conflicts with Internet Map default port 8080).
- `self._doInstall(node:Node, server:KuboServer)` does all service-level installation (port bindings and bootstrapping), and then begins server-level installation for the given node.
    - Bootstrap list and bootstrap script are generated once when this method is first called, and reused for all other method calls.
- `self._getBootstrapIps()` populates the service's bootstrap list using the first valid, local IPv4 address for each node.

### KuboServer
- `self.setVersion(version:str)` attempts to verify the format of the version string to ensure that it matches the expected format (using RegEx).
- `self.config` is a public variable so that users are encouraged to directly modify the `DottedDict`, however, we also provide `self.importConfig()` and `self.setConfig()`. Both of these are redundant and could be removed.