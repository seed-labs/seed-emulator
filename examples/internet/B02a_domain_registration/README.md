# B02a: Hidden-primary TLD DNS

This scenario extends B02's DNS Internet with independent Namingo Registrar and
Registry nodes plus a Namingo-compatible `.com` authoritative topology. The
removed Agent Registrar, provisioning API, and managed customer-zone services
are not part of this example.

- Namingo Registrar (`10.150.0.73`) runs the upstream Registrar WHOIS/RDAP
  components with a custom backend placeholder and the official Namingo EPP
  Client pinned to `v1.1.22`.
- Loom (`10.150.0.74`) is the customer-facing Registrar web application. Its
  source is pinned to commit `212410852c821b14bfc9603043ab0a61632bd576`, and
  its `.com` provider connects directly to the Namingo Registry over mutually
  authenticated EPP/TLS. The discovery label publishes
  `http://10.150.0.74:80` and an opaque `b02a.loom.admin` credential reference.
- Namingo Registry (`10.154.0.73`) runs the upstream EPP service for `.com`,
  provisions the `seedemu` registrar account, and restricts that account to the
  Registrar node address.
- Registrar connects to `epp.registry.com:700` with verified TLS 1.2, validates
  the Registry certificate against the scenario CA, logs in with its EPP
  credentials, runs a domain check, and logs out. The background health probe
  writes `/run/seedemu-epp-health.json`; `seedemu-epp-client check NAME` exposes
  the same authenticated path for interactive checks.
- `epp.registry.com`, `whois.registrar.com`, and `rdap.registrar.com` are
  published through the `.com` authoritative infrastructure.

- COM-A (`10.151.0.71`) is the hidden primary. It is absent from the root
  delegation, rejects public queries and RFC 2136 updates, and permits zone
  transfer only with the dedicated TSIG key.
- COM-B (`10.152.0.71`) is a public secondary inherited from B02.
- COM-C (`10.153.0.73`) is an additional public secondary created by B02a.
- COM-B and COM-C receive NOTIFY and AXFR/IXFR only from COM-A with TSIG.
- Registry Zone Writer generates `/var/lib/bind/com.zone` and publishes it to
  COM-A over SSH. COM-A pins its SSH host key, restricts the publisher key to
  source `10.154.0.73` and one forced command, validates the candidate with
  `named-checkzone`, rejects SOA serial rollback, atomically replaces the zone,
  and reloads BIND. The SSH publisher key is separate from transfer TSIG.
- Ordinary DNS containers and the inherited B02 zones keep their original
  behavior.

- AS160 advertises the dedicated `11.160.0.0/24` owner DNS network.
  `owner-dns-primary` (`11.160.0.53`) and `owner-dns-secondary`
  (`11.160.0.54`) form a `DomainNameService` source-owned authoritative DNS pair. The Agent uses
  `dns.configure` through AS150 `host_1` to provision the allowlisted
  `example.com` zone and maintain its records. A deployment-local SSH identity
  is stored only in that source. Both DNS nodes enforce the public key, the
  source address, a forced command, and the zone allowlist. Runtime updates use
  an update TSIG while Primary-to-Secondary transfer uses a separate TSIG.

Compile the example from the repository root:

```sh
.venv/bin/python examples/internet/B02a_domain_registration/domain_registration.py
```

Run the complete Docker lifecycle:

```sh
.venv/bin/python seedemu/testing/cli.py all \
  examples/internet/B02a_domain_registration/example.yaml \
  --artifact-dir ci-artifacts/b02a-namingo-e2e
```

The `all` command removes the previous generated `output`, compiles and builds
the emulation, starts it, runs readiness and runtime checks, then tears it down.
The JSON summaries and command logs are retained under the artifact directory.

The runtime test verifies the Loom web page, database/provider initialization,
Loom-originated mutual-TLS EPP login/check/logout, the Namingo processes;
mutual-TLS EPP login, check,
contact create, domain create, host create, and domain nameserver update; the
authenticated Zone Writer delivery; serial advancement and rollback rejection
on COM-A; B/C transfer convergence; public delegation and glue; service-name
resolution; BIND ACLs; omission of COM-A from the root zone; and an inherited
DNS resolution path. Negative checks also require rejection of a wrong EPP
password, an untrusted client certificate, and an unauthorized SSH key.

`NamingoRegistrarService` is still not itself a customer billing portal; Loom
provides that customer-facing role. The supporting service's EPP client remains
an authenticated provisioning interface and exposes Namingo's native `contactCreate`,
`domainCreate`, and `domainUpdateNS` operations as `contact-create`,
`host-create`, `domain-create`, and `domain-update`. Mutating operations accept
one JSON object as the second command-line argument. For example:

```sh
seedemu-epp-client host-create \
  '{"hostname":"ns1.example.com","ipaddress":"11.160.0.53"}'
seedemu-epp-client domain-update \
  '{"domainname":"example.com","nameservers":["ns1.example.com","ns2.example.com"]}'
```

Namingo Registry currently rejects RFC 1918 host addresses in `host:create`
through its upstream PHP validation. Consequently, the runtime registration
uses documentation-only public-looking glue addresses `11.150.0.71` and
`11.150.0.73`; these are registry data, not addresses assigned to SeedEmu
containers. Using `10.150.x.x` would fail before zone publication unless the
upstream Namingo validation policy is changed.

The command wrapper and its input validation are SeedEmu integration code; the
EPP client methods and the Registry-side EPP processing are unmodified Namingo
open-source components. The SSH zone receiver/publisher, health probe, fixed
simulation credentials, and removal of Namingo's untouched `.test` and
`.com.test` sample rows during bootstrap are also SeedEmu integration code.
The compact EC TLS and Ed25519 SSH credentials are kept as one-line constants
in `domain_registration.py`. Production deployments must inject separately
managed secrets instead.
