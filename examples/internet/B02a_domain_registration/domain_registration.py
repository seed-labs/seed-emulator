#!/usr/bin/env python3
# encoding: utf-8

"""Build B02a with Namingo Registrar, Registry, and authoritative TLD DNS."""

from __future__ import annotations

import argparse
import base64
import secrets
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.internet.B02_mini_internet_with_dns import mini_internet_with_dns
from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base
from seedemu.services import (
    DomainNameService,
    EppTlsCredentials,
    LoomRegistrarService,
    NamingoRegistrarService,
    NamingoRegistryService,
    RegistrarIdentity,
)


COM_TRANSFER_KEY_NAME = "com-transfer"
COM_HIDDEN_PRIMARY_IP = "10.151.0.71"
COM_PUBLIC_SECONDARY_IPS = ["10.152.0.71", "10.153.0.73"]
SOURCE_IP = "10.150.0.72"
REGISTRAR_IP = "10.150.0.73"
LOOM_IP = "10.150.0.74"
REGISTRY_IP = "10.154.0.73"
OWNER_DNS_NETWORK = "owner-dns-net"
OWNER_DNS_PREFIX = "11.160.0.0/24"
OWNER_DNS_ROUTER_IP = "11.160.0.254"
OWNER_DNS_PRIMARY_IP = "11.160.0.53"
OWNER_DNS_SECONDARY_IP = "11.160.0.54"
OWNER_DNS_SERVICE_ID = "b02a.source-owned-dns"
LOOM_COMMIT = "212410852c821b14bfc9603043ab0a61632bd576"
REGISTRY_EPP_HOSTNAME = "epp.registry.com"
REGISTRAR_EPP_CLID = "seedemu"
LOOM_RDDS_DB_USER = "loom_rdds"


EPP_PASSWORD = "seedemu-epp"
LOOM_DATABASE_PASSWORD = "seedemu-loom"
RDDS_DATABASE_PASSWORD = "seedemu-loom-rdds"
LOOM_WEBAUTHN_SECRET = "seedemu-loom-webauthn"

COM_SERVICE_RECORDS = [
    ("epp.registry", "A", [REGISTRY_IP]),
    ("whois.registrar", "A", [REGISTRAR_IP]),
    ("rdap.registrar", "A", [REGISTRAR_IP]),
    ("whois.registry", "A", [REGISTRY_IP]),
    ("rdap.registry", "A", [REGISTRY_IP]),
]
COM_ZONE_WRITER_RECORDS = [
    ("ns1", "A", [COM_PUBLIC_SECONDARY_IPS[0]]),
    ("ns2", "A", [COM_PUBLIC_SECONDARY_IPS[1]]),
    *COM_SERVICE_RECORDS,
    ("twitter", "NS", ["ns1.twitter.com."]),
    ("ns1.twitter", "A", ["10.161.0.71"]),
    ("google", "NS", ["ns1.google.com."]),
    ("ns1.google", "A", ["10.162.0.71"]),
]


def configure_com_authoritative_topology(
    dns: DomainNameService,
    transfer_key_secret: str,
    zone_publisher_public_key: str,
    primary_host_private_key: str,
    primary_host_public_key: str,
) -> None:
    """Configure A-com as hidden primary and B/C-com as public secondaries."""
    targets = dns.getPendingTargets()
    a_com = targets["a-com-server"]
    b_com = targets["b-com-server"]

    a_com.setHiddenPrimary().setTransferKey(
        COM_TRANSFER_KEY_NAME, transfer_key_secret
    ).enableZoneFileReceiver(
        "com.",
        REGISTRY_IP,
        zone_publisher_public_key,
        primary_host_private_key,
        primary_host_public_key,
    )
    for secondary_ip in COM_PUBLIC_SECONDARY_IPS:
        a_com.addTransferTarget(secondary_ip)

    b_com.setSecondary(COM_HIDDEN_PRIMARY_IP).setTransferKey(
        COM_TRANSFER_KEY_NAME, transfer_key_secret
    )

    c_com = dns.install("c-com-server").addZone("com.")
    c_com.setSecondary(COM_HIDDEN_PRIMARY_IP).setTransferKey(
        COM_TRANSFER_KEY_NAME, transfer_key_secret
    )


def create_registration_nodes(base: Base) -> None:
    """Create the physical Registrar, Registry, and Loom hosts."""
    base.getAutonomousSystem(150).createHost("namingo-registrar").joinNetwork(
        "net0", address=REGISTRAR_IP
    ).setDisplayName("Namingo Registrar")
    base.getAutonomousSystem(154).createHost("namingo-registry").joinNetwork(
        "net0", address=REGISTRY_IP
    ).setDisplayName("Namingo Registry")
    base.getAutonomousSystem(150).createHost("loom-registrar").joinNetwork(
        "net0", address=LOOM_IP
    ).setDisplayName("Loom Registrar Frontend")


