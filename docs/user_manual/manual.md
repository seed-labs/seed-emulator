# Manual


<a name="create-network-with-prefix"></a>
## Creating networks with a custom prefix

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

<a name="assign-ip-to-interface"></a>
## Assigning IP addresses to interfaces

The IP addresses in a network are assigned with `AddressAssignmentConstraint`. The default constraints are as follow:

- Host nodes: from 71 to 99
- Router nodes: from 254 to 200
- Router nodes in internet exchange: ASN

For example, in AS150, if a host node joined a local network, it's IP address will be `10.150.0.71`. The next host joined the network will become `10.150.0.72`. If a router joined a local network, it's IP address will be `10.150.0.254`, and if the router joined an internet exchange network (say IX100), it will be `10.100.0.150`.

Sometimes it will be useful to override the automated assignment for once. `joinNetwork` accept an `address` argument for overriding the assignment:

```python
as11872_router.joinNetwork('ix100', address = '10.100.0.118')
```

We may alternatively implement our own `AddressAssignmentConstraint` class instead. Both `createInternetExchange` and `createNetwork` accept the `aac` argument, which will alter the auto address assignment behavior. Foe details, please refer to the API documentation.


<a name="transit-as-network"></a>
## Transit Autonomous System's internal network

We can use OSPF and IBGP for internal routing. IBGP and OSPF layer do not need to be configured explicitly; they are by default enabled on all autonomous systems.

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

<a name="rendering"></a>
## Rendering

After configuring all the layers, we need to add the layers to the renderer to render the emulation.
The rendering process is where all the actual "things" happen. Software is added to the nodes, 
routing tables and protocols are configured, and BGP peers are configured.
Here is an example: 


```python
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.render()
```

<a name="compilation"></a>
## Compilation

After all the layers are rendered, all the nodes and networks are created. 
They are still stored using internal data structures. We need to 
compile them into the final emulation files. 

In this example, we will use docker on a single host to run the emulation, 
so we use the `Docker` compiler. The following example generate all
the docker files inside the `./output` folder. 
The docker compiler comes with a docker-compose configuration. 
To run the emulation, simply run `docker-compose build && docker-compose up` 
in the `output` directory.

```python
emu.compile(Docker(), './output')
```

There are several other compilation options. See [this document](./manual_compiler.md)
for details.



