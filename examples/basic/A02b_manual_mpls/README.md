# Transit AS Manual MPLS

This example demonstrates manual MPLS label-table setup. It is the companion to
`A02a_transit_as_mpls`, which uses LDP to distribute labels automatically.

The topology has one transit AS and three stub ASes. `AS2` has three BGP edge
routers that also act as MPLS provider-edge routers, plus three internal MPLS
core routers:

```text
             AS151
               |
             IX101
               |
              e1
               |
              r1
             /  \
            /    \
          r2 ---- r3
          |       |
          e2      e3
          |       |
        IX102   IX103
          |       |
        AS152   AS153
```

`e1`, `e2`, and `e3` are AS2's BGP edge routers and MPLS ingress/egress
routers:

- `e1`: `IX101`, connected to `AS151`.
- `e2`: `IX102`, connected to `AS152`.
- `e3`: `IX103`, connected to `AS153`.

`r1`, `r2`, and `r3` are internal AS2 routers. They form the triangle MPLS
core and do not connect directly to any IX:

- `e1 -- r1`
- `e2 -- r2`
- `e3 -- r3`
- `r1 -- r2`
- `r2 -- r3`
- `r3 -- r1`

The example uses normal BGP/OSPF routing, but it does not use the SEED Emulator
`Mpls` layer and does not use LDP. Instead, AS2's edge and core routers install
static MPLS routes from `/manual_mpls_setup.sh`. The edge routers push labels
when traffic enters the provider backbone and pop labels when traffic leaves it.
The internal routers only swap labels across the provider core.

## Manual Labels

The labels are directional:

| Traffic | Edge push | Core swap | Edge pop |
| --- | --- | --- |
| AS151 to AS152 | `e1` pushes `200` to `r1` | `r1`: `200 -> 201`; `r2`: `201 -> 202` | `e2` pops `202`, forwards to AS152 |
| AS151 to AS153 | `e1` pushes `210` to `r1` | `r1`: `210 -> 211`; `r3`: `211 -> 212` | `e3` pops `212`, forwards to AS153 |
| AS152 to AS151 | `e2` pushes `300` to `r2` | `r2`: `300 -> 301`; `r1`: `301 -> 302` | `e1` pops `302`, forwards to AS151 |
| AS152 to AS153 | `e2` pushes `310` to `r2` | `r2`: `310 -> 311`; `r3`: `311 -> 312` | `e3` pops `312`, forwards to AS153 |
| AS153 to AS151 | `e3` pushes `400` to `r3` | `r3`: `400 -> 401`; `r1`: `401 -> 402` | `e1` pops `402`, forwards to AS151 |
| AS153 to AS152 | `e3` pushes `410` to `r3` | `r3`: `410 -> 411`; `r2`: `411 -> 412` | `e2` pops `412`, forwards to AS152 |

The Docker host must support Linux MPLS:

```sh
sudo modprobe mpls_router
sudo modprobe mpls_iptunnel
sudo modprobe mpls_gso
```

GitHub-hosted runners may not provide these modules, so this example is not
included in the default CI workflow.

## Standard Arguments

```sh
python examples/basic/A02b_manual_mpls/manual_mpls.py amd
python examples/basic/A02b_manual_mpls/manual_mpls.py --platform amd --output examples/basic/A02b_manual_mpls/output
python examples/basic/A02b_manual_mpls/manual_mpls.py --dumpfile examples/basic/A02b_manual_mpls/manual_mpls.bin
```

Supported arguments:

- `amd|arm`: optional legacy platform argument.
- `--platform amd|arm`: named platform argument.
- `--output PATH`: output folder for Docker compiler results.
- `--dumpfile PATH`: save a serialized emulator instead of compiling Docker output.
- `--override` / `--no-override`: control whether existing output is replaced.
- `--skip-render`: compile without calling `emu.render()` first.

## TestRunner Lifecycle

```sh
python seedemu/testing/cli.py all examples/basic/A02b_manual_mpls/example.yaml --artifact-dir ci-artifacts/a02b-manual-mpls
```

The runtime test uses `ComposeRuntimeTest`. It verifies cross-AS reachability,
checks that edge routers install the expected push/pop labels, checks that core
routers install the expected swap labels, and confirms that LDP is not used.

## Learning Activities

- Trace AS151 to AS152 and identify labels `200`, `201`, and `202`.
- Trace AS151 to AS153 and identify labels `210`, `211`, and `212`.
- Break one label in `/manual_mpls_setup.sh` and observe which destination fails.
- Compare this example with `A02a_transit_as_mpls` to see what LDP automates.
