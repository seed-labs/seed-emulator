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
- The `DomainNameService` layer, TODO.
- The `DomainNameCachingService` layer, TODO.
- The `Dnssec` layer, TODO.
- The `WebService` layer provides API for install `nginx` web server on hosts.

## Step 2: create an internet exchange

## Step 3: create a zone

## Step 4: create an autonomous system and host the root zone

### Step 4.1: create the autonomous system instance

### Step 4.2: create the host

### Step 4.3: create the router and configure the network

### Step 4.4: host the zone

## Step 5: create an autonomous system and host the TLD zone

## Step 6: create an autonomous system and host the zone

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

### Automated NS configuration 

### Automated root DNS override

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