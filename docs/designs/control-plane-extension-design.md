# Control-Plane Extension Design

This slice adds a narrow FRR and ExaBGP foundation without changing the default
IPv4/BIRD behavior.

## Backend Ownership

`Router` owns the routing daemon choice:

```python
as2.createRouter("r1")
as2.createRouter("r2", routingBackend="frr")
```

Only `bird` and `frr` are valid router backends. `exabgp` and `external` are
intentionally rejected because ExaBGP is not a full router daemon in this model.

## Intent Versus Rendering

`Ebgp`, `Ibgp`, and `Ospf` record control-plane intent:

- BGP peer address, ASN, relationship, import policy, export policy.
- OSPF active/passive interface intent.

They do not decide whether the router runs BIRD or FRR. `Routing` is the only
layer that renders backend-specific daemon files:

- BIRD routers get `/etc/bird/bird.conf` and `bird -d`.
- FRR routers get `/etc/frr/frr.conf` and `/frr_start`.

This keeps protocol semantics stable while allowing backend-specific rendering
to evolve.

## ExaBGP Shape

ExaBGP is modeled as `ExaBgpService + Binding`.

The service installs an ExaBGP speaker on a bound node, resolves the attached
router, emits `/etc/exabgp/exabgp.conf`, and records the router-side BGP peer
intent. `Routing` then renders that peer on the router's selected backend.

This avoids three legacy traps:

- ExaBGP is not a router backend.
- ExaBGP is not a `Layer` shim for BGP routing.
- ExaBGP is not mixed with Looking Glass route-state observation.

## Current Scope

This review slice is IPv4-only and intentionally excludes IPv6 readiness,
Looking Glass, K8s, CI redesign, and runtime evidence plumbing. Those belong to
separate follow-up work.
