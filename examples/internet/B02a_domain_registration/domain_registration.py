#!/usr/bin/env python3
# encoding: utf-8

"""Build B02a with Namingo Registrar, Registry, and authoritative TLD DNS."""

from __future__ import annotations

import argparse
import base64
import hashlib
import secrets
import subprocess
import sys
import tempfile
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
    LoomRegistrarService,
    NamingoRegistrarService,
    NamingoRegistryService,
)


COM_TRANSFER_KEY_NAME = "com-transfer"
COM_TRANSFER_KEY_SECRET = "c2VlZGVtdS1jb20tdHJhbnNmZXIta2V5"
COM_HIDDEN_PRIMARY_IP = "10.151.0.71"
COM_PUBLIC_SECONDARY_IPS = ["10.152.0.71", "10.153.0.73"]
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
REGISTRAR_EPP_PASSWORD = "seedemu-epp"
LOOM_RDDS_DB_USER = "loom_rdds"
LOOM_RDDS_DB_PASSWORD = "seedemu-loom-rdds"
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


def loom_environment() -> str:
    """Return the pinned Loom version's complete runtime environment."""
    return f"""APP_NAME='SeedEmu Loom Registrar'
APP_ENV=local
APP_URL=https://{LOOM_IP}
APP_DOMAIN=registrar.com
WHOIS_SERVER=whois.registrar.com
RDAP_SERVER=rdap.registrar.com
LANG=en_US
UI_LANG=us
DEFAULT_CURRENCY=USD
WEB_AUTHN_ENABLED=false
WEBAUTHN_DUMMY_SECRET=seedemu-loom-webauthn
DB_DRIVER=mysql
DB_HOST=127.0.0.1
DB_DATABASE=loom
DB_USERNAME=loom
DB_PASSWORD=seedemu-loom
DB_PORT=3306
MAIL_DRIVER=none
ENABLED_GATEWAYS=balance
PASSWORD_EXPIRATION_SKIP_USERS=admin
COMPANY_NAME='SeedEmu Registrar'
COMPANY_ADDRESS='150 Simulation Road'
COMPANY_ADDRESS2=''
COMPANY_COUNTRY_CODE=US
COMPANY_VAT_NUMBER=''
COMPANY_PHONE='+1.5550100'
COMPANY_EMAIL=registrar@registrar.com
TLS=1.2
VERIFY_PEER=true
VERIFY_PEER_NAME=true
VERIFY_HOST=true
SELF_SIGNED=false
BIND=false
BIND_IP={LOOM_IP}
VALIDATE_PHONE=false
VALIDATE_EMAIL=false
VALIDATE_POSTAL=false
IANA_ID=9999
MOSAPI_USERNAME=''
MOSAPI_PASSWORD=''
"""


def loom_provider_sql() -> str:
    """Provision Loom's Namingo EPP provider without changing Loom code."""
    return """INSERT INTO providers
(name,type,api_endpoint,credentials,pricing,status,tld)
VALUES
('SeedEmu Namingo Registry','domain','epp.registry.com:700',
 JSON_OBJECT('ssl',true,'cert_file','/opt/loom-epp/client.crt',
 'key_file','/opt/loom-epp/client.key','cafile','/opt/loom-epp/ca.crt',
 'passphrase','','auth',JSON_OBJECT('username','seedemu','password','seedemu-epp'),
 'client_id','seedemu','contactRoles',JSON_ARRAY('registrant','admin','tech','billing'),
 'contactType','int','autoCreateHosts',true),
 JSON_OBJECT('.com',JSON_OBJECT('register',JSON_OBJECT('1',10),
 'renew',JSON_OBJECT('1',10),'transfer',JSON_OBJECT('1',10),
 'restore',JSON_OBJECT('1',30))),'active','.com')
ON DUPLICATE KEY UPDATE api_endpoint=VALUES(api_endpoint),
credentials=VALUES(credentials),pricing=VALUES(pricing),status=VALUES(status);
"""


