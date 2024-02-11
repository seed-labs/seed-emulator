# User Manual: Autonomous System

Examples for creating and configuring autonomous systems
are given in the following examples:

 - [Simple Stub Autonomous System](./examples/A00-simple-as) 
 - [Transit Autonomous System](./examples/A01-transit-as) 


## Overwrite the default setting 

When we create networks within an autonomous system, 
the default IP prefixes for these networks are `10.ASN.0.0/24`,
`10.ASN.1.0/24` etc, where `ASN` is the autonomous system
number. In the following example, the IP prefix for the `net0`
network in AS-150 is `10.150.0.0/24`. 

```
as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
```

This default setting requires the autonomous system number to be 
less than 255. If our ASN is larger than 255, we need to overwrite
this default setting by providing the IP prefix parameter when creating
a network. See the following example. 

```
as350 = base.createAutonomousSystem(350)
as350.createNetwork(name='net0', prefix='128.230.0.0/16')
as350.createRouter('router0').joinNetwork('net0').joinNetwork('ix100', '10.100.0.35')
```

Moreover, when a BGP router from AS-150 
connects to an Internet Exchange network (e.g., `10.100.0.0/24`), 
the default IP address assigned to the BGP router is `10.100.0.150`. If the 
ASN is larger than 255, we can specify our own IP address (see the example above). 


