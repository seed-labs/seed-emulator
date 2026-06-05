# IPv6 Branch Task Map

This is an initial task map for future agents. It is intentionally not a rigid
ticket list. The goal in `GOAL.md` is fixed; the order here may change when
tests or code review reveal a better path.

## Current Baseline

Already established in this branch:

- shared endpoint/address helpers in `seedemu.core`;
- optional IPv6 core state for networks and interfaces;
- deterministic IPv6 allocation under default `2000::/12`;
- Docker dual-stack output for IPv6-enabled networks;
- optional IPv6 service network and custom container / Internet Map attachment
  support in the Docker compiler;
- repository readiness design and user manual updates;

Not yet re-landed on `development2`:

- BIRD/FRR IPv6 BGP and OSPFv3 rendering;
- ExaBGP IPv6 control-plane announcements;
- Looking Glass IPv6 route-state observation;
- baseline dual-stack DNS and `/etc/hosts` behavior;
- IPv6-aware `Filter` / `Binding` matching.

Before adding more work, verify the baseline still passes:

```bash
python3 -m pytest -q test_ipv6_repository_readiness.py test_bgp_control_plane_extensions.py
git diff --check
```

## Phase 1: Stabilize the Current Branch State

- Review the current uncommitted diff and split it into clean commit groups.
- Confirm docs, tests, and code describe the same IPv6 contract.
- Run the static validation suite.
- Regenerate A15-A17 output only when the examples or compiler behavior changed.
- Confirm old IPv4 examples do not gain IPv6 Compose fields by default.
- Commit only clean source/docs/tests. Avoid generated output unless the repo
  convention for that example requires it.

Suggested commit groups:

- core address-family helpers and Binding/Filter readiness;
- Docker compiler and attachment IPv6 support;
- DNS and `/etc/hosts` baseline dual-stack readiness;
- repository design/user docs;
- tests.

## Phase 2: Core Contract Gaps

- Audit remaining core APIs that carry endpoints or addresses.
- Add family-aware helpers only where repeated service logic would otherwise
  duplicate formatting or selection.
- Extend tests for IPv4/IPv6 prefix conflict detection.
- Add or tighten tests for `Filter`/`Binding` IPv4 and IPv6 matching.
- Verify service network IPv4-only and dual-stack compile paths.
- Verify `attachCustomContainer` and `attachInternetMap` IPv4-only and
  dual-stack compile paths.
- Decide whether `crossConnect(...)` needs a separate design doc before any
  implementation. Do not casually add dual-stack cross-connect behavior because
  SCION and legacy examples depend on it.

Current readiness coverage added in `test_ipv6_repository_readiness.py`:

- explicit IPv6 local prefixes are claimed and automatic `/64` allocation skips
  them;
- explicit IPv6 prefixes that overlap the configured root without being a root
  subnet are rejected, while fully disjoint prefixes outside the root remain
  user-managed;
- reserved infrastructure prefixes and explicit IX prefixes are claimed so
  automatic AS allocation cannot collide with them;
- late `Base.enableIpv6()` rejects overlapping explicit AS/IX IPv6 prefixes;
- late `Base.enableIpv6()` claims existing explicit prefixes before future
  automatic allocation;
- explicit IPv6 root, AS/IX network, route-server, service-network, and
  interface topology inputs tolerate padded literals, bracketed IPv6 literals,
  and CIDRs through shared normalization helpers;
- explicit IPv4/IPv6 interface address inputs route through shared address
  literal normalization while keeping `getAddress()` as IPv4 and
  `getIpv6Address()` as IPv6;
- `Filter` / `Binding` can require explicit IPv4 and IPv6 matches together;
- `Filter` / `Binding` candidate matching uses shared interface address
  helpers and preserves mixed legacy `ip` / explicit IPv4/IPv6 prefix AND
  matching semantics;
- node address/prefix matching helpers are shared by `Binding` and CA
  certificate-install filters instead of duplicating address-family logic;
- `Filter` / `Binding` address and prefix selectors tolerate padded IPv4/IPv6
  literals, bracketed IPv6 literals, and CIDRs without changing their match
  semantics;
- explicit-family `Filter` selectors such as `ipv4`, `ipv6`, `ipv4Prefix`, and
  `ipv6Prefix` use shared node match helpers with a family guard so wrong-family
  literals do not accidentally match;
