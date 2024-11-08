# Hybrid Internet

Most part of this example is similar to the mini-internet example,
but several things are added to this example to enable
the emulator to communicate with the real world. With these
additions, nodes inside the emulator can communicate with
the machines in the real Internet, and the machines in the
real Internet can VPN into the emulator to become a node
in the emulation. 


## Real-World Autonomous System 11872

The example creates a real-world AS (`AS-11872`), which is
Syracuse University's autonomous system number. It will collect
the network prefixes announced by this autonomous system in the real
world, and announce them inside the emulator. Packets (from inside
the emulator) going to these networks will be routed to this AS, and
then be forwarded to the real world. Returning packets
will come back from the outside, enter the emulator at
this AS, and be routed to its final destination inside
the emulator.

```
as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter('rw').joinNetwork('ix102', '10.102.0.118')
```

## Real-World Autonomous System 99999

The example creates a real-world AS (`AS-99999`), which is 
a hybrid autonomous system for the emulator. The prefixes of the AS
are configured as [`0.0.0.0/1`, `128.0.0.0/1`] and announce 
them inside the emulator. These two IP prefixes cover the 
entire IPv4 address space. Therefore, if the destination of a
packet does not match any network inside the emulator,
the packet will be routed to this AS, and
then be forwarded to the real world (via NAT). Returning packets
will come back from the outside, enter the emulator at 
this AS, and be routed to its final destination inside 
the emulator.

```
as99999 = base.createAutonomousSystem(99999)
as99999.createRealWorldRouter('rw-real-world', 
    prefixes=['0.0.0.0/1', '128.0.0.0/1']).joinNetwork('ix100', '10.100.0.99')
```


## Allow Real-World Access

The `AS-152` is configured to allow real-world access. This means
a machine from outside of the emulator can VPN into `AS-152`'s network,
and essentially becomes a node of the emulator. This allows outside
real-world machines to participate in the emulation.
Please refer to [this document](../../../misc/openvpn-remote-access/README.md)
for instructions on how to VPN into this host. 

```
as152 = base.getAutonomousSystem(152)
as152.getNetwork('net0').enableRemoteAccess(ovpn)
```

