from __future__ import annotations

import ipaddress
import json
import re
from typing import List, Optional

from seedemu.core import Node, Server, Service


NAMINGO_REGISTRY_REPOSITORY = "https://github.com/getnamingo/registry.git"
NAMINGO_REGISTRY_VERSION = "v1.0.33"
NAMINGO_REGISTRY_COMMIT = "a783a3c37a5614827f7141f07028e9a6a2d4f5cb"
NAMINGO_REGISTRY_INSTALL_DIR = "/opt/registry"
NAMINGO_REGISTRY_LABEL_META = "namingo.{key}"


def _php(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
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
        self.__registrar_whitelist: List[str] = ["10.0.0.0/8"]
        self.__registrar_ssl_fingerprint: Optional[str] = None

        self.__enable_whois = False
        self.__enable_rdap = False
        self.__enable_das = False
        self.__zone_writer_config: Optional[str] = None
        self.__zone_writer_interval = 30
        self.__zone_writer_custom_records: dict[str, str] = {}
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
        clid: str,
        password: str,
        prefix: str,
        whitelist: List[str],
        name: str = "SeedEmu Registrar",
        iana_id: int = 9999,
        email: str = "registrar@seedemu.test",
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
        assert 0 <= iana_id <= 99999, "invalid registrar IANA id"
        assert "@" in email, "invalid registrar email"
        if ssl_fingerprint is not None:
            normalized_fingerprint = ssl_fingerprint.replace(":", "").upper()
            assert re.fullmatch(r"[0-9A-F]{64}", normalized_fingerprint), (
                "registrar TLS fingerprint must be a SHA-256 fingerprint"
            )
        else:
            normalized_fingerprint = None
        self.__registrar_name = name
        self.__registrar_iana_id = iana_id
        self.__registrar_clid = clid
        self.__registrar_password = password
        self.__registrar_prefix = prefix.upper()
        self.__registrar_email = email
        self.__registrar_whitelist = list(dict.fromkeys(whitelist))
        self.__registrar_ssl_fingerprint = normalized_fingerprint
        return self

    def enableWhois(self, enabled: bool = True) -> NamingoRegistryServer:
        self.__enable_whois = enabled
        return self

    def enableRdap(self, enabled: bool = True) -> NamingoRegistryServer:
        self.__enable_rdap = enabled
        return self

    def enableDas(self, enabled: bool = True) -> NamingoRegistryServer:
        self.__enable_das = enabled
        return self

    def enableZoneWriter(
        self, config_php: str, interval_seconds: int = 30
    ) -> NamingoRegistryServer:
        """Enable the upstream writer that produces local TLD zone files."""
        assert config_php.strip(), "Zone Writer config cannot be empty"
        assert interval_seconds >= 5, "Zone Writer interval must be at least 5 seconds"
        self.__zone_writer_config = config_php
        self.__zone_writer_interval = interval_seconds
        return self

    def setZonePublisher(
        self,
        zonename: str,
        primary_ip: str,
        private_key: str,
        primary_host_public_key: str,
        zone_file: Optional[str] = None,
    ) -> NamingoRegistryServer:
        """Publish a Zone Writer output file to a restricted SSH receiver."""
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
        self.__zone_publisher = {
            "zone": zone + ".",
            "primary_ip": primary_ip,
            "private_key": private_key.strip() + "\n",
            "host_public_key": primary_host_public_key.strip(),
            "zone_file": output_path,
        }
        return self

    def setZoneWriterCustomRecords(
        self, tld: str, records_php: str
    ) -> NamingoRegistryServer:
        """Install a TLD-specific custom-record file used by Zone Writer."""
        zone = tld.strip().lower().strip(".")
        assert re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", zone
        ), "custom-record TLD must be a single DNS label"
        assert records_php.strip().startswith("<?php"), "invalid custom records PHP"
        self.__zone_writer_custom_records[zone] = records_php.strip() + "\n"
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
                "rdap_url": "http://rdap.registry.seedemu",
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
        . "VALUES (:name, :iana, :clid, :pw, :prefix, :email, 'whois.registrar.seedemu', "
        . "'rdap.registrar.seedemu', 'http://registrar.seedemu', :email, '+1.5550100', "
        . "100000, 100000, 500, 'fixed', 'USD', :ssl_fingerprint, CURRENT_TIMESTAMP) "
        . 'ON DUPLICATE KEY UPDATE name = VALUES(name), iana_id = VALUES(iana_id), '
        . 'pw = VALUES(pw), prefix = VALUES(prefix), email = VALUES(email), '
        . 'ssl_fingerprint = VALUES(ssl_fingerprint)'
    );
    $stmt->execute([
        'name' => $settings['registrar_name'],
        'iana' => $settings['registrar_iana_id'],
        'clid' => $settings['registrar_clid'],
        'pw' => $registrarPassword,
        'prefix' => $settings['registrar_prefix'],
        'email' => $settings['registrar_email'],
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
                "zone publisher requires enableZoneWriter()"
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
                "/opt/registry/automation/config.php", self.__zone_writer_config
            )
            for tld, records_php in self.__zone_writer_custom_records.items():
                node.setFile(
                    "/opt/registry/automation/{}.php".format(tld), records_php
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
ssh -T -i /opt/seedemu/namingo/zone-publisher-key \\
    -o BatchMode=yes \\
    -o IdentitiesOnly=yes \\
    -o StrictHostKeyChecking=yes \\
    -o UserKnownHostsFile=/opt/seedemu/namingo/known_hosts \\
    root@{primary_ip} {receiver_command} < {zone_file}
'''.format(
                    zone_file=publisher["zone_file"],
                    primary_ip=publisher["primary_ip"],
                    receiver_command="/usr/local/sbin/seedemu-install-zone-{}".format(
                        publisher["zone"].rstrip(".")
                    ),
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

    def getName(self) -> str:
        return "NamingoRegistryService"

    def _createServer(self) -> NamingoRegistryServer:
        return NamingoRegistryServer()

    def print(self, indent: int) -> str:
        return " " * indent + "NamingoRegistryService\n"
