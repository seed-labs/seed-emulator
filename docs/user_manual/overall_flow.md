# Create an Internet Emulator: the Overall Flow


We show how to build a simple Internet Emulator, consisting 
of three stub autonomous systems and one transit autonomous system. 
We only cover the basic features. 
The complete code and more detailed explanation 
can be found in the example [A01-transit-as](../../examples/A01-transit-as).

- [Create stub autonomous systems](#create-stub-as)
- [Create transit autonomous system](#create-transit-as)
- [Conduct BGP Peering](#bgp-peering)
- [Adding layers and conduct rendering](#rendering)
- [Compilation](#compilation)
- [Run emulation](#run-emulation)


<a id="create-stub-as"></a>
## Create the base layer and Internet Exchanges 

We first need to create a base layer. The entire emulator 
will be built on top of this base. 
After this layer is created, we create two Internet exchanges,
each of which consists of an internal network. Later on,
we will attach BGP routers to these networks. 


```python
base  = Base()

base.createInternetExchange(100)
base.createInternetExchange(101)
```

<a id="create-stub-as"></a>
## Create stub autonomous systems

We create three autonomous systems. In the following code example,
we create an autonomous system AS-151. Inside this AS, we create 
one internal network, with one router and one host. The router
is attached to the internal network (`net0`) and to the 
Internet Exchange IX100's network (`ix100`). Routers connected to
an Internet exchange will be automatically configured as BGP routers.
The code for the other 2 autonomous systems is similar. 


```python
as151 = base.createAutonomousSystem(151)

# Create an internal network 
as151.createNetwork('net0')

# Create a host and attach it to the network
as151.createHost('host0').joinNetwork('net0')

# Create a router and attach it to two networks
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
```

<a id="create-transit-as"></a>
## Create a transit autonomous system

We create a transit autonomous system, which provides the 
transit service to the stub autonomous systems created
previously, pulling traffic from one Internet exchange to another.
A transit autonomous system typically has multiple 
routers, connecting to multiple Internet exchanges. 

```python
as2 = base.createAutonomousSystem(2)

# Create 3 internal networks
as2.createNetwork('net0')
as2.createNetwork('net1')
as2.createNetwork('net2')

# Create four routers and attach them to networks. 
# ix100 <--> r1 <--> r2 <--> r3 <--> r4 <--> ix101
as2.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
as2.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
as2.createRouter('r3').joinNetwork('net1').joinNetwork('net2')
as2.createRouter('r4').joinNetwork('net2').joinNetwork('ix101')
```

In the example above, routers `r1` and `r4` are BGP routers 
because they are connected to Internet exchanges. Routers `r2`
and `r3` are internal routers. Corresponding routing protocol
will be automatically set up on them. 



<a id="bgp-peering"></a>
## Create an Ebgp layer and Conduct BGP Peering

We need to peer the autonomous systems, so they can be connected. 
We first create the `Ebgp` layer, and then create the 
peering relationships among the autonomous systems. More details on the 
BGP peering can be found in the [bgp_peering.md](./bgp_peering.md)
document. 


```python
ebgp    = Ebgp()

# Peer AS-2 with ASes 151, 152, and 153 (AS-2 is the Internet service provider)
ebgp.addPrivatePeering(100, 2, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 152, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 153, abRelationship = PeerRelationship.Provider)

# Peer AS-152 and AS-153 (as equal peers for mutual benefit)
ebgp.addPrivatePeering(101, 152, 153, abRelationship = PeerRelationship.Peer)
```


<a id="rendering"></a>
## Adding Layers and Conduct Rendering

After configuring all the layers, we need to add the layers to the renderer to
render the emulation.  The rendering process is where all the actual "things"
happen. Software is added to the nodes, routing tables and protocols are
configured, and BGP peers are configured.  Here is an example:


```python
emu.addLayer(base)
emu.addLayer(Routing())
emu.addLayer(ebgp)
emu.addLayer(Ibgp())
emu.addLayer(Ospf())

emu.render()
```

All the above layers are necessary for setting up the routing 
in the emulator. More details on routing can be found in
the [routing.md](./routing.md) manual.


<a id="compilation"></a>
## Compilation

After all the layers are rendered, the emulation data 
are still stored using internal data structures. In the final step,
we need to export them to create the emulation files. This step is 
called *compilation*. In this example, we use docker on a single machine
to run the emulation, so we will use the `Docker` compiler. 

We first create a `Docker` compiler object, and then 
use it to compile the emulation. The output, docker files,
are put inside the `./output` folder (the `override` flag
indicates whether we can overwrite the `output` folder if
it already exists). 


```python
docker = Docker(internetMapEnabled=True, platform=Platform.AMD64)
emu.compile(docker, './output', override = True)
```

The `internetMapEnabled` flag indicates whether the 
visualization app (the Internet Map app, running inside an independent container) 
should be included in the generated 
files (the default value is `True`, i.e., the map will
be automatically included if this flag is not specified). 
The `platform` option indicates which platform
we are generating the emulation for, AMD64 or ARM64 (for Apple Silicon
Machines, i.e., M1/M2 chips). 
More features on docker and compiler can be 
found from the [docker](./docker.md) and the [compiler](./compiler.md)
manuals. 


<a id="run-emulation"></a>
## Run the Emulation

To run the emulation, simply go to the `output/` folder,
run `docker-compose build && docker-compose up`. 
The emulator will start running. Give it a
minute or two (or longer if your emulator is large) 
to let the routers do their jobs.

This example already include the visualization container (called Internet
Map). Point your browser to `http://127.0.0.1:8080/map.html`, and you will
see the visualization. More instructions on how to use the visualization app
is given in [this manual](./internet_map.md). 
