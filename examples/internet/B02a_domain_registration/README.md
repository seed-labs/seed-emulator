# B02a: Dynamic Domain Registration

This scenario extends B02 without modifying B02 itself. It adds three dedicated
nodes for stage 2:

- a registrar/control node in AS150;
- a managed authoritative DNS master at `10.161.0.53` in AS161;
- a managed authoritative DNS secondary at `10.162.0.53` in AS162.

The two authoritative servers host `seedemu-dns.net`. Their resolvable names,
`ns1.seedemu-dns.net` and `ns2.seedemu-dns.net`, are included in the registrar's
default nameserver policy. The existing `DomainRegistrarService` is not changed
or used by this scenario.

Domains are not preloaded into an inventory. A syntactically valid, unreserved
`.com` name is available when it is absent from the registrar database. The
purchase transaction atomically claims that name, creates an idempotent order,
and records a pending DNS provisioning event.

Compile the example from the repository root:

```sh
python3 examples/internet/B02a_domain_registration/domain_registration.py
```

Run its complete test lifecycle with:

```sh
python3 seedemu/testing/cli.py all \
  examples/internet/B02a_domain_registration/example.yaml \
  --artifact-dir ci-artifacts/b02a-domain-registration
```

The offline API listens on port 8080 and stores its runtime state in SQLite at
`/var/lib/seedemu-agent-registrar/registrar.db`. A purchase atomically reserves
a domain, creates an idempotent order, and writes a pending DNS provisioning
event. No price fields are maintained.

The registrar outbox is connected to the provisioner on port `8053`. For each
purchase, `POST /v1/zones` configures the managed secondary, asks the master's
local daemon on port `8054` to atomically create and validate the zone, waits
for TSIG-protected AXFR, publishes the `.com` delegation, and marks the order
active only after both authoritative servers and both `.com` servers agree.

Parent updates and managed-zone updates use separate TSIG keys. The B02a build
replaces the inherited permissive update ACL on the `.com` master in the
generated B02a container only. The managed master uses another update key and
a dedicated transfer key for NOTIFY/AXFR. PUT and DELETE record requests follow
the same outbox path and complete after master/secondary convergence.
