

## Peering two simulators at IX100

If an IX exists in both simulators, merging is simple. 
If one of the simulators (or both) does not have this IX, 
we need to create one for it, set up everything needed,
before doing the merging. Here is the sample code:

```py
sim1 = Simulator()
sim1.load("sim1.json")
sim2 = Simulator()
sim2.load("sim2.josn")


ix100_1 = sim1.getIxByNumber(100)
if ix100_1 is None: # This IX doesn ot exist
   # It is the developer's job here.
   # - Create ix100, and add it to the simulator.
   # - Create an BGP router and connect it to the ix100's network.
   # - Attach the BGP router to an existing network inside the AS,
   #   or create a new network and attach the BGP router to it.
   # - If the network is new, attach it to some internal networks.

ix100_2 = sim2.getIxByNumber(100)
if ix100_2 is None:
   # Do the same as in sim1

# At this point, we ensure that ix100 exists in both simulators
sim1.merge(sim2)

# After the merging, the two simulators become one. 
# If we want to establish private peerings or other things, we can
# do that using the provided APIs. It is the same as doing 
# that in a single simulator.
```
