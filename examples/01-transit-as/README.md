# Transit AS

This is a more in-depth example; in this example, we will configure two internet exchanges, AS150 will be in both exchanges. AS151 and AS152 will be in IX100 and IX101, respectively. AS150 will serve as the transit AS for AS151 and AS152. There will be four hops in AS150. AS151 and AS152 will each announce one /24 prefix and host one web server in the network.

Most part of this example is the same as that in the `00-simple-peering` example,
so we will not repeat all the explanation. 

## Step 1: Create layers

In this setup, in addition to the layers created in the `00-simple-peering` example, 
we add two new layers: 

- The `Ibgp` layer: automatically sets up full-mesh iBGP peering between all routers within an autonomous system.
- The `Ospf` layer: automatically sets up OSPF routing on all routers within an autonomous system.


## Step 2: Create the internet exchanges

```python
base.createInternetExchange(100)
base.createInternetExchange(101)
```
Two internet exchanges are created. 
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

We need four routers. 

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


## Step 4: Create and set up stub autonomous systems

This part is the same as the `00-simple-peering` example, so we will not 
repeat the explanation.


## Step 5: Set up BGP peering

```python
# Peer AS150 with AS151 inside Internet Exchange 100
ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)

# Peer AS150 with AS152 inside Internet Exchange 101
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
```

See [this manual](../manual.md#bgp-private-peering) for the explanation of 
the use of `Ebgp::addPrivatePeering`. 


## Step 7: Render and compile the emulation

Same as the `00-simple-peering` example.



