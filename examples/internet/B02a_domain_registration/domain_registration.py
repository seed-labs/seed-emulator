#!/usr/bin/env python3
# encoding: utf-8

"""Build B02a with Namingo Registrar, Registry, and authoritative TLD DNS."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


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
    NamingoRegistrarService,
    NamingoRegistryService,
)


COM_TRANSFER_KEY_NAME = "com-transfer"
COM_TRANSFER_KEY_SECRET = "c2VlZGVtdS1jb20tdHJhbnNmZXIta2V5"
COM_HIDDEN_PRIMARY_IP = "10.151.0.71"
COM_PUBLIC_SECONDARY_IPS = ["10.152.0.71", "10.153.0.73"]
REGISTRAR_IP = "10.150.0.73"
REGISTRY_IP = "10.154.0.73"
REGISTRY_EPP_HOSTNAME = "epp.registry.com"
REGISTRAR_EPP_CLID = "seedemu"
REGISTRAR_EPP_PASSWORD = "seedemu-epp"


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


def configure_com_authoritative_topology(
    dns: DomainNameService,
) -> None:
    """Configure A-com as hidden primary and B/C-com as public secondaries."""
    targets = dns.getPendingTargets()
    a_com = targets["a-com-server"]
    b_com = targets["b-com-server"]

    a_com.setHiddenPrimary().setTransferKey(
        COM_TRANSFER_KEY_NAME, COM_TRANSFER_KEY_SECRET
    )
    for secondary_ip in COM_PUBLIC_SECONDARY_IPS:
        a_com.addTransferTarget(secondary_ip)

    b_com.setSecondary(COM_HIDDEN_PRIMARY_IP).setTransferKey(
        COM_TRANSFER_KEY_NAME, COM_TRANSFER_KEY_SECRET
    )

    c_com = dns.install("c-com-server").addZone("com.")
    c_com.setSecondary(COM_HIDDEN_PRIMARY_IP).setTransferKey(
        COM_TRANSFER_KEY_NAME, COM_TRANSFER_KEY_SECRET
    )


def configure_namingo_services(emu: Emulator, base: Base, dns: DomainNameService) -> None:
    """Add independent Namingo Registrar and Registry nodes to B02a."""
    base.getAutonomousSystem(150).createHost("namingo-registrar").joinNetwork(
        "net0", address=REGISTRAR_IP
    ).setDisplayName("Namingo Registrar")
    base.getAutonomousSystem(154).createHost("namingo-registry").joinNetwork(
        "net0", address=REGISTRY_IP
    ).setDisplayName("Namingo Registry")

    # Publish stable service names through the existing COM zone. The Registry
    # exposes EPP/TLS and provisions the Registrar account, but the current
    # Registrar wrapper does not yet initiate EPP transactions.
    com_zone = dns.getZone("com.")
    com_zone.addRecord("epp.registry A {}".format(REGISTRY_IP))
    com_zone.addRecord("whois.registrar A {}".format(REGISTRAR_IP))
    com_zone.addRecord("rdap.registrar A {}".format(REGISTRAR_IP))

    registrar = NamingoRegistrarService()
    registrar.install("namingo-registrar").setBackend("custom").setIdentity(
        name="SeedEmu Namingo Registrar",
        iana_id="9999",
        url="http://registrar.com",
        whois_host="whois.registrar.com",
        rdap_url="http://rdap.registrar.com",
        abuse_email="abuse@registrar.com",
        abuse_phone="+1.5550100",
    )

    registry = NamingoRegistryService()
    registry.install("namingo-registry").setEppEndpoint(
        REGISTRY_EPP_HOSTNAME, 700
    ).setTlds(["com"]).setRegistrar(
        clid=REGISTRAR_EPP_CLID,
        password=REGISTRAR_EPP_PASSWORD,
        prefix="SEED",
        whitelist=[REGISTRAR_IP],
        name="SeedEmu Namingo Registrar",
        iana_id=9999,
        email="registrar@registrar.com",
    )

    emu.addBinding(
        Binding(
            "namingo-registrar",
            filter=Filter(asn=150, nodeName="namingo-registrar"),
        )
    )
    emu.addBinding(
        Binding(
            "namingo-registry",
            filter=Filter(asn=154, nodeName="namingo-registry"),
        )
    )
    emu.addLayer(registrar)
    emu.addLayer(registry)


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
    configure_com_authoritative_topology(dns)
    emu.getVirtualNode("a-com-server").setDisplayName("COM-A Hidden Primary")
    emu.getVirtualNode("b-com-server").setDisplayName("COM-B Public Secondary")
    emu.getVirtualNode("c-com-server").setDisplayName("COM-C Public Secondary")

    emu.addBinding(
        Binding(
            "c-com-server",
            filter=Filter(asn=153, nodeName="c-com"),
        )
    )

    configure_namingo_services(emu, base, dns)

    return emu


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