- shared prefix normalization canonicalizes IPv4/IPv6 CIDR inputs for
  `Binding`, node prefix matching, and ExaBGP announcements without changing
  IPv4 defaults;
- service network compile output remains IPv4-only by default, becomes
  dual-stack only when `serviceNetworkIpv6Prefix` is set, and emits
  per-node `ipv6_address` only for interfaces carrying IPv6 state;
- `attachCustomContainer(...)` and `attachInternetMap(...)` cover explicit
  IPv6 addresses without changing their IPv4-only default, and neither
  attachment path invents a per-container IPv6 address on a dual-stack network
  unless one is provided explicitly. Explicit static IPv4/IPv6 attachment
  addresses now route through shared address-literal normalization before
  compose fields and metadata labels are generated, and mismatched address
  families are rejected.

## Phase 3: Endpoint and DNS Foundation

- Make `EtcHosts` output stable for dual-stack nodes.
- Keep authoritative DNS A records unchanged for IPv4-only scenarios.
- Generate AAAA records only when node/interface IPv6 state exists.
- Confirm DNS cache/root-hint behavior stays compatible with old IPv4 flows.
- Add focused tests for helper formatting:
  `formatHostPort`, `formatUrl`, and `formatMultiaddr`.
- Document endpoint helper rules in service-author docs.

Current readiness coverage added in `test_ipv6_repository_readiness.py`:

- endpoint helper tests cover `formatHost`, IPv4, IPv6, padded host literals,
  DNS names, URL paths, bracketed IPv6 host inputs, bracketed IPv6 authorities
  with ports, explicit-port override for legacy IPv4, DNS-name, and bracketed
  IPv6 authorities, malformed bracketed IPv6 authority rejection, query-only
  and fragment-only URL components, padded explicit ports for host-port, URL,
  and multiaddr helpers, empty/non-numeric explicit port rejection, and padded
  multiaddr formatting;
- service-author documentation now records the IPv4-first address API contract
  and the shared helper rule for URL, host-port, multiaddr, and node-address
  selection; Kubo and Traffic developer notes align with their current explicit
  address-family APIs;
- shared prefix helper tests cover padded and bracketed IPv4/IPv6 CIDR inputs;
- shared DNS-style address-record normalization covers manual A/AAAA literals,
  including bracketed IPv6 literals, without changing non-address record
  handling, and rejects manual A/AAAA records whose address literal does not
  match the requested record family;
- address-family normalization accepts common user-facing and socket-family
  spellings such as `ipv4`, `ip6`, `inet`, and `AF_INET6`;
- migrated service endpoint address-family APIs reuse the shared normalizer
  for padded aliases instead of interpreting family strings locally;
- authoritative DNS and `/etc/hosts` keep IPv4-only defaults and emit AAAA only
  when IPv6 interface state exists; manual authoritative A/AAAA records
  normalize explicit IPv4/IPv6 address literals on add/delete;
- `/etc/hosts` intentionally keeps Bridge/service-network addresses so
  service-only nodes remain resolvable, while continuing to skip IX peering
  addresses that should not become host aliases;
- reverse DNS keeps the existing IPv4 `in-addr.arpa.` PTR generation and adds
  `ip6.arpa.` PTR records only for interfaces carrying IPv6 state;
- DNS cache root hints and forward zones preserve IPv4 while accepting IPv6
  authoritative records; manual root hints normalize A/AAAA address literals,
  and imported forwarder addresses normalize padded records;
- DNS cache address selection is Local IPv4 first, then Local IPv6, then first
  available interface fallback for compatibility with service-network-only
  nodes.
- explicit Base/AS/Node resolver nameserver inputs normalize padded IPv4/IPv6
  literals before writing `resolv.conf` commands.
- `ResolvConfHook` and `ResolvConfHookByAs` resolver nameserver inputs reuse
  shared address-list normalization before writing `resolv.conf` commands.
- DNS authoritative and cache service address selection and A/AAAA record
  literal/address-list normalization now route through shared core helpers
  instead of service-local duplication.
- DNS glue records and manual master IPs normalize explicit IPv4/IPv6 address
  literals, including bracketed IPv6 literals, before generating A/AAAA records,
  slave master lists, or forwarder lists; manual and imported master-IP zone
  keys are normalized to canonical DNS zone names before lookup/output; authoritative
  zone creation and hosting inputs are normalized to the same canonical zone
  names so padded zone strings do not leak into zone files, BIND zone names, or
  cache fallback lookups.
