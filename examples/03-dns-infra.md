# DNS infrastructure

In this example, we will set up the entire DNS infrastructure, complete with root server, TLD server, and DNSSEC support.

## Step 1: import and create required componets

```python
from seedsim.layers import Base, Routing, Ebgp, DomainNameService, DomainNameCachingService, Dnssec, WebService
from seedsim.renderer import Renderer
from seedsim.compiler import Docker
```

In this setup, we will need these layers: 

- The `Base` layer provides the base of the simulation; it describes what hosts belong to what autonomous system and how hosts are connected with each other. 
- The `Routing` layer acts as the base of other routing protocols. `Routing` layer (1) installs BIRD internet routing daemon on every host with router role, (2) provides lower-level APIs for manipulating BIRD's FIB (forwarding information base), adding new protocols, etc., and (3) setup proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides API for setting up intra-AS BGP peering.
- The `DomainNameService` layer provides APIs and tools for hosting domain name servers in the simulation.
- The `DomainNameCachingService` layer provides tools for hosting a local caching domain name server.
- The `Dnssec` layer works with the `DomainNameService` layer to enable DNSSEC support.
- The `WebService` layer provides API for install `nginx` web server on hosts.

We will use the defualt renderer and compiles the simulation to docker containers.

Once the classes are imported, initialize them:

```python
base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()
dns = DomainNameService(autoNs = True)
dnssec = Dnssec()
ldns = DomainNameCachingService(autoRoot = True, setResolvconf = True)

rendrer = Renderer()
docker_compiler = Docker()
```

Here, we set `autoNs = True` for the `DomainNameService` layer. `autoNs` is default to true; we only put it here so we can mention it in this guide. The `autoNs` option controls the automated `NS` behavior. When it is on (true), the DNS layer will look for host nodes hosting the zone and add their IP address to the nameserver(s) of the parent zones. In other words, it enables the DNS layer to automatically discover what zone are hosted on what nodes and add the "glue records" for them.

`autoRoot = True` is also a defualt option and it was included here for documentation. The `autoRoot` options automatically look for the root DNS in the simulation and update the root hint file bind uses, so it will use the root DNS hosted in the simulation instead of the real ones. If you want to keep the real roots while hosting root DNS in simulation, you need to explicitly disable this option. 

We also set `setResolvconf = True` for the `DomainNameCachingService` layer. This tells the layer to update the `resolv.conf` file on all nodes within the autonomous system to use the local DNS node as their DNS. This one is not on by default.

## Step 2: create an internet exchange

```python
base.createInternetExchange(100)
```

The current version of the internet simulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function call creates a new internet exchange, and will create a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetworkByName` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`. For details, check to remarks section.

Here, the internet exchange `100` is created. It creates the network `ix100`.

## Step 3: create a zone

```python
example_com = dns.getZone('example.com.')
```

The `getZone` call gets a zone or creates the zone if no such zone exists. A `Zone` instance will be returned; we will see how to work with the `Zone` object later.

Note that the `getZone` call may create more than one zones. For example, in this call, it actually created three new zones - the root zone (`.`), the `.com` TLD zone (`com.`), and the `example.com` zone (`example.com.`).

## Step 4: create an autonomous system and host the root zone (`.`)

### Step 4.1: create the autonomous system instance

### Step 4.2: create the host

### Step 4.3: create the router and configure the network

### Step 4.4: host the zone

## Step 5: create an autonomous system and host the TLD zone (`com.`)

## Step 6: create an autonomous system and host the zone (`example.com`)

## Step 7: create an autonomous system for users (optional)

## Step 8: configure DNSSEC (optional)

## Step 9: configure BGP peering

## Step 10: render the simulation

We are now done configuring the layers. The next step is to add all layers to the renderer and render the simulation:

```python
rendrer.addLayer(base)
rendrer.addLayer(routing)
rendrer.addLayer(ebgp)
rendrer.addLayer(dns)
rendrer.addLayer(ldns)
rendrer.addLayer(dnssec)
rendrer.addLayer(web)

rendrer.render()
```

The rendering process is where all the actual "things" happen. Softwares are added to the nodes, routing tables and protocols are configured, and BGP peers are configured.


## Step 11: compile the simulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the simulation to other formats. 

In this example, we will use docker on a single host to run the simulation, so we use the `Docker` compiler:

```python
docker_compiler.compile('./dns-infra')
```

Now we can find the output in the `dns-infra` directory. The docker compiler comes with a docker-compose configuration. To bring up the simulation, simply run `docker-compose build && docker-compose up` in the `dns-infra` directory.

## Remarks

### DNS chain

### DNSSEC chain

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