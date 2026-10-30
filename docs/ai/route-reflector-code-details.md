# AS-level iBGP Mode Prompt

## Background

Original related code locations:

- `seedemu/core/AutonomousSystem.py`
  - `createBgpCluster(address)` registers an RR cluster ID.
  - `_aggregateBgpClusters()` aggregates cluster, RR, and client membership.
  - The current implicit default cluster ID is hard-coded as `"10.0.0.0"`.
- `seedemu/core/Node.py`
  - `Router.makeRouteReflector()` records whether a router is an RR.
  - `Router.joinBgpCluster(cluster_id)` records the cluster a router belongs to.
- `seedemu/layers/Ibgp.py`
  - `configure()` currently calls `asobj._aggregateBgpClusters()`.
  - It currently uses `has_rr = any(len(rrs) > 0 ...)` to decide whether to use RR mode or full mesh mode.
  - `_render_rr_mode()` writes RR/client session intent into routers.
  - `_render_full_mesh_mode()` keeps the legacy full mesh behavior.
- `seedemu/layers/_bgp_metadata.py`
  - `route_reflector_client` and `route_reflector_cluster_id` are BGP intent fields.
  - BIRD renders `rr client` and `rr cluster id ...`.
- `seedemu/layers/Routing.py`
  - FRR renders `bgp cluster-id ...` and `neighbor ... route-reflector-client`.

## Behavior Requirements

1. `Ibgp.configure()` must no longer infer the mode by itself using `has_rr`.
2. `Ibgp.configure()` should get the effective iBGP mode from `AutonomousSystem`:
   - `"full-mesh"` calls `_render_full_mesh_mode()`.
   - `"route-reflector"` calls `_render_rr_mode()`.
3. RR cluster aggregation, the default cluster ID, and default RR selection must all be completed inside `AutonomousSystem`.
4. For an AS to enter effective `"route-reflector"` mode, the user must explicitly call `setIbgpMode("route-reflector")`. Only after that should the following APIs be callable:
   - `createBgpCluster()`.
   - `makeRouteReflector(True)`.
   - `joinBgpCluster(cluster_id)`.
5. If the user explicitly sets `"full-mesh"`, that setting should be respected unless RR-specific configuration already exists.
   If there is a conflict, do not silently ignore it. Raise a clear error, for example:
   `"AS2 has route-reflector cluster/router configuration but ibgp_mode is full-mesh"`.
6. Multi-cluster RR must still validate that every cluster has an RR and clients. The default RR is only used when the user selected `"route-reflector"` and did not provide any RR configuration.
7. Do not change the intent schema in `_bgp_metadata.py`. Continue using the existing fields
   `route_reflector_client` and `route_reflector_cluster_id`.
8. Do not change BIRD/FRR rendering semantics. BIRD should still render RR configuration through `_bgp_metadata.py`, and FRR should still render cluster-id and route-reflector-client through `Routing.py`.
9. Existing old RR usage through `createBgpCluster()`, `joinBgpCluster()`, and `makeRouteReflector()` must not be broken.
10. `setIbgpMode()` must validate the input. Invalid values should directly raise `ValueError` or `AssertionError`, and the error message must include the valid values.