def publish_initial_registration_records(dns: DomainNameService) -> None:
    """Publish endpoints needed before Registry Zone Writer takes ownership."""
    com_zone = dns.getZone("com.")
    # A low deterministic initial serial lets the first Zone Writer snapshot
    # pass the receiver's anti-rollback check.
    if not com_zone.findRecords("SOA"):
        com_zone.addRecord("@ SOA ns1.com. hostmaster.com. 1 900 900 1800 60")
    for name, record_type, parameters in COM_SERVICE_RECORDS:
        com_zone.addRecord("{} {} {}".format(
            name, record_type, " ".join(parameters)
        ))


def bind_registration_services(
    emu: Emulator,
    registrar: NamingoRegistrarService,
    registry: NamingoRegistryService,
    loom: LoomRegistrarService,
) -> None:
    """Bind registration vnodes and register their service layers."""
    for vnode, asn, node_name in [
        ("namingo-registrar", 150, "namingo-registrar"),
        ("namingo-registry", 154, "namingo-registry"),
        ("loom-registrar", 150, "loom-registrar"),
    ]:
        emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName=node_name)))
    emu.addLayer(registrar)
    emu.addLayer(registry)
    emu.addLayer(loom)


def configure_namingo_services(
    emu: Emulator,
    base: Base,
    dns: DomainNameService,
    epp_tls: EppTlsCredentials,
    zone_publisher_private_key: str,
    primary_host_public_key: str,
) -> None:
    """Add independent Namingo Registrar and Registry nodes to B02a."""
    identity = RegistrarIdentity(
        name="SeedEmu Namingo Registrar",
        company_name="SeedEmu Registrar",
        domain="registrar.com",
        iana_id=9999,
        url="http://registrar.com",
        whois_host="whois.registrar.com",
        rdap_url="http://rdap.registrar.com",
        email="registrar@registrar.com",
        phone="+1.5550100",
        address="150 Simulation Road",
        country_code="US",
        abuse_email="abuse@registrar.com",
        abuse_phone="+1.5550100",
    )
    create_registration_nodes(base)

    # Publish stable service names through the existing COM zone. Loom owns the
    # order-driven EPP path; Namingo Registrar reads Loom through its upstream
    # backend adapter to provide the Registrar WHOIS/RDAP services.
    publish_initial_registration_records(dns)

    registrar = NamingoRegistrarService()
    registrar.install("namingo-registrar").setBackend("loom").setExternalDatabase(
        host=LOOM_IP,
        port=3306,
        name="loom",
        username=LOOM_RDDS_DB_USER,
        password=RDDS_DATABASE_PASSWORD,
    ).setIdentity(identity).exposeRddsToAgent()

    registry = NamingoRegistryService()
    registry_server = registry.install("namingo-registry")
    registry_server.setEppEndpoint(
        REGISTRY_EPP_HOSTNAME, 700
    ).setTlds(["com"]).setRddsEndpoints(
        "whois.registry.com", "http://rdap.registry.com"
    ).enableWhois().enableRdap().exposeRddsToAgent().setRegistrar(
        identity=identity,
        clid=REGISTRAR_EPP_CLID,
        password=EPP_PASSWORD,
        prefix="SEED",
        whitelist=[LOOM_IP],
        ssl_fingerprint=epp_tls.client_sha256_fingerprint,
    ).configureZoneWriter(
        nameservers={"ns1": "ns1.com", "ns2": "ns2.com"},
        soa_contact="hostmaster.com",
        interval_seconds=30,
    ).setZonePublisher(
        "com.",
        COM_HIDDEN_PRIMARY_IP,
        zone_publisher_private_key,
        primary_host_public_key,
        secondary_ips=COM_PUBLIC_SECONDARY_IPS,
    ).setTlsCertificate(
        epp_tls.server_certificate,
        epp_tls.server_private_key,
        client_ca_pem=epp_tls.ca_certificate,
    )
    for name, record_type, parameters in COM_ZONE_WRITER_RECORDS:
        registry_server.addZoneWriterRecord("com", name, record_type, parameters)

    # Only this example client receives an identity. Its ID is not a secret.
    source = base.getAutonomousSystem(150).getHost("host_1")
    source_id = "b02a.as150.host_1"
    origin = f"https://{LOOM_IP}:443"
    web_tls = LoomRegistrarService.generateWebTlsCredentials(LOOM_IP)

    loom = LoomRegistrarService()
    # Namingo Registrar's upstream Loom adapter reads the Loom service database.
    loom.install("loom-registrar").setCommit(LOOM_COMMIT).configureDatabase(
        database="loom",
        app_username="loom",
        app_password=LOOM_DATABASE_PASSWORD,
    ).configureEnvironment(
        identity=identity,
        webauthn_secret=LOOM_WEBAUTHN_SECRET,
    ).setWebTls(web_tls.certificate, web_tls.private_key).provisionSourceAccount(
        source_node=source,
        registrar_url=origin,
        ca_certificate=web_tls.certificate,
        source_id=source_id, address=SOURCE_IP,
        email="b02a-host1@example.com", username="b02a_host1", credit_limit=1000.0,
    ).setEppClientCredentials(
        epp_tls.ca_certificate,
        epp_tls.client_certificate,
        epp_tls.client_private_key,
    ).enableEppProbe(
        tld="com",
        probe_domain="loom-runtime-check.com",
    ).addReadOnlyDatabaseUser(
        username=LOOM_RDDS_DB_USER,
        password=RDDS_DATABASE_PASSWORD,
        source=REGISTRAR_IP,
    ).initializeDatabase().addEppProvider(
        name="SeedEmu Namingo Registry",
        hostname=REGISTRY_EPP_HOSTNAME,
        port=700,
        tld="com",
        clid=REGISTRAR_EPP_CLID,
        password=EPP_PASSWORD,
        prices={
            "register": {1: 10},
            "renew": {1: 10},
            "transfer": {1: 10},
            "restore": {1: 30},
        },
    ).createAdminUser()

    bind_registration_services(emu, registrar, registry, loom)


