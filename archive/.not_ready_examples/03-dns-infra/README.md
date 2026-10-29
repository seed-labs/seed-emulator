# DNS infrastructure & other DNS services

In this example, we will set up the entire DNS infrastructure, complete with root server, TLD server, and DNSSEC support.

## Step 1: import and create required componets

```python
from seedemu.layers import Base, Routing, Ebgp, Dnssec
from seedemu.services import DomainNameService, DomainNameCachingService, WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker
```

In this setup, we will need these layers: 

- The `Base` layer provides the base of the emulation; it describes what hosts belong to what autonomous system and how hosts are connected with each other. 
- The `Routing` layer acts as the base of other routing protocols. `Routing` layer (1) installs BIRD internet routing daemon on every host with router role, (2) provides lower-level APIs for manipulating BIRD's FIB (forwarding information base), adding new protocols, etc., and (3) setup proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides API for setting up intra-AS BGP peering.
- The `DomainNameService` layer provides APIs and tools for hosting domain name servers in the emulation.
- The `DomainNameCachingService` layer provides tools for hosting a local caching domain name server.
- The `Dnssec` layer works with the `DomainNameService` layer to enable DNSSEC support.
- The `WebService` layer provides API for install `nginx` web server on hosts.

We will use the defualt renderer and compiles the emulation to docker containers.

Once the classes are imported, initialize them:

```python
emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
dns = DomainNameService()
dnssec = Dnssec()
ldns = DomainNameCachingService()
```

Here, we set `autoNameServer = True` for the `DomainNameService` layer. `autoNameServer` is default to true; we only put it here so we can mention it in this guide. The `autoNameServer` option controls the automated `NS` behavior. When it is on (true), the DNS layer will look for host nodes hosting the zone and add their IP address to the nameserver(s) of the parent zones. In other words, it enables the DNS layer to automatically discover what zone are hosted on what nodes and add the "glue records" for them.

`autoRoot = True` is also a defualt option and it was included here for documentation. The `autoRoot` options automatically look for the root DNS in the emulation and update the root hint file bind uses, so it will use the root DNS hosted in the emulation instead of the real ones. If you want to keep the real roots while hosting root DNS in emulation, you need to explicitly disable this option. 

## Step 2: create an internet exchange

```python
base.createInternetExchange(100)
```

The `Base::createInternetExchange` function call creates a new internet exchange, and will create a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetwork` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`. For details, check to remarks section.

Here, the internet exchange `100` is created. It creates the network `ix100`.

## Step 3: create a zone

```python
example_com = dns.getZone('example.com.')
```

The `getZone` call gets a zone or creates the zone if no such zone exists. A `Zone` instance will be returned; we will see how to work with the `Zone` object later.

Note that the `getZone` call may create more than one zones. For example, in this call, it actually created three new zones - the root zone (`.`), the `.com` TLD zone (`com.`), and the `example.com` zone (`example.com.`).

## Step 4: create an autonomous system and host node for the root zone (`.`)

Now we have the zones, but we still need to host it somewhere. Let's first create an autonomous system for hosting our root server. Note that we are only creating server nodes now and not installing services on the nodes yet. We will do the installations later.

### Step 4.1: create the autonomous system instance

```python
as150 = base.createAutonomousSystem(150)
```

Creating a new autonomous system is simple; just call the `Base::createAutonomousSystem` function. The call returns an `AutonomousSystem` class instance, and it can be used to further create hosts in the autonomous system.

### Step 4.2: create a host node

Now, we need to create a host node to run the DNS service on. Once we have the `AutonomousSystem` instance, we can create a new host for the web service. Creating a new host is also simple; simply call the `AutonomousSystem::createHost` API. The call only takes one parameter, `name`, which is the name of the host, and it will return an `Node` instance on success:

```python
root_server = as150.createHost('root_server')
```

We won't install the DNS on the node just yet. The reason will be explained later.

