# Transit AS

This is a more in-depth example; in this example, we will configure two internet exchanges, AS150 will be in both exchanges. AS151 and AS152 will be in IX100 and IX101, respectively. AS150 will serve as the transit AS for AS151 and AS152. There will be four hops in AS150. AS151 and AS152 will each announce one /24 prefix and host one web server in the network.

## Step 1: Import and create required components

```python
from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.compiler import Docker
```

In this setup, we will need these layers. We only explain the layers that 
are not covered in the previous examples. 

- The `Base` layer.
- The `Routing` layer.
- The `Ebgp` layer. 
- The `Ibgp` layer: automatically sets up full-mesh iBGP peering between all routers within an autonomous system.
- The `Ospf` layer: automatically sets up OSPF routing on all routers within an autonomous system.
- The `WebService` layer. 


```python
emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
web = WebService()
```

## Step 2: Create the internet exchanges

```python
base.createInternetExchange(100)
base.createInternetExchange(101)
```
See `00-simple-peering` for the explanation of the `Base::createInternetExchange` API.
Here, two internet exchanges are created. 
This adds two new networks, `ix100` and `ix101`, to the emulation.

## Step 3: Create a transit autonomous system

### Step 3.1: Create AS150 and its internal networks

Since we plan to have four hops in AS150, we will need three internal networks to connect the routers together.

```python
as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')
```

### Step 3.2: Create routers

We need four routers. The `AutonomousSystem::createRouter` takes a name and returns the router `Node` instance:

```python
r1 = as150.createRouter('r1')
r2 = as150.createRouter('r2')
r3 = as150.createRouter('r3')
r4 = as150.createRouter('r4')
```
### Step 3.3: Attach routers to networks

We need to connect the routers to the networks. We use `r1` and `r4` as the eBGP routers,
so they need to connect to the network in the corresponding internet exchange. The 
`r2` and `r3` are just internal routers. 

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
### Note:

In this particular example, we used OSPF and IBGP for internal routing. IBGP and OSPF layer does not need to be configured explicitly; they are by default enabled on all autonomous systems.
The default behaviors are as follow (see [this manual](../manual.md#transit-as-network) if you want to customize
the behaviors):

- IBGP is configured between all routers within an autonomous system,
- OSPF is enabled on all networks that have two or more routers in them.
- Passive OSPF is enabled on all other connected networks.


## Step 4: Create and set up an autonomous system

This part is the same as the `00-simple-peering` example, so we will not 
repeat the explanation.

```python
as151 = base.createAutonomousSystem(151)

# Create a host called web
as151_web = as151.createHost('web')

# Create the web151 virtual node and bind it to the web host in ASN 151
web.install('web151')
emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))

# Create the router
as151_router = as151.createRouter('router0')
as151_net = as151.createNetwork('net0')

# Add net0 to FIB (marking it as "direct" network, so it can be laoded into BIRD's FIB)
routing.addDirect(151, 'net0')

# Join the network
as151_web.joinNetwork(as151_net)
as151_router.joinNetwork(as151_net)

# Make as151 the BGP router, so it needs to join the internet exchange network
as151_router.joinNetwork('ix100')
```

## Step 5: Create and set up another autonomous system

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

## Step 6: Set up BGP peering

```python
# Peer AS150 with AS151 inside Internet Exchange 100
ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)

# Peer AS150 with AS152 inside Internet Exchange 101
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
```

The `Ebgp::addPrivatePeering` call takes four parameters; internet exchange ID, first ASN, the second ASN, and the relationship. The relationship parameter defaults to `Peer`. The call will configure peering between the two given ASNs in the given exchange. 

The peering relationship can be one of the followings:

- `PeerRelationship.Provider`: The first ASN is considered as the upstream provider of the second ASN. The first ASN will export all routes to the second ASN, and the second ASN will only export its customers' and its own prefixes to the first ASN.
- `PeerRelationship.Peer`: The two ASNs are considered as peers. Both sides will only export their customers and their own prefixes.
- `PeerRelationship.Unfiltered`: Make both sides export all routes to each other.

We may also use the `Ebgp::addRsPeer` call to configure peering; it takes two parameters; the first is an internet exchange ID, and the second is ASN. It will configure peering between the given ASN and the given exchange's route server (i.e., setup Multi-Lateral Peering Agreement (MLPA)). Note that the session with RS will always be `Peer` relationship.

The eBGP layer sets up peering by looking for the router node of the given autonomous system from within the internet exchange network. So as long as there is a router of that AS in the exchange network (i.e., joined the IX with `as15X_router.joinNetworkByName('ix100')`), the eBGP layer should be able to setup peeing just fine.


## Step 7: render the emulation

```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

emu.render()
```

The rendering process is where all the actual "things" happen. Software is added to the nodes, routing tables and protocols are configured, and BGP peers are configured.


## Step 8: compile the emulation

After rendering the layers, all the nodes and networks are created. They are still stored as internal data structures; to create something we can run, we need to "compile" the emulation to other formats. 
We use docker on a single host to run the emulation, so we use the `Docker` compiler:

```python
emu.compile(Docker(), './output')
```

