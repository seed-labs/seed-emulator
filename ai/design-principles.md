# SEED Control Plane Design Principles

This file records the branch-level design rules we want future SEED Emulator control-plane work to follow.

## Boundaries

- Keep topology construction in `Base`, `AutonomousSystem`, `InternetExchange`, `Network`, `Node`, and `Interface`.
- Keep routing daemon selection on `Router`; use `createRouter(..., routingBackend="bird|frr")`.
- Keep protocol layers as intent recorders. `Ebgp`, `Ibgp`, and `Ospf` should describe peers, relationships, address families, export policy, and active/passive interfaces.
- Keep daemon syntax in `Routing`. BIRD and FRR config templates should be rendered from the same intent model.
- Keep ExaBGP as a `Service + Binding` control-plane speaker, not as a full transit router backend.
- Keep Looking Glass as a route-state observer service. Do not mix it with ExaBGP event-stream semantics.

## Compatibility

- Preserve IPv4 defaults. New IPv6 work must be opt-in unless a later design explicitly changes the default.
- Preserve old public methods where possible. Add IPv6-specific accessors instead of changing IPv4 return values.
- Keep examples additive when testing a new branch-level capability. Do not weaken existing A12-A14 regression examples.

## Addressing

- Treat IPv6 as topology state owned by `Base` and core objects, not as example-local configuration.
- Keep IPv6 root prefixes explicit and inspectable. The default root is `2000::/12`; the reserved infrastructure prefix is `2000:ffff::/48`.
- Keep automatic IPv6 allocation deterministic: `/48` per AS, `/64` per local network, `/64` per IX LAN.
- Track explicit IPv6 prefixes that fall under the configured root so later automatic allocation cannot collide with them.
- Keep per-network opt-out (`ipv6Prefix=None`) and per-interface opt-out (`ipv6Address=None`) available for mixed migration scenarios.

## Validation

- Generated config is not enough. Runtime evidence must include daemon processes, neighbor state, learned routes, and observable route-state/event surfaces.
- Validate mixed backends. A control-plane feature should prove BIRD and FRR can coexist in one topology.
- Validate service boundaries. ExaBGP must show speaker config and live announce/withdraw; Looking Glass must show router route-state.
