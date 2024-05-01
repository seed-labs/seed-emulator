# Hybrid Internet

This is a example that can connect to the realworld. It creates 6 Internet exchanges,
5 transit ASes, and 12 stub ASes same as mini-internet example. 
One of the ASes (`AS-99999`) is a hybrid autonomous system, 
which announces these prefixes; [`0.0.0.0/1`, `128.0.0.0/1`]
to the emulator. Packets to these prefixes will be routed out to the 
real Internet.

The emulator generated from this example is saved to a component file, 
and be used by several other examples as the basis.

## Hybrid Autonomous System 

The example creates a real-world AS (`AS-99999`), which is 
a hybrid autonomous system for the emulator. The prefixes of the AS
are configured as [`0.0.0.0/1`, `128.0.0.0/1`] and announce 
them inside the emulator. Packets (from inside the emulator) 
going to these networks will be routed to this AS, and 
then be forwarded to the real world. Returning packets
will come back from the outside, enter the emulator at 
this AS, and be routed to its final destination inside 
the emulator.

```
# Create hybrid AS.
# AS99999 is the emulator's autonomous system that routes the traffics to the real-world internet
as99999 = base.createAutonomousSystem(99999)
as99999.createRealWorldRouter('rw-real-world', prefixes=['0.0.0.0/1', '128.0.0.0/1']).joinNetwork('ix100', '10.100.0.99')
```