def configure_source_owned_dns(emu: Emulator, base: Base, dns: DomainNameService) -> None:
    """Add two authoritative DNS nodes controlled only by B02a's source."""
    owner_as = base.getAutonomousSystem(160)
    owner_as.createNetwork(OWNER_DNS_NETWORK, OWNER_DNS_PREFIX)
    owner_as.getRouter("router0").joinNetwork(
        OWNER_DNS_NETWORK, address=OWNER_DNS_ROUTER_IP
    )
    owner_as.createHost("owner-dns-primary").joinNetwork(
        OWNER_DNS_NETWORK, address=OWNER_DNS_PRIMARY_IP
    ).setDisplayName("Source-owned DNS Primary")
    owner_as.createHost("owner-dns-secondary").joinNetwork(
        OWNER_DNS_NETWORK, address=OWNER_DNS_SECONDARY_IP
    ).setDisplayName("Source-owned DNS Secondary")

    source = base.getAutonomousSystem(150).getHost("host_1")
    source.setLabel(
        "agent.exposed.dns.authoritative_services",
        OWNER_DNS_SERVICE_ID,
    )
    source_address = SOURCE_IP
    control_private, control_public = dns.generateSshKeyPair("b02a-source-dns-control")
    primary_host_private, primary_host_public = dns.generateSshKeyPair("b02a-owner-dns-primary")
    secondary_host_private, secondary_host_public = dns.generateSshKeyPair(
        "b02a-owner-dns-secondary"
    )
    credential_dir = f"/opt/seedemu/dns/{OWNER_DNS_SERVICE_ID}"
    source.setFile(credential_dir + "/control.key", control_private)
    source.setFile(
        credential_dir + "/known_hosts",
        f"{OWNER_DNS_PRIMARY_IP} {primary_host_public}\n"
        f"{OWNER_DNS_SECONDARY_IP} {secondary_host_public}\n",
    )
    source.appendStartCommand(
        f"chmod 0700 {credential_dir}; chmod 0600 {credential_dir}/control.key; "
        f"chmod 0644 {credential_dir}/known_hosts"
    )
    source.addSoftware("openssh-client dnsutils whois")

    update_secret = base64.b64encode(secrets.token_bytes(32)).decode()
    transfer_secret = base64.b64encode(secrets.token_bytes(32)).decode()
    common = {
        "service_id": OWNER_DNS_SERVICE_ID,
        "primary": OWNER_DNS_PRIMARY_IP,
        "secondary": OWNER_DNS_SECONDARY_IP,
        "source_address": source_address,
        "source_public_key": control_public,
        "update_secret": update_secret,
        "transfer_secret": transfer_secret,
        "zones": ["example.com"],
    }
    dns.install("source-owned-dns-primary").enableRuntimeZoneManagement(
        role="primary", ssh_host_private_key=primary_host_private,
        ssh_host_public_key=primary_host_public, **common
    )
    dns.install("source-owned-dns-secondary").enableRuntimeZoneManagement(
        role="secondary", ssh_host_private_key=secondary_host_private,
        ssh_host_public_key=secondary_host_public, **common
    )
    emu.addBinding(Binding("source-owned-dns-primary", filter=Filter(
        asn=160, nodeName="owner-dns-primary")))
    emu.addBinding(Binding("source-owned-dns-secondary", filter=Filter(
        asn=160, nodeName="owner-dns-secondary")))


