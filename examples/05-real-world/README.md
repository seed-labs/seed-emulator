# Real-world interaction

The topology of this example is the same as that in `01-transit-as`. 
In AS151 and AS152, we will host VPN servers that are accessible from outside of the emulator, so real-world hosts can connect to the emulation. In addition, we also add a real-world autonomous system, AS11872 (Syracuse University). This autonomous system will collect the real prefixes from the real Internet, announce them inside the emulator. Packets reaching this AS will exit the emulator and be routed to the real destination. 

## Step 1: Import and create required components

Most of this part is the same as that in `01-transit-as`. The only difference is the following:

```python
ovpn = OpenVpnRemoteAccessProvider()
```

This creates an OpenVPN remote access provider. A remote access provider contains the logic to enable remote access to a network. It takes the following options:

- `startPort`: The starting port number to assign to the OpenVPN servers. Default to `65000`.
- `naddrs`: Number of addresses to reserve from the network. Default to `8`.
- `ovpnCa`: CA to use for the OpenVPN server. Default to `None` (uses bulletin CA).
- `ovpnCert`: Server certificate to use for the OpenVPN server. Default to `None` (uses bulletin certificate).
- `ovpnKey`: Server key to use for the OpenVPN server. Default to `None` (uses bulletin key).

For details on how to connect to the OpenVPN server with bulletin CA/cert/key, see [misc/openvpn-remote-access](../../misc/openvpn-remote-access).

The way a remote access provider work is that the emulator will provide the remote access provider with:

- The network to enable remote access on. 
- A for-service bridging network: this network is not a part of the emulation. Instead, it was used by special services like this to communicate with the emulator host.
- A bridging node: this node is not a part of emulation. It is a special node that will have access to both the for-service bridging network and the network to enable remote access on.

Then, what a remote access provider usually do is:

- Start a VPN server, listen for incoming connections on the for-service bridge network, so the emulator host can port-forward to the VPN server and allow hosts in the real world to connect.
- Add the VPN server interface and the network to enable remote access on to the same bridge so that clients can access the network.

In the OpenVPN access provider, besides the two steps above, also reserve some IP addresses (8 by default) for the client IP address pool.

However, note that a remote access provider does not necessarily create a VPN server - they can also be a VPN client that connects to another emulator or just a regular Linux bridge, to connect to, say, a network created by some other virtualization software.


## Step 2: create the internet exchanges

This part is the same as that in `01-transit-as`. 


## Step 3: Create a transit autonomous system

This part is the same as that in `01-transit-as`. 


## Step 4: Create and set up autonomous systems

Most part of this is the same as that in `01-transit-as`. The only difference is the following:


```python
as151_net0.enableRemoteAccess(ovpn)
```

The `Network::enableRemoteAccess` call enables remote access to a network. `enableRemoteAccess` takes only one parameter, the remote access proivder. See step 1 for details.


## Step 5: create the real-world customer autonomous system

First, create the autonomous system object:

```python
as11872 = base.createAutonomousSystem(11872)
```

Then, create a real world router:

```python
as11872_router = as11872.createRealWorldRouter('rw')
```

The `createRealWorldRouter` call takes three parameters:

- `name`: name of the node.
- `hideHops`: enable hide hops feature. When `True`, the router will hide real world hops from traceroute. This works by setting TTL = 64 to all real world destinations on `POSTROUTING`. Default to `True`.
- `prefixes`: list of prefix. Can be a list of prefixes or `None`. When set to `None`, the router will automatically fetch the list of prefixes announced by the autonomous system in the real world. Default to `None`.

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

After everything is done, we can render and compile the emulation. This part is the 
same as the other examples. 

```
emu.render()
emu.compile(Docker(), './output')
```