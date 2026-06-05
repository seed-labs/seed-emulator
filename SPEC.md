# IPv6 Branch Development Spec

This file tells future agents how to continue the IPv6 branch without
restarting the design or breaking existing SEED behavior.

## Working Context

- Work in `/home/zzw/seed-dev/worktrees/ipv6-control-plane`.
- Stay on `feat/ipv6-control-plane` unless the user explicitly asks otherwise.
- Do not switch to `master` for development.
- The root `ai/` directory is project knowledge: principles, skills, and future
  extension planning. It is not the Codex runtime root and should not be moved.
- Before changing code, read the relevant design docs and the local skill:
  `docs/designs/ipv6-control-plane-design.md`,
  `docs/designs/ipv6-repository-readiness-design.md`,
  `docs/user_manual/ipv6.md`, `ai/design-principles.md`, and
  `ai/skills/ipv6-control-plane/SKILL.md`.

## Architecture Contract

SEED's existing separation of concerns must stay intact.

| Layer | Responsibility | IPv6 rule |
| --- | --- | --- |
| core | topology objects, addresses, prefixes, bindings, endpoints | Store IPv6 beside IPv4; keep IPv4 APIs stable. |
| layers | routing/system intent | Record address-family intent only. |
| services | daemon/application configuration | Consume core state and helpers; do not invent topology state. |
| compiler | runnable artifacts | Emit IPv6 only when model state contains IPv6. |
| examples | user-visible proof | Add IPv6 variants; do not weaken old examples. |
| docs/tests | contract and evidence | State support level and prove regressions. |

Use this mental model when deciding where code belongs:

```text
Base / AS / IX / Network / Interface
  -> carry IPv4 and optional IPv6 topology state
Ebgp / Ibgp / Ospf
  -> record backend-neutral protocol and family intent
Routing
  -> renders BIRD or FRR syntax
Services
  -> read addresses/endpoints and generate service config
Docker
  -> compiles modeled networks, addresses, sysctls, and files
```

## Address-Family API Rules

- `Network.getPrefix()` returns IPv4 and must remain compatible.
- `Interface.getAddress()` returns IPv4 and must remain compatible.
- Use `Network.hasIpv6Prefix()` and `Network.getIpv6Prefix()` for IPv6
  prefixes.
- Use `Interface.hasIpv6Address()` and `Interface.getIpv6Address()` for IPv6
  addresses.
- Use family-aware helpers from `seedemu.core` when formatting endpoints:
  `AddressFamily`, `getInterfaceAddress`, `formatHostPort`, `formatUrl`, and
  `formatMultiaddr`.
- Do not manually concatenate IPv6 `host:port` strings. IPv6 literals need
  bracket handling in URLs and socket-like strings.
- A service must explicitly choose IPv4, IPv6, or dual-stack. It must not assume
  that the first interface's `getAddress()` is the only address.

## IPv6 Addressing Rules

- Default root prefix: `2000::/12`.
- Reserved infrastructure prefix: `2000:ffff::/48`.
- Automatic AS allocation: stable `/48` per AS.
- Automatic local network allocation: stable `/64` per AS network.
- Automatic IX LAN allocation: stable `/64` per Internet Exchange.
- Explicit IPv6 prefixes under the configured root must be claimed so later
  automatic allocation cannot collide.
- Per-network opt-out must remain available with `ipv6Prefix=None`.
- Per-interface opt-out must remain available with `ipv6Address=None`.
- Do not change the old `10.0.0.0/8` style IPv4 examples as part of IPv6 work
  unless a test requires it.

## Routing and Control Plane Rules

- Router daemon selection belongs on `Router`, not a new layer.
- `Ebgp`, `Ibgp`, and `Ospf` are intent layers. They may record families,
  peers, areas, relationships, and policy, but they should not write BIRD/FRR
  daemon syntax.
- `Routing` is the backend renderer for BIRD and FRR.
- BIRD IPv4 and IPv6 tables must stay separate where daemon semantics require
  it.
- OSPFv2 and OSPFv3 must stay separate. Do not reuse an IPv4 OSPF table for
  IPv6.
- FRR IPv6 BGP belongs in `address-family ipv6 unicast`.
- ExaBGP is a service speaker. It should peer on an explicit shared network and
  render family-aware ExaBGP config.
- Looking Glass observes route state. It should expose IPv4 and IPv6 outputs
  clearly without mixing with ExaBGP event streams.

## Service Migration Rules

Migrate services incrementally. A service is not "IPv6 supported" until it has
implementation, docs, and verification.

Recommended service tiers:

| Tier | Area | Rule |
| --- | --- | --- |
| 1 | `EtcHosts`, DNS, DNS cache, Web/CA, Traffic | Prefer early migration because many other services depend on endpoints. |
| 2 | ExaBGP, Looking Glass | Keep tightening tests and docs around the control plane. |
| 3 | Email, Kubo, Tor, Ethereum, Monero, Chainlink | Migrate one service at a time through endpoint helpers. |
| 4 | SCION, MPLS/EVPN, DHCP, RealWorldRouter, OpenVPN, k8s | Require separate designs before broad IPv6 claims. |

