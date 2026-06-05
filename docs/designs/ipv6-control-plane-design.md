# IPv6 Addressing and Control Plane Design

This design promotes IPv6 from example-specific wiring to a project-level
optional dual-stack capability. IPv4 remains the default behavior. The target
API enables IPv6 explicitly through `Base(enableIpv6=True,
ipv6RootPrefix="2000::/12")` or by calling `base.enableIpv6(...)` before
rendering.

The design follows SEED's existing model: `Base` owns topology and addressing,
protocol layers record intent, `Routing` renders daemon configuration, and
compilers translate the rendered model into runnable artifacts.

## 中文摘要

本设计把 IPv6 提升为仿真器级别的可选能力，而不是 A15-A17 的局部演示
逻辑。默认行为仍然是 IPv4-only；只有用户在 `Base` 层显式开启 IPv6，
拓扑对象、控制面渲染和 Docker 编译结果才会进入双栈模式。这样既保留
旧示例和旧 API 的稳定性，也给后续 IPv6 场景、服务和实验分支留下统一
入口。

核心边界是：

- `Base`、`AutonomousSystem`、`InternetExchange`、`Network` 和
  `Interface` 负责拓扑与地址状态；
- `Ebgp`、`Ibgp`、`Ospf` 只记录协议意图和 address-family 信息；
- `Routing` 统一把意图渲染成 BIRD/FRR 配置；
- `ExaBgpService` 和 Looking Glass 仍然是服务，不改造成路由层；
- Docker 编译器只把已经带 IPv6 前缀的网络编译为双栈网络。

## Current Landing Status

The first PR landed the repository contract and shared helper foundation on top
of `development2`. The core-topology PR adds optional IPv6 state to
`Base`, `AutonomousSystem`, `InternetExchange`, `Network`, `Node`, and
`Interface`, including late enablement and per-network/per-interface opt-out.
It still does not claim that compiler output, Routing, ExaBGP, Looking Glass,
DNS, or example runtime paths have been re-integrated. Those pieces should be
ported in follow-up PRs against this design without reintroducing removed
legacy control-plane shims.

## Design Position

- Keep IPv4 API compatibility. Existing calls to `getPrefix()`,
  `getAddress()`, and `joinNetwork(..., address="auto")` remain IPv4-oriented.
- Add IPv6 state beside IPv4 state instead of changing return types.
- Make IPv6 opt-in at the `Base` layer, but allow per-network and per-interface
  overrides.
- Keep routing semantics address-family aware without moving daemon syntax into
  `Ebgp`, `Ibgp`, or `Ospf`.
- Treat IPv6 as emulator addressing state, not as a separate feature bolted onto
  A15-A17.

## Core API Shape

| Concern | IPv4 API kept | IPv6 API added |
| --- | --- | --- |
| Global switch | `Base()` | `Base(enableIpv6=True)`, `base.enableIpv6(...)` |
| Network prefix | `Network.getPrefix()` | `Network.getIpv6Prefix()`, `Network.hasIpv6Prefix()` |
| Interface address | `Interface.getAddress()` | `Interface.getIpv6Address()`, `Interface.hasIpv6Address()` |
| Node attachment | `joinNetwork(net, address="auto")` | optional `ipv6Address="auto"|None|explicit` |
| AS network | `createNetwork(..., prefix="auto")` | optional `ipv6Prefix="auto"|None|explicit` |
| IX network | `createInternetExchange(..., prefix="auto")` | optional `ipv6Prefix`, `rsIpv6Address` |

`Base.enableIpv6()` also applies to existing AS and IX networks that were
created with the default IPv6 intent. This supports the common migration path:
build an IPv4 topology first, then make the same topology dual stack before
rendering.

## Prefix Plan

`Ipv6Addressing` owns automatic IPv6 allocation.

