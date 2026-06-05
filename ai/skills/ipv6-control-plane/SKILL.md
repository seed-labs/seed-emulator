# IPv6 Control Plane Skill

Use this skill when designing, implementing, or reviewing IPv6 control-plane support in SEED Emulator.

## Rules

- Default behavior must remain IPv4-only unless `Base(enableIpv6=True)` or `base.enableIpv6(...)` is used.
- `Network.getPrefix()` and `Interface.getAddress()` remain IPv4 APIs. Use `getIpv6Prefix()` and `getIpv6Address()` for IPv6.
- IPv6 auto allocation starts from the configured root prefix, default `2000::/12`, with `/48` per AS and `/64` per local or IX network.
- The reserved infrastructure prefix is `2000:ffff::/48`; do not allocate customer or IX LAN prefixes from it.
- Explicit IPv6 prefixes under the configured root must be claimed before later auto allocation.
- Protocol layers record address-family intent; `Routing` renders BIRD and FRR syntax.
- OSPFv3 uses a separate IPv6 table from OSPFv2.
- ExaBGP IPv6 support belongs in `ExaBgpService`; it should peer on a shared IX/router-facing network and produce `ipv6 unicast` config.
- Looking Glass shows route-state for both families and must stay separate from ExaBGP event dashboards.

## Evidence Checklist

- Compose networks include IPv6 IPAM and `enable_ipv6`.
- Containers show expected `ip -6 addr`.
- BIRD shows IPv6 routes through `birdc show route all`.
- FRR shows IPv6 BGP and OSPFv3 with `vtysh`.
- ExaBGP accepts IPv6 static and live announce/withdraw.
- Looking Glass `/api/state` includes IPv6 route-state for observed routers.
