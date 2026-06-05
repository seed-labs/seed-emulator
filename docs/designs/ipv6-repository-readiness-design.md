# Repository-Wide IPv6 Readiness Design

This document defines how SEED Emulator should evolve from IPv4-first
examples to optional dual-stack capability across the repository. It is the
migration contract for incremental IPv6 work on top of `development2`.

## 中文摘要

IPv6 不应该被理解成几个示例的局部能力，而是仿真器级别的可选能力。
默认仍然是 IPv4-only；旧示例、旧 API、旧输出都应保持稳定。只有用户在
`Base`、网络、接口或相关 service API 中显式启用 IPv6，编译结果才进入
双栈状态。

全仓库迁移遵守下面的边界：

- core 保存拓扑、地址、前缀、绑定和 endpoint 的通用语义；
- layer 只表达协议或系统 intent；
- service 读取地址族能力并生成自身配置；
- compiler 把已经存在的模型状态编译成运行制品；
- examples 用新增 IPv6 variant 展示新能力，不改旧示例含义。

## Current Landing Status

The first PR landed the contract and shared helper foundation:

- shared address-family and endpoint formatting helpers in `seedemu.core`;
- deterministic IPv6 prefix allocation helper;
- design, user, and agent-facing migration documents.

The core-topology PR adds optional IPv6 model state to `Base`, AS networks, IX
LANs, node interfaces, and route-server attachments.

The Docker-compiler PR adds Compose dual-stack output for networks and
interfaces that already carry IPv6 state, optional IPv6 service-network
prefixes, and explicit static IPv6 attachment output for custom containers and
Internet Map. It intentionally does not claim that Routing, ExaBGP, Looking
Glass, DNS, `/etc/hosts`, or repository services are already dual-stack on
`development2`. Their rows below describe the target migration contract and
must be treated as implemented only after follow-up PRs add code and tests.

## Address-Family Contract

Existing IPv4 APIs remain IPv4 APIs:

- `Network.getPrefix()` returns the IPv4 prefix.
- `Interface.getAddress()` returns the IPv4 address.
- `Filter(ip=...)` and `Filter(prefix=...)` remain accepted and now parse either
  IPv4 or IPv6 literals; bracketed IPv6 address literals are normalized when a
  helper accepts address literals. Explicit-family selectors such as
  `Filter(ipv4=...)`, `Filter(ipv6=...)`, `Filter(ipv4Prefix=...)`, and
  `Filter(ipv6Prefix=...)` require the literal to match the selected family.

Dual-stack aware code should use the explicit IPv6 APIs or the shared helpers:

- `Network.hasIpv6Prefix()` / `Network.getIpv6Prefix()`.
- `Interface.hasIpv6Address()` / `Interface.getIpv6Address()`.
- `AddressFamily`, `getInterfaceAddress(...)`, `formatHost(...)`,
  `formatHostPort(...)`,
  `getNodeAddress(...)`, `getNodeAddresses(...)`, `getNodePreferredAddress(...)`,
  `nodeHasAddress(...)`, `nodeHasAddressInPrefix(...)`, `formatUrl(...)`,
  `formatMultiaddr(...)`, `normalizeAddressList(...)`, `normalizePrefix(...)`, and
  `normalizeAddressRecord(...)` from `seedemu.core`.

Services must not assume that the first interface address is the only usable
address. A service should either select IPv4 explicitly, select IPv6
explicitly, or generate both families when its daemon supports dual stack. When
a legacy API already carries a bracketed IPv6 authority such as
`[2000::1]:8443`, shared URL helpers preserve that authority and canonicalize
the IPv6 literal instead of treating it as an unparsed hostname. If the caller
also supplies a separate port, the separate port overrides the port embedded in
a legacy IPv4, DNS-name, or bracketed IPv6 authority, and padded explicit port
values are trimmed before `host:port`, URL, or multiaddr output is generated.
Malformed bracketed IPv6 authorities, such as `[2000::1]:bad`, are rejected
instead of being emitted as ambiguous endpoints. Explicit port arguments must
be non-empty decimal strings, so helpers reject invalid socket-like endpoints
before a service writes them into config. URL components beginning with `?` or
`#` are preserved as query or fragment components rather than being rewritten
as path segments.

## Core Readiness

Landing foundation:

- Optional IPv6 root prefix and deterministic AS/IX `/64` allocation.
- IPv6 state on `Network` and `Interface`.
- Docker Compose dual-stack network/IPAM and service `ipv6_address` output for
  explicitly IPv6-enabled model state.
- Optional IPv6 service network prefix, with per-node `ipv6_address` emitted
  only for service-network attachments that carry IPv6 state.
