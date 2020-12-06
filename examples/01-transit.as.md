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

The current version of the internet simulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function calls create a new internet exchange, and will a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetworkByName` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`.

- TODO: `aac` (`AddressAssignmentConstraint` docs)

Here, two internet exchanges are created. This add two new networks, `ix100` and `ix101`, to the simulation.

## Step 3: create an autonomous system

## Step 4: create another autonomous system

## Step 5: create the transit autonomous system

## Step 6: setup BGP peering

## Step 7: rendrer the simulation

## Step 8: compile the simulation
