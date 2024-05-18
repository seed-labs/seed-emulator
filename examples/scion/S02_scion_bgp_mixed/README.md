# SCION and BGP Coexistence

SCION can operate independently from but alongside BGP. This example demonstrates a more complex topology with both SCION and BGP routing.

## Step 1: Create layers

```python
from seedemu.compiler import Docker, Graphviz
from seedemu.core import Emulator
from seedemu.layers import (
    ScionBase, ScionRouting, ScionIsd, Scion, Ospf, Ibgp, Ebgp, PeerRelationship)
from seedemu.layers.Scion import LinkType as ScLinkType

emu = Emulator()
base = ScionBase()
routing = ScionRouting()
ospf = Ospf()
scion_isd = ScionIsd()
scion = Scion()
ibgp = Ibgp()
ebgp = Ebgp()
```

In addition to the SCION layers we instantiate the `Ibgp` and `Ebgp` layers for BGP as well as `Ospf` for AS-internal routing.

## Step 2: Create isolation domains and internet exchanges

```python
base.createIsolationDomain(1)
base.createIsolationDomain(2)

base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)
base.createInternetExchange(103)
base.createInternetExchange(104)
```

We have two ISDs and four internet exchanges this time.

## Step 3: Create autonomous systems

The topology we create contains the two core ASes 150 and 160. AS 150 is in ISD 1 and AS 160 is in ISD 2. ISD 1 has three additional non-core ASes. In ISD 2 we have one non-core AS.

### Step 3.1: Core AS of ISD 1

```python
as150 = base.createAutonomousSystem(150)
scion_isd.addIsdAs(1, 150, is_core=True)
as150.createNetwork('net0')
as150.createNetwork('net1')
as150.createNetwork('net2')
as150.createNetwork('net3')
as150.createControlService('cs1').joinNetwork('net0')
as150.createControlService('cs2').joinNetwork('net2')
as150_br0 = as150.createRouter('br0')
as150_br1 = as150.createRouter('br1')
as150_br2 = as150.createRouter('br2')
as150_br3 = as150.createRouter('br3')
as150_br0.joinNetwork('net0').joinNetwork('net1').joinNetwork('ix100')
as150_br1.joinNetwork('net1').joinNetwork('net2').joinNetwork('ix101')
as150_br2.joinNetwork('net2').joinNetwork('net3').joinNetwork('ix102')
as150_br3.joinNetwork('net3').joinNetwork('net0').joinNetwork('ix103')
```

AS 150 contains four internal network connected in a ring topology by the four border routers br0, br1, br2, and br3. There are two control services cs1 and cs2. We will use br0 to connect to the core of ISD 2 (i.e., AS 160) and the other border routers to connect to customer/child ASes 151, 152, and 153.

### Step 3.2 Non-Core ASes of ISD 1

```python
asn_ix = {
    151: 101,
    152: 102,
    153: 103,
}
for asn, ix in asn_ix.items():
    as_ = base.createAutonomousSystem(asn)
    scion_isd.addIsdAs(1, asn, is_core=False)
    scion_isd.setCertIssuer((1, asn), issuer=150)
    as_.createNetwork('net0')
    as_.createControlService('cs1').joinNetwork('net0')
    as_.createRouter('br0').joinNetwork('net0').joinNetwork(f'ix{ix}')
```

ISD 1 contains three non-core ASes that connect back to the core on ix101, ix102, and ix103, respectively.

### Step 3.3: ISD 2

AS 160 is the second ISD's core. It contains two border routers.

```python
as160 = base.createAutonomousSystem(160)
scion_isd.addIsdAs(2, 160, is_core=True)
as160.createNetwork('net0')
as160.createControlService('cs1').joinNetwork('net0')
as160.createRouter('br0').joinNetwork('net0').joinNetwork('ix100')
as160.createRouter('br1').joinNetwork('net0').joinNetwork('ix104')
```

Furthermore, there is the non-core AS 161 in ISD 2.

```python
as161 = base.createAutonomousSystem(161)
scion_isd.addIsdAs(2, 161, is_core=False)
scion_isd.setCertIssuer((2, 161), issuer=160)
as161.createNetwork('net0')
as161.createControlService('cs1').joinNetwork('net0')
as161.createRouter('br0').joinNetwork('net0').joinNetwork('ix104')
```

### Step 4: SCION links

```python
scion.addIxLink(100, (1, 150), (2, 160), ScLinkType.Core)
scion.addIxLink(101, (1, 150), (1, 151), ScLinkType.Transit)
scion.addIxLink(102, (1, 150), (1, 152), ScLinkType.Transit)
scion.addIxLink(103, (1, 150), (1, 153), ScLinkType.Transit)
scion.addIxLink(104, (2, 160), (2, 161), ScLinkType.Transit)
```

We connect the two core ASes with a core link. The non-core ASes are connected to the ISD cores by transit links.

### Step 5: BGP peering

```python
ebgp.addPrivatePeering(100, 150, 160, abRelationship=PeerRelationship.Peer)
ebgp.addPrivatePeering(101, 150, 151, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(102, 150, 152, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(103, 150, 153, abRelationship=PeerRelationship.Provider)
ebgp.addPrivatePeering(104, 160, 161, abRelationship=PeerRelationship.Provider)
```

For BGP, we use private peering between the pair of core ASes and between the cores and their non-core children.

### Step 6: ICMP and SCMP Ping

Once the topology has been compiled and is running, we can test BGP and SCION connectivity using the `ping` and `scion` tools, respectively.

For example, to ping a host in AS 161 we can use a command such as
```zsh
ping 10.161.0.71
```

To do the same in SCION, we can use
```zsh
scion ping 2-161,10.161.0.71
```

If both ping commands show responses then both the BGP and SCION routing are working.