- Optional IPv6 address on `attachCustomContainer(...)` and
  `attachInternetMap(...)`; explicit static IPv4/IPv6 attachment addresses are
  normalized before compose fields and metadata labels are emitted, and
  mismatched address-family inputs are rejected.

Target follow-up foundation:

- IPv6-aware BGP/OSPF intent rendering for BIRD and FRR.
- IPv6-aware ExaBGP speaker service and Looking Glass route-state queries.
- IPv6-aware `Filter` / `Binding` matching and `Action.NEW` placement.

Deferred core items:

- `crossConnect(...)` remains IPv4-only in this branch. It is used heavily by
  SCION and legacy examples, so dual-stack cross-connect links need a separate
  design rather than an implicit API change.
- Real-world connectivity and OpenVPN remain IPv4-oriented.
- DHCP remains IPv4-only; DHCPv6/SLAAC behavior should be designed separately.

## Service Readiness Matrix

| Area | Status | Migration rule |
| --- | --- | --- |
| Routing control plane | Pending follow-up | Keep protocol intent family-aware; render backend syntax only in `Routing`. |
| ExaBGP | Pending follow-up | Service speaker may use IPv4 or IPv6 shared peer address; static announcement prefixes use shared prefix normalization before rendering. |
| Looking Glass | Pending follow-up | Route-state views separate IPv4/IPv6 output; frontend-to-proxy URLs use shared URL helpers, default to IPv4, and may explicitly select bracketed IPv6 proxy endpoints. |
| Docker compiler | Supported | Emit IPv6 only for networks/interfaces carrying IPv6 state. |
| `/etc/hosts` | Pending follow-up | Generate IPv4 and IPv6 entries when available; keep service-network Bridge addresses for service-only nodes, and skip IX peering addresses. |
| DNS authoritative | Pending follow-up | Generate A and AAAA for node-backed records; manual A/AAAA and glue record literals use shared normalization, including bracketed IPv6 literals, and reject address-family mismatches such as A-with-IPv6 or AAAA-with-IPv4; authoritative zone inputs and master-IP zone keys are normalized to canonical DNS zone names, and masters may include both address families; reverse DNS keeps IPv4 `in-addr.arpa.` PTR records and adds `ip6.arpa.` PTR records only when interfaces carry IPv6 state. |
| Domain Registrar | Pending follow-up | Dynamic DNS updates preserve A as the default record type, allow explicit AAAA submissions, and reject submitted IP addresses whose family does not match the selected A/AAAA record type; TLD placement and runtime behavior remain the existing Domain Registrar model. |
| DNS cache | Pending follow-up | Prefer IPv4 for old resolver behavior; accept IPv6 forwarders/root hints, normalize manual A/AAAA root-hint literals through the shared helper, normalize forward-zone names to canonical DNS zone names, and use shared node-address helpers for forward-zone fallback to authoritative zone servers. |
| Web/CA | Compatible | Existing IPv4 behavior preserved; CA certificate-install filters match IPv4/IPv6 address and prefix selectors through shared node address/prefix helpers; CA IP/network helper parsing uses shared address and prefix normalization; CA domain inputs trim DNS names and normalize padded or bracketed IPv4/IPv6 endpoint literals before ACME directory URLs use shared URL helpers, but Web HTTPS and ACME runtime behavior still need validation before a full support claim. |
| Cymru IP origin | IPv4-first | Origin ASN TXT mapping remains IPv4-only; accepted IPv4 prefix inputs use shared prefix normalization, and IPv6 prefixes are rejected explicitly rather than partially mapped. |
| Traffic services | Compatible | Raw receiver targets are unchanged; receiver vnodes can be resolved to IPv4 or IPv6 targets through shared node-address helpers, and generated reachability probes select IPv6 ping for IPv6 literal targets, but each tool still needs runtime validation before a full support claim. |
| Kubo/IPFS | Compatible | Bootstrap RPC URLs, bootstrap helper probes, peer multiaddrs, and the legacy `getIP` utility use shared endpoint helpers with Local-network-first, service-network fallback address selection, default to IPv4, and may explicitly select IPv6; broader Kubo runtime behavior still needs validation before a full support claim. |
| Botnet | Compatible | Binding-based C2/dropper URLs use shared node-address and URL helpers, preserve the first-interface IPv4 default, and may explicitly select bracketed IPv6 URLs; legacy fallbacks bracket bare IPv6 host arguments, and DGA dropper runners preserve preformatted HTTP(S) URLs and existing `host:port` authority outputs while bracketing bare IPv6 host fallbacks, but BYOB client/server runtime behavior and DGA endpoints still need validation before a full support claim. |
| Monero | Compatible | Seed and full-node RPC endpoint lists and seed wait probes use shared address-family and host-port helpers with Local-network-first, service-network fallback address selection, default to IPv4, and may explicitly select IPv6; daemon listener/runtime behavior still needs validation before a full support claim. |
| Chainlink | Compatible | Generated Chainlink RPC, faucet, utility, and node WebSocket/HTTP URLs use shared endpoint helpers with Local-network-first, service-network fallback address selection, default to IPv4, and may explicitly select bracketed IPv6 URLs; Ethereum/Chainlink runtime behavior still needs validation before a full support claim. |
| Email | IPv4-first | Provider/gateway/default-route logic must be redesigned before IPv6 claim. |
| Tor | IPv4-first | Directory-authority downloader URLs and hidden-service backend target formatting are helper-ready; explicit IP literals are normalized and IPv6 literals are bracketed without bracketing DNS names; `linkByVnode(..., family=AddressFamily.IPv6)` resolves backend vnodes with Local-network-first, service-network fallback address selection; the entrypoint hidden-service fallback brackets bare IPv6 `TOR_HS_ADDR` values when no preformatted target is provided, but bind/listener, directory authority addressing, consensus, and daemon runtime need a separate migration before an IPv6 support claim. |
| Ethereum | Compatible | Faucet/utility HTTP URLs, faucet-user request URLs, faucet funding-script server URLs, and generated bootnode/beacon helper fetch URLs use shared endpoint helpers with Local-network-first, service-network fallback address selection, default to IPv4, and may explicitly select bracketed IPv6; the Lighthouse validator beacon-node URL template accepts preformatted helper URLs so IPv6 literals are bracketed when supplied, but the current PoS validator install path remains IPv4-first, and ENR content, peer discovery, bootnode bind/listener, and daemon runtime behavior still need validation before a full support claim. |
| SCION | Separate design | Underlay, crossConnect, and SCION control tooling currently assume IPv4. |
| MPLS/EVPN | Separate design | Routing identifiers and dataplane assumptions need dedicated validation. |
| k8s/internetmap2 | Out of this branch | Do not claim IPv6 support until their own branch validates it. |

