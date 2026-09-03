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
EPP_CA_CERTIFICATE = "-----BEGIN CERTIFICATE-----\nMIIBlzCCAT2gAwIBAgIUO6WTWlXpqz/YVLGiEIBzLYt31SUwCgYIKoZIzj0EAwIw\nGTEXMBUGA1UEAwwOU2VlZEVtdSBFUFAgQ0EwHhcNMjYwOTAyMDc1MjQ1WhcNMzYw\nODMwMDc1MjQ1WjAZMRcwFQYDVQQDDA5TZWVkRW11IEVQUCBDQTBZMBMGByqGSM49\nAgEGCCqGSM49AwEHA0IABMVJHZOVUAKg/2p76dI8rPslQJCf6k6ZEFaHUJfX4O1R\n7fNzmIjaNvnD7RY0txOLSsaJUu2RwBB91se8ipzE2vOjYzBhMB0GA1UdDgQWBBQX\nO0akWixlPZ7SG4ZN4m+O0xer6TAfBgNVHSMEGDAWgBQXO0akWixlPZ7SG4ZN4m+O\n0xer6TAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBBjAKBggqhkjOPQQD\nAgNIADBFAiEApmHB1zca7bFIrAUE06J2KNXwoaSizGWg4PZZQswTshoCICk/NQzO\nJh713PHaHGTFT1SOfGSH9vh5nYd7K9cyS3fe\n-----END CERTIFICATE-----\n"
EPP_SERVER_CERTIFICATE = "-----BEGIN CERTIFICATE-----\nMIIBljCCATugAwIBAgIUfjN/wg5Te93W+rAlb8fDizC4XXMwCgYIKoZIzj0EAwIw\nGTEXMBUGA1UEAwwOU2VlZEVtdSBFUFAgQ0EwHhcNMjYwOTAyMDc1MjQ1WhcNMzYw\nODMwMDc1MjQ1WjAbMRkwFwYDVQQDDBBlcHAucmVnaXN0cnkuY29tMFkwEwYHKoZI\nzj0CAQYIKoZIzj0DAQcDQgAEunPc/OZftZK9o8Xm8sV9rXmtXdCNq6LX/v02r3vy\nJQCX2i/nqKmL388TMvcCchH57n3hy+QnE/43ZqtzHfN6baNfMF0wGwYDVR0RBBQw\nEoIQZXBwLnJlZ2lzdHJ5LmNvbTAdBgNVHQ4EFgQUy5ej0Mrvvi+zSctLBvAZNNjS\nGq0wHwYDVR0jBBgwFoAUFztGpFosZT2e0huGTeJvjtMXq+kwCgYIKoZIzj0EAwID\nSQAwRgIhAM/IPdaRojken97CPPjaR/5nD7/nNVRFIEUa642NYM3bAiEAn13cGxLF\nLYZrfzPskxPjb9xBfpVL7BsnRGEdOQP/DCs=\n-----END CERTIFICATE-----\n"
EPP_SERVER_PRIVATE_KEY = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIEkPEwYS2amesQYGh3/0qQvUvZJajUOx8DB4Za1c0y3goAoGCCqGSM49\nAwEHoUQDQgAEunPc/OZftZK9o8Xm8sV9rXmtXdCNq6LX/v02r3vyJQCX2i/nqKmL\n388TMvcCchH57n3hy+QnE/43ZqtzHfN6bQ==\n-----END EC PRIVATE KEY-----\n"
EPP_CLIENT_CERTIFICATE = "-----BEGIN CERTIFICATE-----\nMIIBsDCCAVWgAwIBAgIUAMABH+B1tlG54ns/XKG+3mlc8qgwCgYIKoZIzj0EAwIw\nHDEaMBgGA1UEAwwRc2VlZGVtdS1yZWdpc3RyYXIwHhcNMjYwOTAzMDM0NzM0WhcN\nMzYwODMxMDM0NzM0WjAcMRowGAYDVQQDDBFzZWVkZW11LXJlZ2lzdHJhcjBZMBMG\nByqGSM49AgEGCCqGSM49AwEHA0IABBaY5aeSEGg9nIcsfZCwxQIgsC/myKfZwhey\nxa9lbx6+l42XW4FQTBj/eeryCoZbypOqGfjarR7OQWVLjJrX70ejdTBzMB0GA1Ud\nDgQWBBRyVg24LyxKivHtdf1PNXrzh+5zwDAfBgNVHSMEGDAWgBRyVg24LyxKivHt\ndf1PNXrzh+5zwDAMBgNVHRMBAf8EAjAAMA4GA1UdDwEB/wQEAwIHgDATBgNVHSUE\nDDAKBggrBgEFBQcDAjAKBggqhkjOPQQDAgNJADBGAiEAztAkowt7R2xHa5HXa56t\nBE/Mm/VtaxtwW/GMV15FQg0CIQC0h37IkxjG701Qzok7SrPSeq2N8Eail6i3MqA5\nFsVAvA==\n-----END CERTIFICATE-----\n"
EPP_CLIENT_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgoKPpxpgm2N1Og6Ck\ngJRs7a5tBC1zw5h3dIkI80GTiqmhRANCAAQWmOWnkhBoPZyHLH2QsMUCILAv5sin\n2cIXssWvZW8evpeNl1uBUEwY/3nq8gqGW8qTqhn42q0ezkFlS4ya1+9H\n-----END PRIVATE KEY-----\n"
EPP_CLIENT_SHA256_FINGERPRINT = "FF27554CE85BDBF56F45770518C5CF7C9133E5184BF541EBA245061C821CB4A8"
ZONE_PUBLISHER_PRIVATE_KEY = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\nQyNTUxOQAAACC7opid8eb++pvN5qQMZvIzzJCjhKaVTeneTeNcKFFQ6AAAAJhdaEkSXWhJ\nEgAAAAtzc2gtZWQyNTUxOQAAACC7opid8eb++pvN5qQMZvIzzJCjhKaVTeneTeNcKFFQ6A\nAAAECvO1WXJlpLMB2WMWeGrJO+7R4v7zWdwbYVGOMaYB4AZruimJ3x5v76m83mpAxm8jPM\nkKOEppVN6d5N41woUVDoAAAAE2IwMmEtem9uZS1wdWJsaXNoZXIBAg==\n-----END OPENSSH PRIVATE KEY-----\n"
ZONE_PUBLISHER_PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILuimJ3x5v76m83mpAxm8jPMkKOEppVN6d5N41woUVDo b02a-zone-publisher"
COM_PRIMARY_SSH_HOST_PRIVATE_KEY = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\nQyNTUxOQAAACBic6dnfsurUnrx3YDk722YO2he3xPOcn/zMBs9PW6t5gAAAJh4LdPReC3T\n0QAAAAtzc2gtZWQyNTUxOQAAACBic6dnfsurUnrx3YDk722YO2he3xPOcn/zMBs9PW6t5g\nAAAEC6HcbLSNYYXBK5FqaWFUxXmIbFfrqPxfGPlOIWXLHZu2Jzp2d+y6tSevHdgOTvbZg7\naF7fE85yf/MwGz09bq3mAAAAD2IwMmEtY29tLWEtaG9zdAECAwQFBg==\n-----END OPENSSH PRIVATE KEY-----\n"
COM_PRIMARY_SSH_HOST_PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGJzp2d+y6tSevHdgOTvbZg7aF7fE85yf/MwGz09bq3m b02a-com-a-host"

