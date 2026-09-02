# B02a: Hidden-primary TLD DNS

This scenario extends B02's DNS Internet with independent Namingo Registrar and
Registry nodes plus a Namingo-compatible `.com` authoritative topology. The
removed Agent Registrar, provisioning API, and managed customer-zone services
are not part of this example.

- Namingo Registrar (`10.150.0.73`) runs the upstream Registrar WHOIS/RDAP
  components with a custom backend placeholder.
- Namingo Registry (`10.154.0.73`) runs the upstream EPP service for `.com`,
  provisions the `seedemu` registrar account, and restricts that account to the
  Registrar node address.
- `epp.registry.com`, `whois.registrar.com`, and `rdap.registrar.com` are
  published through the `.com` authoritative infrastructure.

- COM-A (`10.151.0.71`) is the hidden primary. It is absent from the root
  delegation, rejects public queries and RFC 2136 updates, and permits zone
  transfer only with the dedicated TSIG key.
- COM-B (`10.152.0.71`) is a public secondary inherited from B02.
- COM-C (`10.153.0.73`) is an additional public secondary created by B02a.
- COM-B and COM-C receive NOTIFY and AXFR/IXFR only from COM-A with TSIG.
- Ordinary DNS containers and the inherited B02 zones keep their original
  behavior.

Compile the example from the repository root:

```sh
.venv/bin/python examples/internet/B02a_domain_registration/domain_registration.py
```

Run the complete Docker lifecycle:

```sh
.venv/bin/python seedemu/testing/cli.py all \
  examples/internet/B02a_domain_registration/example.yaml \
  --artifact-dir ci-artifacts/b02a-tld-dns
```

The runtime test verifies the Namingo processes and generated configuration,
service-name resolution, BIND ACLs, TSIG-protected transfer relationship,
COM-B/COM-C convergence, omission of COM-A from the root zone, and an inherited
DNS resolution path.

The current `NamingoRegistrarService` provides upstream Registrar WHOIS/RDAP
components; it is not yet an EPP client or customer billing portal. Registry
Zone Writer delivery to the separate COM-A node remains a distinct integration
step.
