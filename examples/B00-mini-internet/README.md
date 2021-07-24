# Mini Internet

This is a comprehensive example. It creates 6 Internet exchanges,
5 transit ASes, and 12 stub ASes. One of the ASes (`AS-11872`) is a real-world
autonomous system, which announces the real-work network prefixes 
to the emulator. Packets to these prefixes will be routed out to the 
real Internet. Another AS (`AS-152`) allows machines from the outside
to join the emulation (via VPN), so they can interact with the machines
inside the emulator.

The emulator generated from this example is saved to a component file, 
and be used by several other examples as the basis.


## Using Utility Functions

We have created a few utility functions to help make it easy
to create autonomous systems. 
The following example creates a transit AS (`AS-2`), which
has a presence at 3 Internet exchanges (`ix-100`, `ix-101`,
and `ix-102`). It also creates two internal networks to 
connect the 3 BGP routers of this AS.

```
Makers.makeTransitAs(base, 2, [100, 101, 102],
       [(100, 101), (101, 102)]
)
```

The following example creates a stub AS (`AS-153`), 
which has a presence at `ix-101`. Three hosts will be 
created for this AS, one running a web service, and the other 
two not running any service. 

```
Makers.makeStubAs(emu, base, 153, 101, [web, None, None])
```

## Real-World Autonomous System 

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

## Allow Real-World Access

The `AS-152` is configured to allow real-world access. This means 
a machine from outside of the emulator can VPN into `AS-152`'s network,
and essentially becomes a node of the emulator. This allows outside
real-world machines to participate in the emulation.

```
as152 = base.getAutonomousSystem(152)
as152.getNetwork('net0').enableRemoteAccess(ovpn)
```

