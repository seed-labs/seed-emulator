# Manual: Routing


<a name="ibgp-ospf-protocol"></a>
## Configure the OSPF and IBGP Routing Protocols

We can use OSPF and IBGP for internal routing. IBGP and OSPF layer do not need
to be configured explicitly; they are by default enabled on all autonomous
systems.

The default behaviors are as follow:

- IBGP is configured between all routers within an autonomous system,
- OSPF is enabled on all networks that have two or more routers in them.
- Passive OSPF is enabled on all other connected networks.

We may "mask" an autonomous system from OSPF or IBGP, if we don't want the
behavior. For IBGP, use `Ibgp::mask` method. It takes an ASN as input and will
disable IBGP on that autonomous system:

```python
ibgp.mask(151)
```

The above masks AS151 from IBGP, meaning the IBGP layer won't touch any routers
from AS151. However, in this particular example, AS151 has only one router, so
it wasn't going to be configured by the IBGP layer anyway.

For the OSPF layer, we have a bit more customizability. To mask an entire
autonomous system, use `Ospf::maskAsn`:

```python
ospf.maskAsn(151)
```

We can also mask only a single network with `Ospf::maskNetwork` and
`Ospf::maskByName`. `maskNetwork` call takes one parameter - the reference to
the network object, and `maskByName` call takes two parameters, the first is
the scope (i.e., ASN) of the network, and the second is the name of the
network. Masking a network takes it out of the OSPF layer's consideration. In
other words, no OSPF will be enabled on any interface connected to the network,
passive or active.

```python
# mask with name
ospf.maskByName('151', 'net0')

# mask with reference
ospf.maskNetwork(as152_net)
```