### Step 4.3: create the router and configure the network

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
root_server.joinNetwork(as150_net)
as150_router.joinNetwork(as150_net)
```

The `Node::joinNetwork` call connects a node to a network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

Last, put the router into the internet exchange:

```python
as150_router.joinNetwork('ix100')
```

The `Node::joinNetwork` call connects a node to a network. It first searches through the local networks, then global networks. Internet exchanges, for example, are considered as global network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

## Step 5: create an autonomous system and host node for the TLD zone (`com.`)

Now, repeat step 4 with a different ASN for the `com.` zone:

```python
as151 = base.createAutonomousSystem(151)
as151 = base.createAutonomousSystem(151)

com_server = as151.createHost('com_server')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')

com_server.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')
```

## Step 6: create an autonomous system and host node for the zone (`example.com`)

Then, repeat step 4/5 with a different ASN for the `example.com.` zone:

```python
as152 = base.createAutonomousSystem(152)

example_com_web = as152.createHost('example_web')

example_com_server = as152.createHost('example_com_server')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

example_com_web.joinNetwork('net0', '10.152.0.200')
example_com_server.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix100')

example_com.addRecord('@ A 10.152.0.200')
```

There are a few new things here; let's break them down.

```python
example_com_web = as152.createHost('example_web')
```

Here, in addition to the name server node, we created a web server node. We will use this node later to host a web page on example.com.

```python
example_com_web.joinNetwork('net0', '10.152.0.200')
```

Here, when joining the network with the webserver node, we manually assigned an IP address to the node. 

```python
example_com.addRecord('@ A 10.152.0.200')
```

The above adds a new `A` record to the `example.com.` zone. It points the `@` domain to the IP address of the webserver node, `10.152.0.200`.

## Step 7: create an autonomous system for users

Now, since we are not using the real IP address of root DNS, nor do we set up a recursive DNS server to lookup our root server, normal containers won't be able to use the zones we hosted in the emulation. To deal with this, we can create a new autonomous system for users and host a recursive DNS server (or local DNS, DNS caching server):

```python
as153 = base.createAutonomousSystem(153)

local_dns = as153.createHost('local_dns')

client = as153.createHost('client')

as153_router = as153.createRouter('router0')

as153_net = as153.createNetwork('net0', '8.8.8.0/24')

routing.addDirect(153, 'net0')

local_dns.joinNetwork('net0', '8.8.8.8')
client.joinNetwork('net0')
as153_router.joinNetwork('net0')

as153_router.joinNetwork('ix100')
```

The important part is:

```python
local_dns = as153.createHost('local_dns')
```

This creates a local DNS server node. We will install the local DNS server to it in the next two steps.

## Step 8: creating virtual nodes

Before we proceed further, let's first talk about the concept of virtual node and physical node. Physical nodes are "real" nodes; they are created by the `AutonomousSystem::createHost` API, just like what we did above. Virtual nodes are not "real" nodes; consider them as a "blueprint" of a physical node. We can make changes to the "blueprint" then bind the virtual nodes to physical nodes. The changes we made to the virtual node will be applied to the physical node that the virtual node is attached to.

### Step 8.1: creating virtual nodes for DNS servers

To install a DNS server on a node, we first need to call `Service::install`. `DomainNameService` class derives from the `Service` class, so it also has the `install` method. The `install` takes a virtual node name and installs the service on that virtual node. The call will return a server instance. In `DomainNameService`'s case, it returns a `DomainNameServer` instance, which allows us to manipulate the configuration of the name server.

For example, if we would like to host the root zone (`.` zone) on a virtual node with the name `root_server`, we can do this:

```python
root_dns_server = dns.install('root_server')
root_server.addZone('.')
```

With this, host our zones in the emulation:

```python
dns.install('root_server').addZone('.')
dns.install('com_server').addZone('com.')
dns.install('example_com_server').addZone('example.com.')
```

### Step 8.1: creating virtual nodes for other services

We want two other services. Let's create virtual nodes for them too:

```python
ldns.install('local_dns').setConfigureResolvconf(True)

