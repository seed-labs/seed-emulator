# Transit AS (MPLS)

This example is similar to the regular transit example. In this example, we will configure two internet exchanges, AS150 will be in both exchanges. AS151 and AS152 will be in IX100 and IX101, respectively. AS150 will serve as the transit AS for AS151 and AS152. There will be four hops in AS150. AS151 and AS152 will each announce one /24 prefix and host one web server in the network.

In other words, the topology is the exact same as the last example. The only difference in this example is that we will not use MPLS instead of OSPF and IBGP in the transit network. With MPLS, non-edge routers don't need to carry the BGP routing table at all. Non-edge routes only need to keep track of a small amount of MPLS labels, which greatly reduces the resources needed on non-edge routes.

## Step 0: host system support

MPLS requires support from the Linux kernel; for this example to work properly, load the MPLS kernel module on the emulator host with the following command, as root:

```
# modprobe mpls_router
```

## Step 1: import and create required componets

```python
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Mpls
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker
```

In this setup, we will need these layers: 

- The `Base` layer provides the base of the emulation; it describes what hosts belong to what autonomous system and how hosts are connected with each other. 
- The `Routing` layer acts as the base of other routing protocols. `Routing` layer (1) installs BIRD internet routing daemon on every host with router role, (2) provides lower-level APIs for manipulating BIRD's FIB (forwarding information base), adding new protocols, etc., and (3) setup proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides API for setting up intra-AS BGP peering.
- The `Mpls` layer automatically setup MPLS. The default behavior for the MPLS layer are as follow:
    - First, it classifies router nodes as edge routers and non-edge routers. Routers with at least one connection to an internet exchange or to a network with host role nodes connected are considered as edge routers. All other routers are considered as non-edge routers.
    - Then, for all edge routers, it setup LDP, OSPF and IBGP full mesh sessions between them. For all non-edge routers, it setup only LDP and OSPF.
- The `WebService` layer provides API for install `nginx` web server on hosts.

We will use the defualt renderer and compiles the emulation to docker containers.

Once the classes are imported, initialize them:

```python
emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
mpls = Mpls()
web = WebService()
```

## Step 2: create the internet exchanges

```python
base.createInternetExchange(100)
base.createInternetExchange(101)
```

The current version of the internet emulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function call creates a new internet exchange, and will create a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetworkByName` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`. For details, check to remarks section.

Here, two internet exchanges are created. This add two new networks, `ix100` and `ix101`, to the emulation.

## Step 3: create a transit autonomous system

### Step 3.1: create the autonomous system instance

```python
as150 = base.createAutonomousSystem(150)
```

Creating a new autonomous system is simple; just call the `Base::createAutonomousSystem` function. The call returns an `AutonomousSystem` class instance, and it can be used to further create hosts in the autonomous system.

### Step 3.2: create the internal networks

```python
as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')
```

The `AutonomousSystem::createNetwork` calls create a new local network (as opposed to the networks created by `Base::createInternetExchange`), which can only be joined by nodes from within the autonomous system. Similar to the `createInternetExchange` call, the `createNetwork` call also automatically assigns network prefixes; it uses `10.{asn}.{id}.0/24` by default. `createNetwork` call also accept `prefix` and `aac` parameter for configuring prefix and setting up auto address assignment. For details, check to remarks section.

Since we planned to have four hops in AS150, meaning we will need three internal networks to connect the routers together.

### Step 3.3: create routers

Next, we will need routers. The `AutonomousSystem::createRouter` takes a name and returns router `Node` instance:

```python
r1 = as150.createRouter('r1')
r2 = as150.createRouter('r2')
r3 = as150.createRouter('r3')
r4 = as150.createRouter('r4')
```

Again, we planned to have four hops, so we created four routers here.

### Step 3.4: configure routers

We now have both networks and routers. We need to connect the routers to networks.

```python
r1.joinNetwork('ix100')
r1.joinNetwork('net0')

r2.joinNetwork('net0')
r2.joinNetwork('net1')

r3.joinNetwork('net1')
r3.joinNetwork('net2')

r4.joinNetwork('net2')
r4.joinNetwork('ix101')
```

The `Node::joinNetwork` calls take the name of the network and join the network. It first searches through the local networks, then global networks. The `joinNetwork` call also takes an optional parameter, `address`, for overriding auto address assignment.

### Step 3.5: configure MPLS

