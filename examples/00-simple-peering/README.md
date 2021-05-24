# Simple BGP peering

This is the most basic example; peer three autonomous systems (AS150, AS151, and AS152) at an internet exchange. Each autonomous system announces a /24 prefix, and each is running a single web server within the network.

## Step 1: import and create required componets

```python
from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter
```

In this setup, we will need four layers: 

- The `Base` layer provides the base of the emulation; it describes what hosts belong to what autonomous system and how hosts are connected with each other. 
- The `Routing` layer acts as the base of other routing protocols. `Routing` layer (1) installs BIRD internet routing daemon on every host with router role, (2) provides lower-level APIs for manipulating BIRD's FIB (forwarding information base) and adding new protocols, etc., and (3) setup proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides API for setting up intra-AS BGP peering.
- The `WebService` layer provides API for install `nginx` web server on hosts.

We will compile the emulation to docker containers.

Once the classes are imported, initialize them:

```python
emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
```

## Step 2: create an internet exchange

```python
base.createInternetExchange(100)
```

The current version of the internet emulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function call creates a new internet exchange, and will create a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetworkByName` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`. For details, check to remarks section.

Here, the internet exchange `100` is created. It creates the network `ix100`.

## Step 3: create an autonomous system

### Step 3.1: create the autonomous system instance

```python
as150 = base.createAutonomousSystem(150)
```

Creating a new autonomous system is simple; just call the `Base::createAutonomousSystem` function. The call returns an `AutonomousSystem` class instance, and it can be used to further create hosts in the autonomous system.

### Step 3.2: create the host

Once we have the `AutonomousSystem` instance, we can create a new host for the web service. Creating a new host is also simple; simply call the `AutonomousSystem::createHost` API. The call only takes one parameter, `name`, which is the name of the host, and it will return an `Node` instance on success. In this case, we will name our new host `web`, since we will be hosting `WebService` on it:

```python
as150_web = as150.createHost('web')
```

Before we proceed further, let's first talk about the concept of virtual node and physical node. Physical nodes are "real" nodes; they are created by the `AutonomousSystem::createHost` API, just like what we did above. Virtual nodes are not "real" nodes; consider them as a "blueprint" of a physical node. We can make changes to the "blueprint" then bind the virtual nodes to physical nodes. The changes we made to the virtual node will be applied to the physical node that the virtual node is attached to.

To install `WebService` on the node we just created before, we need to first use the `Service::install` call. `WebService` class derives from the `Service` class, so it also has the `install` method. The `install` takes a virtual node name and install the service on that virtual node:

```python
web.install('web150')
```

The call above created a virtual node with the name `web150`; it has `WebServices` installed on it. The next step is to tell the emulator how to bind this virtual node. To bind a virtual node, we need `Binding` and `Filter`. `Binding` allows us to define binding for a given virtual node name. `Filter` allows us to define some constrict on what physical nodes are considered as binding candidates. Here, we want to bind to the node with the name `web` under AS150. So we can add a binding like this to the emulator:

```python
emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))
```

There are also other constraints one can use to select candidates. See the remarks section for more details.

### Step 3.3: create the router and setup the network

Next, we will need a router. Creating a router is similar to creating a host. The `AutonomousSystem::createRouter` takes a name and returns `Node` instance:

```python
as150_router = as150.createRouter('router0')
```

To connect the router (`router0`) with our host node (`web`), create a new network:

```python
as150_net = as150.createNetwork('net0')
```

The `AutonomousSystem::createNetwork` calls create a new local network (as opposed to the networks created by `Base::createInternetExchange`), which can only be joined by nodes from within the autonomous system. Similar to the `createInternetExchange` call, the `createNetwork` call also automatically assigns network prefixes; it uses `10.{asn}.{id}.0/24` by default. `createNetwork` call also accept `prefix` and `aac` parameter for configuring prefix and setting up auto address assignment. For details, check to remarks section.

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

## Step 4: create more autonomous systems

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

## Step 5: setup BGP peering

Setting up BGP peering is also simple:

```python
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
```

The `Ebgp::addRsPeer` call takes two parameters; the first is an internet exchange ID, and the second is ASN. It will configure peering between the given ASN and the given exchange's route server (i.e., setup Multi-Lateral Peering Agreement (MLPA)). 

Peering can alternatively be configured with `Ebgp::addPrivatePeering`. `addPrivatePeering` method takes four parameters: internet exchange ID, first participant ASN, second participant ASN, and the peer relationship. `addPrivatePeering` will setup peering between first and second ASN. The peering relationship can be one of the followings:

- `PeerRelationship.Provider`: The first ASN is considered as the upstream provider of the second ASN. The first ASN will export all routes to the second ASN, and the second ASN will only export its customers' and its own prefixes to the first ASN.
- `PeerRelationship.Peer`: The two ASNs are considered as peers. Both sides will only export their customers and their own prefixes.
- `PeerRelationship.Unfiltered`: Make both sides export all routes to each other.

