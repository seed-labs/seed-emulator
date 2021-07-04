# Demonstration of Compilers

The topology used in this example is the exact same as the 
`02-transit-as-mpls` MPLS transit example. 

This example demonstrates the uses of different compilers. 
The emulator provides a few other compilers for running the emulation in
different environments. It also includes a graphing system for visualizing
various topologies. 


```python
# Demonstrate the use of Registry
print(emu.getRegistry())

# Demonstrate the use of various compilers
mkdir('./output')
emu.compile(Docker(), './output/regular-docker')
emu.compile(Graphviz(), './output/graphs')
emu.compile(DistributedDocker(), './output/distributed-docker')
emu.compile(GcpDistributedDocker(), './output/gcp-distributed-docker')
```

Here is the [manual for the compilers](../manual_compiler.md),
and the [manual for the registry](../manual_misc.md#registry).

