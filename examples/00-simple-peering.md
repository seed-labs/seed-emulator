Simple BGP peering
---

This is the most basic example; peer three autonomous systems (AS150, AS151, and AS152) at an internet exchange. Each autonomous system announces a /24 prefix, and each is running a single web server within the network.

## Step 1: import and create required componets

```python
from seedsim.layers import Base, Routing, Ebgp, WebService
from seedsim.renderer import Renderer
from seedsim.compiler import Docker
```

In this setup, we will need four layers: 

- The `Base` layer provides the base of the simulation; it describes what hosts belong to what autonomous system and how hosts are connected with each other. 
- The `Routing` layer acts as the base of other routing protocols. `Routing` layer (1) installs BIRD internet routing daemon on every host with router role, (2) provides lower-level APIs for manipulating BIRD's FIB (forwarding information base), adding new protocols, etc., and (3) setup proper default route on non-router role hosts to point to the first router in the network.
- The `Ebgp` layer provides API for setting up intra-AS BGP peering.
- The `WebService` layer provides API for install `nginx` web server on hosts.

We will use the defualt renderer and compiles the simulation to docker containers.

Then, initialize them:

```python
base = Base()
routing = Routing()
ebgp = Ebgp()
web = WebService()

rendrer = Renderer()

docker_compiler = Docker()
```

## Step 2: create an internet exchange

```python
base.createInternetExchange(100)
```

The current version of the internet simulator is only possible to peer autonomous systems from within the internet exchange. The `Base::createInternetExchange` function calls create a new internet exchange, and will a new global network name `ix{id}` with network prefix of `10.{id}.0.0/24`, where `{id}` is the ID of the internet exchange. The exchange network can later be joined by router nodes using the `Node::joinNetworkByName` function call.

You may optionally set the IX LAN prefix with the `prefix` parameter and the way it assigns IP addresses to nodes with the `aac` parameter when calling `createInternetExchange`.

- TODO: `aac` (`AddressAssignmentConstraint` docs)

Here, the internet exchange `100` is created. It creates the network `ix100`.

## Step 3: create an autonomous system

### Step 3.1: create the autonomous system instance

```python
as150 = base.createAutonomousSystem(150)
```

Creating a new autonomous system is as simple as calling the `Base::createAutonomousSystem` function. The call returns an `AutonomousSystem` class instance, and it can be used to further create hosts in the autonomous system.

### Step 3.2: create the host

Once we have the `AutonomousSystem` instance, we can create a new host for the web service. Creating a new host is also simple; simply call the `AutonomousSystem::createHost` API. The call only takes one parameter, `name`, which is the name of the host, and it will return an `Node` instance on success. In this case, we will name our new host `web`, since we will be hosting `WebService` on it:

```python
as150_web = as150.createHost('web')
```

Then, we can start installing `WebService` onto the host node we just created. This can be done with the `Service::installOn` call. `WebService` class derives from the `Service` class, so it also has the `installOn` method. The `installOn` takes a `Node` instance and install the service on that node:

```python
web.installOn(as150_web)
```

Alternatively, we can use the `Service::installOnAll` API to install the service on all nodes of an autonomous system. The `installOnAll` API takes an integer as input and install the service on all host nodes in that AS. In other words, we can use `web.installOnAll(150)` to install `WebService` on all hosts nodes of AS150.

### Step 3.3: create the router and setup the network

Next, we will need a router. Creating a router is similar to creating a host. The `AutonomousSystem::createRouter` takes a name and returns `Node` instance:

```python
as150_router = as150.createRouter('router0')
```

To connect the router (`router0`) with our host node (`web`), create a new network:

```python
as150_net = as150.createNetwork('net0')
```

The `AutonomousSystem::createNetwork` calls create a new local network (as opposed to the networks created by `Base::createInternetExchange`), which can only be joined by nodes from within the autonomous system. Similar to the `createInternetExchange` call, the `createNetwork` call also automatically assigns network prefixes; it uses `10.{asn}.{id}.0/24` by default. `createNetwork` call also accept `prefix` and `aac` parameter for configuring prefix and setting up auto address assignment.

