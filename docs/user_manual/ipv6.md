# IPv6 Readiness

IPv6 support is being added as an optional repository-level capability. The
current `development2` landing provides shared address-family helpers,
deterministic IPv6 prefix allocation, optional topology IPv6 state, and the
migration contract. The Docker compiler now emits dual-stack Compose output
only for explicitly IPv6-enabled networks and attachments. Routing, ExaBGP,
Looking Glass, DNS, and service runtime support are staged for follow-up PRs
and should not be treated as fully available until their code, examples, and
tests land.

Existing emulations remain IPv4-only by default. New IPv6 work must preserve
the existing IPv4 APIs and add IPv6 state beside them instead of changing old
return values.

```python
base = Base(enableIpv6=True)
```

The topology API also allows enabling IPv6 after building the base topology, as
long as this is done before rendering:

```python
base = Base()
as150 = base.createAutonomousSystem(150)
as150.createNetwork("net0")
base.createInternetExchange(100)

base.enableIpv6()
```

## Address Plan

The shared IPv6 allocator uses `2000::/12` as the default root prefix. It is a
public-style emulation prefix; it does not claim that generated routes are
globally reachable outside the emulator. `Base` can override the root prefix:

```python
base = Base(enableIpv6=True, ipv6RootPrefix="2000::/12")
```

Automatic allocation uses the following plan:

- one stable `/48` per AS;
- one stable `/64` per AS local network;
- one stable `/64` per Internet Exchange peering LAN;
- `2000:ffff::/48` is reserved for routing infrastructure, such as loopback
  addresses used by the `Routing` layer.

User-provided IPv6 prefixes under the root are normalized and reserved before
later automatic allocation. Padded CIDR strings and bracketed IPv6 literals are
accepted consistently across root, AS network, IX LAN, and service-network
prefix inputs. Overlapping explicit AS/IX prefixes are rejected, and automatic
allocation skips claimed prefixes instead of reusing them. Prefixes outside the
configured root may be used as user-managed prefixes when they are fully
disjoint from the root. Prefixes that overlap the root without being subnets of
it are rejected because automatic allocation could otherwise collide with them.

IPv6 address assignment follows the existing `AddressAssignmentConstraint`
intent. Hosts use the host offset range, routers use the router offset range,
and IX participants prefer ASN-derived offsets.

## Network and Interface APIs

The existing IPv4 accessors remain IPv4-only:

```python
network.getPrefix()
interface.getAddress()
```

Use the explicit IPv6 accessors for dual-stack state:

```python
network.hasIpv6Prefix()
network.getIpv6Prefix()
interface.hasIpv6Address()
interface.getIpv6Address()
```

## Per-Network Control

With global IPv6 enabled, local AS networks and IX peering LANs use automatic
IPv6 prefixes by default.

```python
as150.createNetwork("net0")
base.createInternetExchange(100)
```

Users can override or disable IPv6 on a specific network:

```python
as150.createNetwork("explicit", ipv6Prefix="2000:0:150::/64")
as150.createNetwork("v4only", ipv6Prefix=None)
base.createInternetExchange(200, ipv6Prefix="2000:8:0:200::/64")
```

## Per-Interface Control

`joinNetwork()` also accepts an IPv6 address intent. The default is `"auto"`.
Use `None` for an IPv4-only attachment on a dual-stack network, or provide an
explicit IPv6 address.

```python
as150.createHost("web").joinNetwork("net0")
as150.createHost("legacy").joinNetwork("net0", ipv6Address=None)
as150.createHost("fixed").joinNetwork("net0", ipv6Address="2000:0:150::71")
```

Explicit IPv4 and IPv6 interface address literals are normalized before being
stored. Padded values and bracketed IPv6 literals such as
`ipv6Address="[2000:0:150::71]"` are accepted, while `getAddress()` remains the
IPv4 accessor and `getIpv6Address()` remains the IPv6 accessor.

## Routing

The routing behavior described here is the target control-plane migration
contract. It is not claimed as fully re-landed on `development2` until the
Routing, ExaBGP, Looking Glass, examples, and runtime checks land in follow-up
PRs.

The routing layers remain intent based. `Ebgp`, `Ibgp`, and `Ospf` record
peering and interface intent. The `Routing` layer renders address-family
specific BIRD or FRR configuration.

When IPv6 is present:

- BIRD receives IPv6 routing tables and IPv6 BGP/OSPFv3 blocks as needed;
- FRR receives `address-family ipv6 unicast` and OSPFv3 configuration as
  needed;
- OSPFv2 and OSPFv3 stay separate;
- ExaBGP can announce IPv6 prefixes when the speaker and peer share IPv6 on the
  peering network;
- Looking Glass can report IPv4 and IPv6 route-state separately.

Manual BGP session intent accepts the same address-family aliases and address
literal normalization as services. Padded IPv4/IPv6 values and bracketed IPv6
literals are canonicalized before BIRD/FRR/ExaBGP config is rendered.

See [routing.md](./routing.md) for backend selection and
[IPv6 Addressing and Control Plane Design](../designs/ipv6-control-plane-design.md)
for the design boundary.

## Docker Compiler

The Docker compiler emits IPv6 runtime configuration only for networks that
have IPv6 prefixes. Dual-stack networks include `enable_ipv6: true`, IPv6 IPAM,
and service-level `ipv6_address` entries only for interfaces carrying IPv6
state. Interfaces that opt out with `ipv6Address=None` remain IPv4-only even on
a dual-stack service network. Custom container and Internet Map attachments
follow the same explicit-address rule: a dual-stack network does not imply a
static per-container `ipv6_address` unless `ipv6_address` is provided.
Explicit static `ip_address` and `ipv6_address` values on those attachment
APIs are normalized before compose and metadata output, including padded values
and bracketed IPv6 literals. The IPv4 field rejects IPv6 literals, and the IPv6
field rejects IPv4 literals.

For `selfManagedNetwork=True`, the compiler uses dummy IPv6 subnets and rewrites
container addresses at startup, matching the existing IPv4 self-managed network
behavior.

## Repository Readiness

IPv6 support is being expanded as a repository-level contract. This PR lands
the Docker compiler portion of that contract on top of the helper and topology
foundation. Later PRs must update this section as each feature is implemented
and verified on `development2`.

Target categories:

- landed: core addressing, optional topology IPv6 state, Docker dual-stack
  networks, optional IPv6 service network, and custom container / Internet Map
  static IPv6 attachment output;
- pending control-plane target: BIRD/FRR BGP, OSPFv3, ExaBGP, Looking Glass;
- pending DNS baseline target: DNS authoritative and reverse records, and
  `/etc/hosts`;
- compatible but not fully migrated: DNS cache, Domain Registrar dynamic A/AAAA
  updates, Web/CA, traffic wrappers, Kubo bootstrap endpoints, Botnet
  C2/dropper endpoint formatting, Monero seed/RPC endpoint formatting,
  Chainlink generated URL formatting, Ethereum faucet/utility, faucet-user,
  and bootnode/beacon helper HTTP URL formatting;
- IPv4-first pending design: Email; Cymru IP origin ASN mapping remains
  IPv4-only with normalized IPv4 prefix inputs; Tor remains IPv4-first with
  directory-authority downloader and hidden-service backend target formatting
  guarded by shared endpoint helpers;
- separate design required: SCION underlay, cross-connect, DHCPv6, MPLS/EVPN,
  real-world connectivity, OpenVPN, k8s, internetmap2.

Reverse DNS preserves existing IPv4 `in-addr.arpa.` PTR generation. When
interfaces carry IPv6 state, `ReverseDomainNameService` also populates
`ip6.arpa.` PTR records; IPv4-only topologies do not create the IPv6 reverse
zone. Manual DNS A/AAAA records use shared normalization and reject mismatched
address families, such as an A record with an IPv6 literal or an AAAA record
with an IPv4 literal. Manual and imported authoritative master-IP zone keys are
normalized to canonical DNS zone names before slave or cache forwarder
configuration is generated. Authoritative zone creation and hosting APIs use
the same canonical zone-name normalization, so padded zone inputs do not change
generated BIND zone names or zone file paths.

`EtcHosts` writes IPv4 and IPv6 entries for node interfaces that carry those
addresses. Service-network Bridge addresses are intentionally kept so
service-only nodes remain resolvable. IX peering addresses are skipped, matching
the existing rule that peering LAN addresses should not become host aliases.

Domain Registrar dynamic updates preserve A as the default record type. The
registration page also allows users to explicitly choose AAAA records for IPv6
addresses, and rejects submitted IP addresses whose family does not match the
selected A/AAAA record type. The registrar still follows the existing
TLD/master-DNS placement model; this is not a broader DNS workflow redesign.