- Domain Registrar dynamic DNS updates preserve A as the default record type
  and allow users to explicitly submit AAAA records while rejecting A/AAAA
  updates whose submitted IP address does not match the selected record family,
  without changing DNS server placement or runtime assumptions.
- DNS cache forward-zone fallback now resolves canonical zone-server names
  through shared node-address helpers, preserving IPv4 defaults while adding
  IPv6 forwarders only when authoritative zone-server nodes carry IPv6 state.
  Forward-zone names are normalized to canonical DNS zone names before master
  lookups and BIND forward-zone output are generated.

## Phase 4: Control-Plane Runtime Proof

- Keep A15 as the mixed BIRD/FRR dual-stack BGP plus OSPFv2/OSPFv3 proof.
- Keep A16 as the ExaBGP IPv6 static/live announce/withdraw proof.
- Keep A17 as the Looking Glass IPv4/IPv6 route-state proof.
- For each runtime example, record the exact observation commands in the
  example README or user manual.
- Validate neighbors and routes, not only generated config.
- Keep ExaBGP event streams separate from Looking Glass route-state views.
- Looking Glass frontend-to-proxy URLs now route through shared URL helpers,
  default to IPv4, and explicitly select bracketed IPv6 proxy URLs with
  `setProxyAddressFamily(AddressFamily.IPv6)`; proxy address-family parsing
  reuses the shared core normalizer for padded aliases.
- BGP and OSPF intent address-family parsing now reuses the shared core
  address-family normalizer, keeping protocol layers backend-neutral while
  accepting the same explicit IPv4/IPv6 family aliases as services; manual BGP
  session address literals also route through shared address normalization so
  padded and bracketed IPv6 inputs do not leak into rendered daemon config.

Useful runtime checks:

```bash
docker exec <node> ip -6 addr
docker exec <bird-router> birdc show protocols
docker exec <bird-router> birdc show route all
docker exec <frr-router> vtysh -c 'show bgp ipv6 unicast'
docker exec <frr-router> vtysh -c 'show ipv6 ospf6 neighbor'
curl -fsS http://127.0.0.1:<lg-port>/api/state
```

## Phase 5: Service Migration Candidates

Move one service at a time. Each migration needs code, docs, and a regression
test or minimal example.

Priority candidates:

- Web/CA endpoint formatting through shared helpers.
- Traffic service address-family selection.
- Kubo/IPFS multiaddr generation through `formatMultiaddr`.
- Email design audit before implementation; do not migrate casually because
  gateway/provider behavior needs careful endpoint decisions.
- Tor design audit for listeners, authorities, and generated configs.
- Ethereum/Monero/Chainlink endpoint audit for RPC, peer discovery, and
  generated URLs.

For each service:

1. Identify where it calls `getAddress()`, formats `host:port`, or writes URLs.
2. Preserve the IPv4 path.
3. Add explicit family selection or dual-stack output only when IPv6 exists.
4. Add tests proving old behavior and the new IPv6 path.
5. Update the readiness matrix.

Current readiness coverage added in `test_ipv6_repository_readiness.py`:

- Traffic generator raw receiver target lists remain unchanged.
- Traffic generator receiver vnode targets can be resolved through shared core
  node-address helpers, default to IPv4, and explicitly select IPv6 when
  requested; generated reachability probes select IPv6 ping for IPv6 literal
  targets while preserving the existing IPv4/hostname ping path.
- Kubo bootstrap RPC URLs, peer multiaddrs, and the legacy `getIP` utility now
  route through shared endpoint helpers with Local-network-first,
  service-network fallback address selection, default to IPv4, and explicitly
  select IPv6 when requested; generated bootstrap helper probes use the same
  explicit address family as the selected bootstrap endpoints.
- Botnet C2/dropper URLs now route through shared node-address and URL helpers,
  preserve the existing first-interface IPv4 default, and explicitly select
  bracketed IPv6 URLs when requested; the legacy dropper fallback brackets bare
  IPv6 host arguments, and DGA dropper runners preserve preformatted HTTP(S)
  URLs and existing `host:port` authority outputs while bracketing bare IPv6
  host fallbacks before generating dropper URLs, but BYOB client/server runtime
  behavior and DGA endpoint handling still need validation before a support
  claim.