- Default root prefix: `2000::/12`.
- Reserved infrastructure prefix: `2000:ffff::/48`.
- AS allocation: stable `/48` prefixes under the root.
- AS local network allocation: stable `/64` prefixes under the AS `/48`.
- IX peering LAN allocation: stable `/64` prefixes under the root, collision
  checked against AS and reserved prefixes.
- Interface IDs reuse the existing `AddressAssignmentConstraint` offsets, so
  host/router intent stays recognizable across IPv4 and IPv6.
- IX participants still prefer ASN-derived host offsets. If an offset is out of
  range or collides, the allocator advances deterministically and asserts only
  when exhausted.

`2000::/12` is a public-style emulation prefix. It is not a claim that generated
routes are globally reachable. Users can override it with another root prefix
when a scenario needs a different address plan.

The reserved infrastructure prefix is deliberately outside automatic AS and IX
allocation. `Routing` uses it as the default IPv6 loopback pool, so routing
infrastructure does not collide with customer or IX LAN prefixes.

Explicit user prefixes are claimed by the allocator when they fall under the
configured IPv6 root. Later automatic allocations must avoid them. Prefixes
outside the root are treated as user-managed and are not rewritten by the
allocator. A prefix that overlaps the configured root but is not a subnet of it
is rejected because it would make later automatic allocation ambiguous.

## Core Change Map

| File | Role |
| --- | --- |
| `seedemu/core/Ipv6Addressing.py` | Owns the default root prefix, reserved infrastructure prefix, AS `/48`, local `/64`, IX `/64`, and collision checks. |
| `seedemu/layers/Base.py` | Exposes the global IPv6 switch, root prefix accessor, reserved-prefix accessor, and late enablement backfill for AS/IX networks. |
| `seedemu/core/AutonomousSystem.py` | Carries the IPv6 allocator into local networks and preserves per-network `ipv6Prefix` intent. |
| `seedemu/core/InternetExchange.py` | Carries IX IPv6 prefix intent and route-server IPv6 address intent. |
| `seedemu/core/Network.py` | Stores optional IPv6 prefix and prefix intent beside the existing IPv4 prefix. |
| `seedemu/core/Node.py` | Stores optional interface IPv6 addresses through `joinNetwork(..., ipv6Address=...)`. |
| `seedemu/layers/Routing.py` | Renders BIRD/FRR address-family syntax, IPv6 loopbacks, IPv6 BGP, and OSPFv3. |
| `seedemu/compiler/Docker.py` | Emits IPv6 compose networks, service IPv6 addresses, forwarding sysctls, metadata labels, and self-managed dummy IPv6 replacement. |

## Class Relationship

```text
Base(enableIpv6=True, ipv6RootPrefix)
  owns Ipv6Addressing(root, reserved infra prefix)
  -> AutonomousSystem.setIpv6Addressing(...)
       -> createNetwork(..., ipv6Prefix)
       -> Network(ipv6Prefix, ipv6PrefixIntent)
  -> createInternetExchange(..., ipv6Prefix, rsIpv6Address)
       -> InternetExchange
       -> Network(type=InternetExchange, ipv6PrefixIntent)
  -> Node.joinNetwork(..., ipv6Address)
       -> Interface(address, ipv6Address)

Ebgp / Ibgp / Ospf
  -> record backend-neutral address-family intent
  -> Routing renders BIRD or FRR
  -> Docker compiles runtime networks and container addresses
```

This keeps the original layer model intact: topology construction does not know
daemon syntax, protocol layers do not write config files, and compilers do not
invent routing semantics.

## Per-Topology Control

Global dual stack:

```python
base = Base(enableIpv6=True)
```

Late enablement before render:

```python
base = Base()
as150 = base.createAutonomousSystem(150)
as150.createNetwork("net0")
base.createInternetExchange(100)

base.enableIpv6()
```

Per-network override:

```python
as150.createNetwork("net0", ipv6Prefix="2000:0:150::/64")
as150.createNetwork("v4only", ipv6Prefix=None)
```

Per-interface override:

