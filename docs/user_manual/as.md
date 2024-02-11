# User Manual: Autonomous System

- [Create Simple Stub Autonomous Systems (example)](../../examples/A00-simple-as) 
- [Create Transit Autonomous System (example)](../../examples/A01-transit-as) 
- [The Default Network Prefix](#default-network-prefix)
- [Overwrite the Default Network Prefix](#overwrite-default-prefix)


<a id="default-network-prefix"></a>
## The Default Network Prefix

When we create a network inside an autonomous system or an Internet exchange, 
the default network prefix is assigned using the following scheme:

```
10.{asn}.{id}.0/24
```

The `asn` is the autonomous system number, and `{id}` is the nth network created. 
For example, for `AS150`, the first network is `10.150.0.0/24`, and the second one 
is `10.150.1.0/24`. For Internet exchanges, the `{id}` part is always `0`.
For example, the default prefix of `IX100` is `10.100.0.0/24`.


<a id="overwrite-default-prefix"></a>
## Change the Default Network Prefix 

If the autonomous system number is greater than 255, 
the default network prefix assignment will not work. 
We can explicitly set the network prefix when creating a network. 


```python
# For the network in Internet exchanges
base.createInternetExchange(asn = 33108, prefix = '206.81.80.0/23')

# For the network in autonomous system
as350 = base.createAutonomousSystem(350)
as350.createNetwork(name='net0', prefix = '128.230.0.0/16')
as350.createRouter('router0').joinNetwork('net0').joinNetwork('ix100', '10.100.0.35')
```

Moreover, in the example above, when a BGP router from AS350 
connects to an Internet Exchange network (e.g., `10.100.0.0/24`), 
the default IP address assigned to the BGP router is `10.100.0.350`, 
which is not a valid IP address (350 > 255). We can
assign a valid IP address to the router explicitly. 