Unlike OSPF and IBGP, MPLS needs to be explicitly enabled for an autonomous system. This can be done by `Mpls::enableOn`:

```python
mpls.enableOn(150)
```

The `enableOn` call takes on parameter, the ASN to enable MPLS on.

Here, only `r1` and `r4` are edge routers; thus, IBGP session will only be set up between them. `r2` and `r3` will only participate in OSPF and LDP. The topology looks like this:

```
       |  AS150's MPLS backbone                         |
       |          ____________ ibgp ___________         |
       |         /                             \        |
as151 -|- as150_r1 -- as150_r2 -- as150_r3 -- as150_r4 -|- as152 
       |                                                |
```

Since `r2` and `r3` don't carry table from AS151 and AS152, traceroute will look like this:

```
HOST: 0e58e675b98b Loss%   Snt   Last   Avg  Best  Wrst StDev
 1.|-- 10.152.0.254  0.0%    10    0.1   0.1   0.1   0.1   0.0
 2.|-- 10.101.0.150  0.0%    10    0.1   0.1   0.1   0.2   0.0
 3.|-- ???          100.0    10    0.0   0.0   0.0   0.0   0.0
 4.|-- ???          100.0    10    0.0   0.0   0.0   0.0   0.0
 5.|-- 10.150.0.254  0.0%    10    0.1   0.1   0.1   0.2   0.0
 6.|-- 10.100.0.151  0.0%    10    0.3   0.2   0.1   0.3   0.1
 7.|-- 10.151.0.71   0.0%    10    0.2   0.2   0.1   0.3   0.0
```

The two missing hops are `r2` and `r3`. We can also validate that the network is indeed running on MPLS by `tcpdump`:

```
root@d5d8ad0d6d48 / # tcpdump -i net1 -n mpls
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on net1, link-type EN10MB (Ethernet), capture size 262144 bytes
19:39:33.831880 MPLS (label 21, exp 0, [S], ttl 61) IP 10.152.0.71 > 10.151.0.71: ICMP echo request, id 123, seq 1, length 64
19:39:33.832051 MPLS (label 19, exp 0, [S], ttl 61) IP 10.151.0.71 > 10.152.0.71: ICMP echo reply, id 123, seq 1, length 64
19:39:34.877246 MPLS (label 21, exp 0, [S], ttl 61) IP 10.152.0.71 > 10.151.0.71: ICMP echo request, id 123, seq 2, length 64
19:39:34.877314 MPLS (label 19, exp 0, [S], ttl 61) IP 10.151.0.71 > 10.152.0.71: ICMP echo reply, id 123, seq 2, length 64
^C
4 packets captured
4 packets received by filter
0 packets dropped by kernel
```

## Step 4: create a customer autonomous system

### Step 4.1: create the autonomous system instance

```python
as151 = base.createAutonomousSystem(151)
```

Creating a new autonomous system is simple; just call the `Base::createAutonomousSystem` function. The call returns an `AutonomousSystem` class instance, and it can be used to further create hosts in the autonomous system.

### Step 4.2: create the host

Once we have the `AutonomousSystem` instance, we can create a new host for the web service. Creating a new host is also simple; simply call the `AutonomousSystem::createHost` API. The call only takes one parameter, `name`, which is the name of the host, and it will return an `Node` instance on success. In this case, we will name our new host `web`, since we will be hosting `WebService` on it:

```python
as151_web = as151.createHost('web')
```

Before we proceed further, let's first talk about the concept of virtual node and physical node. Physical nodes are "real" nodes; they are created by the `AutonomousSystem::createHost` API, just like what we did above. Virtual nodes are not "real" nodes; consider them as a "blueprint" of a physical node. We can make changes to the "blueprint" then bind the virtual nodes to physical nodes. The changes we made to the virtual node will be applied to the physical node that the virtual node is attached to.

To install `WebService` on the node we just created before, we need to first use the `Service::install` call. `WebService` class derives from the `Service` class, so it also has the `install` method. The `install` takes a virtual node name and install the service on that virtual node:

```python
web.install('web151')
```

The call above created a virtual node with the name `web151`; it has `WebServices` installed on it. The next step is to tell the emulator how to bind this virtual node. To bind a virtual node, we need `Binding` and `Filter`. `Binding` allows us to define binding for a given virtual node name. `Filter` allows us to define some constrict on what physical nodes are considered as binding candidates. Here, we want to bind to the node with the name `web` under AS150. So we can add a binding like this to the emulator:

