from __future__ import annotations

import ipaddress
import hashlib
import json
import re
import ssl
import subprocess
import tempfile
from pathlib import Path
from typing import List, NamedTuple, Optional
from urllib.parse import urlparse

from seedemu.core import Node, Server, Service
from seedemu.services.RegistrarIdentity import RegistrarIdentity


NAMINGO_REGISTRY_REPOSITORY = "https://github.com/getnamingo/registry.git"
NAMINGO_REGISTRY_VERSION = "v1.0.33"
NAMINGO_REGISTRY_COMMIT = "a783a3c37a5614827f7141f07028e9a6a2d4f5cb"
NAMINGO_REGISTRY_INSTALL_DIR = "/opt/registry"
NAMINGO_REGISTRY_LABEL_META = "namingo.{key}"
AGENT_RDDS_LABEL_META = "agent.exposed.rdds.{key}"


class EppTlsCredentials(NamedTuple):
    """One CA and a matching EPP server/client mutual-TLS identity set."""

    ca_certificate: str
    server_certificate: str
    server_private_key: str
    client_certificate: str
    client_private_key: str
    client_sha256_fingerprint: str


def _php(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return "[{}]".format(
            ", ".join("{} => {}".format(_php(key), _php(item))
                      for key, item in value.items())
        )
    if isinstance(value, (list, tuple)):
        return "[{}]".format(", ".join(_php(item) for item in value))
    return json.dumps(str(value), ensure_ascii=False)


def _sql_string(value: str) -> str:
    return "'{}'".format(value.replace("\\", "\\\\").replace("'", "''"))


class NamingoRegistryServer(Server):
    """Install a pinned Namingo Registry on a SeedEmu host.

    EPP is always enabled. WHOIS, RDAP, DAS, and the local Zone Writer are
    optional so small emulations do not need the complete production stack.
    The Zone Writer only produces validated zone files inside this Registry
    node; delivery to a separate hidden-primary DNS node is intentionally a
    separate SeedEmu integration boundary.
    """

    def __init__(self):
        super().__init__()
        self.__db_name = "registry"
        self.__db_user = "registryuser"
        self.__db_password = "seedemu-registry"
        self.__epp_host = "epp.registry.seedemu"
        self.__epp_port = 700
        self.__tlds: List[str] = ["com"]
        self.__roid = "SEED"
        self.__minimum_data = False
        self.__ns_mode = "hostObj"

        self.__registrar_name = "SeedEmu Registrar"
        self.__registrar_iana_id = 9999
        self.__registrar_clid = "seedemu"
        self.__registrar_password = "seedemu-epp"
        self.__registrar_prefix = "SEED"
        self.__registrar_email = "registrar@seedemu.test"
        self.__registrar_whois = "whois.registrar.seedemu"
        self.__registrar_rdap = "rdap.registrar.seedemu"
        self.__registrar_url = "http://registrar.seedemu"
        self.__registrar_abuse_email = "registrar@seedemu.test"
        self.__registrar_abuse_phone = "+1.5550100"
        self.__registrar_whitelist: List[str] = ["10.0.0.0/8"]
        self.__registrar_ssl_fingerprint: Optional[str] = None

        self.__enable_whois = False
        self.__enable_rdap = False
        self.__enable_das = False
        self.__whois_host = "whois.registry.seedemu"
        self.__rdap_url = "http://rdap.registry.seedemu"
        self.__expose_rdds_to_agent = False
        self.__zone_writer_config: Optional[dict] = None
        self.__zone_writer_interval = 30
        self.__zone_writer_custom_records: dict[str, List[dict]] = {}
        self.__zone_publisher: Optional[dict] = None

        self.__certificate_pem: Optional[str] = None
        self.__private_key_pem: Optional[str] = None
        self.__client_ca_pem: Optional[str] = None

    def getVersion(self) -> str:
        """Return the pinned upstream Namingo Registry version."""
        return NAMINGO_REGISTRY_VERSION

    def setDatabase(
        self, name: str, username: str, password: str
    ) -> NamingoRegistryServer:
        identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        assert identifier.fullmatch(name), "invalid MariaDB database name"
        assert name == "registry", (
            "Namingo's upstream MariaDB schema is qualified with the registry "
            "database name"
        )
        assert identifier.fullmatch(username), "invalid MariaDB username"
        assert password, "MariaDB password cannot be empty"
        self.__db_name = name
        self.__db_user = username
        self.__db_password = password
        return self

    def setEppEndpoint(
        self, hostname: str, port: int = 700
    ) -> NamingoRegistryServer:
        assert re.fullmatch(
            r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?",
            hostname,
        ), "invalid EPP hostname"
        assert 1 <= port <= 65535, "invalid EPP port"
        self.__epp_host = hostname.lower()
        self.__epp_port = port
        return self

    def setTlds(self, tlds: List[str]) -> NamingoRegistryServer:
        assert tlds, "at least one TLD is required"
        normalized = []
        for tld in tlds:
            value = tld.strip().lower().strip(".")
            assert value and len(value) <= 31, "invalid TLD"
            assert all(
                re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in value.split(".")
            ), "invalid TLD {}".format(tld)
            if value not in normalized:
                normalized.append(value)
        self.__tlds = normalized
        return self

    def setRoid(self, roid: str) -> NamingoRegistryServer:
        assert re.fullmatch(r"[A-Za-z0-9-]{2,16}", roid), "invalid ROID prefix"
        self.__roid = roid.upper()
        return self

    def setMinimumData(self, enabled: bool) -> NamingoRegistryServer:
        self.__minimum_data = enabled
        return self

    def setNameserverMode(self, mode: str) -> NamingoRegistryServer:
        assert mode in {"hostObj", "hostAttr"}, "unsupported nameserver mode"
        self.__ns_mode = mode
        return self

    def setRegistrar(
        self,
        identity: RegistrarIdentity,
        clid: str,
        password: str,
        prefix: str,
        whitelist: List[str],
        ssl_fingerprint: Optional[str] = None,
    ) -> NamingoRegistryServer:
        assert re.fullmatch(r"[A-Za-z0-9_.-]{1,16}", clid), "invalid registrar clid"
        assert password, "registrar EPP password cannot be empty"
        assert re.fullmatch(r"[A-Za-z0-9]{2,5}", prefix), "invalid registrar prefix"
        assert whitelist, "at least one registrar source address/CIDR is required"
        try:
            for item in whitelist:
                if "/" in item:
                    ipaddress.ip_network(item, strict=False)
                else:
                    ipaddress.ip_address(item)
        except ValueError as error:
            raise AssertionError("invalid registrar whitelist entry") from error
        if ssl_fingerprint is not None:
            normalized_fingerprint = ssl_fingerprint.replace(":", "").upper()
            assert re.fullmatch(r"[0-9A-F]{64}", normalized_fingerprint), (
                "registrar TLS fingerprint must be a SHA-256 fingerprint"
            )
        else:
            normalized_fingerprint = None
        self.__registrar_name = identity.name
        self.__registrar_iana_id = identity.iana_id
        self.__registrar_clid = clid
        self.__registrar_password = password
        self.__registrar_prefix = prefix.upper()
        self.__registrar_email = identity.email
        self.__registrar_whois = identity.whois_host
        self.__registrar_rdap = identity.rdap_host
        self.__registrar_url = identity.url.rstrip("/")
        self.__registrar_abuse_email = identity.abuse_email
        self.__registrar_abuse_phone = identity.abuse_phone
        self.__registrar_whitelist = list(dict.fromkeys(whitelist))
        self.__registrar_ssl_fingerprint = normalized_fingerprint
        return self

    def setTlsCertificate(
        self,
        certificate_pem: str,
        private_key_pem: str,
        client_ca_pem: Optional[str] = None,
    ) -> NamingoRegistryServer:
        """Install explicit EPP TLS material; a client CA enables mutual TLS."""
        assert "BEGIN CERTIFICATE" in certificate_pem, "invalid TLS certificate"
        assert "PRIVATE KEY" in private_key_pem, "invalid TLS private key"
        if client_ca_pem is not None:
            assert "BEGIN CERTIFICATE" in client_ca_pem, "invalid client CA certificate"
        self.__certificate_pem = certificate_pem
        self.__private_key_pem = private_key_pem
        self.__client_ca_pem = client_ca_pem
        return self

    def enableWhois(self, enabled: bool = True) -> NamingoRegistryServer:
        self.__enable_whois = enabled
        return self

    def enableRdap(self, enabled: bool = True) -> NamingoRegistryServer:
        self.__enable_rdap = enabled
        return self

    def setRddsEndpoints(
        self, whois_host: str, rdap_url: str
    ) -> NamingoRegistryServer:
        """Set the public names advertised by Registry WHOIS and RDAP."""
        hostname = re.compile(
            r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        )
        assert hostname.fullmatch(whois_host), "invalid WHOIS hostname"
        parsed_rdap = urlparse(rdap_url)
        assert (
            parsed_rdap.scheme in {"http", "https"}
            and parsed_rdap.netloc
            and parsed_rdap.username is None
            and parsed_rdap.password is None
            and not parsed_rdap.query
            and not parsed_rdap.fragment
        ), "invalid RDAP base URL"
        self.__whois_host = whois_host.lower()
        self.__rdap_url = rdap_url.rstrip("/")
        return self

    def exposeRddsToAgent(self, enabled: bool = True) -> NamingoRegistryServer:
        """Publish enabled Registry RDDS endpoints for metadata-driven Agent lookup."""
        self.__expose_rdds_to_agent = enabled
        return self

    def enableDas(self, enabled: bool = True) -> NamingoRegistryServer:
        self.__enable_das = enabled
        return self

    def configureZoneWriter(
        self,
        nameservers: dict[str, str],
        soa_contact: str,
        interval_seconds: int = 30,
        initial_serial: int = 1,
        reload_dns: bool = False,
        zone_mode: str = "default",
        dns_server: str = "bind",
    ) -> NamingoRegistryServer:
        """Configure the upstream writer using this Registry's database."""
        assert self.__zone_writer_config is None, "Zone Writer is already configured"
        assert nameservers, "at least one Zone Writer nameserver is required"
        hostname = re.compile(
            r"(?=.{1,253}\.?$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.?"
        )
        assert all(re.fullmatch(r"[A-Za-z0-9_-]{1,63}", name)
                   for name in nameservers), "invalid Zone Writer nameserver name"
        assert all(hostname.fullmatch(value) for value in nameservers.values()), (
            "invalid Zone Writer nameserver hostname"
        )
        assert hostname.fullmatch(soa_contact), "invalid Zone Writer SOA contact"
        assert interval_seconds >= 5, "Zone Writer interval must be at least 5 seconds"
        assert initial_serial >= 1, "Zone Writer serial must be positive"
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,32}", zone_mode), (
            "invalid Zone Writer mode"
        )
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,32}", dns_server), (
            "invalid Zone Writer DNS server"
        )
        self.__zone_writer_config = {
            "dns_server": dns_server,
            "ns": dict(nameservers),
            "dns_soa": soa_contact,
            "dns_serial": initial_serial,
            "dns_reload": reload_dns,
            "zone_mode": zone_mode,
        }
        self.__zone_writer_interval = interval_seconds
        return self

    def addZoneWriterRecord(
        self, tld: str, name: str, record_type: str, parameters: List[str]
    ) -> NamingoRegistryServer:
        """Add one static record retained in a Zone Writer TLD snapshot."""
        zone = tld.strip().lower().strip(".")
        assert re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", zone
        ), "Zone Writer record TLD must be a single DNS label"
        normalized_name = name.strip().lower().rstrip(".")
        assert normalized_name == "@" or all(
            re.fullmatch(r"[a-z0-9_*](?:[a-z0-9_*-]{0,61}[a-z0-9_*])?", label)
            for label in normalized_name.split(".")
        ), "invalid Zone Writer record name"
        normalized_type = record_type.strip().upper()
        assert re.fullmatch(r"[A-Z][A-Z0-9]{0,15}", normalized_type), (
            "invalid Zone Writer record type"
        )
        assert parameters and all(
            isinstance(value, str) and value and "\n" not in value and "\r" not in value
            for value in parameters
        ), "invalid Zone Writer record parameters"
        if normalized_type in {"A", "AAAA"}:
            assert len(parameters) == 1, "address records require one parameter"
            address = ipaddress.ip_address(parameters[0])
            assert (normalized_type == "A") == (address.version == 4), (
                "Zone Writer address family does not match record type"
            )
        self.__zone_writer_custom_records.setdefault(zone, []).append({
            "name": normalized_name,
            "type": normalized_type,
            "parameters": list(parameters),
        })
        return self

    def setZonePublisher(
        self,
        zonename: str,
        primary_ip: str,
        private_key: str,
        primary_host_public_key: str,
        zone_file: Optional[str] = None,
        secondary_ips: Optional[List[str]] = None,
        secondary_wait_seconds: int = 90,
    ) -> NamingoRegistryServer:
        """Publish a zone and optionally wait for authoritative secondaries."""
        zone = zonename.strip().lower().strip(".")
        assert zone and all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in zone.split(".")
        ), "invalid publisher zone name"
        ipaddress.ip_address(primary_ip)
        assert "BEGIN OPENSSH PRIVATE KEY" in private_key, "invalid publisher private key"
        assert primary_host_public_key.startswith("ssh-ed25519 "), (
            "primary host key must be an Ed25519 public key"
        )
        output_path = zone_file or "/var/lib/bind/{}.zone".format(zone)
        assert output_path.startswith("/"), "zone file path must be absolute"
        assert "\n" not in output_path, "invalid zone file path"
        secondaries = list(dict.fromkeys(secondary_ips or []))
        for address in secondaries:
            ipaddress.ip_address(address)
        assert primary_ip not in secondaries, "primary cannot also be a secondary"
        assert secondary_wait_seconds >= 1, "secondary wait must be positive"
        self.__zone_publisher = {
            "zone": zone + ".",
            "primary_ip": primary_ip,
            "private_key": private_key.strip() + "\n",
            "host_public_key": primary_host_public_key.strip(),
            "zone_file": output_path,
            "secondary_ips": secondaries,
            "secondary_wait_seconds": secondary_wait_seconds,
        }
        return self

    @staticmethod
    def _secondary_wait_script(publisher: dict) -> str:
        """Render direct SOA polling for configured public secondaries."""
        addresses = publisher["secondary_ips"]
        if not addresses:
            return ""
        return '''secondary_addresses='{addresses}'
remaining={wait_seconds}
while true; do
    all_ready=true
    for server in $secondary_addresses; do
        observed_serial=$(dig +short +time=2 +tries=1 "@$server" {zone} SOA |
            awk '{{ print $3; exit }}')
        if [ "$observed_serial" != "$expected_serial" ]; then
            all_ready=false
        fi
    done
    if "$all_ready"; then
        echo "public secondaries reached {zone} serial $expected_serial"
        break
    fi
    remaining=$((remaining - 1))
    if [ "$remaining" -le 0 ]; then
        echo "public secondaries did not reach {zone} serial $expected_serial" >&2
        exit 1
    fi
    sleep 1
done'''.format(
            addresses=" ".join(addresses),
            wait_seconds=publisher["secondary_wait_seconds"],
            zone=publisher["zone"],
        )

    def _database_config(self) -> dict:
        return {
            "db_type": "mysql",
            "db_host": "127.0.0.1",
            "db_port": 3306,
            "db_database": self.__db_name,
            "db_username": self.__db_user,
            "db_password": self.__db_password,
        }

    def _php_config(self, settings: dict) -> str:
        body = ",\n".join(
            "    {} => {}".format(_php(key), _php(value))
            for key, value in settings.items()
        )
        return "<?php\nreturn [\n{}\n];\n".format(body)

    def _zone_writer_config(self) -> str:
        assert self.__zone_writer_config is not None
        settings = self._database_config()
        settings.update(self.__zone_writer_config)
        return self._php_config(settings)

    def _zone_writer_records(self, records: List[dict]) -> str:
        return "<?php\nreturn {};\n".format(_php(records))

    def _epp_config(self) -> str:
        settings = self._database_config()
        settings.update(
            {
                "epp_host": "0.0.0.0",
                "epp_port": self.__epp_port,
                "epp_pid": "/run/epp.pid",
                "epp_greeting": "SeedEmu Namingo EPP Server",
                "epp_prefix": "namingo",
                "ssl_cert": "/opt/seedemu/namingo/tls/epp.crt",
                "ssl_key": "/opt/seedemu/namingo/tls/epp.key",
                "test_tlds": ",".join("." + tld for tld in self.__tlds),
                "rately": False,
                "limit": 1000,
                "period": 60,
                "minimum_data": self.__minimum_data,
                "ns_mode": self.__ns_mode,
                "epp_max_frame": 4 * 1024 * 1024,
                "mandatory_client_ssl": self.__client_ca_pem is not None,
                "ssl_client_ca": (
                    "/opt/seedemu/namingo/tls/registrar-ca.crt"
                    if self.__client_ca_pem is not None
                    else "/etc/ssl/certs/ca-certificates.crt"
                ),
            }
        )
        return self._php_config(settings)

    def _whois_config(self) -> str:
        settings = self._database_config()
        settings.update(
            {
                "whois_ipv4": "0.0.0.0",
                "whois_ipv6": False,
                "privacy": False,
                "minimum_data": self.__minimum_data,
                "limited_whois": False,
                "roid": self.__roid,
                "rately": False,
                "limit": 25,
                "period": 60,
            }
        )
        return self._php_config(settings)

    def _rdap_config(self) -> str:
        settings = self._database_config()
        settings.update(
            {
                "roid": self.__roid,
                "minimum_data": self.__minimum_data,
                "limited_rdap": False,
                "registry_url": "http://registry.seedemu/rdap-terms",
                "rdap_url": self.__rdap_url,
                "rately": False,
                "limit": 1000,
                "period": 60,
            }
        )
        return self._php_config(settings)

    def _das_config(self) -> str:
        settings = self._database_config()
        settings.update(
            {
                "das_ipv4": "0.0.0.0",
                "das_ipv6": False,
                "rately": False,
                "limit": 1000,
                "period": 60,
            }
        )
        return self._php_config(settings)

    def _database_init(self) -> str:
        return """\
CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `registryTransaction` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS {username}@'127.0.0.1' IDENTIFIED BY {password};
GRANT ALL PRIVILEGES ON `{database}`.* TO {username}@'127.0.0.1';
GRANT ALL PRIVILEGES ON `registryTransaction`.* TO {username}@'127.0.0.1';
FLUSH PRIVILEGES;
""".format(
            database=self.__db_name,
            username=_sql_string(self.__db_user),
            password=_sql_string(self.__db_password),
        )

    def _bootstrap_php(self) -> str:
        values = {
            "database": self.__db_name,
            "tlds": self.__tlds,
            "registrar_name": self.__registrar_name,
            "registrar_iana_id": self.__registrar_iana_id,
            "registrar_clid": self.__registrar_clid,
            "registrar_password": self.__registrar_password,
            "registrar_prefix": self.__registrar_prefix,
            "registrar_email": self.__registrar_email,
            "registrar_whois": self.__registrar_whois,
            "registrar_rdap": self.__registrar_rdap,
            "registrar_url": self.__registrar_url,
            "registrar_abuse_email": self.__registrar_abuse_email,
            "registrar_abuse_phone": self.__registrar_abuse_phone,
            "registrar_whitelist": self.__registrar_whitelist,
            "registrar_ssl_fingerprint": self.__registrar_ssl_fingerprint,
        }
        encoded = json.dumps(values, ensure_ascii=False).replace("</", "<\\/")
        return """<?php
declare(strict_types=1);

$settings = json_decode(<<<'JSON'
{settings}
JSON, true, 512, JSON_THROW_ON_ERROR);

$pdo = new PDO(
    'mysql:unix_socket=/run/mysqld/mysqld.sock;dbname=' . $settings['database'] . ';charset=utf8mb4',
    'root',
    '',
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
);

$pdo->beginTransaction();
try {{
    // Disable the public demonstration EPP credentials shipped in the sample schema.
    $disabled = password_hash(bin2hex(random_bytes(32)), PASSWORD_ARGON2ID);
    $stmt = $pdo->prepare('UPDATE registrar SET pw = :pw WHERE clid <> :clid');
    $stmt->execute(['pw' => $disabled, 'clid' => $settings['registrar_clid']]);

    // The upstream schema also ships .test and .com.test demonstration TLDs.
    // Remove only those untouched sample rows when this emulation did not ask
    // for them, so the upstream Zone Writer does not emit unrelated zones.
    $configuredTlds = array_map(
        static fn(string $tld): string => '.' . ltrim(strtolower($tld), '.'),
        $settings['tlds']
    );
    foreach (['.test', '.com.test'] as $sampleTld) {{
        if (in_array($sampleTld, $configuredTlds, true)) {{
            continue;
        }}
        $stmt = $pdo->prepare(
            'SELECT id FROM domain_tld WHERE tld = :tld '
            . 'AND NOT EXISTS (SELECT 1 FROM domain WHERE domain.tldid = domain_tld.id) '
            . 'AND NOT EXISTS (SELECT 1 FROM application WHERE application.tldid = domain_tld.id)'
        );
        $stmt->execute(['tld' => $sampleTld]);
        $sampleTldId = $stmt->fetchColumn();
        if ($sampleTldId !== false) {{
            $pdo->prepare('DELETE FROM domain_restore_price WHERE tldid = :id')
                ->execute(['id' => $sampleTldId]);
            $pdo->prepare('DELETE FROM domain_price WHERE tldid = :id')
                ->execute(['id' => $sampleTldId]);
            $pdo->prepare('DELETE FROM domain_tld WHERE id = :id')
                ->execute(['id' => $sampleTldId]);
        }}
    }}

    $tldPattern = '/^(?!-)(?!.*--)[A-Z0-9-]{{1,63}}(?<!-)(\\.(?!-)(?!.*--)[A-Z0-9-]{{1,63}}(?<!-))*$/i';
    $insertTld = $pdo->prepare(
        'INSERT INTO domain_tld (tld, idn_table, secure, launch_phase_id) '
        . 'VALUES (:tld, :pattern, 0, NULL) ON DUPLICATE KEY UPDATE tld = VALUES(tld)'
    );
    $findTld = $pdo->prepare('SELECT id FROM domain_tld WHERE tld = :tld');
    $insertPrice = $pdo->prepare(
        'INSERT INTO domain_price '
        . '(tldid, registrar_id, command, m0, m12, m24, m36, m48, m60, m72, m84, m96, m108, m120) '
        . "VALUES (:tldid, NULL, :command, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50) "
        . 'ON DUPLICATE KEY UPDATE m12 = VALUES(m12)'
    );
    foreach ($settings['tlds'] as $tld) {{
        $fqdn = '.' . $tld;
        $insertTld->execute(['tld' => $fqdn, 'pattern' => $tldPattern]);
        $findTld->execute(['tld' => $fqdn]);
        $tldId = (int) $findTld->fetchColumn();
        foreach (['create', 'renew', 'transfer'] as $command) {{
            $insertPrice->execute(['tldid' => $tldId, 'command' => $command]);
        }}
    }}

    $registrarPassword = password_hash($settings['registrar_password'], PASSWORD_ARGON2ID);
    $stmt = $pdo->prepare(
        'INSERT INTO registrar '
        . '(name, iana_id, clid, pw, prefix, email, whois_server, rdap_server, url, '
        . 'abuse_email, abuse_phone, accountBalance, creditLimit, creditThreshold, '
        . 'thresholdType, currency, ssl_fingerprint, crdate) '
        . "VALUES (:name, :iana, :clid, :pw, :prefix, :email, :whois, "
        . ":rdap, :url, :abuse_email, :abuse_phone, "
        . "100000, 100000, 500, 'fixed', 'USD', :ssl_fingerprint, CURRENT_TIMESTAMP) "
        . 'ON DUPLICATE KEY UPDATE name = VALUES(name), iana_id = VALUES(iana_id), '
        . 'pw = VALUES(pw), prefix = VALUES(prefix), email = VALUES(email), '
        . 'whois_server = VALUES(whois_server), rdap_server = VALUES(rdap_server), '
        . 'url = VALUES(url), abuse_email = VALUES(abuse_email), '
        . 'abuse_phone = VALUES(abuse_phone), '
        . 'ssl_fingerprint = VALUES(ssl_fingerprint)'
    );
    $stmt->execute([
        'name' => $settings['registrar_name'],
        'iana' => $settings['registrar_iana_id'],
        'clid' => $settings['registrar_clid'],
        'pw' => $registrarPassword,
        'prefix' => $settings['registrar_prefix'],
        'email' => $settings['registrar_email'],
        'whois' => $settings['registrar_whois'],
        'rdap' => $settings['registrar_rdap'],
        'url' => $settings['registrar_url'],
        'abuse_email' => $settings['registrar_abuse_email'],
        'abuse_phone' => $settings['registrar_abuse_phone'],
        'ssl_fingerprint' => $settings['registrar_ssl_fingerprint'],
    ]);
    $stmt = $pdo->prepare('SELECT id FROM registrar WHERE clid = :clid');
    $stmt->execute(['clid' => $settings['registrar_clid']]);
    $registrarId = (int) $stmt->fetchColumn();
    $pdo->prepare('DELETE FROM registrar_whitelist WHERE registrar_id = :id')
        ->execute(['id' => $registrarId]);
    $stmt = $pdo->prepare(
        'INSERT INTO registrar_whitelist (registrar_id, addr) VALUES (:id, :addr)'
    );
    foreach ($settings['registrar_whitelist'] as $address) {{
        $stmt->execute(['id' => $registrarId, 'addr' => $address]);
    }}
    $pdo->commit();
}} catch (Throwable $error) {{
    if ($pdo->inTransaction()) {{
        $pdo->rollBack();
    }}
    throw $error;
}}
""".format(settings=encoded)

    def _start_script(self) -> str:
        commands = [
            "/usr/bin/php8.5 /opt/registry/epp/start_epp.php "
            ">>/var/log/namingo/epp.stdout.log 2>&1 &"
        ]
        if self.__enable_whois:
            commands.append(
                "/usr/bin/php8.5 /opt/registry/whois/port43/start_whois.php "
                ">>/var/log/namingo/whois.stdout.log 2>&1 &"
            )
        if self.__enable_rdap:
            commands.append(
                "/usr/bin/php8.5 /opt/registry/rdap/start_rdap.php "
                ">>/var/log/namingo/rdap.stdout.log 2>&1 &"
            )
            commands.append("service nginx start")
        if self.__enable_das:
            commands.append(
                "/usr/bin/php8.5 /opt/registry/das/start_das.php "
                ">>/var/log/namingo/das.stdout.log 2>&1 &"
            )
        if self.__zone_writer_config is not None:
            writer_command = "/usr/bin/php8.5 /opt/registry/automation/write-zone.php"
            if self.__zone_publisher is not None:
                writer_command = "/usr/local/bin/seedemu-publish-namingo-zone"
            commands.append(
                "while true; do {} || echo 'zone publication failed; retrying'; "
                "sleep {}; done >>/var/log/namingo/write-zone.stdout.log 2>&1 &".format(
                    writer_command,
                    self.__zone_writer_interval
                )
            )
        return """#!/bin/sh
set -eu

service mariadb start
service redis-server start
until mariadb-admin ping --silent; do sleep 1; done
mariadb < /opt/seedemu/namingo/init.sql

if ! mariadb -Nse "SELECT 1 FROM information_schema.tables WHERE table_schema='{database}' AND table_name='users'" | grep -q 1; then
    mariadb < /opt/registry/database/registry.mariadb.sql
fi

/usr/bin/php8.5 /opt/seedemu/namingo/bootstrap.php
mkdir -p /var/log/namingo /run /var/lib/bind /opt/seedemu/namingo/tls

if [ ! -s /opt/seedemu/namingo/tls/epp.crt ] || [ ! -s /opt/seedemu/namingo/tls/epp.key ]; then
    openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 14 \
        -subj '/CN={epp_host}' -addext 'subjectAltName=DNS:{epp_host}' \
        -keyout /opt/seedemu/namingo/tls/epp.key \
        -out /opt/seedemu/namingo/tls/epp.crt
fi
chmod 600 /opt/seedemu/namingo/tls/epp.key

{commands}
""".format(
            database=self.__db_name,
            epp_host=self.__epp_host,
            commands="\n".join(commands),
        )

    def install(self, node: Node):
        assert not self.__zone_writer_custom_records or self.__zone_writer_config is not None, (
            "Zone Writer records require configureZoneWriter()"
        )
        assert all(tld in self.__tlds for tld in self.__zone_writer_custom_records), (
            "Zone Writer records require a configured Registry TLD"
        )
        components = ["epp"]
        if self.__enable_whois:
            components.append("whois/port43")
        if self.__enable_rdap:
            components.append("rdap")
        if self.__enable_das:
            components.append("das")
        if self.__zone_writer_config is not None:
            components.append("automation")

        node.appendClassName("NamingoRegistryService")
        node.setLabel(NAMINGO_REGISTRY_LABEL_META.format(key="role"), "registry")
        node.setLabel(
            NAMINGO_REGISTRY_LABEL_META.format(key="version"),
            NAMINGO_REGISTRY_VERSION,
        )
        node.setLabel(
            NAMINGO_REGISTRY_LABEL_META.format(key="components"),
            ",".join(components),
        )
        node.setLabel(
            NAMINGO_REGISTRY_LABEL_META.format(key="tlds"),
            ",".join(self.__tlds),
        )
        if self.__expose_rdds_to_agent:
            node.setLabel(AGENT_RDDS_LABEL_META.format(key="authority"), "registry")
            if self.__enable_whois:
                node.setLabel(
                    AGENT_RDDS_LABEL_META.format(key="whois_server"), self.__whois_host
                )
            if self.__enable_rdap:
                node.setLabel(
                    AGENT_RDDS_LABEL_META.format(key="rdap_url"), self.__rdap_url
                )

        software = (
            "ca-certificates curl git gnupg2 mariadb-client mariadb-server "
            "openssl redis-server software-properties-common unzip"
        )
        if self.__enable_rdap:
            software += " nginx-light"
        if self.__zone_writer_config is not None:
            software += " bind9-utils"
        if self.__zone_publisher is not None:
            assert self.__zone_writer_config is not None, (
                "zone publisher requires configureZoneWriter()"
            )
            software += " openssh-client"
        node.addSoftware(software)
        node.addBuildCommand("add-apt-repository -y ppa:ondrej/php")
        node.addBuildCommand("apt-get update")
        php_packages = (
            "composer php8.5-cli php8.5-common php8.5-curl php8.5-gmp "
            "php8.5-intl php8.5-mbstring php8.5-mysql php8.5-swoole "
            "php8.5-redis php8.5-xml php8.5-zip"
        )
        if self.__zone_writer_config is not None:
            php_packages += " php8.5-bcmath php8.5-bz2 php8.5-gd php8.5-yaml"
        node.addBuildCommand(
            "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "
            + php_packages
        )
        node.addBuildCommand(
            "git clone --filter=blob:none {} {} && "
            "git -C {} checkout {} && "
            "test \"$(git -C {} rev-parse HEAD)\" = {}".format(
                NAMINGO_REGISTRY_REPOSITORY,
                NAMINGO_REGISTRY_INSTALL_DIR,
                NAMINGO_REGISTRY_INSTALL_DIR,
                NAMINGO_REGISTRY_VERSION,
                NAMINGO_REGISTRY_INSTALL_DIR,
                NAMINGO_REGISTRY_COMMIT,
            )
        )
        node.addBuildCommand(
            "sed -i "
            "'s/named-checkzone {{$escapedZone}} {{$escapedPath}}/"
            "named-checkzone -i local {{$escapedZone}} {{$escapedPath}}/' "
            "{}/automation/helpers.php && "
            "grep -Fq 'named-checkzone -i local' {}/automation/helpers.php".format(
                NAMINGO_REGISTRY_INSTALL_DIR,
                NAMINGO_REGISTRY_INSTALL_DIR,
            )
        )
        for component in components:
            node.addBuildCommand(
                "COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --no-interaction "
                "--prefer-dist --working-dir={}/{}".format(
                    NAMINGO_REGISTRY_INSTALL_DIR, component
                )
            )

        node.setFile("/opt/registry/epp/config.php", self._epp_config())
        if self.__enable_whois:
            node.setFile(
                "/opt/registry/whois/port43/config.php", self._whois_config()
            )
        if self.__enable_rdap:
            node.setFile("/opt/registry/rdap/config.php", self._rdap_config())
            node.setFile(
                "/etc/nginx/sites-available/default",
                """server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:7500;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
""",
            )
        if self.__enable_das:
            node.setFile("/opt/registry/das/config.php", self._das_config())
        if self.__zone_writer_config is not None:
            node.setFile(
                "/opt/registry/automation/config.php", self._zone_writer_config()
            )
            for tld, records in self.__zone_writer_custom_records.items():
                node.setFile(
                    "/opt/registry/automation/{}.php".format(tld),
                    self._zone_writer_records(records),
                )
        if self.__zone_publisher is not None:
            publisher = self.__zone_publisher
            known_host_key = " ".join(publisher["host_public_key"].split()[:2])
            node.setFile(
                "/opt/seedemu/namingo/zone-publisher-key",
                publisher["private_key"],
            )
            node.setFile(
                "/opt/seedemu/namingo/known_hosts",
                "{} {}\n".format(publisher["primary_ip"], known_host_key),
            )
            node.setFile(
                "/usr/local/bin/seedemu-publish-namingo-zone",
                '''#!/bin/sh
set -eu

/usr/bin/php8.5 /opt/registry/automation/write-zone.php
test -s {zone_file}
expected_serial=$(named-checkzone -i none -D -o - {zone} {zone_file} 2>/dev/null |
    awk '$4 == "SOA" {{ print $7; exit }}')
test -n "$expected_serial"
ssh -T -i /opt/seedemu/namingo/zone-publisher-key \\
    -o BatchMode=yes \\
    -o IdentitiesOnly=yes \\
    -o StrictHostKeyChecking=yes \\
    -o UserKnownHostsFile=/opt/seedemu/namingo/known_hosts \\
    root@{primary_ip} {receiver_command} < {zone_file}
{secondary_wait}
'''.format(
                    zone_file=publisher["zone_file"],
                    primary_ip=publisher["primary_ip"],
                    receiver_command="/usr/local/sbin/seedemu-install-zone-{}".format(
                        publisher["zone"].rstrip(".")
                    ),
                    zone=publisher["zone"],
                    secondary_wait=self._secondary_wait_script(publisher),
                ),
            )

        node.setFile("/opt/seedemu/namingo/init.sql", self._database_init())
        node.setFile("/opt/seedemu/namingo/bootstrap.php", self._bootstrap_php())
        if self.__certificate_pem is not None:
            node.setFile(
                "/opt/seedemu/namingo/tls/epp.crt", self.__certificate_pem
            )
            node.setFile(
                "/opt/seedemu/namingo/tls/epp.key", self.__private_key_pem
            )
        if self.__client_ca_pem is not None:
            node.setFile(
                "/opt/seedemu/namingo/tls/registrar-ca.crt",
                self.__client_ca_pem,
            )
        node.setFile("/usr/local/bin/seedemu-start-namingo-registry", self._start_script())
        if self.__zone_publisher is not None:
            node.appendStartCommand(
                "chmod 0600 /opt/seedemu/namingo/zone-publisher-key"
            )
            node.appendStartCommand(
                "chmod 0644 /opt/seedemu/namingo/known_hosts"
            )
            node.appendStartCommand(
                "chmod 0755 /usr/local/bin/seedemu-publish-namingo-zone"
            )
        node.addBuildCommandAtEnd(
            "chmod +x /usr/local/bin/seedemu-start-namingo-registry"
        )
        node.appendStartCommand("/usr/local/bin/seedemu-start-namingo-registry")

    def print(self, indent: int) -> str:
        return " " * indent + "NamingoRegistryServer\n"


