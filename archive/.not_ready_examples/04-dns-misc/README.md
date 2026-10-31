# DNS infrastructure and zone-generating layers

In this example, we will set up the entire DNS infrastructure, complete with root server, TLD server, and DNSSEC support. We will also configure some additional services that create DNS zones that add reverse DNS and ASN associations for IP addresses.

## Step 1: import and create required componets

```python
from seedemu.layers import Base, Routing, Ebgp, Dnssec
from seedemu.services import DomainNameService, DomainNameCachingService, WebService, CymruIpOriginService, ReverseDomainNameService
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
- The `CymruIpOriginService` hosts the `cymru.com` zone. Team Cymru provides a way to look up the origin ASN of any given IP address by DNS; the service is used by various network utilities like `traceroute` and `mtr`, which we will be using in the emulator to check routes. The service works by hosting the zone `origin.asn.cymru.com`; for example, try `dig TXT '0.0.230.128.origin.asn.cymru.com'`. In the emulator, this layer collects all networks in the emulation and creates the zone in the DNS layer.
- The `ReverseDomainNameService` creates the `in-addr.arpa.` zone (i.e., the reverse IP zone). All IP addresses on any node in the emulation will be given a reverse DNS record like `nodename-netname.nodetype.asn.net`.

We will use the defualt renderer and compiles the emulation to docker containers.

Once the classes are imported, initialize them:

```python
emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
dns = DomainNameService(autoNameServer = True)
dnssec = Dnssec()
ldns = DomainNameCachingService(autoRoot = True)
rdns = ReverseDomainNameService()
ip_origin = CymruIpOriginService()
```

Here, we set `autoNameServer = True` for the `DomainNameService` layer. `autoNameServer` is default to true; we only put it here so we can mention it in this guide. The `autoNameServer` option controls the automated `NS` behavior. When it is on (true), the DNS layer will look for host nodes hosting the zone and add their IP address to the nameserver(s) of the parent zones. In other words, it enables the DNS layer to automatically discover what zone are hosted on what nodes and add the "glue records" for them.

`autoRoot = True` is also a defualt option and it was included here for documentation. The `autoRoot` options automatically look for the root DNS in the emulation and update the root hint file bind uses, so it will use the root DNS hosted in the emulation instead of the real ones. If you want to keep the real roots while hosting root DNS in emulation, you need to explicitly disable this option. 

## Step 2: create an internet exchange

```python
base.createInternetExchange(100)
```

The current version of the internet emulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function call creates a new internet exchange, and will create a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetwork` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`. For details, check to remarks section.

Here, the internet exchange `100` is created. It creates the network `ix100`.

## Step 3: create a zone

```python
example_com = dns.getZone('example.com.')
```

The `getZone` call gets a zone or creates the zone if no such zone exists. A `Zone` instance will be returned; we will see how to work with the `Zone` object later.

Note that the `getZone` call may create more than one zones. For example, in this call, it actually created three new zones - the root zone (`.`), the `.com` TLD zone (`com.`), and the `example.com` zone (`example.com.`).

## Step 4: create an autonomous system and host the root zone (`.`)

Now we have the zones, but we still need to host it somewhere. Let's first create an autonomous system for hosting our root server.

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
root_server.joinNetwork('net0')
as150_router.joinNetwork('net0')
```

The `Node::joinNetwork` call connects a node to a network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

Last, put the router into the internet exchange:

```python
as150_router.joinNetwork('ix100')
```

The `Node::joinNetwork` call connects a node to a network. It first searches through the local networks, then global networks. Internet exchanges, for example, are considered as global network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

### Step 4.4: host the zone

Now, with the network interfaces properly configured, we can start hosting DNS zone on the host node: 

```python
dns.install('root_server').addZone('.')
```

The `DomainNameService::install` call install the service on a virtual node and return a name server instance. The call above created a virtual node `root_server` and hosted the root zone (`.`) on it.

Next, bind the virtual node to the physical node we just created:

```python
emu.addBinding(Binding('root_server', filter = Filter(asn = 150, nodeName = 'root_server')))
```

## Step 5: create an autonomous system and host the TLD zones (`com.`, `arpa.`)

Now, repeat step 4 with a different ASN and host `com.` and `arpa.` zone:

```python
as151 = base.createAutonomousSystem(151)

com_server = as151.createHost('com_server')
arpa_server = as151.createHost('arpa_server')

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(151, 'net0')

com_server.joinNetwork('net0')
arpa_server.joinNetwork('net0')
as151_router.joinNetwork('net0')

as151_router.joinNetwork('ix100')

dns.install('com_server').addZone('com.')
dns.install('arpa_server').addZone('arpa.')

emu.addBinding(Binding('com_server', filter = Filter(asn = 151, nodeName = 'com_server')))
emu.addBinding(Binding('arpa_server', filter = Filter(asn = 151, nodeName = 'arpa_server')))
```

