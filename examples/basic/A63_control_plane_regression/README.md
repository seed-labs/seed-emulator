# A63 Control-Plane Regression

This example is the compact runtime regression entry for the control-plane
foundation work. It intentionally keeps several independent slices in one
emulation so a reviewer can run one example after changes to Routing, BGP
intent metadata, FRR rendering, ExaBGP service binding, or MPLS readiness.

Covered slices:

- IX100 uses the legacy BIRD route server path with AS150/AS151 clients.
- AS2 mixes a BIRD router and an FRR router from the same OSPF/iBGP/eBGP intent.
- AS3 uses an FRR route reflector and an FRR RR client.
- AS180 installs ExaBGP through `ExaBgpService + Binding` and peers with an FRR
  router in AS4. ExaBGP is not a router backend.
- AS20 enables MPLS/LDP readiness with AS-level `setCoreForwarding("mpls")` on
  a small FRR transit chain. The default runtime test checks generated MPLS
  interface and FRR LDP config. Full MPLS dataplane validation remains
  host-gated because GitHub hosted runners may not provide MPLS kernel modules.

Run it locally:

```bash
python -m seedemu.testing.cli clean examples/basic/A63_control_plane_regression/example.yaml
python -m seedemu.testing.cli compile examples/basic/A63_control_plane_regression/example.yaml
COMPOSE_PROJECT_NAME=seedemu-a63-control-plane python -m seedemu.testing.cli all examples/basic/A63_control_plane_regression/example.yaml
```