## Migration Pattern for Services

A service migration should follow this order:

1. Keep the old IPv4 path unchanged.
2. Add explicit address-family selection or generate both families only when
   the target node/interface has IPv6 state.
3. Use shared endpoint helpers for URLs, `host:port`, and multiaddr strings.
4. Add a minimal IPv6 example or test without changing old examples.
5. Document unsupported daemon features clearly instead of generating partial
   IPv6 config.

The acceptance rule is simple: enabling IPv6 must not make an IPv4-only service
silently wrong. It may continue using IPv4, or it may clearly expose dual-stack
support after tests prove it.

## Validation Baseline

Repository-level IPv6 work should keep these checks green:

- Existing IPv4 examples compile without IPv6 Compose fields.
- A15-A17 keep proving the control-plane path.
- `Filter` / `Binding` match IPv4 and IPv6 addresses/prefixes.
  Explicit-family selectors reject wrong-family literals instead of falling
  back to the literal's parsed family.
- IPv6 prefix allocation rejects reserved infrastructure reuse and overlapping
  explicit AS/IX prefixes, including late `Base.enableIpv6()` migration paths;
  explicit root, AS/IX, and service-network IPv6 prefixes use shared prefix
  normalization so padded and bracketed CIDR inputs behave consistently.
  Explicit prefixes that overlap the configured root without being root subnets
  are rejected, while fully disjoint prefixes outside the root remain
  user-managed.
- Explicit interface IPv4/IPv6 address inputs use shared address literal
  normalization while preserving `getAddress()` as IPv4 and
  `getIpv6Address()` as IPv6.
- Service network and custom containers compile as IPv4-only by default and
  dual-stack only when IPv6 is provided; service-network interface opt-out,
  custom container attachments, and custom Internet Map attachments without an
  explicit IPv6 address suppress per-node `ipv6_address` even on a dual-stack
  network. Explicit static attachment addresses normalize padded or bracketed
  IPv4/IPv6 literals before compose and metadata output, and reject IPv4/IPv6
  field mismatches.
- DNS and `/etc/hosts` emit stable A/AAAA and hosts entries when IPv6 exists,
  and manual A/AAAA records reject mismatched address families.
- DNS address selection uses shared core helpers so service code does not
  duplicate Local-vs-service-network fallback rules.
- Explicit resolver nameserver inputs, including `ResolvConfHook` and
  `ResolvConfHookByAs`, use shared address-list normalization before writing
  `resolv.conf` commands.
- Authoritative DNS and DNS cache forward-zone fallback resolve canonical
  zone names, normalize zone inputs before lookup/output, and emit IPv6
  forwarders only for zone-server nodes with IPv6 state.