## Step 6: create an autonomous system and host the domain zones (`example.com`, `cymru.com`, `in-addr.arpa`)

Then, repeat step 4/5 with a different ASN and host the `example.com.` zone:

```python
as152 = base.createAutonomousSystem(152)

example_com_web = as152.createHost('example_web')

web.install('example_web')
emu.addBinding(Binding('example_web', filter = Filter(asn = 152, nodeName = 'example_web')))

example_com_server = as152.createHost('example_com_server')
cymru_com_server = as152.createHost('cymru_com_server')
v4_rdns_server = as152.createHost('v4_rdns_server')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')

example_com_web.joinNetwork('net0', '10.152.0.200')
example_com.addRecord('@ A 10.152.0.100')

example_com_server.joinNetwork('net0')
cymru_com_server.joinNetwork('net0')
v4_rdns_server.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix100')

dns.install('example_com_server').addZone('example.com.')
dns.install('cymru_com_server').addZone('cymru.com.')
dns.install('v4_rdns_server').addZone('in-addr.arpa.')

emu.addBinding(Binding('example_com_server', filter = Filter(asn = 152, nodeName = 'example_com_server')))
emu.addBinding(Binding('cymru_com_server', filter = Filter(asn = 152, nodeName = 'cymru_com_server')))
emu.addBinding(Binding('v4_rdns_server', filter = Filter(asn = 152, nodeName = 'v4_rdns_server')))
```

There are a few new things here; let's break them down.

```python
web.install('example_web')
emu.addBinding(Binding('example_web', filter = Filter(asn = 152, nodeName = 'example_web')))
```

The above install `WebService` on `example_web` virtual node and bind the node to `example_web` physical node. 

```python
example_com_web.joinNetwork('net0', '10.152.0.200')
example_com.addRecord('@ A 10.152.0.100')
```

When joining network with the `example_web` node, we want to fix its IP address and have `example.com` points to it. 

## Step 7: create an autonomous system for users

Now, since we are not using the real IP address of root DNS, nor do we set up a recursive DNS server to lookup our root server, normal containers won't be able to use the zones we hosted in the emulation. To deal with this, we can create a new autonomous system for users and host a recursive DNS server (or local DNS, DNS caching server):

```python
as153 = base.createAutonomousSystem(153)

local_dns = as153.createHost('local_dns')

ldns.install('local_dns').setConfigureResolvconf(True)
emu.addBinding(Binding('local_dns', filter = Filter(asn = 153, nodeName = 'local_dns')))

client = as153.createHost('client')

as153_router = as153.createRouter('router0')

as153_net = as153.createNetwork('net0')

routing.addDirect(as153_net)

local_dns.joinNetwork(as153_net)
client.joinNetwork(as153_net)
as153_router.joinNetwork(as153_net)

as153_router.joinNetwork('ix100')
```

The important part is:

```python
ldns.install('local_dns').setConfigureResolvconf(True)
emu.addBinding(Binding('local_dns', filter = Filter(asn = 153, nodeName = 'local_dns')))
```

This creates a local DNS server. The `setConfigureResolvconf` method is provided by the local DNS server. It defaults to false, and when set to true, will automatically update `resolv.conf` on all nodes within the AS to use it as the name server; and since we have `autoRoot`, the local DNS will be able to find the root zone we hosted in the emulation.

## Step 8: configure DNSSEC (optional)

The DNSSEC layer configures DNSSEC for a zone. It works by signing the zone on-the-fly when the emulator starts and sending DS records to parents with `nsupdate`.

```python
dnssec.enableOn('.')
dnssec.enableOn('com.')
dnssec.enableOn('example.com.')
```

The `Dnssec::enableOn` call takes only one parameter, the zone name. Note that for DNSSEC to work, you will need to sign the entire chain to build the "chain of trust." 

## Step 9: configure BGP peering

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

## Step 10: render the emulation

We are now done configuring the layers. The next step is to add all layers to the renderer and render the emulation:

```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(dns)
emu.addLayer(ldns)
emu.addLayer(dnssec)
emu.addLayer(web)
emu.addLayer(rdns)
emu.addLayer(ip_origin)

emu.render()
```

The rendering process is where all the actual "things" happen. Softwares are added to the nodes, routing tables and protocols are configured, and BGP peers are configured.

## Step 11: compile the emulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the emulation to other formats. 

In this example, we will use docker on a single host to run the emulation, so we use the `Docker` compiler:

```python
emu.compile(Docker(), './dns-misc')
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

Sometimes it will be useful to override the automated assignment for once. Both `joinNetwork` accepts an `address` argument for overriding the assignment:

```python
as11872_router.joinNetwork('ix100', address = '10.100.0.118')
```

We may alternatively implement our own `AddressAssignmentConstraint` class instead. Both `createInternetExchange` and `createNetwork` accept the `aac` argument, which will alter the auto address assignment behavior. Foe details, please refer to the API documentation.