class NamingoRegistryService(Service):
    """SeedEmu service layer for Namingo Registry instances."""

    def __init__(self):
        super().__init__()
        self.addDependency("Base", False, False)

    @staticmethod
    def generateEppTlsCredentials(
        server_hostname: str,
        client_name: str,
        validity_days: int = 3650,
    ) -> EppTlsCredentials:
        """Generate a CA-signed EPP server/client mutual-TLS credential set."""
        hostname_pattern = (
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
        )
        assert re.fullmatch(hostname_pattern, server_hostname), (
            "invalid EPP server hostname"
        )
        assert re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", client_name), (
            "invalid EPP client name"
        )
        assert validity_days >= 1, "TLS validity must be at least one day"

        with tempfile.TemporaryDirectory() as work:
            directory = Path(work)
            ca_key = directory / "ca.key"
            ca_cert = directory / "ca.crt"
            server_key = directory / "server.key"
            server_csr = directory / "server.csr"
            server_cert = directory / "server.crt"
            server_ext = directory / "server.ext"
            client_key = directory / "client.key"
            client_csr = directory / "client.csr"
            client_cert = directory / "client.crt"
            client_ext = directory / "client.ext"

            def run_openssl(*arguments: str) -> None:
                subprocess.run(
                    ["openssl", *arguments], check=True, capture_output=True
                )

            run_openssl(
                "ecparam", "-name", "prime256v1", "-genkey", "-noout",
                "-out", str(ca_key),
            )
            run_openssl(
                "req", "-new", "-x509", "-sha256", "-days", str(validity_days),
                "-key", str(ca_key), "-out", str(ca_cert),
                "-subj", "/CN=SeedEmu EPP CA",
                "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            )

            server_ext.write_text(
                "basicConstraints=critical,CA:FALSE\n"
                "keyUsage=critical,digitalSignature,keyAgreement\n"
                "extendedKeyUsage=serverAuth\n"
                "subjectAltName=DNS:{}\n".format(server_hostname)
            )
            run_openssl(
                "ecparam", "-name", "prime256v1", "-genkey", "-noout",
                "-out", str(server_key),
            )
            run_openssl(
                "req", "-new", "-sha256", "-key", str(server_key),
                "-out", str(server_csr), "-subj", "/CN={}".format(server_hostname),
            )
            run_openssl(
                "x509", "-req", "-sha256", "-days", str(validity_days),
                "-in", str(server_csr), "-CA", str(ca_cert),
                "-CAkey", str(ca_key), "-CAcreateserial",
                "-out", str(server_cert), "-extfile", str(server_ext),
            )

            client_ext.write_text(
                "basicConstraints=critical,CA:FALSE\n"
                "keyUsage=critical,digitalSignature,keyAgreement\n"
                "extendedKeyUsage=clientAuth\n"
            )
            run_openssl(
                "ecparam", "-name", "prime256v1", "-genkey", "-noout",
                "-out", str(client_key),
            )
            run_openssl(
                "req", "-new", "-sha256", "-key", str(client_key),
                "-out", str(client_csr), "-subj", "/CN={}".format(client_name),
            )
            run_openssl(
                "x509", "-req", "-sha256", "-days", str(validity_days),
                "-in", str(client_csr), "-CA", str(ca_cert),
                "-CAkey", str(ca_key), "-CAcreateserial",
                "-out", str(client_cert), "-extfile", str(client_ext),
            )

            client_certificate = client_cert.read_text()
            client_der = ssl.PEM_cert_to_DER_cert(client_certificate)
            return EppTlsCredentials(
                ca_certificate=ca_cert.read_text(),
                server_certificate=server_cert.read_text(),
                server_private_key=server_key.read_text(),
                client_certificate=client_certificate,
                client_private_key=client_key.read_text(),
                client_sha256_fingerprint=hashlib.sha256(client_der).hexdigest().upper(),
            )

    def getName(self) -> str:
        return "NamingoRegistryService"

    def _createServer(self) -> NamingoRegistryServer:
        return NamingoRegistryServer()

    def print(self, indent: int) -> str:
        return " " * indent + "NamingoRegistryService\n"
