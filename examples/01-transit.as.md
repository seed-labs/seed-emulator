# Transit AS

This is a more in-depth example; in this example, we will configure two internet exchanges, AS150 will be in both exchanges. AS151 and AS152 will be in IX100 and IX101, respectively. AS150 will serves as the transit AS for AS151 and AS152, AS151 and AS152 will each announce one /24 prefix and host one web server in the network.

## Step 1: import and create required componets

```python
from seedsim.layers import Base, Routing, Ebgp, Ibgp, Ospf, WebService
from seedsim.renderer import Renderer
from seedsim.compiler import Docker
```

In this setup, we will need these layers: 

- The `Base` layer provides the base of the simulation; it describes what hosts belong to what autonomous system and how hosts are connected with each other. 
- The `Routing` layer acts as the base of other routing protocols. `Routing` layer (1) installs BIRD internet routing daemon on every host with router role, (2) provides lower-level APIs for manipulating BIRD's FIB (forwarding information base), adding new protocols, etc., and (3) setup proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides API for setting up intra-AS BGP peering.
- The `Ibgp` layer automatically setup full-mesh iBGP peering between all routers within an autonomous system.
- The `Ospf` layer automatically setup OSPF routing on all routers within an autonomous system.
- The `WebService` layer provides API for install `nginx` web server on hosts.

We will use the defualt renderer and compiles the simulation to docker containers.

Once the classes are imported, initialize them:

```python
base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
web = WebService()

rendrer = Renderer()
docker_compiler = Docker()
```

## Step 2: create the internet exchanges

```python
base.createInternetExchange(100)
base.createInternetExchange(101)
```

The current version of the internet simulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function call creates a new internet exchange, and will create a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetworkByName` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`. For details, check to remarks section.

Here, two internet exchanges are created. This add two new networks, `ix100` and `ix101`, to the simulation.

## Step 3: create an autonomous system

## Step 4: create another autonomous system

## Step 5: create the transit autonomous system

## Step 6: setup BGP peering

## Step 7: rendrer the simulation

## Step 8: compile the simulation

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

Sometimes it will be useful to override the automated assignment for once. Both `joinNetwork` and `joinNetworkByName` accept an `address` argument for overriding the assignment:

```python
as11872_router.joinNetworkByName('ix100', address = '10.100.0.118')
```

We may alternatively implement our own `AddressAssignmentConstraint` class instead. Both `createInternetExchange` and `createNetwork` accept the `aac` argument, which will alter the auto address assignment behavior. Foe details, please refer to the API documentation.