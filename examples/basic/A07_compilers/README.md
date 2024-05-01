# Demonstration of Compilers and Registry

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

Here is the [manual for the compilers](/docs/user_manual/compiler.md),
and the [manual for the registry](/docs/user_manual/misc.md#registry).

