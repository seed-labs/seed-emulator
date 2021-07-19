# Simple BGP peering

This is the most basic example: peering three autonomous systems (AS150, AS151, and AS152) at an internet exchange. Each autonomous system announces a /24 prefix, and each is running a single web server within the network.

## Step 1: Import and create required components

```python
from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
```

In this setup, we will need four layers: 

- The `Base` layer provides the base of the emulation; it describes what hosts belong to what autonomous system and how hosts are connected with one another. 
- The `Routing` layer acts as the base of the routing protocols. It does the following: (1) installing BIRD internet routing daemon on every host with the router role, (2) providing lower-level APIs for manipulating BIRD's FIB (forwarding information base) and adding new protocols, etc., and (3) setting up proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides APIs for setting up External BGP peering.
- The `WebService` layer provides APIs for installing the `nginx` web server on hosts.

We will compile the emulation to docker containers.

Once the classes are imported, initialize them:

```python
emu     = Emulator()

base    = Base()
routing = Routing()
ebgp    = Ebgp()
web     = WebService()
```

## Step 2: Create an internet exchange

```python
base.createInternetExchange(100)
```

The `Base::createInternetExchange` function call creates a new internet exchange. By default, it creates a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetwork` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`. 
For details, see [this manual](../manual.md#create-network-with-prefix).

Here, the internet exchange `100` is created. It creates the network `ix100`.

## Step 3: Create an autonomous system

### Step 3.1: Create the autonomous system instance

```python
as150 = base.createAutonomousSystem(150)
```

The call returns an `AutonomousSystem` class instance, and it can be used to further 
create hosts and networks in the autonomous system.


### Step 3.2: Create an internal network

```
as150.createNetwork('net0')
```

The `AutonomousSystem::createNetwork` calls create a new local network (as opposed to the networks created by `Base::createInternetExchange`), which can only be joined by nodes from within the autonomous system. Similar to the `createInternetExchange` call, the `createNetwork` call also automatically assigns network prefixes; it uses `10.{asn}.{id}.0/24` by default. `createNetwork` call also accept `prefix` and `aac` parameter for configuring prefix and setting up auto address assignment. For details, see [this manual](/docs/user_manual/manual.md#create-network-with-prefix).


### Step 3.3: Create a router and connect it to two networks

We will create a router and connect it to both the internal network `net0` and the 
network in the internet exchange `ix100`. Basically, we are making this router
a BGP router.

```
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
```

The `Node::joinNetwork` call connects a node to a network. It first searches through the local networks, then global networks. Internet exchanges, for example, are considered as global network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 


### Step 3.4: Create a host 

We will create a host and later put a web server on this host. 
This host will join our internal network `net0`.

```python
as150.createHost('web').joinNetwork('net0')
```

The `AutonomousSystem::createHost` API takes one parameter, `name`,
which is the name of the host, and it will return an `Node` instance on
success. In this case, we will name our new host `web`, since we will be
hosting `WebService` on it:


### Step 3.5: Run a web server on this host

In our design, we do not directly install a web server on a host.
We first create a virtual node and install the web service 
on this virtual node. Virtual nodes are not "real" nodes; consider them as a
"blueprint" of a physical node. They are decoupled from the physical node,
making reusing them much easier. Whatever the changes we make to
the virtual nodes are the changes to the "blueprint". Eventually,
a virtual node needs to be mapped to a physical node, so all the 
configurations and changes in the "blueprint" can be applied
to physical node. Physical nodes are "real" nodes; they are created by the
`AutonomousSystem::createHost` API. 


To install `WebService` on the node created before, we need to first use the
`Service::install` call. `WebService` class derives from the `Service` class,
so it also has the `install` method. The `install` takes a virtual node name
and install the service on that virtual node:

```
web.install('web150')
```

### Step 3.6: Bind to physical node

We need to tell the emulator which physical node this virtual node should bind to. 
To bind a virtual node, we
need `Binding` and `Filter`. `Binding` allows us to define binding for a given
virtual node name. `Filter` allows us to define some constraints on what
physical nodes are considered as binding candidates. Here, we want to bind to
the node with the name `web` in AS-150. So we can add a binding like this to
the emulator:

```python
emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))
```

There are also other constraints one can use to select candidates. 
See [this manual](/docs/user_manual/component.md#virtual-node-binding) for details. 



## Step 4: Set up BGP peering

Once we have created the autonomous systems, we need to 
set up the peering among them. 
Setting up BGP peering is done at the eBGP layer. The following
peers the `AS-150`, `AS-151`, and `AS-152` at the Internet Exchange `IX-100`. 

```python
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
```

Their peering relationship be default is `Peer` type.  
See [this manual](/docs/user_manual/bgp_peering.md) for detailed 
discussions on this `Ebgp::addRsPeer` call.


## Step 5: Render the emulation

Render the emulation. This is when the actual "things" happen: 
software is added to the nodes, routing tables and protocols are configured, 
and BGP peers are configured, etc.
See [this manual](/docs/user_manual/manual.md#rendering).


## Step 6: Compile the emulation

Generate the emulation files. See [this manual](/docs/user_manual/compiler.md).