DNS cache forward zones preserve IPv4 defaults. When a forward zone falls back
to authoritative zone-server bindings instead of explicit master IPs, the cache
normalizes the forward-zone name, uses the same node-address helpers as
authoritative DNS, and adds IPv6 forwarders only for zone-server nodes that
actually have IPv6 state. Explicit resolver nameserver inputs, including
`Base`, AS, node, `ResolvConfHook`, and `ResolvConfHookByAs` paths, normalize
padded IPv4/IPv6 literals before writing `resolv.conf` commands.

Traffic generators preserve existing raw receiver target lists. For explicit
address-family selection, use `addReceiverVnodes(..., family=AddressFamily.IPv6)`
to resolve receiver virtual nodes through the shared node-address helpers. The
generated reachability probe uses IPv6 ping for IPv6 literal targets while
preserving the existing IPv4/hostname ping path. Individual traffic tools still
need runtime validation before a full IPv6 support claim.

Kubo bootstrap endpoints preserve IPv4 defaults and select bootstrap node
addresses through the shared Local-network-first helper, falling back to the
service network when a bootstrap node has no Local interface. The generated
bootstrap helper probes use the same address family as the selected bootstrap
endpoints. The legacy Kubo `getIP` utility follows the same rule: IPv4 remains
the default, and callers may explicitly request IPv6. For explicit IPv6
bootstrap RPC URLs and peer multiaddrs, use
`KuboService(bootstrapAddressFamily=AddressFamily.IPv6)` or
`setBootstrapAddressFamily(AddressFamily.IPv6)`.

Botnet C2/dropper endpoints preserve the existing first-interface IPv4
default. In a dual-stack emulation, call
`BotnetServer.setEndpointAddressFamily(AddressFamily.IPv6)` to generate a
bracketed IPv6 dropper URL for binding-based clients. DGA dropper runners
preserve preformatted HTTP(S) URLs and existing `host:port` authority outputs
without adding their own host/path wrapper, while DGA and legacy non-DGA
fallbacks bracket bare IPv6 host arguments if no preformatted URL is provided.
BYOB client/server runtime behavior and DGA endpoints have not been validated
as full IPv6 support.

Looking Glass route-state observation remains separate from ExaBGP event
dashboards. Its frontend-to-proxy traffic preserves the IPv4 default. In a
dual-stack emulation, call
`BgpLookingGlassServer.setProxyAddressFamily(AddressFamily.IPv6)` to generate
bracketed IPv6 proxy URLs for the frontend; this selects only the management
endpoint family, not the set of route families queried from the router.

CA certificate installation filters accept IPv4 and IPv6 address/prefix
selectors. For example, `installCACert(Filter(ipv6="2000:0:3::72"))` installs
the root CA certificate only on nodes with that IPv6 address; CA address and
prefix matching, including helper utilities, normalize padded and bracketed
IPv6 literals through the shared address helpers. CA domain inputs trim DNS
names and normalize padded or bracketed IPv4/IPv6 endpoint literals before Web
HTTPS ACME directory URLs use shared URL helpers, but Web HTTPS and ACME runtime
behavior remain compatible and not fully migrated.

Monero seed and full-node RPC endpoint lists preserve IPv4 defaults and select
node addresses through the shared Local-network-first helper, falling back to
the service network when a node has no Local interface. In a dual-stack
emulation, call `blockchain.setEndpointAddressFamily(AddressFamily.IPv6)` to
generate bracketed IPv6 `host:port` endpoints for those lists; generated seed
wait probes use the same endpoint address family. Monero daemon listener
behavior has not been runtime-validated as full IPv6 support.

Chainlink generated URLs preserve IPv4 defaults and select referenced Ethereum,
faucet, and utility endpoints through the shared Local-network-first helper,
falling back to the service network when a referenced node has no Local
interface. In a dual-stack emulation, call
`chainlink.setEndpointAddressFamily(AddressFamily.IPv6)` or pass
`endpointAddressFamily=AddressFamily.IPv6` to generate bracketed IPv6 RPC,
faucet, utility, and WebSocket/HTTP node URLs. The underlying Ethereum and
Chainlink runtime path has not been validated as full IPv6 support.