- TODO: `aac` (`AddressAssignmentConstraint` docs)

We now have the network, it is not in the FIB yet, and thus will not be announce to BGP peers. We need to let our routing daemon know we want the network in FIB. This can be done by:

```python
routing.addDirect(as150_net)
```

The `Routing::addDirect` call marks a network as a "direct" network. A "direct" network will be added to the `direct` protocol block of BIRD, so the prefix of the directly connected network will be loaded into FIB.

Alternatively, `Routing::addDirectByName` can be used to mark networks as direct network by network name. For example, `routing.addDirectByName(150, 'net0')` will do the same thing as above.

Now, put the host and router in the network:

```python
as150_web.joinNetwork(as150_net)
as150_router.joinNetwork(as150_net)
```

The `Node::joinNetwork` call connects a node to a network. It can also optionally takes another parameter, `address`, to override the auto address assignment. 

Last, put the router into the internet exchange:

```python
as150_router.joinNetworkByName('ix100')
```

The `Node::joinNetworkByName` calls take the name of the network and join the network. It first searches through the local networks, then global networks. You may use this to join a local network too. (i.e., instead of `as150_router.joinNetwork(as150_net)`, you can do `as150_router.joinNetworkByName('net0')` too.) `joinNetworkByName` call also takes an optional parameter, `address`, for overriding auto address assignment.

## Step 4: create more autonomous systems

Repeat step 3 two more times with different ASNs:

```python
as151 = base.createAutonomousSystem(151)

as151_web = as151.createHost('web')
web.installOn(as151_web)

as151_router = as151.createRouter('router0')

as151_net = as151.createNetwork('net0')

routing.addDirect(as151_net)

as151_web.joinNetwork(as151_net)
as151_router.joinNetwork(as151_net)

as151_router.joinNetworkByName('ix100')

###############################################################################

as152 = base.createAutonomousSystem(152)

as152_web = as152.createHost('web')
web.installOn(as152_web)

as152_router = as152.createRouter('router0')

as152_net = as152.createNetwork('net0')

routing.addDirect(as152_net)

as152_web.joinNetwork(as152_net)
as152_router.joinNetwork(as152_net)

as152_router.joinNetworkByName('ix100')
```

## Step 5: setup BGP peering

Setting up BGP peering is also simple:

```python
ebgp.addRsPeer(100, 150)
ebgp.addRsPeer(100, 151)
ebgp.addRsPeer(100, 152)
```

The `Ebgp::addRsPeer` call takes two parameters; the first is an internet exchange ID, and the second is ASN. It will configure peering between the given ASN and the given exchange's route server (i.e., setup Multi-Lateral Peering Agreement (MPLA)). Peering can alternatively be configured with `Ebgp::addPrivatePeering`. `addPrivatePeering` method takes three parameters: internet exchange ID, first participant ASN, and second participant ASN. `addPrivatePeering` will setup peering between first and second ASN. 

The eBGP layer setup peering by looking for the router node of the given autonomous system from within the internet exchange network. So as long as there is a router of that AS in the exchange network (i.e., joined the IX with `as15X_router.joinNetworkByName('ix100')`), the eBGP layer should be able to setup peeing just fine.

## Step 6: rendrer the simulation

We are now done configuring the layers. The next step is to add all layers to the renderer and render the simulation:

```python
rendrer.addLayer(base)
rendrer.addLayer(routing)
rendrer.addLayer(ebgp)
rendrer.addLayer(web)

rendrer.render()
```

The rendering process is where all the actual "things" happen. Softwares are added to the nodes, routing tables and protocols are configured, and BGP peers are configured.

## Step 7: compile the simulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the simulation to other formats. 

In this example, we will use docker on a single host to run the simulation, so we use the `Docker` compiler:

```python
docker_compiler.compile('./simple-peering')
```

Now we can find the output in the `simple-peering` directory. The docker compiler comes with a docker-compose configuration. To bring up the simulation, simply run `docker-compose build && docker-compose up` in the `simple-peering` directory.