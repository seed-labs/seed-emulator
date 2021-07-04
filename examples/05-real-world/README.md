# Real-world interaction

The topology of this example is the same as that in `01-transit-as`. 
In AS151 and AS152, we will host VPN servers that are accessible from outside of the emulator, so real-world hosts can connect to the emulation. In addition, we also add a real-world autonomous system, AS11872 (Syracuse University). This autonomous system will collect the real prefixes from the real Internet, announce them inside the emulator. Packets reaching this AS will exit the emulator and be routed to the real destination. 


## Step 1: Import and create required components

This part is the same as that in `01-transit-as`. 


## Step 2: create the internet exchanges

This part is the same as that in `01-transit-as`. 


## Step 3: Create a transit autonomous system

This part is the same as that in `01-transit-as`. 


## Step 4: Create and set up autonomous systems

Most part of this is the same as that in `01-transit-as`. 
The only difference is the following:


```python
real.enableRealWorldAccess(as151, 'net0')
```

The `Reality::enableRealWorldAccess` call enables real-world access to a network by hosting an OpenVPN server. The server will be reachable from the real world; we can check the server port by doing `docker ps` once the emulation is up. 

`enableRealWorldAccess` accepts three parameters; the first is the reference to the AS object, the second one is the name of network, and the third one, `naddr`, is an optional parameter for specifying how many host IP addresses to allocate to the server (default to 8). It uses the network's IP assigner to get IP addresses for host-role nodes. For details, check the `AddressAssignmentConstraint` in the remarks section.



## Step 5: create the real-world customer autonomous system

First, create the autonomous system object:

```python
as11872 = base.createAutonomousSystem(11872)
```

Then, create a real world router:

```python
as11872_router = real.createRealWorldRouter(as11872)
```

The `createRealWorldRouter` call takes three parameters; the first is the reference to the autonomous system object to create the router, the second, `nodename`, is the name of router node (default to `rw`), and the third, `prefixes` is a list of prefixes (default to `None`). Here, we let it default to `None`, so the layer will get the prefixes list for us.

If `prefixes` is set to `None` (the `NoneType`, not empty list), the layer will automatically fetch the list of prefixes announced by the autonomous system in the real world. Otherwise, it will use the list of prefixes we specified.

The `createRealWorldRouter` returns a `RealWorldRouter` instance. `RealWorldRouter` class was derived from the regular router node class; it adds an `addRealWorldRoute` method to router class. `addRealWorldRoute` accepts one parameter, `prefix`, and will route the given prefix to real-world.

The last step is to connect the autonomous system to an internet exchange. Here, we picked IX101. We need to override the auto address assignment, as 11872 is out of the 2~254 range:

```python
as11872_router.joinNetwork('ix101', '10.101.0.118')
```

## Step 6: Set up BGP peering

```python
ebgp.addPrivatePeering(100, 150, 151, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 152, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 150, 11872, abRelationship = PeerRelationship.Provider)
```

## Step 7: Host the services

We have created two web server nodes, but we have not hosted the actual web service on them. Let's proceed to host the services. First, we create two virtual nodes of the web type (i.e., it has web services) 

```python
web.install('web1')
web.install('web2')
```

We then bind the virtual nodes to the physical nodes created earlier. 

```python
emu.addBinding(Binding('web1', filter = Filter(asn = 151, nodeName = 'web')))
emu.addBinding(Binding('web2', filter = Filter(asn = 152, nodeName = 'web')))
```

## Step 8: Render and compile the emulation