```python
emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))
```

There are also other constraints one can use to select candidates. See the remarks section for more details.

### Step 4.3: create the router and setup the network

Next, we will need a router. Creating a router is similar to creating a host. The `AutonomousSystem::createRouter` takes a name and returns `Node` instance:

```python
as151_router = as151.createRouter('router0')
```

To connect the router (`router0`) with our host node (`web`), create a new network:

```python
as151_net = as151.createNetwork('net0')
```

The `AutonomousSystem::createNetwork` calls create a new local network (as opposed to the networks created by `Base::createInternetExchange`), which can only be joined by nodes from within the autonomous system. Similar to the `createInternetExchange` call, the `createNetwork` call also automatically assigns network prefixes; it uses `10.{asn}.{id}.0/24` by default. `createNetwork` call also accept `prefix` and `aac` parameter for configuring prefix and setting up auto address assignment. For details, check to remarks section.

We now have the network, it is not in the FIB yet, and thus will not be announce to BGP peers. We need to let our routing daemon know we want the network in FIB. This can be done by:

```python
routing.addDirect(151, 'net0')
```

The `Routing::addDirect` call marks a network as a "direct" network. A "direct" network will be added to the `direct` protocol block of BIRD, so the prefix of the directly connected network will be loaded into FIB.

Now, put the host and router in the network:

```python
as151_web.joinNetwork(as151_net)
as151_router.joinNetwork(as151_net)
```

The `Node::joinNetwork` call connects a node to a network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

Last, put the router into the internet exchange:

```python
as151_router.joinNetworkByName('ix100')
```

The `Node::joinNetworkByName` calls take the name of the network and join the network. It first searches through the local networks, then global networks. You may use this to join a local network too. (i.e., instead of `as151_router.joinNetwork(as151_net)`, we can do `as151_router.joinNetworkByName('net0')` too.) `joinNetworkByName` call also takes an optional parameter, `address`, for overriding auto address assignment.

## Step 5: create another customer autonomous system

Repeat step 4 with a different ASN and exchange to create another transit customer:

```python
as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')
web.install('web152')
emu.addBinding(Binding('web152', filter = Filter(nodeName = 'web', asn = 152)))

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix101')
```

## Step 6: setup BGP peering

```python
ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
```

The `Ebgp::addPrivatePeering` call takes four paramters; internet exchange ID, first ASN, the second ASN, and the relationship. The relationship parameter defaults to `Peer`. The call will configure peering between the two given ASNs in the given exchange. 

The peering relationship can be one of the followings:

- `PeerRelationship.Provider`: The first ASN is considered as the upstream provider of the second ASN. The first ASN will export all routes to the second ASN, and the second ASN will only export its customers' and its own prefixes to the first ASN.
- `PeerRelationship.Peer`: The two ASNs are considered as peers. Both sides will only export their customers and their own prefixes.
- `PeerRelationship.Unfiltered`: Make both sides export all routes to each other.

We may also use the `Ebgp::addRsPeer` call to configure peering; it takes two parameters; the first is an internet exchange ID, and the second is ASN. It will configure peering between the given ASN and the given exchange's route server (i.e., setup Multi-Lateral Peering Agreement (MLPA)). Note that the session with RS will always be `Peer` relationship.

The eBGP layer setup peering by looking for the router node of the given autonomous system from within the internet exchange network. So as long as there is a router of that AS in the exchange network (i.e., joined the IX with `as15X_router.joinNetworkByName('ix100')`), the eBGP layer should be able to setup peeing just fine.

## Step 7: render the emulation

```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(mpls)
emu.addLayer(web)

emu.render()
```

The rendering process is where all the actual "things" happen. Softwares are added to the nodes, routing tables and protocols are configured, and BGP peers are configured.

## Step 8: compile the emulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the emulation to other formats. 

In this example, we will use docker on a single host to run the emulation, so we use the `Docker` compiler:

```python
emu.compile(Docker(), './transit-as-mpls')
```

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

Sometimes it will be useful to override the automated assignment for once. Both `joinNetwork` and `joinNetworkByName` accept an `address` argument for overriding the assignment:

```python
as11872_router.joinNetworkByName('ix100', address = '10.100.0.118')
```

We may alternatively implement our own `AddressAssignmentConstraint` class instead. Both `createInternetExchange` and `createNetwork` accept the `aac` argument, which will alter the auto address assignment behavior. Foe details, please refer to the API documentation.