def build_emulator() -> Emulator:
    """Extend B02 with a hidden primary and two public COM secondaries."""
    # Reuse B02 so this example has the same routed Internet, authoritative DNS
    # hierarchy, and recursive resolvers as the preceding example.
    emu = mini_internet_with_dns.build_emulator()
    base: Base = emu.getLayer("Base")
    dns: DomainNameService = emu.getLayer("DomainNameService")

    epp_tls = NamingoRegistryService.generateEppTlsCredentials(
        REGISTRY_EPP_HOSTNAME,
        "seedemu-registrar",
    )
    zone_publisher_private, zone_publisher_public = dns.generateSshKeyPair(
        "b02a-zone-publisher"
    )
    com_primary_host_private, com_primary_host_public = dns.generateSshKeyPair(
        "b02a-com-a-host"
    )
    com_transfer_key_secret = base64.b64encode(secrets.token_bytes(32)).decode()

    ############################################################################
    # B02 already supplies A-com and B-com. Add the physical C-com host.
    base.getAutonomousSystem(153).createHost("c-com").joinNetwork(
        "net0", address=COM_PUBLIC_SECONDARY_IPS[1]
    ).setDisplayName("COM-C Public Secondary")

    # B02 exposes A-com and B-com. B02a turns A-com into a hidden distribution
    # primary, retains B-com as a public secondary, and adds C-com as a second
    # public secondary. Only B/C publish NS and glue records to the root zone.
    configure_com_authoritative_topology(
        dns,
        com_transfer_key_secret,
        zone_publisher_public,
        com_primary_host_private,
        com_primary_host_public,
    )
    emu.getVirtualNode("a-com-server").setDisplayName("COM-A Hidden Primary")
    emu.getVirtualNode("b-com-server").setDisplayName("COM-B Public Secondary")
    emu.getVirtualNode("c-com-server").setDisplayName("COM-C Public Secondary")

    emu.addBinding(
        Binding(
            "c-com-server",
            filter=Filter(asn=153, nodeName="c-com"),
        )
    )

    configure_namingo_services(
        emu,
        base,
        dns,
        epp_tls,
        zone_publisher_private,
        com_primary_host_public,
    )
    configure_source_owned_dns(emu, base, dns)

    return emu


def parse_args() -> argparse.Namespace:
    """Parse compilation options while retaining the legacy amd/arm argument."""
    parser = argparse.ArgumentParser(
        description="Build B02a with Namingo Registrar, Registry, and COM DNS."
    )
    parser.add_argument("legacy_platform", nargs="?", choices=["amd", "arm"])
    parser.add_argument("--platform", choices=["amd", "arm"])
    parser.add_argument("--output", default=str(SCRIPT_DIR / "output"))
    parser.add_argument("--dumpfile")
    parser.add_argument("--override", dest="override", action="store_true", default=True)
    parser.add_argument("--no-override", dest="override", action="store_false")
    parser.add_argument("--skip-render", dest="render", action="store_false", default=True)
    args = parser.parse_args()
    args.platform = args.platform or args.legacy_platform or "amd"
    return args


def resolve_platform(name: str) -> Platform:
    """Translate the example's short platform name into a compiler platform."""
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def run(
    dumpfile=None,
    output=None,
    platform=Platform.AMD64,
    override=True,
    render=True,
):
    """Build the scenario, then dump it or compile it into Docker artifacts."""
    emu = build_emulator()
    if dumpfile is not None:
        # Component mode: save the unrendered emulator for composition elsewhere.
        emu.dump(dumpfile)
        return

    # Standalone mode: render bindings and compile the Docker deployment.
    if render:
        emu.render()
    output_dir = Path(output or SCRIPT_DIR / "output").resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    emu.compile(Docker(platform=platform), str(output_dir), override=override)


def main() -> int:
    """Command-line entry point."""
    args = parse_args()
    run(
        dumpfile=args.dumpfile,
        output=str(Path(args.output).resolve()),
        platform=resolve_platform(args.platform),
        override=args.override,
        render=args.render,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
