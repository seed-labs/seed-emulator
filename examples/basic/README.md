# Basic Examples

This folder contains small, focused SEED Emulator examples. The `A00`-series
examples introduce core emulator concepts, progressively adding routing,
real-world connectivity, components, compiler behavior, customization, mixed
backends, ExaBGP, generated topologies, and control-plane regression coverage.

Many examples include an `example.yaml` manifest and `test_runtime.py` so they
can be run through `seedemu.testing`.

## Examples

| Example | Purpose |
| --- | --- |
| `A00_simple_as` | Builds three simple autonomous systems on one IX, adds web hosts, and verifies basic cross-AS reachability. This is the minimal reference example for the standardized test lifecycle. |
| `A01_transit_as` | Demonstrates a transit AS connecting two stub ASes through eBGP and internal routing. It also shows how to save the emulation as a reusable component. |
| `A02a_transit_as_mpls` | Demonstrates MPLS/LDP in a transit AS using the emulator's MPLS layer. This example depends on host MPLS kernel support for full runtime validation. |
| `A02b_manual_mpls` | Demonstrates manual MPLS label-table setup instead of relying on LDP. It is useful for teaching MPLS label push, swap, and pop behavior explicitly. |
| `A03a_out_to_real_world` | Demonstrates outbound real-world connectivity from inside the emulator, using a real-world AS/prefix target. |
| `A03b_from_real_world` | Demonstrates access from the real world into the emulator using OpenVPN remote access. |
| `A04_visualization` | Demonstrates visualization metadata, including display information used by maps or graphing tools. |
| `A05_components` | Demonstrates loading a prebuilt component, modifying it, and adding new ASes, hosts, and IXes around it. |
| `A06_merge_emulation` | Demonstrates merging two separately built emulations into one combined emulator. |
| `A07_compilers` | Demonstrates compiler and registry usage, including different compiler outputs. |
| `A08_buildtime_docker` | Demonstrates using a build-time Docker container during emulator build, including generated artifacts from a helper image. |
| `A09_node_customization` | Demonstrates node customization, including adding programs and custom behavior to nodes. |
| `A10_add_containers` | Demonstrates attaching existing containers to networks inside an emulation. |
| `A11_add_containers_new` | Demonstrates newer patterns for adding existing containers and displaying them in the Internet map. |
| `A12_bgp_mixed_backend` | Demonstrates mixed BIRD and FRR routing backends in the same IPv4 emulator topology. |
| `A13_exabgp` | Demonstrates adding an ExaBGP speaker to the emulator and manually announcing or withdrawing routes through a helper script. |
| `A15_toplogy_generator` | Demonstrates the NetworkX-based autonomous-system topology generator, including generated internal topology, eBGP attachment, iBGP mode selection, and topology artifacts. |
| `A20_nano_internet` | Builds a very small Internet to demonstrate basic Internet-scale composition with transit and stub ASes. |
| `A21_shadow_internet` | Demonstrates a shadow Internet topology for experimenting with a larger emulated Internet structure. |
| `A62_route_reflector` | Demonstrates route-reflector use in transit ASes and compares iBGP designs with and without route reflection. |
| `A63_control_plane_regression` | Provides a compact regression example covering BIRD route servers, mixed BIRD/FRR routers, route reflectors, ExaBGP binding, and MPLS/LDP readiness. |

## Running Tested Examples

For examples with `example.yaml`, use:

```sh
python -m seedemu.testing.cli all examples/basic/A00_simple_as/example.yaml
```

Replace the path with the example you want to run. Some examples, especially
MPLS and real-world connectivity examples, require host or network support that
may not be available in every CI environment.
