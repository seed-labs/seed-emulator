# Mini Internet

This is a comprehensive example. It creates 6 Internet exchanges,
5 transit ASes, and 12 stub ASes. One of the ASes (`AS-99999`) is a real-world
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

