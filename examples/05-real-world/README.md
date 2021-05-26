# Real-world interation

In this example, we will frist setup some basic transit; we will configure two internet exchanges, AS150 will be in both exchanges. AS151 and AS152 will be in IX100 and IX101, respectively. AS150 will serve as the transit AS for AS151 and AS152. There will be four hops in AS150. AS151 and AS152 will each announce one /24 prefix and host one web server in the network.

In AS151 and AS152, we will host VPN servers that are accessible from outside the emulator, so real-world hosts can connect to the emulation. We will then add a real-world autonomous system, AS11872 (Syracuse University), to the emulation. The real-world autonomous system will collect the prefixes it announced in the real-world, and route them to the real-world from the emulation.

## Step 1: import and create required componets

```python
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf, Reality
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker
```

In this setup, we will need these layers: 

- The `Base` layer provides the base of the emulation; it describes what hosts belong to what autonomous system and how hosts are connected with each other. 
- The `Routing` layer acts as the base of other routing protocols. `Routing` layer (1) installs BIRD internet routing daemon on every host with router role, (2) provides lower-level APIs for manipulating BIRD's FIB (forwarding information base), adding new protocols, etc., and (3) setup proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides API for setting up intra-AS BGP peering.
- The `Ibgp` layer automatically setup full-mesh iBGP peering between all routers within an autonomous system.
- The `Ospf` layer automatically setup OSPF routing on all routers within an autonomous system.
- The `WebService` layer provides API for install `nginx` web server on hosts.

We will use the defualt renderer and compiles the emulation to docker containers.

Once the classes are imported, initialize them:

```python
emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
web = WebService()
real = Reality()
```

## Step 2: create the internet exchanges

```python
base.createInternetExchange(100)
base.createInternetExchange(101)
```

The current version of the internet emulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function call creates a new internet exchange, and will create a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetwork` function call.

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

The `Node::joinNetwork` call connects a node to a network. It first searches through the local networks, then global networks. Internet exchanges, for example, are considered as global network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

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

```python
real.enableRealWorldAccess(as151, 'net0')
```

The `Reality::enableRealWorldAccess` call enables real-world access to a network by hosting an OpenVPN server. The server will be reachable from the real world; we can check the server port by doing `docker ps` once the emulation is up. 

`enableRealWorldAccess` accepts three parameters; the first is the reference to the AS object, the second one is the name of network, and the third one, `naddr`, is an optional parameter for specifying how many host IP addresses to allocate to the server (default to 8). It uses the network's IP assigner to get IP addresses for host-role nodes. For details, check the `AddressAssignmentConstraint` in the remarks section.

Now, put the host and router in the network:

```python
as151_web.joinNetwork(as151_net)
as151_router.joinNetwork(as151_net)
```

The `Node::joinNetwork` call connects a node to a network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

Last, put the router into the internet exchange:

```python
as151_router.joinNetwork('ix100')
```

The `Node::joinNetwork` call connects a node to a network. It first searches through the local networks, then global networks. Internet exchanges, for example, are considered as global network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

## Step 5: create another customer autonomous system

Repeat step 4 with a different ASN and exchange to create another transit customer:

```python
as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(152, 'net0')
real.enableRealWorldAccess(as152, 'net0')

as152_web.joinNetwork('net0')
as152_router.joinNetwork('net0')

