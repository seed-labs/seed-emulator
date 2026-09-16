# B02a: Hidden-primary TLD DNS

This scenario extends B02's DNS Internet with independent Namingo Registrar and
Registry nodes plus a Namingo-compatible `.com` authoritative topology. The
removed Agent Registrar, provisioning API, and managed customer-zone services
are not part of this example.

- Namingo Registrar (`10.150.0.73`) runs only the upstream WHOIS/RDAP
  components. Its Loom backend uses a read-only connection to the Loom
  database; this node does not install or run an EPP client.
- Loom (`10.150.0.74`) is the customer-facing Registrar web application. Its
  source is pinned to commit `212410852c821b14bfc9603043ab0a61632bd576`, and
  its `.com` provider connects directly to the Namingo Registry over mutually
  authenticated EPP/TLS. The discovery label publishes
  `http://10.150.0.74:80` and an opaque `b02a.loom.admin` credential reference.
- Namingo Registry (`10.154.0.73`) runs the upstream EPP, WHOIS, and RDAP services for `.com`,
  provisions the `seedemu` registrar account, and restricts that account to the
  Loom node address.
- Loom connects to `epp.registry.com:700` with mutual TLS, reads the active
  `.com` provider from its own database, runs a periodic domain check through
  Loom's native EPP path, and writes
  `/run/seedemu-loom-epp-health.json` atomically.
- `epp.registry.com`, `whois.registrar.com`, `rdap.registrar.com`,
  `whois.registry.com`, and `rdap.registry.com` are
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
  `dns.authoritative_find` with AS150 `host_1` to discover the pair, then uses
  `dns.configure` through that source to provision the allowlisted
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
Loom-originated mutual-TLS EPP login/check/logout, the Namingo WHOIS/RDAP
processes and read-only Loom database connection, authenticated Zone Writer
delivery, serial advancement and rollback rejection on COM-A, B/C transfer
convergence, service-name resolution, BIND ACLs, omission of COM-A from the
root zone, and an inherited DNS resolution path.

`NamingoRegistrarService` is not a customer billing portal; Loom owns customer
accounts, orders, payment, and all EPP provisioning. Namingo Registrar only
completes Loom with WHOIS/RDAP service.

The Loom health probe is SeedEmu integration code and uses Loom's native EPP
helper. Registry-side EPP processing remains an unmodified Namingo component.
The SSH zone receiver/publisher, fixed
simulation credentials, and removal of Namingo's untouched `.test` and
`.com.test` sample rows during bootstrap are also SeedEmu integration code.
The compact EC TLS and Ed25519 SSH credentials are kept as one-line constants
in `domain_registration.py`. Production deployments must inject separately
managed secrets instead.
