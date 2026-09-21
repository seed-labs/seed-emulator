#!/usr/bin/env python3
# encoding: utf-8

"""Build B02a with Namingo Registrar, Registry, and authoritative TLD DNS."""

from __future__ import annotations

import argparse
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
    DomainRegistrationSystem,
    DomainNameService,
    RegistrarIdentity,
    RegistrationNode,
    RuntimeDnsNode,
)


COM_HIDDEN_PRIMARY_IP = "10.151.0.71"
COM_PUBLIC_SECONDARY_IPS = ["10.152.0.71", "10.153.0.73"]
SOURCE_IP = "10.150.0.72"
LOOM_IP = "10.150.0.74"
REGISTRY_IP = "10.154.0.73"
OWNER_DNS_NETWORK = "owner-dns-net"
OWNER_DNS_PREFIX = "11.160.0.0/24"
OWNER_DNS_ROUTER_IP = "11.160.0.254"
OWNER_DNS_PRIMARY_IP = "11.160.0.53"
OWNER_DNS_SECONDARY_IP = "11.160.0.54"
OWNER_DNS_SERVICE_ID = "b02a.source-owned-dns"
REGISTRY_EPP_HOSTNAME = "epp.registry.com"

COM_PRESEEDED_DELEGATIONS = [
    ("twitter", "NS", ["ns1.twitter.com."]),
    ("ns1.twitter", "A", ["10.161.0.71"]),
    ("google", "NS", ["ns1.google.com."]),
    ("ns1.google", "A", ["10.162.0.71"]),
]


def create_registration_nodes(base: Base) -> None:
    """Create the combined Registrar and independent Registry hosts."""
    base.getAutonomousSystem(154).createHost("namingo-registry").joinNetwork(
        "net0", address=REGISTRY_IP
    ).setDisplayName("Namingo Registry")
    base.getAutonomousSystem(150).createHost("loom-registrar").joinNetwork(
        "net0", address=LOOM_IP
    ).setDisplayName("Loom Registrar with Namingo RDDS")


def configure_namingo_services(
    emu: Emulator,
    base: Base,
    dns: DomainNameService,
) -> None:
    """Compose Loom, colocated Registrar RDDS, Registry, and publication."""
    identity = RegistrarIdentity(
        name="SeedEmu Namingo Registrar",
        company_name="SeedEmu Registrar",
        domain="registrar.com",
        iana_id=9999,
        url="http://registrar.com",
        whois_host="whois.registrar.com",
        rdap_url="http://rdap.registrar.com:8080",
        email="registrar@registrar.com",
        phone="+1.5550100",
        address="150 Simulation Road",
        country_code="US",
        abuse_email="abuse@registrar.com",
        abuse_phone="+1.5550100",
    )
    create_registration_nodes(base)

    drs = DomainRegistrationSystem(emu, base, dns, identity)
    drs.addRegistry(
        "com-registry",
        RegistrationNode("namingo-registry", 154, "namingo-registry", REGISTRY_IP),
        epp_hostname=REGISTRY_EPP_HOSTNAME,
        tlds=["com"],
        whois_host="whois.registry.com",
        rdap_url="http://rdap.registry.com",
    )
    drs.addLoomRegistrar(
        "seedemu-registrar",
        RegistrationNode("loom-registrar", 150, "loom-registrar", LOOM_IP),
    )
    drs.connectEpp(
        registrar_id="seedemu-registrar",
        registry_id="com-registry",
        tld="com",
        prices={
            "register": {1: 10},
            "renew": {1: 10},
            "transfer": {1: 10},
            "restore": {1: 30},
        },
    )
    drs.addRegistrarRdds(
        "seedemu-registrar-rdds",
        "seedemu-registrar",
        RegistrationNode("namingo-registrar", 150, "loom-registrar", LOOM_IP),
        rdap_proxy_port=8080,
    )
    drs.connectTldDns(
        registry_id="com-registry",
        zone="com.",
        hidden_primary_vnode="a-com-server",
        hidden_primary_ip=COM_HIDDEN_PRIMARY_IP,
        public_secondaries=[
            ("b-com-server", COM_PUBLIC_SECONDARY_IPS[0]),
            ("c-com-server", COM_PUBLIC_SECONDARY_IPS[1]),
        ],
        nameservers={"ns1": "ns1.com", "ns2": "ns2.com"},
        soa_contact="hostmaster.com",
        static_records=COM_PRESEEDED_DELEGATIONS,
    )

    # Only this example client receives an identity. Its ID is not a secret.
    source = base.getAutonomousSystem(150).getHost("host_1")
    drs.enrollSource(
        source_node=source,
        registrar_id="seedemu-registrar",
        source_id="b02a.as150.host_1",
        source_address=SOURCE_IP,
        email="b02a-host1@example.com",
        username="b02a_host1",
        credit_limit=1000.0,
    )
    drs.install()


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
    dns.configureRuntimeZoneService(
        emu,
        source,
        service_id=OWNER_DNS_SERVICE_ID,
        source_address=SOURCE_IP,
        primary=RuntimeDnsNode(
            "source-owned-dns-primary", 160, "owner-dns-primary", OWNER_DNS_PRIMARY_IP
        ),
        secondary=RuntimeDnsNode(
            "source-owned-dns-secondary", 160, "owner-dns-secondary", OWNER_DNS_SECONDARY_IP
        ),
        zone_suffixes=["com"],
    )


def build_emulator() -> Emulator:
    """Extend B02 with a hidden primary and two public COM secondaries."""
    # Reuse B02 so this example has the same routed Internet, authoritative DNS
    # hierarchy, and recursive resolvers as the preceding example.
    emu = mini_internet_with_dns.build_emulator()
    base: Base = emu.getLayer("Base")
    dns: DomainNameService = emu.getLayer("DomainNameService")

    ############################################################################
    # B02 already supplies A-com and B-com. Add the physical C-com host.
    base.getAutonomousSystem(153).createHost("c-com").joinNetwork(
        "net0", address=COM_PUBLIC_SECONDARY_IPS[1]
    ).setDisplayName("COM-C Public Secondary")

    # B02 exposes A-com and B-com. B02a turns A-com into a hidden distribution
    # primary, retains B-com as a public secondary, and adds C-com as a second
    # public secondary. Only B/C publish NS and glue records to the root zone.
    dns.install("c-com-server").addZone("com.")
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
