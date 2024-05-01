# IP Anycast 

The purpose of this example is to demonstrate the IP anycast feature.
We will use the emulator from example-B00 as the base. 
The IP anycast technology allows multiple computers on the Internet to have 
the same IP address. When another machine sends a packet to this IP address,
one of the computers will get the packet. Exactly which one will 
get the packet depends on BGP routing. IP anycast is naturally supported by BGP.

One of the well-known applications of IP anycast is the DNS root servers. 
Some of the DNS root servers, such as the F server, 
have multiple machines geographically located in many different places around the world, 
but they have the same IP address.
For example, all the F servers have the same IP address `192.5.5.241`. 
When a DNS client sends a request to this 
IP address, one of the F servers will get the request. 


## Create Two Hosts with Same IP Address

We will first create an autonomous system (`AS-180`). We create two networks
inside this AS, but we give them the same network prefix. We also create 
a host on each network, and assign the same IP address to them. 

```
as180 = base.createAutonomousSystem(180)
as180.createNetwork('net0', '10.180.0.0/24')
as180.createNetwork('net1', '10.180.0.0/24')

as180.createHost('host-0').joinNetwork('net0', address = '10.180.0.100')
as180.createHost('host-1').joinNetwork('net1', address = '10.180.0.100')
```
It should be noted that this AS has two disjoint parts: one has `net0`, and the 
other has `net1`. These two networks are not connected by any router.
We then connect one part of the AS to `ix100`, and connect the other part
of the AS to `ix105`, and peer the AS with other ASes at these two locations.

```
as180.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
ebgp.addPrivatePeerings(100, [3, 4],  [180], PeerRelationship.Provider)

as180.createRouter('router1').joinNetwork('net1').joinNetwork('ix105')
ebgp.addPrivatePeerings(105, [2, 3],  [180], PeerRelationship.Provider)
```

When compiling the emulation to generate the docker files, we need 
to set the `selfManagedNetwork` option to True. Without this option,
the network will be entirely managed by Docker, which will not 
allow us to have two networks with the same IP prefix. Using
this option will solve this problem.

```
emu.compile(Docker(selfManagedNetwork=True), './output')
```


Now, we have deployed two hosts using the IP anycast technology. 
When other machines send a packet to `10.180.0.100`, one of these two
hosts will get the packet. 


## ICMP Testing

We can ping `10.180.0.100` from one of the hosts in the emulator,
we set the filter to `icmp`. We should be able to see the 
traffic going to one of the `10.180.0.100` hosts. If we disable 
this location's BGP session, we will see that the traffic 
immediately switches to the other `10.180.0.100` host. 
We should also be able to find two hosts inside the emulator,
such that they talk to a different `10.180.0.100` host. 


## UDP Testing

We can run a UDP server on each of the `10.180.0.100` host using `nc -luk 9090`. 
Then from another machine, we send a UDP message to `10.180.0.100`. 
One of the hosts will receive the message, depending on where the client 
is located. If we disable the BGP session at one of the locations,
we can see that the UDP message will go to the other server. 

```
# echo hello | nc -u 10.180.0.100 9090
```