as152_router.joinNetwork('ix101')
```

## Step 6: create the real-world customer autonomous system

First, create the autonomous system object:

```python
as11872 = base.createAutonomousSystem(11872)
```

Then, create a real world router:

```python
as11872_router = real.createRealWorldRouter(as11872)
```

The `createRealWorldRouter` call takes three parameters; the first is the reference to the autonomous system object to create the router, the second, `nodename`, is the name of router node (default to `rw`), and the third, `prefixes` is a list of prefixes (default to `None`). Here, we let it default to `None`, so the layer will get the prefixes list for us.

If `prefixes` is set to `None` (the `NoneType`, not empty list), the layer will automatically fetch the list of prefixes announced by the autonomous system in the real world. Otherwise, it will use the list of prefixes we specified.

The `createRealWorldRouter` returns a `RealWorldRouter` instance. `RealWorldRouter` class was derived from the regular router node class; it adds an `addRealWorldRoute` method to router class. `addRealWorldRoute` accepts one parameter, `prefix`, and will route the given prefix to real-world.

The last step is to connect the autonomous system to an internet exchange. Here, we picked IX101. We need to override the auto address assignment, as 11872 is out of the 2~254 range:

```python
as11872_router.joinNetwork('ix101', '10.101.0.118')
```

## Step 7: setup BGP peering

```python
ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 11872, abRelationship = PeerRelationship.Provider)
```

The `Ebgp::addPrivatePeering` call takes four paramters; internet exchange ID, first ASN, the second ASN, and the relationship. The relationship parameter defaults to `Peer`. The call will configure peering between the two given ASNs in the given exchange. 

The peering relationship can be one of the followings:

- `PeerRelationship.Provider`: The first ASN is considered as the upstream provider of the second ASN. The first ASN will export all routes to the second ASN, and the second ASN will only export its customers' and its own prefixes to the first ASN.
- `PeerRelationship.Peer`: The two ASNs are considered as peers. Both sides will only export their customers and their own prefixes.
- `PeerRelationship.Unfiltered`: Make both sides export all routes to each other.

We may also use the `Ebgp::addRsPeer` call to configure peering; it takes two parameters; the first is an internet exchange ID, and the second is ASN. It will configure peering between the given ASN and the given exchange's route server (i.e., setup Multi-Lateral Peering Agreement (MLPA)). Note that the session with RS will always be `Peer` relationship.

The eBGP layer setup peering by looking for the router node of the given autonomous system from within the internet exchange network. So as long as there is a router of that AS in the exchange network (i.e., joined the IX with `as15X_router.joinNetwork('ix100')`), the eBGP layer should be able to setup peeing just fine.

## Step 8: host the services

We have created two web server nodes, but we have not hosted the actual web service on them. Let's proceed to host the services.

```python
web.install('web1')
web.install('web2')
```

First, create two virual nodes with the `Service::install` call.

```python
emu.addBinding(Binding('web1', filter = Filter(asn = 151, nodeName = 'web')))
emu.addBinding(Binding('web2', filter = Filter(asn = 152, nodeName = 'web')))
```

Then, bind them to the physical nodes we created eariler.

## Step 9: render the emulation

```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)
emu.addLayer(real)

emu.render()
```

The rendering process is where all the actual "things" happen. Softwares are added to the nodes, routing tables and protocols are configured, and BGP peers are configured.

## Step 9: compile the emulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the emulation to other formats. 

In this example, we will use docker on a single host to run the emulation, so we use the `Docker` compiler:

```python
emu.compile(Docker(), './real-world')
```

## Remarks

### Transit's internal network

In this particular example, we used OSPF and IBGP for internal routing. IBGP and OSPF layer does not need to be configured explicitly; they are by default enabled on all autonomous systems.

The default behaviors are as follow:

- IBGP is configured between all routers within an autonomous system,
- OSPF is enabled on all networks that have two or more routers in them.
- Passive OSPF is enabled on all other connected networks.

We may "mask" an autonomous system from OSPF or IBGP, if we don't want the behavior. For IBGP, use `Ibgp::mask` method. It takes an ASN as input and will disable IBGP on that autonomous system:

```python
ibgp.mask(151)
```

The above masks AS151 from IBGP, meaning the IBGP layer won't touch any routers from AS151. However, in this particular example, AS151 has only one router, so it wasn't going to be configured by the IBGP layer anyway.

For the OSPF layer, we have a bit more customizability. To mask an entire autonomous system, use `Ospf::maskAsn`:

```python
ospf.maskAsn(151)
```

We can also mask only a single network with `Ospf::maskNetwork` and `Ospf::maskByName`. `maskNetwork` call takes one parameter - the reference to the network object, and `maskByName` call takes two parameters, the first is the scope (i.e., ASN) of the network, and the second is the name of the network. Masking a network takes it out of the OSPF layer's consideration. In other words, no OSPF will be enabled on any interface connected to the network, passive or active.

```python
# mask with name
ospf.maskByName('151', 'net0')

# mask with reference
ospf.maskNetwork(as152_net)
```

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