#!/usr/bin/env python3
# encoding: utf-8

"""Build B02a: an agent-facing registrar on top of the B02 DNS Internet."""

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
from seedemu.services import DomainNameService
from seedemu.services.AgentDnsProvisioningService import AgentDnsProvisioningService
from seedemu.services.AgentDomainRegistrarService import AgentDomainRegistrarService
from seedemu.services.AgentManagedDnsService import AgentManagedDnsService


def parse_args() -> argparse.Namespace:
    """Parse compilation options while retaining the legacy amd/arm argument."""
    parser = argparse.ArgumentParser(
        description="Build the B02a dynamic domain-registration scenario."
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


def registrar_policy() -> str:
    """Return the registrar policy exposed by the agent-facing JSON API."""
    return """{
  "supported_tlds": ["com"],
  "reserved_names": ["google.com", "twitter.com"],
  "max_years": 10,
  "default_nameservers": [
    {"name": "ns1.seedemu-dns.net.", "address": "10.161.0.53"},
    {"name": "ns2.seedemu-dns.net.", "address": "10.162.0.53"}
  ]
}"""


def secure_com_parent_updates(base: Base) -> None:
    """Replace B02's permissive com update ACL in this B02a instance only."""
    key = 'key "agent-parent-update" { algorithm hmac-sha256; secret "YWdlbnQtcGFyZW50LXVwZGF0ZS1rZXk="; };\n'
    master = base.getAutonomousSystem(151).getHost("host_0")
    master.setFile("/etc/bind/agent-parent-update.key", key)
    master.appendStartCommand(
        "grep -q 'agent-parent-update.key' /etc/bind/named.conf || "
        "printf '%s\\n' 'include \"/etc/bind/agent-parent-update.key\";' >> /etc/bind/named.conf"
    )
    master.appendStartCommand(
        "sed -i 's/allow-update { any; }/allow-update { key \"agent-parent-update\"; }/' "
        "/etc/bind/named.conf.zones && rndc reconfig"
    )


def build_emulator() -> Emulator:
    """Extend B02 with a registrar API and managed authoritative DNS hosts."""
    # Reuse B02 so this example has the same routed Internet, authoritative DNS
    # hierarchy, and recursive resolvers as the preceding example.
    emu = mini_internet_with_dns.build_emulator()
    base: Base = emu.getLayer("Base")
    dns: DomainNameService = emu.getLayer("DomainNameService")

    ############################################################################
    # Create the physical hosts that will run the new virtual services.
    base.getAutonomousSystem(150).createHost("registrar").joinNetwork("net0").setDisplayName("Domain Registrar")
    base.getAutonomousSystem(161).createHost("managed-dns-master").joinNetwork("net0", address="10.161.0.53").setDisplayName("Managed DNS Master")
    base.getAutonomousSystem(162).createHost("managed-dns-secondary").joinNetwork("net0", address="10.162.0.53").setDisplayName("Managed DNS Secondary")

    ############################################################################
    # Install and configure the agent-facing registrar service. A successful
    # purchase becomes pending_dns; a provisioning consumer can later process
    # the service's outbox event and update the DNS hierarchy.
    registrar_service = AgentDomainRegistrarService()
    registrar_server = registrar_service.install("agent-registrar-api")
    registrar_server.setPolicy(registrar_policy()).setProvisionerUrl("http://127.0.0.1:8053")

    # Stage 2 step 3 provisions and verifies delegation in the inherited com.
    # parent zone. It remains separate from the registrar outbox until managed
    # zone creation and secondary synchronization are implemented.
    provisioner_service = AgentDnsProvisioningService()
    provisioner_service.install("dns-provisioner").setParentServers(
        "10.151.0.71", ["10.152.0.71"]
    ).setManagedServers("10.161.0.53", ["10.162.0.53"])

    managed_dns = AgentManagedDnsService()
    managed_dns.install("managed-dns-master").setMaster("10.162.0.53")
    managed_dns.install("managed-dns-secondary").setSecondary("10.161.0.53")

    # Delegate the provider identity zone in B02a's inherited net. parent. The
    # records are added to this emulator instance only; B01/B02 remain unchanged.
    net_zone = dns.getZone("net.")
    net_zone.addRecord("seedemu-dns.net. NS ns1.seedemu-dns.net.")
    net_zone.addRecord("seedemu-dns.net. NS ns2.seedemu-dns.net.")
    net_zone.addRecord("ns1.seedemu-dns.net. A 10.161.0.53")
    net_zone.addRecord("ns2.seedemu-dns.net. A 10.162.0.53")

    ############################################################################
    # Bind each virtual service to the corresponding physical host. Specifying
    # both ASN and node name keeps the placement explicit and deterministic.
    emu.addBinding(
        Binding(
            "agent-registrar-api",
            filter=Filter(asn=150, nodeName="registrar"),
        )
    )
    emu.addBinding(
        Binding(
            "managed-dns-master",
            filter=Filter(
                asn=161,
                nodeName="managed-dns-master",
            ),
        )
    )
    emu.addBinding(
        Binding(
            "managed-dns-secondary",
            filter=Filter(
                asn=162,
                nodeName="managed-dns-secondary",
            ),
        )
    )
    emu.addBinding(
        Binding(
            "dns-provisioner",
            filter=Filter(asn=150, nodeName="registrar", allowBound=True),
        )
    )

    # The registrar service is a new service layer. DomainNameService already
    # belongs to the inherited B02 emulator and therefore is not added again.
    emu.addLayer(registrar_service)
    emu.addLayer(provisioner_service)
    emu.addLayer(managed_dns)

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
        secure_com_parent_updates(emu.getLayer("Base"))
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
