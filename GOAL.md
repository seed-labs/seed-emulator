# IPv6 Branch Goal

This file is the branch handoff contract for future agents working on
`feat/ipv6-control-plane`. The goal is fixed; the implementation path may
evolve as the repository reveals better integration points.

## Final Objective

Make IPv6 a repository-level optional capability of SEED Emulator.

The branch should let users build existing IPv4 emulations exactly as before,
while allowing new or migrated scenarios to opt into dual-stack IPv4/IPv6
behavior through explicit topology and service APIs. IPv6 must become part of
the simulator model, not a demo-only patch inside a few examples.

In practice, the final state should support these observations:

- Existing IPv4 examples, APIs, generated files, and runtime behavior remain
  stable by default.
- A scenario can explicitly enable IPv6 at the `Base`, network, interface, or
  service boundary and receive deterministic IPv6 topology state.
- Core topology objects own address state; layers own protocol intent; services
  consume model state; compilers emit runnable artifacts.
- BIRD, FRR, ExaBGP, and Looking Glass can prove dual-stack control-plane
  behavior at runtime.
- Repository services migrate incrementally through shared address-family and
  endpoint helpers instead of each service inventing its own IPv6 conventions.
- Documentation states what is supported, what is compatible but not migrated,
  and what remains IPv4-only or requires a separate design.

## Non-Negotiable Design Rules

- IPv4 remains the default. Do not emit IPv6 state unless the topology or
  service explicitly asked for it.
- Keep old IPv4 public methods stable. `getAddress()` and `getPrefix()` retain
  IPv4 semantics; IPv6 uses explicit accessors or family-aware helpers.
- Do not move daemon syntax into protocol intent layers. `Ebgp`, `Ibgp`, and
  `Ospf` record intent; `Routing` renders BIRD/FRR syntax.
- Router backend selection belongs on `Router`, for example
  `createRouter(..., routingBackend="bird|frr")`.
- ExaBGP remains a service speaker installed with `ExaBgpService + Binding`,
  not a full routing layer or transit-router backend.
- Looking Glass remains a route-state observer service. Do not merge it with
  ExaBGP event/dashboard semantics.
- Do not claim full IPv6 support for a component until code, docs, examples,
  and regression tests prove it.

## Branch Scope

This branch is for IPv6 control-plane and repository readiness. It includes:

- Core optional IPv6 address state and deterministic allocation.
- Docker dual-stack compilation for modeled IPv6 networks.
- BIRD/FRR BGP and OSPFv3 rendering.
- ExaBGP IPv6 announcements and live control-plane operations.
- Looking Glass IPv4/IPv6 route-state observation.
- Repository-wide migration rules, endpoint helpers, DNS and `/etc/hosts`
  baseline dual-stack readiness.

This branch should not silently absorb unrelated work. Keep these as separate
designs unless the user explicitly changes scope:

- email full IPv6 migration;
- k8s;
- internetmap2;
- SCION underlay dual-stack redesign;
- MPLS/EVPN redesign;
- DHCPv6/SLAAC;
- real-world connectivity/OpenVPN IPv6.

## Completion Definition

The branch is ready when all of the following are true:

- Old IPv4 tests/examples still compile and do not gain unintended IPv6 output.
- New IPv6 examples demonstrate real runtime behavior, not only generated
  configuration.
- Shared helpers exist for address-family selection and endpoint formatting.
- Migrated services use those helpers and keep IPv4 behavior unchanged.
- Design docs and user docs explain the model boundaries and readiness matrix.
- Each commit is scoped, reviewable, and tied to a real capability or test.

## Primary References

- `docs/designs/ipv6-control-plane-design.md`
- `docs/designs/ipv6-repository-readiness-design.md`
- `docs/user_manual/ipv6.md`
- `ai/design-principles.md`
- `ai/skills/ipv6-control-plane/SKILL.md`
- `test_bgp_control_plane_extensions.py`
- `test_ipv6_repository_readiness.py`
