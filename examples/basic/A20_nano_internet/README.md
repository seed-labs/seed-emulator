# Nano Internet 

In this example, we build a very small Internet to demonstrate 
some of the features of the emulator. We have recorded a 
[YouTube video](https://www.youtube.com/watch?v=WqtFS2AoKH4&list=PLwCoMLt7WGjan54CuqeYGnJuMqA-RzQwD) 
to explain this example, so we will not explain it 
here. The following
features are demonstrated in this example:

- Creating internet exchange 
- Creating transit and stub AS
- Using utility function to create AS
- Node customization
- BGP peering
- Install web service on nodes
- Binding virtual nodes to physical nodes
- Compilation


## Note for ARM machine 

It should be noted that in the example, we used 
a custom image called `handsonsecurity/seed-ubuntu:small` (for AMD)
and `handsonsecurity/seed-ubuntu:small-arm` (for ARM).
If you use Apple silicon machines, you need to run this example
using the `arm` argument (`./nano_internet.py arm`);
otherwise the AMD image will be used, which can cause problems. 

