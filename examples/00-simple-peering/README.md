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
- The `Ebgp` layer provides APIs for setting up intra-AS BGP peering.
- The `WebService` layer provides APIs for installing the `nginx` web server on hosts.

We will compile the emulation to docker containers.

Once the classes are imported, initialize them:

```python
emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
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

Creating a new autonomous system is simple: just call the `Base::createAutonomousSystem` function. The call returns an `AutonomousSystem` class instance, and it can be used to further create hosts in the autonomous system.

### Step 3.2: Create the host

Once we have the `AutonomousSystem` instance, we can create a new host for the web service. Creating a new host is also simple: simply call the `AutonomousSystem::createHost` API. The call only takes one parameter, `name`, which is the name of the host, and it will return an `Node` instance on success. In this case, we will name our new host `web`, since we will be hosting `WebService` on it:

```python
as150_web = as150.createHost('web')
```

Before proceeding further, let's first talk about the concept of virtual node and physical node. Physical nodes are "real" nodes; they are created by the `AutonomousSystem::createHost` API, just like what we did above. Virtual nodes are not "real" nodes; consider them as a "blueprint" of a physical node. We can make changes to the "blueprint" then bind the virtual nodes to physical nodes. The changes we made to the virtual node will be applied to the physical node that the virtual node is attached to.

To install `WebService` on the node created before, we need to first use the `Service::install` call. `WebService` class derives from the `Service` class, so it also has the `install` method. The `install` takes a virtual node name and install the service on that virtual node:

```python
web.install('web150')
```

The call above created a virtual node with the name `web150`; it has `WebServices` installed on it. The next step is to tell the emulator which physical node should this virtual node binds to. To bind a virtual node, we need `Binding` and `Filter`. `Binding` allows us to define binding for a given virtual node name. `Filter` allows us to define some constraints on what physical nodes are considered as binding candidates. Here, we want to bind to the node with the name `web` under AS150. So we can add a binding like this to the emulator:

```python
emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))
```

There are also other constraints one can use to select candidates. 
See [this manual](../manual.md#virtual-node-binding) for details. 

### Step 3.3: Create the router and set up the network

Next, we will need a router. Creating a router is similar to creating a host. The `AutonomousSystem::createRouter` takes a name and returns `Node` instance:

```python
as150_router = as150.createRouter('router0')
```

To connect the router (`router0`) with our host node (`web`), create a new network:

```python
as150_net = as150.createNetwork('net0')
```

The `AutonomousSystem::createNetwork` calls create a new local network (as opposed to the networks created by `Base::createInternetExchange`), which can only be joined by nodes from within the autonomous system. Similar to the `createInternetExchange` call, the `createNetwork` call also automatically assigns network prefixes; it uses `10.{asn}.{id}.0/24` by default. `createNetwork` call also accept `prefix` and `aac` parameter for configuring prefix and setting up auto address assignment. For details, see [this manual](../manual.md#create-network-with-prefix).

We now have the network, it is not in the FIB yet, and thus will not be announce to BGP peers. We need to let our routing daemon know we want the network in FIB. This can be done by:

```python
routing.addDirect(150, 'net0')
```

The `Routing::addDirect` call marks a network as a "direct" network. A "direct" network will be added to the `direct` protocol block of BIRD, so the prefix of the directly connected network will be loaded into FIB.

Now, put the host and router in the network:

```python
as150_web.joinNetwork('net0')
as150_router.joinNetwork('net0')
```

The `Node::joinNetwork` call connects a node to a network. It first searches through the local networks, then global networks. Internet exchanges, for example, are considered as global network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

Last, put the router into the internet exchange:

```python
as150_router.joinNetwork('ix100')
```

## Step 4: Create more autonomous systems

Repeat step 3 two more times with different ASNs:

```python
as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')
web.install('web151')
emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')

as151_web.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

###############################################################################

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')
web.install('web152')
emu.addBinding(Binding('web152', filter = Filter(nodeName = 'web', asn = 152)))

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix100')
```

## Step 5: Set up BGP peering

Setting up BGP peering is done at the eBGP layer:

```python
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
```

The `Ebgp::addRsPeer` call takes two parameters; the first is an internet exchange ID, and the second is ASN. It will configure the peering between the given ASN and the given internet exchange's route server (i.e., setting up Multi-Lateral Peering Agreement (MLPA)). 

Peering can alternatively be configured with `Ebgp::addPrivatePeering`. `addPrivatePeering` method takes four parameters: internet exchange ID, first participant ASN, second participant ASN, and the peer relationship. `addPrivatePeering` will setup peering between first and second ASN. The peering relationship can be one of the followings:

- `PeerRelationship.Provider`: The first ASN is considered as the upstream provider of the second ASN. The first ASN will export all routes to the second ASN, and the second ASN will only export its customers' and its own prefixes to the first ASN.
- `PeerRelationship.Peer`: The two ASNs are considered as peers. Both sides will only export their customers and their own prefixes.
- `PeerRelationship.Unfiltered`: Make both sides export all routes to each other.

Note that the session with RS (`addRsPeer`) will always be `Peer` relationship.

The eBGP layer sets up peering by looking for the router node of the given autonomous system from within the internet exchange network. So as long as there is a router of that AS in the exchange network (i.e., joined the IX with `as15X_router.joinNetwork('ix100')`), the eBGP layer should be able to set up the peeing.

## Step 6: Render the emulation

See [this manual](../manual.md#rendering).

## Step 7: Compile the emulation

See [this manual](../manual.md#compilation).