```python
as150.createHost("web").joinNetwork("net0", ipv6Address="2000:0:150::71")
as150.createHost("legacy").joinNetwork("v4only", ipv6Address=None)
```

## Render Flow

```text
Base / AS / IX
-> Network + Interface carry optional IPv6 state
-> Ebgp / Ibgp / Ospf record address-family intent
-> _bgp_metadata normalizes BGP sessions and OSPF interface intent
-> Routing renders BIRD or FRR syntax
-> Docker compiler emits dual-stack compose networks and container addresses
```

Protocol layers do not write daemon-specific IPv6 syntax. BIRD and FRR syntax
stays in `Routing`. Manual BGP session intent still goes through shared
address-family and address-literal normalization, so padded or bracketed IPv6
inputs are canonicalized before `Routing` renders daemon config.

## Docker Compiler

The regular Docker compiler emits `enable_ipv6: true`, IPv6 IPAM subnets, and
service-level `ipv6_address` only for networks that actually have IPv6 prefixes.

For `selfManagedNetwork=True`, the compiler now creates dummy IPv6 subnets from
`dummyIpv6NetworksPool` and records replacement mappings in
`/dummy_addr_map.txt`, matching the existing IPv4 self-managed behavior.

Router, border-router, openvpn-router, and route-server containers get IPv6
forwarding sysctls when they have IPv6 interfaces. Host containers remain
ordinary IPv6 hosts.

## BIRD and FRR Rendering

BIRD:

- keeps IPv4 `t_direct`, `t_ospf`, and `t_bgp`;
- adds IPv6 `t_direct6`, `t_ospf6`, and `t_bgp6` only when IPv6 is present;
- renders BGP family blocks from the same session intent;
- renders OSPFv3 as a separate IPv6 OSPF protocol/table.

FRR:

- keeps OSPFv2 and IPv4 BGP behavior;
- enables `ospf6d` for IPv6 routers;
- renders `address-family ipv6 unicast`;
- renders OSPFv3 interface commands for IPv6-capable interfaces.

## Services

ExaBGP remains a service speaker. It resolves the shared network with the peer
router, installs router-side BGP intent, and writes `/etc/exabgp/exabgp.conf`
with `ipv6 unicast` when IPv6 is available or IPv6 prefixes are announced.

Looking Glass remains a route-state observer. The proxy queries BIRD route
state through `birdc` and FRR route state through `vtysh`, including IPv6 BGP
and OSPFv3 commands. Frontend-to-proxy traffic keeps an IPv4 endpoint by
default; scenarios that explicitly select IPv6 proxy endpoints use shared URL
helpers so IPv6 literals are bracketed correctly.

Other services remain compatible with IPv4 defaults. A service that wants IPv6
should read IPv6 through `Interface.hasIpv6Address()` and
`Interface.getIpv6Address()` instead of changing existing IPv4 code paths.

## Examples and Validation

| Example | Purpose | Evidence |
| --- | --- | --- |
| `A15_bgp_ipv6_dual_stack` | BIRD/FRR mixed dual-stack BGP with OSPFv2/OSPFv3 | IPv6 compose IPAM, `ip -6 addr`, `birdc show route all`, FRR `show bgp ipv6 unicast`, `show ipv6 ospf6 neighbor` |
| `A16_exabgp_ipv6_control_plane` | ExaBGP IPv6 static/live announce | `exabgp.conf` has `ipv6 unicast`, peer learns and withdraws IPv6 prefixes |
| `A17_ipv6_looking_glass` | IPv6 route-state observability | Looking Glass `/api/state` includes BIRD and FRR IPv6 route-state |

Existing A12-A14 remain the IPv4 regression baseline.

## Repository-Level Follow-Up

This document focuses on the control-plane foundation. The repository-wide
migration contract for services, endpoint formatting, DNS, `/etc/hosts`,
custom containers, service network IPv6, and IPv4-first components is tracked
in [Repository-Wide IPv6 Readiness Design](./ipv6-repository-readiness-design.md).