- CA `installCACert(Filter(...))` target selection now matches IPv4 and IPv6
  address/prefix filters through shared node address/prefix helpers while
  keeping the existing default of installing on all nodes; CA IP/network helper
  parsing also reuses shared address and prefix normalization for padded and
  bracketed IPv6 literals.
- Web/CA CA domain inputs trim DNS names and normalize padded or bracketed
  IPv4/IPv6 endpoint literals before ACME directory URLs route through shared
  URL helpers; explicit IPv6 CA endpoint literals are bracketed, and Web HTTPS
  and ACME runtime behavior still need validation before a support claim.
- Cymru IP origin mapping remains IPv4-only but now routes accepted IPv4 prefix
  inputs through shared prefix normalization, including padded or bracketed
  literals, and rejects IPv6 prefixes explicitly.
- Monero seed and full-node RPC endpoint lists now route through shared
  address-family and host-port helpers with Local-network-first,
  service-network fallback address selection, default to IPv4, and explicitly
  select bracketed IPv6 endpoints when requested; generated seed wait probes
  use the endpoint address family, but Monero daemon runtime behavior still
  needs validation before a support claim.
- Chainlink generated RPC, faucet, utility, and WebSocket/HTTP node URLs now
  route through shared address-family and URL helpers with Local-network-first,
  service-network fallback address selection, default to IPv4, and explicitly
  select bracketed IPv6 URLs when requested; Ethereum/Chainlink runtime
  behavior still needs validation before a support claim.
- Ethereum faucet/utility HTTP URLs, faucet-user request URLs, faucet
  funding-script server URLs, and generated bootnode/beacon helper fetch URLs
  now route through shared
  address-family and URL helpers with
  Local-network-first, service-network fallback address selection, default to
  IPv4, and explicitly select bracketed IPv6 URLs when requested; the
  Lighthouse validator beacon-node URL template now accepts a preformatted
  helper URL so IPv6 literals are bracketed when supplied, while the current
  PoS validator install path remains IPv4-first and Ethereum ENR content, peer
  discovery, bootnode bind/listener, and daemon runtime behavior still need
  validation before a support claim.
- Tor directory-authority fingerprint downloader URLs and hidden-service
  backend targets now route through shared endpoint helpers, preserving IPv4
  defaults, normalizing and bracketing explicit IPv6 literals without
  bracketing DNS names, and resolving `linkByVnode(...,
  family=AddressFamily.IPv6)` targets with Local-network-first,
  service-network fallback address selection; the entrypoint hidden-service
  fallback brackets bare IPv6 `TOR_HS_ADDR` values when no preformatted target
  is provided, but Tor bind/listener, directory authority, consensus, and
  daemon runtime behavior remain IPv4-first and need a separate migration
  before any support claim.

## Phase 6: Separate Designs Before Code

Do not implement these as quick patches. Start with a design doc and ask for
review when scope is unclear.

- SCION underlay and `crossConnect(...)` dual-stack behavior.
- DHCPv6 or SLAAC.
- MPLS/EVPN IPv6 semantics.
- RealWorldRouter/OpenVPN IPv6 behavior.
- k8s IPv6 support.
- internetmap2 IPv6 visualization/runtime integration.
- Full email IPv6 delivery/provider model.

## Phase 7: Repository Documentation

- Keep `README.md` high-level: SEED supports optional dual-stack emulation, not
  every service is fully migrated.
- Keep `docs/user_manual/ipv6.md` user-facing and operational.
- Keep `docs/designs/ipv6-control-plane-design.md` focused on control-plane
  architecture and class relationships.
- Keep `docs/designs/ipv6-repository-readiness-design.md` focused on the
  repository migration contract and service readiness matrix.
- Keep `ai/design-principles.md` short enough for future agents to actually
  read before coding.
- Update this file when major milestones are completed.

## Stop Conditions

Pause and ask for review before continuing if:

- a change would alter default IPv4 output;
- a service appears to require a new public API rather than helper usage;
- generated runtime behavior differs between BIRD and FRR in a way the design
  docs do not explain;
- a migration touches SCION, k8s, internetmap2, OpenVPN, or email delivery
  semantics;
- tests pass statically but runtime daemon state cannot prove the feature.