Ethereum faucet/utility generated URLs, faucet-user request URLs, faucet
funding-script server URLs, and bootnode/beacon helper fetch URLs preserve IPv4
defaults and select referenced nodes through the shared Local-network-first
helper, falling back to the service network when a referenced node has no Local
interface. In a dual-stack emulation, call
`blockchain.setEndpointAddressFamily(AddressFamily.IPv6)` or
`faucetUserService.setEndpointAddressFamily(AddressFamily.IPv6)` to generate
bracketed IPv6 HTTP RPC, faucet, enode-fetch, beacon-identity, and beacon-setup
helper URLs. The Lighthouse validator beacon-node URL template accepts a
preformatted helper URL so IPv6 literals are bracketed when supplied, but the
current PoS validator install path remains IPv4-first. Ethereum ENR content,
peer discovery, bootnode bind/listener, and daemon runtime behavior have not
been runtime-validated as full IPv6 support.

Tor remains IPv4-first. Directory-authority fingerprint downloader URLs and
hidden-service backend targets use shared endpoint helpers so explicit IPv6
literals are normalized and bracketed correctly without bracketing DNS names.
Hidden-service backends linked with `linkByVnode(...,
family=AddressFamily.IPv6)` resolve through the shared Local-network-first
helper and fall back to the service network when the backend node has no Local
interface. If no preformatted hidden-service target is provided, the entrypoint
fallback brackets bare IPv6 `TOR_HS_ADDR` values before writing
`HiddenServicePort`. Tor bind/listener, directory authority, consensus, and
daemon runtime behavior still require a separate migration.

See
[Repository-Wide IPv6 Readiness Design](../designs/ipv6-repository-readiness-design.md)
for the migration contract.

## Service Author Rules

Keep `getAddress()` and `getPrefix()` as IPv4-only APIs. A service that needs
IPv6 should use `hasIpv6Address()`, `getIpv6Address()`, or the shared helpers in
`seedemu.core`:

```python
from seedemu.core import (
    AddressFamily,
    getInterfaceAddress,
    getNodeAddress,
    getNodeAddresses,
    getNodePreferredAddress,
    nodeHasAddress,
    nodeHasAddressInPrefix,
    formatHost,
    formatHostPort,
    formatUrl,
    formatMultiaddr,
    normalizeAddressList,
    normalizePrefix,
    normalizeAddressRecord,
)
```

Use `formatHost()`, `formatHostPort()`, or `formatUrl()` instead of manually
concatenating host strings or `host:port`, because IPv6 literals need brackets
in URLs. Use `formatUrl()` with separate host and port arguments when possible;
if a legacy path already passes a bracketed IPv6 authority such as
`[2000::1]:8443`, the helper preserves the authority and canonicalizes the
literal. When a caller also supplies a separate port, that separate port is
used instead of any port embedded in a legacy IPv4, DNS-name, or bracketed IPv6
authority. Padded explicit port values are trimmed before `host:port`, URL, or
multiaddr output is generated. Malformed bracketed IPv6 authorities, such as
`[2000::1]:bad`, are rejected instead of being emitted as ambiguous endpoints.
Explicit port arguments must be non-empty decimal strings, so invalid
socket-like endpoints fail before a service writes them into config.
URL paths that start with `?` or `#` are treated as query or fragment
components instead of being rewritten as path segments. Use
`formatMultiaddr()` when generating IPFS/libp2p multiaddrs. Use
`getNodeAddress()`, `getNodePreferredAddress()`, or `getNodeAddresses()` when a
service needs stable Local-network-first address selection with service-network
fallback. Use `nodeHasAddress()` and `nodeHasAddressInPrefix()` when matching a
node against IPv4 or IPv6 address/prefix selectors. Pass an explicit
`AddressFamily` to those match helpers when implementing family-specific
selectors such as `Filter(ipv4=...)` or `Filter(ipv6Prefix=...)`, so
wrong-family literals do not accidentally match. Use
`normalizeAddressList()` when a service accepts a list of IPv4/IPv6 literals,
including bracketed IPv6 address literals. Use `normalizePrefix()` when a
service accepts IPv4/IPv6 CIDR prefixes, and use `normalizeAddressRecord()` when
a service accepts DNS-style manual A/AAAA records and needs canonical IPv4/IPv6
literals without changing other record types. `normalizeAddressRecord()` also
rejects A/AAAA records whose address literal does not match the requested
record family.

Do not claim service-level IPv6 support until the service has a minimal IPv6 or
dual-stack example and a regression check showing that old IPv4 behavior is
unchanged.
