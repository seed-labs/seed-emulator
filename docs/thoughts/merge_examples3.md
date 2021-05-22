

## Dealing with Common AS

If two emulators have common ASes, we need to resolve the conflict. 

```py
sim1 = Emulator()
sim1.load("sim1.json")
sim2 = Emulator()
sim2.load("sim2.josn")

common_ases = Utility.findCommonASes (sim1.getASes(), sim2.getASes())

# Let the developers resolve the conflict:
for a in common_ases:
   a1 = sim1.getAS(a)
   a2 = sim2.getAS(a)
   
   ## Choice 1: delete a from sim2 (or from sim1)
   sim2.deleteAS(a)


   ## Choice 2: merge these two ASes.
   ##     How two ASs are merged depends on the user provided function. 
   ##     We can provide a default merge function if none is provided.
   ##     We can also provide a list of pre-defined merge functions for 
   ##        developers to choose. For example, we can implement a
   ##        merge_delect() to cover the first choice. We can also implement
   ##        merge_useNetworksInFirst() to use the network in the first simualtor 
   ##        if there is a common network.  
   ##     We will provide the needed APIs.  
   a_merged = a1.mergeWith(a2, function=merge)
   sim1.replaceAS(a_merged)
   sim2.replaceAS(a_merged)


# At this point, all the conflicts of ASes are resolved
sim1.merge(sim2)
```