def registry_zone_writer_config() -> str:
    """Return Namingo automation settings for the COM source zone."""
    return """<?php
return [
    'db_type' => 'mysql',
    'db_host' => '127.0.0.1',
    'db_port' => 3306,
    'db_database' => 'registry',
    'db_username' => 'registryuser',
    'db_password' => 'seedemu-registry',
    'dns_server' => 'bind',
    'ns' => [
        'ns1' => 'ns1.com',
        'ns2' => 'ns2.com',
    ],
    'dns_soa' => 'hostmaster.com',
    'dns_serial' => 1,
    'dns_reload' => false,
    'zone_mode' => 'default',
];
"""


def registry_com_custom_records() -> str:
    """Keep B02 delegations and Namingo endpoints in Zone Writer output."""
    return """<?php
return [
    ['name' => 'ns1', 'type' => 'A', 'parameters' => ['10.152.0.71']],
    ['name' => 'ns2', 'type' => 'A', 'parameters' => ['10.153.0.73']],
    ['name' => 'epp.registry', 'type' => 'A', 'parameters' => ['10.154.0.73']],
    ['name' => 'whois.registrar', 'type' => 'A', 'parameters' => ['10.150.0.73']],
    ['name' => 'rdap.registrar', 'type' => 'A', 'parameters' => ['10.150.0.73']],
    ['name' => 'twitter', 'type' => 'NS', 'parameters' => ['ns1.twitter.com.']],
    ['name' => 'ns1.twitter', 'type' => 'A', 'parameters' => ['10.161.0.71']],
    ['name' => 'google', 'type' => 'NS', 'parameters' => ['ns1.google.com.']],
    ['name' => 'ns1.google', 'type' => 'A', 'parameters' => ['10.162.0.71']],
];
"""


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
    ).enableZoneFileReceiver(
        "com.",
        REGISTRY_IP,
        ZONE_PUBLISHER_PUBLIC_KEY,
        COM_PRIMARY_SSH_HOST_PRIVATE_KEY,
        COM_PRIMARY_SSH_HOST_PUBLIC_KEY,
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
    # A low deterministic initial serial lets the first Zone Writer snapshot
    # pass the receiver's anti-rollback check.
    if not com_zone.findRecords("SOA"):
        com_zone.addRecord("@ SOA ns1.com. hostmaster.com. 1 900 900 1800 60")
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
    ).enableEppClient(
        hostname=REGISTRY_EPP_HOSTNAME,
        port=700,
        clid=REGISTRAR_EPP_CLID,
        password=REGISTRAR_EPP_PASSWORD,
        ca_certificate_pem=EPP_CA_CERTIFICATE,
        client_certificate_pem=EPP_CLIENT_CERTIFICATE,
        client_private_key_pem=EPP_CLIENT_PRIVATE_KEY,
        probe_domain="seedemu-epp-probe.com",
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
        ssl_fingerprint=EPP_CLIENT_SHA256_FINGERPRINT,
    ).enableZoneWriter(
        registry_zone_writer_config(), interval_seconds=30
    ).setZoneWriterCustomRecords(
        "com", registry_com_custom_records()
    ).setZonePublisher(
        "com.",
        COM_HIDDEN_PRIMARY_IP,
        ZONE_PUBLISHER_PRIVATE_KEY,
        COM_PRIMARY_SSH_HOST_PUBLIC_KEY,
    ).setTlsCertificate(
        EPP_SERVER_CERTIFICATE,
        EPP_SERVER_PRIVATE_KEY,
        client_ca_pem=EPP_CLIENT_CERTIFICATE,
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