Service migration checklist:

1. Preserve the old IPv4 path.
2. Add explicit address-family selection or dual-stack generation only when the
   target node/network has IPv6 state.
3. Use shared endpoint helpers for URL, socket, host-port, and multiaddr text.
4. Add a minimal IPv6 or dual-stack test/example.
5. Update readiness docs without overstating support.

## Testing Rules

Generated files are not enough. Control-plane work needs runtime evidence when
the changed behavior affects daemons or services.

Minimum static checks for most IPv6 branch changes:

```bash
python3 -m compileall seedemu examples/basic/A15_bgp_ipv6_dual_stack examples/basic/A16_exabgp_ipv6_control_plane examples/basic/A17_ipv6_looking_glass
python3 -m pytest -q test_ipv6_repository_readiness.py test_bgp_control_plane_extensions.py
git diff --check
```

When touching examples, regenerate the relevant `output` directory and inspect
generated Compose/config files. For old IPv4 examples, verify that default
output does not contain unintended IPv6 fields such as `enable_ipv6`,
`ipv6_address`, or IPv6 IPAM.

Runtime checks should use a unique Compose project name to avoid stale
containers:

```bash
cd examples/basic/A15_bgp_ipv6_dual_stack
rm -rf output
python3 ./bgp.py
cd output
COMPOSE_PROJECT_NAME=seedemu_a15_ipv6 docker compose up -d
docker compose ps
```

Typical runtime evidence:

```bash
docker exec <router-or-host> ip -6 addr
docker exec <bird-router> birdc show protocols
docker exec <bird-router> birdc show route all
docker exec <frr-router> vtysh -c 'show bgp ipv6 unicast'
docker exec <frr-router> vtysh -c 'show ipv6 ospf6 neighbor'
docker exec <frr-router> vtysh -c 'show ipv6 route bgp'
```

ExaBGP IPv6 evidence:

```bash
docker exec <exabgp-node> grep -n 'ipv6 unicast' /etc/exabgp/exabgp.conf
docker exec <exabgp-node> sh -lc "printf 'announce route 2001:db8:100::/64 next-hop self\n' > /run/exabgp/live.in"
docker exec <peer-router> vtysh -c 'show bgp ipv6 unicast'
docker exec <exabgp-node> sh -lc "printf 'withdraw route 2001:db8:100::/64 next-hop self\n' > /run/exabgp/live.in"
```

Looking Glass evidence:

```bash
curl -fsS http://127.0.0.1:<published-port>/api/state
```

The expected observation is not just "the API returns JSON"; it must include
IPv4/IPv6 route-state for registered routers when the example is dual-stack.

Clean up between runtime checks:

```bash
docker compose down -v
```

## Git Discipline

- Do not commit unrelated generated output, temporary logs, caches, or ad-hoc
  demo notes.
- Keep commits scoped by capability: core API, compiler, routing renderer,
  service migration, docs, tests, examples.
- Before committing, run the smallest meaningful test set plus `git diff
  --check`.
- Inspect `git diff --stat` and `git status --short` before commit.
- Commit messages should explain the capability, not the implementation noise.
  Good shape: `ipv6: add repository readiness contract`.
- Do not rewrite or reset user changes. If the worktree is dirty, identify what
  belongs to the current task and leave unrelated changes alone.
- Do not push unless the user explicitly asks to push.

## Documentation Rules

- Keep design docs precise and honest. Do not market unfinished services as
  IPv6-supported.
- Put branch design in `docs/designs/`.
- Put user-facing behavior in `docs/user_manual/ipv6.md`.
- Put future-agent principles and reusable skills under `ai/`.
- If code behavior changes, update docs in the same commit or an adjacent
  commit before handing off.

## How to Start a New Development Session

Use this sequence before coding:

```bash
cd /home/zzw/seed-dev/worktrees/ipv6-control-plane
git status --short --branch
git diff --stat
sed -n '1,220p' GOAL.md
sed -n '1,260p' SPEC.md
sed -n '1,260p' TASKS.md
sed -n '1,220p' ai/skills/ipv6-control-plane/SKILL.md
```

Then inspect the specific files for the task. Do not begin by searching the
whole repository for every IPv6 string unless the task truly requires a broad
audit.

## How to Decide Whether a Change Belongs Here

A change belongs on this branch when it advances optional repository-level IPv6
readiness without changing default IPv4 behavior.

A change probably does not belong here when it:

- changes a service's application semantics without IPv6 necessity;
- rewrites examples for presentation only;
- introduces a new daemon family unrelated to IPv6 readiness;
- changes k8s, email, internetmap2, or SCION behavior without a dedicated
  design and user approval;
- makes IPv6 mandatory for old examples.
