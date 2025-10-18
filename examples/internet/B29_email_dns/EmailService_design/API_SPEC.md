# EmailService API Specification (Design)

Version: 0.1 (plan-only)

## Objectives
- Provide a small, composable API to attach email providers to a SEED Emulator Docker compilation.
- Support two delivery modes:
  - DNS-first (MX lookup; internet-realistic)
  - Transport-map (explicit next-hops; deterministic)
- Keep examples simple, but allow higher integration (DNS authorities, caches, Roundcube, verification) as optional add-ons.

## Terminology
- Provider: one email server instance (domain + container) running `docker-mailserver`.
- Compiler: `seedemu.compiler.Docker` instance consumed by `attach_to_docker()`.

## Constructor

```python
class EmailService:
    def __init__(
        self,
        platform: str = "linux/amd64",
        mode: str = "transport",  # 'transport' | 'dns'
        dns_nameserver: Optional[str] = None,
    ) -> None:
        ...
```

- `platform`: Docker platform string (e.g., `linux/amd64`, `linux/arm64`).
- `mode`: delivery mode, `transport` or `dns`.
- `dns_nameserver`: default resolver IP to inject into containers when `mode='dns'`.

## Provider registration

```python
EmailService.add_provider(
    domain: str,
    asn: int,
    ip: str,
    gateway: str,
    net: str = "net0",
    hostname: str = "mail",
    name: Optional[str] = None,
    ports: Optional[Dict[str, str]] = None,
    dns: Optional[str] = None,
) -> EmailService
```

- `domain`: Fully qualified domain (e.g., `gmail.com`).
- `asn`: AS where the provider container will be attached by the compiler.
- `ip`: IP address of the container on the AS internal network.
- `gateway`: default gateway for the container (`router0` on that AS network).
- `net`: network name inside the AS (typically `net0`).
- `hostname`: mail host (e.g., `mail`).
- `name`: container and compose service name. If not provided, derived from `domain`.
- `ports`: per-mode port exposure dictionary:
  - transport mode: expects `smtp`, `submission`, `imap`, `imaps`.
  - dns mode: expects `smtp`, `imap` (only these two are exposed).
  - unspecified keys use safe defaults.
- `dns`: per-provider resolver IP override; if omitted, uses `dns_nameserver` from constructor.

Notes:
- Idempotency: multiple `add_provider()` calls append distinct entries; it is caller’s responsibility to avoid duplicate domains.
- Validation: the API does minimal validation; the user script should ensure IPs/networks/gateways are consistent with the Base topology.

## Compose attachment

```python
EmailService.attach_to_docker(docker) -> None
```

- Generates compose entries for each registered provider and attaches them to the Docker compiler with `docker.attachCustomContainer(...)`.
- Behavior by mode:
  - `transport`:
    - Generates `/etc/postfix/transport` mapping all other providers’ domains to their IPs via `smtp:[ip]:25`.
    - Runs `postmap` and sets `transport_maps = hash:/etc/postfix/transport`.
  - `dns`:
    - Injects a `dns:` block into compose when a resolver is provided (provider override or default).
    - Configures:
      - `postconf -e 'relayhost ='`
      - `postconf -e 'smtp_host_lookup = dns'`
      - `postconf -e 'smtp_dns_support_level = enabled'`

## Accessors

```python
EmailService.get_providers() -> List[Dict]
```

Returns a shallow copy of provider dicts registered via `add_provider()`.

## Integration hooks (future; design only)

The following methods are part of this design spec; not yet implemented in the current codebase.

```python
EmailService.add_domain_zone(domain: str, records: List[str], asn: int) -> EmailService
```
- Declare and attach an authoritative DNS zone for `domain` in `asn`.
- Intended to wrap `DomainNameService` to simplify demo scripts (authority + mail colocated).

```python
EmailService.add_cache(
    asn: int,
    forwarders: List[Tuple[str, str]],  # e.g., [("gmail.com.", "ns-gmail-com"), ...]
    authoritative_for: Optional[List[str]] = None,
) -> EmailService
```
- Declare a local DNS cache in the AS with forwarders for specific zones.
- If `authoritative_for` is provided, configure those zones as master locally to isolate from routing issues.

```python
EmailService.attach_roundcube(port: int = 8082, providers: Optional[List[str]] = None) -> EmailService
```
- Attach a Roundcube webmail stack pre-wired to the registered providers.

```python
EmailService.verify(plan: List[str]) -> Dict
```
- Execute a standardized verification plan (e.g., `["dns","bgp","smtp"]`) and return a structured report.

## Error handling
- API is intentionally thin; errors in network reachability, DNS, or BGP surface at runtime. The verification hook (future) should help preflight.
- When `mode='dns'`, ensure at least one DNS resolver is set per provider (global or per-provider) if you expect external MX lookups.

## Examples

DNS-first (B29-like):

```python
svc = EmailService(platform="linux/arm64", mode="dns", dns_nameserver="10.150.0.53")
svc.add_provider(domain="qq.com", asn=200, ip="10.200.0.10", gateway="10.200.0.254", ports={"smtp":"2200","imap":"1400"}, dns="10.200.0.53")
svc.add_provider(domain="gmail.com", asn=202, ip="10.202.0.10", gateway="10.202.0.254", ports={"smtp":"2202","imap":"1402"}, dns="10.202.0.53")
svc.attach_to_docker(docker)
```

Transport-map:

```python
svc = EmailService(platform="linux/amd64", mode="transport")
svc.add_provider(domain="seedemail.net", asn=150, ip="10.150.0.10", gateway="10.150.0.254",
                 ports={"smtp":"2525","submission":"5870","imap":"1430","imaps":"9930"})
svc.add_provider(domain="corp.local", asn=151, ip="10.151.0.10", gateway="10.151.0.254",
                 ports={"smtp":"2526","submission":"5871","imap":"1431","imaps":"9931"})
svc.attach_to_docker(docker)
```

## Invariants and expectations
- Compose entries set container default route via the given `gateway` (`ip route add default via ...`).
- Volumes are created per container to persist state; reruns may require cleanup of `output/` if permission issues occur.
- The caller is responsible for creating the underlying topology (AS, networks, routers) and DNS authority/caches unless `add_domain_zone`/`add_cache` extensions are used.

## Compatibility and portability
- Uses `mailserver/docker-mailserver:edge`; pin a specific tag for reproducible classroom runs.
- Platform strings must match Docker engine capabilities on host.

## Security and production caveats
- This API configures plaintext ports for pedagogy; do not deploy in production.
- DKIM/DMARC/SPF are not hardened by default; keep as explicit demo artifacts only.
