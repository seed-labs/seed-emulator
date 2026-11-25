# User Manual: InternetMap

InternetMap is provided as a container bundle consisting of an emulator API,
topology UI, and geographic UI. The traffic observer is supplied separately by
the compiler-managed `SystemBundle`. InternetMap is no longer enabled by a
`Docker` constructor flag.

See the [visualization manual](visualization.md) for setup, port ordering, and
service URLs. See the
[B08 runnable example](../../examples/internet/B08_internet_map_bundle/README.md)
for a bundle connected to an emulated network. Implementation details are in
the [InternetMap bundle design](../designs/internet_map_bundle.md) and the
[SystemBundle design](../designs/system_bundle.md) for system-managed traffic
observer integration.