Note that the session with RS (`addRsPeer`) will always be `Peer` relationship.

The eBGP layer setup peering by looking for the router node of the given autonomous system from within the internet exchange network. So as long as there is a router of that AS in the exchange network (i.e., joined the IX with `as15X_router.joinNetworkByName('ix100')`), the eBGP layer should be able to setup peeing just fine.

## Step 6: render the emulation

We are now done configuring the layers. The next step is to add all layers to the renderer and render the emulation:

```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.render()
```

The rendering process is where all the actual "things" happen. Softwares are added to the nodes, routing tables and protocols are configured, and BGP peers are configured.

## Step 7: compile the emulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the emulation to other formats. 

In this example, we will use docker on a single host to run the emulation, so we use the `Docker` compiler:

```python
emu.compile(Docker(), './simple-peering')
```

Now we can find the output in the `simple-peering` directory. The docker compiler comes with a docker-compose configuration. To bring up the emulation, simply run `docker-compose build && docker-compose up` in the `simple-peering` directory.

## Remarks

### Virtual node binding & filtering

The constructor of a binding looks like this:

```python
def __init__(self, source, action = Action.RANDOM, filter = Filter()):
```

- `source` is a regex string to match virtual node names. For example, if we want to match all nodes starts with "web," we can use `"web.*"`.
- `action` is the action to take after a list of candidates is selected by the filter. It can be `RANDOM`, which select a random node from the list, `FIRST`, which use the first node from the list, or `LAST`, which use the last node from the list. It defaults to `RANDOM`.
- `filter` points to a filter object. Filters will be discussed in detail later. It defaults to an empty filter with no rules set, which will select all physical nodes without binding as candidates.

The constructor of a filter looks like this:

```python
def __init__(
    self, asn: int = None, nodeName: str = None, ip: str = None,
    prefix: str = None, custom: Callable[[str, Node], bool] = None,
    allowBound: bool = False
)
```

All constructor parameters are one of the constraints. If more than one constraint is set, a physical node must meet all constraints to be selected as a candidate. 

- `asn` allows one to limit the AS number of physical nodes. When this is set, only physical nodes from the given AS will be selected.
- `nodeName` allows one to define the name of the physical node to be selected. Note that physical nodes can have the same name given that they are in different AS.
- `ip` allows one to define the IP of the physical node to be selected.
- `prefix` allows one to define the prefix of IP address on the physical node to be selected. Note that the prefix does not have to match the exact prefix attach to the interface of the physical node; as long as the IP address on the interface falls into the range of the prefix given, the physical node will be selected.
- `custom` allows one to use a custom function to select nodes. The function should take two parameters, the first is a string, the virtual node name, and the second is a Node object, the physical node. Then function should then return `True` if a node should be selected, or `False` otherwise.
- `allowBound` allows physical nodes that are already selected by other binding to be selected again.

### Creating networks with a custom prefix

By default, the network prefix is assigned with the following scheme:

```
10.{asn}.{id}.0/24
```

For internet exchanges, the `{id}` part is always `0`. For example, the default prefix of IX100 will be `10.100.0.0/24`.

For other autonomous systems, `{id}` is the nth network created. For example, for AS150, the first network will be `10.150.0.0/24`, and the second one will be `10.150.1.0/24`.

This, however, does not work for all cases. If we have an autonomous system where its ASN is greater than 255, the automated prefix assignment won't work. Or maybe we just want another prefix for the network. In such cases, we can override the prefix assignment by setting the `prefix` argument:

```python
# for internet exchanges:
base.createInternetExchange(33108, prefix = '206.81.80.0/23')

# for local network:
as11872.createNetwork('net0', prefix = '128.230.0.0/16')
```

### Assigning IP addresses to interfaces

The IP addresses in a network are assigned with `AddressAssignmentConstraint`. The default constraints are as follow:

- Host nodes: from 71 to 99
- Router nodes: from 254 to 200
- Router nodes in internet exchange: ASN

For example, in AS150, if a host node joined a local network, it's IP address will be `10.150.0.71`. The next host joined the network will become `10.150.0.72`. If a router joined a local network, it's IP addresss will be `10.150.0.254`, and if the router joined an internet exchange network (say IX100), it will be `10.100.0.150`.

Sometimes it will be useful to override the automated assignment for once. `joinNetwork` accept an `address` argument for overriding the assignment:

```python
as11872_router.joinNetwork('ix100', address = '10.100.0.118')
```

We may alternatively implement our own `AddressAssignmentConstraint` class instead. Both `createInternetExchange` and `createNetwork` accept the `aac` argument, which will alter the auto address assignment behavior. Foe details, please refer to the API documentation.