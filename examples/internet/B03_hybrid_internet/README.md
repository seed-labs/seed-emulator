# Hybrid Internet

This is a example that can connect to the realworld. It creates 6 Internet exchanges,
5 transit ASes, and 12 stub ASes same as mini-internet example. 
One of the ASes (`AS-99999`) is a hybrid autonomous system, 
which announces these prefixes; [`0.0.0.0/1`, `128.0.0.0/1`]
to the emulator. Packets to these prefixes will be routed out to the 
real Internet.

The emulator generated from this example is saved to a component file, 
and be used by several other examples as the basis.


## Real-World Autonomous System 11872

The example creates a real-world AS (`AS-11872`), which is
Syracuse University's autonomous system. It will collect
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
# Create hybrid AS.
# AS99999 is the emulator's autonomous system that routes the traffics to the real-world internet
as99999 = base.createAutonomousSystem(99999)
as99999.createRealWorldRouter('rw-real-world', prefixes=['0.0.0.0/1', '128.0.0.0/1']).joinNetwork('ix100', '10.100.0.99')
```

## Allow Real-World Access

The `AS-152` is configured to allow real-world access. This means
a machine from outside of the emulator can VPN into `AS-152`'s network,
and essentially becomes a node of the emulator. This allows outside
real-world machines to participate in the emulation.

```
as152 = base.getAutonomousSystem(152)
as152.getNetwork('net0').enableRemoteAccess(ovpn)
```

