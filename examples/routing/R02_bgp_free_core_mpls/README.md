# BGP-Free Core MPLS Regression

This example tests the routing design where only edge routers participate in
iBGP, while the core routers forward transit traffic using MPLS. It is intended
as a regression example for the interaction among eBGP, iBGP, OSPF, and MPLS.

The topology contains two independent transit AS slices:

- `AS8`: edge-only full-mesh iBGP with MPLS forwarding.
- `AS9`: edge-only route-reflector iBGP with MPLS forwarding.

Both slices use FRR because the MPLS/LDP support in this emulator path is FRR
based. Each transit AS has two edge routers and two core routers:

```text
stub AS -- IX -- edge0 -- core0 -- core1 -- edge1 -- IX -- stub AS
```

The edge routers learn external routes through eBGP and exchange those routes
with each other through iBGP. The core routers do not run BGP. They run the
underlay routing and MPLS/LDP configuration needed to carry traffic across the
core.

## Files

- `bgp_free_core_mpls.py`: standardized SEED Emulator example entrypoint.
- `example.yaml`: test manifest consumed by the runner.
- `test_runtime.py`: custom runtime checks for BGP roles, MPLS config, and
  BGP-free core behavior.
- `output/`: generated Docker compiler output, removed by the clean command.

## Run Manually

From the repository root:

```sh
python examples/routing/R02_bgp_free_core_mpls/bgp_free_core_mpls.py --platform amd --output examples/routing/R02_bgp_free_core_mpls/output
```

Then run the lifecycle with the testing runner:

```sh
python seedemu/testing/cli.py all examples/routing/R02_bgp_free_core_mpls/example.yaml --artifact-dir ci-artifacts/r02-bgp-free-core-mpls
```

## MPLS Host Requirement

This example requires MPLS support on the Docker host. Before running the
runtime stage, the host generally needs these kernel modules loaded:

```sh
sudo modprobe mpls_router
sudo modprobe mpls_iptunnel
sudo modprobe mpls_gso
```

Because GitHub-hosted runners may not provide these modules, this example is
best suited for manual testing or self-hosted CI runners with MPLS support.

## What The Runner Checks

The compile stage verifies that Docker output is generated.

The readiness stage checks that the transit routers and stub hosts are running.

The declarative probes verify cross-stub reachability through each MPLS transit
AS:

- `AS162` reaches `AS163` through `AS8`.
- `AS164` reaches `AS165` through `AS9`.

The custom runtime test verifies that:

- edge routers are labeled as BGP edge routers;
- core routers are labeled as BGP core routers;
- MPLS/LDP and OSPF are present in the FRR configuration;
- core routers do not contain a BGP process;
- the `AS9` route reflector renders the expected FRR route-reflector config.