web.install('example_web')
```

The `setConfigureResolvconf` method is provided by the local DNS server. It defaults to false, and when set to true, will automatically update `resolv.conf` on all nodes within the AS to use it as the name server.

## Step 9: binding virtual nodes

Now, we need to attach those said "blueprints" to the physical nodes. Before we proceed, let's take a look at the filter and binding class:

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

With this, we can bind virtual nodes to physical nodes. 

For example, if we do not care about what AS the node will be in, and just want to bind the virtual node `root_server` to any physical node with name `root_server`, we can do this:

```python
emu.addBinding(Binding('root_server', filter = Filter(nodeName = 'root_server')))
```

And, if we want to bind the node `com_server` to any available node in AS151, we can do this:

```python
emu.addBinding(Binding('com_server', filter = Filter(asn = 151)))
```

Continue and provide bindings for other virtual nodes:

```python
# bind by name & asn
emu.addBinding(Binding('example_com_server', filter = Filter(
    asn = 152,
    nodeName = 'example_com_server'
)))

# bind by name (regex)
emu.addBinding(Binding('.*web', filter = Filter(nodeName = '.*web')))

# bind by prefix
emu.addBinding(Binding('local_dns', filter = Filter(prefix = '8.8.8.0/24')))
```

## Step 10: configure DNSSEC (optional)

The DNSSEC layer configures DNSSEC for a zone. It works by signing the zone on-the-fly when the emulator starts and sending DS records to parents with `nsupdate`.

```python
dnssec.enableOn('.')
dnssec.enableOn('com.')
dnssec.enableOn('example.com.')
```

The `Dnssec::enableOn` call takes only one parameter, the zone name. Note that for DNSSEC to work, you will need to sign the entire chain to build the "chain of trust." 

## Step 11: configure BGP peering

```python
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
ebgp.addRsPeer(100, 153)
```

The `Ebgp::addRsPeer` call takes two parameters; the first is an internet exchange ID, and the second is ASN. It will configure peering between the given ASN and the given exchange's route server (i.e., setup Multi-Lateral Peering Agreement (MLPA)). 

Peering can alternatively be configured with `Ebgp::addPrivatePeering`. `addPrivatePeering` method takes four parameters: internet exchange ID, first participant ASN, second participant ASN, and the peer relationship. `addPrivatePeering` will setup peering between first and second ASN. The peering relationship can be one of the followings:

- `PeerRelationship.Provider`: The first ASN is considered as the upstream provider of the second ASN. The first ASN will export all routes to the second ASN, and the second ASN will only export its customers' and its own prefixes to the first ASN.
- `PeerRelationship.Peer`: The two ASNs are considered as peers. Both sides will only export their customers and their own prefixes.
- `PeerRelationship.Unfiltered`: Make both sides export all routes to each other.

Note that the session with RS (`addRsPeer`) will always be `Peer` relationship.

The eBGP layer setup peering by looking for the router node of the given autonomous system from within the internet exchange network. So as long as there is a router of that AS in the exchange network (i.e., joined the IX with `as15X_router.joinNetwork('ix100')`), the eBGP layer should be able to setup peeing just fine.

## Step 12: render the emulation

We are now done configuring the layers. The next step is to add all layers to the renderer and render the emulation:

```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(dns)
emu.addLayer(ldns)
emu.addLayer(dnssec)
emu.addLayer(web)

emu.render()
```

The rendering process is where all the actual "things" happen. Softwares are added to the nodes, routing tables and protocols are configured, and BGP peers are configured.

## Step 13: compile the emulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the emulation to other formats. 

In this example, we will use docker on a single host to run the emulation, so we use the `Docker` compiler:

```python
emu.compile(Docker(), './dns-infra')
```

Now we can find the output in the `dns-infra` directory. The docker compiler comes with a docker-compose configuration. To bring up the emulation, simply run `docker-compose build && docker-compose up` in the `dns-infra` directory.

## Remarks

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