def loom_epp_probe() -> str:
    """Exercise Loom's own provider lookup and EPP client implementation."""
    return """<?php
require '/opt/loom/vendor/autoload.php';
Dotenv\\Dotenv::createImmutable('/opt/loom')->load();
require '/opt/loom/bootstrap/helper.php';
$pdo = new PDO('mysql:host=' . $_ENV['DB_HOST'] . ';dbname=' . $_ENV['DB_DATABASE'], $_ENV['DB_USERNAME'], $_ENV['DB_PASSWORD']);
$provider = $pdo->query("SELECT * FROM providers WHERE tld = '.com' AND status = 'active'")->fetch(PDO::FETCH_ASSOC);
if (!$provider) { throw new RuntimeException('Loom Namingo provider not found'); }
$credentials = json_decode($provider['credentials'], true, 512, JSON_THROW_ON_ERROR);
[$host, $port] = explode(':', $provider['api_endpoint'], 2);
$epp = connectEpp('generic', $host, (int)$port, $credentials['cafile'], $credentials['cert_file'], $credentials['key_file'], $credentials['passphrase'], $credentials['auth']['username'], $credentials['auth']['password']);
$reply = $epp->domainCheck(['domains' => ['loom-runtime-check.com']]);
$epp->logout();
if (isset($reply['error'])) { throw new RuntimeException($reply['error']); }
file_put_contents('/run/seedemu-loom-epp-health.json', json_encode(['status' => 'ok', 'transport' => 'epp-over-tls', 'domain' => 'loom-runtime-check.com'], JSON_THROW_ON_ERROR));
"""

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


