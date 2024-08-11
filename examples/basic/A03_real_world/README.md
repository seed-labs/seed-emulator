# Real-world interaction

This example demonstrates two features related to the real world.
The first feature allows outside machines to connect to the 
emulator, so they can participate in the emulation. The way
to achieve this is through VPN. 

The second feature allows an emulation to include real-world 
autonomous systems. A real-world AS included in the emulation
will collect the real network prefixes from the real Internet,
and announce them inside the emulator. Packets reaching this AS
will exit the emulator and be routed to the real destination. 
Responses from the outside will come back to this real-world AS
and be routed to the final destination in the emulator.


## Import and Create Required Components

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

For details on how to connect to the OpenVPN server with bulletin CA/cert/key,
see [misc/openvpn-remote-access](/misc/openvpn-remote-access).

The way a remote access provider works is that the emulator 
will provide the remote access provider with the followings:

- The network to enable remote access on. 
- A for-service bridging network: this network is not a part of the emulation. Instead, it was used by special services like this to communicate with the emulator host.
- A bridging node: this node is not a part of emulation. It is a special node that will have access to both the for-service bridging network and the network to enable remote access on.

Then, what a remote access provider usually does is:

- Start a VPN server, listen for incoming connections on the for-service bridge network, so the emulator host can port-forward to the VPN server and allow hosts in the real world to connect.
- Add the VPN server interface and the network to enable remote access on to the same bridge so that clients can access the network.

In the OpenVPN access provider, besides the two steps above, also reserve some IP addresses (8 by default) for the client IP address pool.

However, note that a remote access provider does not necessarily create a VPN server - they can also be a VPN client that connect to another emulator or just a regular Linux bridge, to connect to, say, a network created by some other virtualization software.


## Enable Remote Access 

To allow remote access on a network, we just need to call the enabling API:

```python
as151.createNetwork('net0').enableRemoteAccess(ovpn)
```

The `Network::enableRemoteAccess` call enables remote access to a network. `enableRemoteAccess` takes only one parameter, the remote access provider.


## Create a Real-World Stub AS 

A real-world AS is an AS, so we will first create an AS:

```python
as11872 = base.createAutonomousSystem(11872)
```

We will create a special router in this AS: 

```python
as11872.createRealWorldRouter('rw')

```

The `createRealWorldRouter` call takes three parameters:

- `name`: name of the node.
- `hideHops`: enable hide hops feature. When `True`, the router will hide real world hops from traceroute. This works by setting TTL = 64 to all real world destinations on `POSTROUTING`. Default to `True`.
- `prefixes`: list of prefix. Can be a list of prefixes or `None`. When set to `None`, the router will automatically fetch the list of prefixes announced by the autonomous system in the real world. Default to `None`.


We will connect this autonomous system to an internet exchange. 
Here, we picked `IX101`. We need to override the auto address assignment,
as 11872 is out of the 2~254 range:

```python
as11872.createRealWorldRouter('rw').joinNetwork('ix101', '10.101.0.118')
```