def generate_ssh_keypair(comment: str) -> tuple[str, str]:
    """Generate one deployment-local Ed25519 identity."""
    with tempfile.TemporaryDirectory() as work:
        key_path = Path(work) / "id_ed25519"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", comment,
             "-f", str(key_path)],
            check=True,
            capture_output=True,
        )
        return key_path.read_text(), key_path.with_suffix(".pub").read_text().strip()


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
    loom_node = base.getAutonomousSystem(150).createHost("loom-registrar").joinNetwork(
        "net0", address=LOOM_IP
    ).setDisplayName("Loom Registrar Frontend")
    loom_node.setFile("/opt/loom-epp/ca.crt", EPP_CA_CERTIFICATE)
    loom_node.setFile("/opt/loom-epp/client.crt", EPP_CLIENT_CERTIFICATE)
    loom_node.setFile("/opt/loom-epp/client.key", EPP_CLIENT_PRIVATE_KEY)
    loom_node.setFile("/opt/seedemu/loom/provider.sql", loom_provider_sql())
    loom_node.setFile("/opt/seedemu/loom/epp-probe.php", loom_epp_probe())

    # Publish stable service names through the existing COM zone. Loom owns the
    # order-driven EPP path; Namingo Registrar reads Loom through its upstream
    # backend adapter to provide the Registrar WHOIS/RDAP services.
    com_zone = dns.getZone("com.")
    # A low deterministic initial serial lets the first Zone Writer snapshot
    # pass the receiver's anti-rollback check.
    if not com_zone.findRecords("SOA"):
        com_zone.addRecord("@ SOA ns1.com. hostmaster.com. 1 900 900 1800 60")
    com_zone.addRecord("epp.registry A {}".format(REGISTRY_IP))
    com_zone.addRecord("whois.registrar A {}".format(REGISTRAR_IP))
    com_zone.addRecord("rdap.registrar A {}".format(REGISTRAR_IP))

    registrar = NamingoRegistrarService()
    registrar.install("namingo-registrar").setBackend("loom").setExternalDatabase(
        host=LOOM_IP,
        port=3306,
        name="loom",
        username=LOOM_RDDS_DB_USER,
        password=LOOM_RDDS_DB_PASSWORD,
    ).setIdentity(
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
        whitelist=[REGISTRAR_IP, LOOM_IP],
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

    # Only this example client receives an identity. Its ID is not a secret.
    source = base.getAutonomousSystem(150).getHost("host_1")
    source_id = "b02a.as150.host_1"
    source_token = secrets.token_hex(32)
    origin = f"https://{LOOM_IP}:443"
    credential_dir = "/opt/seedemu/registrar/" + hashlib.sha256(origin.encode()).hexdigest()
    # Generate a deployment-local trust anchor without retaining temporary files.
    with tempfile.TemporaryDirectory() as work:
        key_path, cert_path = Path(work) / "key.pem", Path(work) / "cert.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key_path), "-out", str(cert_path), "-days", "3650",
            "-subj", "/CN=SeedEmu Loom", "-addext", f"subjectAltName=IP:{LOOM_IP}",
        ], check=True, capture_output=True)
        web_key, web_certificate = key_path.read_text(), cert_path.read_text()
    source.setFile(credential_dir + "/source-id", source_id)
    source.setFile(credential_dir + "/token", source_token)
    source.setFile(credential_dir + "/ca.crt", web_certificate)
    source.appendStartCommand(f"chmod 0700 {credential_dir}; chmod 0600 {credential_dir}/*")

    loom = LoomRegistrarService()
    # Namingo Registrar's upstream Loom adapter reads the Loom service database.
    # Bind MariaDB to the emulated interface; database grants below restrict the
    # integration account to read-only access from the Registrar node.
    loom_node.appendStartCommand(
        "sed -i 's/^bind-address[[:space:]]*=.*/bind-address = 0.0.0.0/' "
        "/etc/mysql/mariadb.conf.d/50-server.cnf"
    )
    loom.install("loom-registrar").setCommit(LOOM_COMMIT).setEnvironment(
        loom_environment()
    ).setWebTls(web_certificate, web_key).addSourceAccount(
        source_id=source_id, address="10.150.0.72",
        token_sha256=hashlib.sha256(source_token.encode()).hexdigest(),
        email="b02a-host1@example.com", username="b02a_host1", credit_limit=1000.0,
    ).addBootstrapCommand(
        "    mariadb -e \"CREATE DATABASE IF NOT EXISTS loom CHARACTER SET utf8mb4 "
        "COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'loom'@'127.0.0.1' "
        "IDENTIFIED BY 'seedemu-loom'; GRANT ALL PRIVILEGES ON loom.* TO "
        "'loom'@'127.0.0.1'; CREATE USER IF NOT EXISTS 'loom_rdds'@'10.150.0.73' "
        "IDENTIFIED BY 'seedemu-loom-rdds'; GRANT SELECT ON loom.* TO "
        "'loom_rdds'@'10.150.0.73'; FLUSH PRIVILEGES;\""
    ).addBootstrapCommand(
        "    php /opt/loom/bin/install-db.php"
    ).addBootstrapCommand(
        "    mariadb -h 127.0.0.1 -uloom -pseedemu-loom loom "
        "< /opt/seedemu/loom/provider.sql"
    ).addBootstrapCommand(
        "    php /opt/loom/bin/create-admin-user.php"
    ).addBootstrapCommand(
        "    chown root:www-data /opt/loom-epp/client.key; "
        "chmod 0640 /opt/loom-epp/client.key; i=0; "
        "until php /opt/seedemu/loom/epp-probe.php; do i=$((i + 1)); "
        "test \"$i\" -lt 60; sleep 2; done"
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
    emu.addBinding(
        Binding(
            "loom-registrar",
            filter=Filter(asn=150, nodeName="loom-registrar"),
        )
    )
    emu.addLayer(registrar)
    emu.addLayer(registry)
    emu.addLayer(loom)


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
    source_address = "10.150.0.72"
    control_private, control_public = generate_ssh_keypair("b02a-source-dns-control")
    primary_host_private, primary_host_public = generate_ssh_keypair("b02a-owner-dns-primary")
    secondary_host_private, secondary_host_public = generate_ssh_keypair(
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
    configure_source_owned_dns(emu, base, dns)

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
