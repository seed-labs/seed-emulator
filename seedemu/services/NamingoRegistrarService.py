from __future__ import annotations

import json
import re
from typing import Optional

from seedemu.core import Node, Server, Service


NAMINGO_REPOSITORY = "https://github.com/getnamingo/registrar.git"
NAMINGO_VERSION = "v1.2.3"
# Pin the tag to the commit inspected when this service was implemented.
NAMINGO_COMMIT = "1b7e0df07223082fb0e11c62f5db50c5e62d4498"
NAMINGO_INSTALL_DIR = "/opt/registrar"
NAMINGO_LABEL_META = "namingo.{key}"
NAMINGO_EPP_CLIENT_REPOSITORY = "https://github.com/getnamingo/epp-client.git"
NAMINGO_EPP_CLIENT_VERSION = "v1.1.22"
NAMINGO_EPP_CLIENT_COMMIT = "2a7610d286f75b74462b51dc2a6cf1a470ef863e"
NAMINGO_EPP_CLIENT_INSTALL_DIR = "/opt/namingo-epp-client"


def _php(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _sql_string(value: str) -> str:
    return "'{}'".format(value.replace("\\", "\\\\").replace("'", "''"))


class NamingoRegistrarServer(Server):
    """Install Namingo Registrar's WHOIS/RDAP toolkit on a SeedEmu host.

    Namingo Registrar is not itself a customer billing portal.  The selected
    backend database (FOSSBilling, WHMCS, Loom, or a custom adapter/schema) must
    be supplied by the emulation author.
    """

    def __init__(self):
        super().__init__()
        self.__backend = "custom"
        self.__db_name = "registrar"
        self.__db_user = "registraruser"
        self.__db_password = "seedemu-namingo"
        self.__schema_sql = ""
        self.__registrar_name = "SeedEmu Namingo Registrar"
        self.__registrar_iana = "9999"
        self.__registrar_url = "http://registrar.seedemu"
        self.__registrar_whois = "whois.registrar.seedemu"
        self.__rdap_url = "http://rdap.registrar.seedemu"
        self.__abuse_email = "abuse@registrar.seedemu"
        self.__abuse_phone = "+1.5550100"
        self.__privacy = True
        self.__minimum_data = False
        self.__enable_whois = True
        self.__enable_rdap = True
        self.__enable_automation = False
        self.__automation_config: Optional[str] = None
        self.__epp_config: Optional[dict] = None

    def getVersion(self) -> str:
        """Return the pinned upstream Namingo Registrar version."""
        return NAMINGO_VERSION

    def enableWhois(self, enabled: bool = True) -> NamingoRegistrarServer:
        """Enable or disable the Namingo WHOIS component."""
        self.__enable_whois = enabled
        return self

    def enableRdap(self, enabled: bool = True) -> NamingoRegistrarServer:
        """Enable or disable the Namingo RDAP component and its HTTP proxy."""
        self.__enable_rdap = enabled
        return self

    def setBackend(self, backend: str) -> NamingoRegistrarServer:
        backend = backend.lower()
        assert backend in {"foss", "whmcs", "loom", "custom"}, "unsupported Namingo backend"
        self.__backend = backend
        return self

    def setDatabase(
        self, name: str, username: str, password: str
    ) -> NamingoRegistrarServer:
        identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        assert identifier.fullmatch(name), "invalid MariaDB database name"
        assert identifier.fullmatch(username), "invalid MariaDB username"
        assert password, "MariaDB password cannot be empty"
        self.__db_name = name
        self.__db_user = username
        self.__db_password = password
        return self

    def setSchemaSql(self, sql: str) -> NamingoRegistrarServer:
        """Set the billing-platform schema/data imported on first boot."""
        assert sql.strip(), "schema SQL cannot be empty"
        self.__schema_sql = sql
        return self

    def setIdentity(
        self,
        name: str,
        iana_id: str,
        url: str,
        whois_host: str,
        rdap_url: str,
        abuse_email: str,
        abuse_phone: str,
    ) -> NamingoRegistrarServer:
        self.__registrar_name = name
        self.__registrar_iana = str(iana_id)
        self.__registrar_url = url.rstrip("/")
        self.__registrar_whois = whois_host
        self.__rdap_url = rdap_url.rstrip("/")
        self.__abuse_email = abuse_email
        self.__abuse_phone = abuse_phone
        return self

    def setPrivacy(self, enabled: bool) -> NamingoRegistrarServer:
        self.__privacy = enabled
        return self

    def setMinimumData(self, enabled: bool) -> NamingoRegistrarServer:
        self.__minimum_data = enabled
        return self

    def enableAutomation(self, config_php: str) -> NamingoRegistrarServer:
        """Enable Namingo cron automation with an explicit upstream config."""
        assert config_php.strip(), "automation config cannot be empty"
        self.__enable_automation = True
        self.__automation_config = config_php
        return self

    def enableEppClient(
        self,
        hostname: str,
        port: int,
        clid: str,
        password: str,
        ca_certificate_pem: str,
        tls_version: str = "1.2",
        client_certificate_pem: Optional[str] = None,
        client_private_key_pem: Optional[str] = None,
        probe_domain: str = "seedemu-epp-probe.com",
        probe_interval: int = 30,
    ) -> NamingoRegistrarServer:
        """Enable the official Namingo client with verified EPP over TLS."""
        assert re.fullmatch(
            r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?",
            hostname,
        ), "invalid EPP hostname"
        assert 1 <= port <= 65535, "invalid EPP port"
        assert re.fullmatch(r"[A-Za-z0-9_.-]{1,16}", clid), "invalid EPP clid"
        assert password, "EPP password cannot be empty"
        assert "BEGIN CERTIFICATE" in ca_certificate_pem, "invalid EPP CA certificate"
        assert tls_version in {"1.2", "1.3"}, "unsupported EPP TLS version"
        assert bool(client_certificate_pem) == bool(client_private_key_pem), (
            "EPP client certificate and private key must be supplied together"
        )
        if client_certificate_pem is not None:
            assert "BEGIN CERTIFICATE" in client_certificate_pem, "invalid EPP client certificate"
            assert "PRIVATE KEY" in client_private_key_pem, "invalid EPP client private key"
        normalized_probe = probe_domain.lower().rstrip(".")
        assert re.fullmatch(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?",
            normalized_probe,
        ), "invalid EPP probe domain"
        assert probe_interval >= 5, "EPP probe interval must be at least 5 seconds"
        self.__epp_config = {
            "hostname": hostname.lower(),
            "port": port,
            "clid": clid,
            "password": password,
            "ca": ca_certificate_pem.strip() + "\n",
            "tls": tls_version,
            "client_certificate": (
                client_certificate_pem.strip() + "\n"
                if client_certificate_pem is not None
                else None
            ),
            "client_key": (
                client_private_key_pem.strip() + "\n"
                if client_private_key_pem is not None
                else None
            ),
            "probe_domain": normalized_probe,
            "probe_interval": probe_interval,
        }
        return self

    def _epp_client_config(self) -> str:
        assert self.__epp_config is not None
        settings = {
            "host": self.__epp_config["hostname"],
            "port": self.__epp_config["port"],
            "clid": self.__epp_config["clid"],
            "password": self.__epp_config["password"],
            "tls": self.__epp_config["tls"],
            "cafile": "/opt/seedemu/namingo/epp-ca.crt",
            "local_cert": (
                "/opt/seedemu/namingo/epp-client.crt"
                if self.__epp_config["client_certificate"] is not None
                else ""
            ),
            "local_pk": (
                "/opt/seedemu/namingo/epp-client.key"
                if self.__epp_config["client_key"] is not None
                else ""
            ),
            "probe_domain": self.__epp_config["probe_domain"],
        }
        body = ",\n".join(
            "    {} => {}".format(_php(key), _php(value))
            for key, value in settings.items()
        )
        return "<?php\nreturn [\n{}\n];\n".format(body)

    def _epp_client_script(self) -> str:
        return r'''#!/usr/bin/php8.5
<?php
declare(strict_types=1);

require_once '/opt/namingo-epp-client/vendor/autoload.php';
use Pinga\Tembo\EppRegistryFactory;

$config = require '/opt/seedemu/namingo/epp-client.php';
$operation = $argv[1] ?? 'health';
$argument = $argv[2] ?? null;
$supported = [
    'health', 'check', 'contact-create', 'host-create', 'domain-create',
    'domain-update',
];
if (!in_array($operation, $supported, true)) {
    fwrite(STDERR, "usage: seedemu-epp-client OPERATION [DOMAIN|JSON]\n");
    fwrite(STDERR, "operations: health, check, contact-create, host-create, domain-create, domain-update\n");
    exit(2);
}

function payload(?string $argument): array
{
    if ($argument === null || trim($argument) === '') {
        throw new InvalidArgumentException('JSON payload is required');
    }
    $value = json_decode($argument, true, 32, JSON_THROW_ON_ERROR);
    if (!is_array($value)) {
        throw new InvalidArgumentException('JSON payload must be an object');
    }
    return $value;
}

function requireFields(array $value, array $fields): void
{
    foreach ($fields as $field) {
        if (!isset($value[$field]) || !is_string($value[$field]) || trim($value[$field]) === '') {
            throw new InvalidArgumentException("missing non-empty string field: {$field}");
        }
    }
}

function requireDnsName(string $value, string $field): void
{
    $name = strtolower(rtrim($value, '.'));
    if (strlen($name) > 253 || !preg_match(
        '/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/D',
        $name
    )) {
        throw new InvalidArgumentException("invalid DNS name in {$field}");
    }
}

function requireContactId(string $value, string $field): void
{
    if (!preg_match('/^[A-Za-z0-9_.:-]{1,64}$/D', $value)) {
        throw new InvalidArgumentException("invalid contact identifier in {$field}");
    }
}

try {
    $epp = EppRegistryFactory::create('generic');
    $epp->disableLogging();
    $epp->setLoginObjects([
        'urn:ietf:params:xml:ns:domain-1.0',
        'urn:ietf:params:xml:ns:contact-1.0',
        'urn:ietf:params:xml:ns:host-1.0',
    ]);
    $epp->setLoginExtensions([
        'urn:ietf:params:xml:ns:secDNS-1.1',
        'urn:ietf:params:xml:ns:rgp-1.0',
    ]);
    $epp->connect([
        'host' => $config['host'],
        'port' => $config['port'],
        'timeout' => 15,
        'tls' => $config['tls'],
        'bind' => false,
        'bindip' => '0.0.0.0:0',
        'verify_peer' => true,
        'verify_peer_name' => true,
        'cafile' => $config['cafile'],
        'local_cert' => $config['local_cert'],
        'local_pk' => $config['local_pk'],
        'passphrase' => '',
        'allow_self_signed' => false,
    ]);
    $login = $epp->login([
        'clID' => $config['clid'],
        'pw' => $config['password'],
        'prefix' => 'namingo',
    ]);
    if (isset($login['error']) || (int)($login['code'] ?? 0) !== 1000) {
        throw new RuntimeException('EPP login failed');
    }
    $result = null;
    $resource = null;
    if ($operation === 'health' || $operation === 'check') {
        $domain = $argument ?? $config['probe_domain'];
        requireDnsName($domain, 'domain');
        $result = $epp->domainCheck(['domains' => [$domain]]);
        $resource = $domain;
    } elseif ($operation === 'contact-create') {
        $input = payload($argument);
        requireFields($input, [
            'id', 'firstname', 'lastname', 'address1', 'city', 'postcode',
            'country', 'fullphonenumber', 'email', 'authInfoPw',
        ]);
        requireContactId($input['id'], 'id');
        if (!preg_match('/^[A-Z]{2}$/D', $input['country'])) {
            throw new InvalidArgumentException('country must be an ISO 3166-1 alpha-2 code');
        }
        $input += ['type' => 'int', 'companyname' => '', 'address2' => '', 'state' => ''];
        $result = $epp->contactCreate($input);
        $resource = $input['id'];
    } elseif ($operation === 'host-create') {
        $input = payload($argument);
        requireFields($input, ['hostname', 'ipaddress']);
        requireDnsName($input['hostname'], 'hostname');
        if (filter_var($input['ipaddress'], FILTER_VALIDATE_IP) === false) {
            throw new InvalidArgumentException('ipaddress must be an IPv4 or IPv6 address');
        }
        $result = $epp->hostCreate($input);
        $resource = $input['hostname'];
    } elseif ($operation === 'domain-create') {
        $input = payload($argument);
        requireFields($input, ['domainname', 'registrant', 'authInfoPw']);
        requireDnsName($input['domainname'], 'domainname');
        requireContactId($input['registrant'], 'registrant');
        if (!isset($input['period'])) {
            $input['period'] = 1;
        }
        if (!is_int($input['period']) || $input['period'] < 1 || $input['period'] > 10) {
            throw new InvalidArgumentException('period must be an integer from 1 to 10');
        }
        if (isset($input['nss']) && !is_array($input['nss'])) {
            throw new InvalidArgumentException('nss must be an array when supplied');
        }
        if (!isset($input['contacts']) || !is_array($input['contacts'])) {
            throw new InvalidArgumentException('contacts must be an object');
        }
        foreach ($input['nss'] ?? [] as $nameserver) {
            if (!is_string($nameserver)) {
                throw new InvalidArgumentException('hostObj nameservers must be strings');
            }
            requireDnsName($nameserver, 'nss');
        }
        foreach ($input['contacts'] as $type => $contactId) {
            if (!in_array($type, ['admin', 'tech', 'billing'], true) || !is_string($contactId)) {
                throw new InvalidArgumentException('contacts supports only admin, tech, and billing string IDs');
            }
            requireContactId($contactId, "contacts.{$type}");
        }
        $result = $epp->domainCreate($input);
        $resource = $input['domainname'];
    } else {
        $input = payload($argument);
        requireFields($input, ['domainname']);
        requireDnsName($input['domainname'], 'domainname');
        if (!isset($input['nameservers']) || !is_array($input['nameservers']) || $input['nameservers'] === []) {
            throw new InvalidArgumentException('nameservers must be a non-empty array');
        }
        if (count($input['nameservers']) > 9) {
            throw new InvalidArgumentException('Namingo domainUpdateNS supports at most 9 nameservers');
        }
        $params = ['domainname' => $input['domainname']];
        foreach (array_values($input['nameservers']) as $index => $nameserver) {
            if (!is_string($nameserver) || trim($nameserver) === '') {
                throw new InvalidArgumentException('each nameserver must be a non-empty string');
            }
            requireDnsName($nameserver, 'nameservers');
            $params['ns' . ($index + 1)] = $nameserver;
        }
        $result = $epp->domainUpdateNS($params);
        $resource = $input['domainname'];
    }
    if (isset($result['error'])) {
        throw new RuntimeException((string)$result['error']);
    }
    $code = (int)($result['code'] ?? 0);
    if (!in_array($code, [1000, 1001], true)) {
        throw new RuntimeException("EPP operation failed with result code {$code}");
    }
    $logout = $epp->logout();
    if ((int)($logout['code'] ?? 0) !== 1500) {
        throw new RuntimeException('EPP logout failed');
    }
    echo json_encode([
        'status' => 'ok',
        'transport' => 'epp-over-tls',
        'peer' => $config['host'] . ':' . $config['port'],
        'operation' => $operation,
        'resource' => $resource,
        'result' => $result,
    ], JSON_UNESCAPED_SLASHES) . PHP_EOL;
} catch (Throwable $error) {
    fwrite(STDERR, 'EPP error: ' . $error->getMessage() . PHP_EOL);
    exit(1);
}
'''

    def _rdds_config(self, rdap: bool) -> str:
        settings = {
            "db_type": "mysql",
            "db_host": "127.0.0.1",
            "db_port": 3306,
            "db_database": self.__db_name,
            "db_username": self.__db_user,
            "db_password": self.__db_password,
            "privacy": self.__privacy,
            "rately": False,
            "limit": 1000 if rdap else 25,
            "period": 60,
            "registrar_whois": self.__registrar_whois,
            "registrar_url": self.__registrar_url,
            "registrar_name": self.__registrar_name,
            "registrar_iana": self.__registrar_iana,
            "abuse_email": self.__abuse_email,
            "abuse_phone": self.__abuse_phone,
            "minimum_data": self.__minimum_data,
            "backend": self.__backend,
        }
        if rdap:
            settings["registry_url"] = self.__registrar_url + "/rdap-terms"
            settings["rdap_url"] = self.__rdap_url
        body = ",\n".join("    {} => {}".format(_php(k), _php(v)) for k, v in settings.items())
        return "<?php\nreturn [\n{}\n];\n".format(body)

    def _database_init(self) -> str:
        return """\
CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS {username}@'127.0.0.1' IDENTIFIED BY {password};
GRANT ALL PRIVILEGES ON `{database}`.* TO {username}@'127.0.0.1';
FLUSH PRIVILEGES;
""".format(
            database=self.__db_name,
            username=_sql_string(self.__db_user),
            password=_sql_string(self.__db_password),
        )

    def _start_script(self) -> str:
        services = []
        if self.__enable_whois:
            services.append(
                "/usr/bin/php8.5 /opt/registrar/whois/start_whois.php "
                ">>/var/log/namingo/whois.stdout.log 2>&1 &"
            )
        if self.__enable_rdap:
            services.append(
                "/usr/bin/php8.5 /opt/registrar/rdap/start_rdap.php "
                ">>/var/log/namingo/rdap.stdout.log 2>&1 &"
            )
            services.append("service nginx start")
        automation = (
            "while true; do /usr/bin/php8.5 /opt/registrar/automation/cron.php; sleep 60; done "
            ">>/var/log/namingo/automation.log 2>&1 &"
            if self.__enable_automation
            else ""
        )
        epp_probe = ""
        if self.__epp_config is not None:
            epp_probe = (
                "while true; do if /usr/local/bin/seedemu-epp-client health "
                ">/run/seedemu-epp-health.json.tmp 2>/var/log/namingo/epp-client.log; "
                "then mv /run/seedemu-epp-health.json.tmp /run/seedemu-epp-health.json; "
                "else rm -f /run/seedemu-epp-health.json.tmp /run/seedemu-epp-health.json; fi; "
                "sleep {}; done &".format(self.__epp_config["probe_interval"])
            )
        return """#!/bin/sh
set -eu

service mariadb start
until mariadb-admin ping --silent; do sleep 1; done
mariadb < /opt/seedemu/namingo/init.sql

if [ -s /opt/seedemu/namingo/schema.sql ] && [ ! -e /var/lib/mysql/.seedemu-namingo-schema ]; then
    mariadb {database} < /opt/seedemu/namingo/schema.sql
    touch /var/lib/mysql/.seedemu-namingo-schema
fi

mkdir -p /var/log/namingo /run/php
{services}
{automation}
{epp_probe}
""".format(
            database=self.__db_name,
            services="\n".join(services),
            automation=automation,
            epp_probe=epp_probe,
        )

    def install(self, node: Node):
        assert (
            self.__enable_whois
            or self.__enable_rdap
            or self.__enable_automation
            or self.__epp_config is not None
        ), "at least one Namingo component must be enabled"

        node.appendClassName("NamingoRegistrarService")
        node.setLabel(NAMINGO_LABEL_META.format(key="role"), "registrar")
        node.setLabel(NAMINGO_LABEL_META.format(key="version"), NAMINGO_VERSION)
        components = []
        if self.__enable_whois:
            components.append("whois")
        if self.__enable_rdap:
            components.append("rdap")
        if self.__enable_automation:
            components.append("automation")
        if self.__epp_config is not None:
            components.append("epp-client")
        node.setLabel(
            NAMINGO_LABEL_META.format(key="components"), ",".join(components)
        )

        software = (
            "ca-certificates curl git gnupg2 mariadb-client mariadb-server "
            "software-properties-common unzip"
        )
        if self.__enable_rdap:
            software += " nginx-light"
        node.addSoftware(software)
        node.addBuildCommand("add-apt-repository -y ppa:ondrej/php")
        node.addBuildCommand("apt-get update")
        php_packages = (
            "composer php8.5-cli php8.5-common php8.5-curl php8.5-gmp "
            "php8.5-intl php8.5-mbstring php8.5-mysql php8.5-swoole "
            "php8.5-xml php8.5-zip"
        )
        if self.__enable_automation:
            php_packages += (
                " php8.5-bcmath php8.5-bz2 php8.5-gd php8.5-imagick "
                "php8.5-imap php8.5-yaml"
            )
        node.addBuildCommand(
            "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "
            + php_packages
        )
        node.addBuildCommand(
            "git clone --filter=blob:none {} {} && "
            "git -C {} checkout {} && "
            "test \"$(git -C {} rev-parse HEAD)\" = {}".format(
                NAMINGO_REPOSITORY,
                NAMINGO_INSTALL_DIR,
                NAMINGO_INSTALL_DIR,
                NAMINGO_VERSION,
                NAMINGO_INSTALL_DIR,
                NAMINGO_COMMIT,
            )
        )
        registrar_components = [
            component for component in components if component != "epp-client"
        ]
        for component in registrar_components:
            node.addBuildCommand(
                "COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --no-interaction "
                "--prefer-dist --working-dir={}/{}".format(
                    NAMINGO_INSTALL_DIR, component
                )
            )
        if self.__epp_config is not None:
            node.addBuildCommand(
                "git clone --filter=blob:none {} {} && "
                "git -C {} checkout {} && "
                "test \"$(git -C {} rev-parse HEAD)\" = {}".format(
                    NAMINGO_EPP_CLIENT_REPOSITORY,
                    NAMINGO_EPP_CLIENT_INSTALL_DIR,
                    NAMINGO_EPP_CLIENT_INSTALL_DIR,
                    NAMINGO_EPP_CLIENT_VERSION,
                    NAMINGO_EPP_CLIENT_INSTALL_DIR,
                    NAMINGO_EPP_CLIENT_COMMIT,
                )
            )
            node.addBuildCommand(
                "COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --no-interaction "
                "--prefer-dist --working-dir={}".format(
                    NAMINGO_EPP_CLIENT_INSTALL_DIR
                )
            )

        if self.__enable_whois:
            node.setFile(
                "/opt/registrar/whois/config.php", self._rdds_config(False)
            )
        if self.__enable_rdap:
            node.setFile("/opt/registrar/rdap/config.php", self._rdds_config(True))
        node.setFile("/opt/seedemu/namingo/init.sql", self._database_init())
        node.setFile("/opt/seedemu/namingo/schema.sql", self.__schema_sql)
        if self.__enable_rdap:
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
        if self.__automation_config is not None:
            node.setFile("/opt/registrar/automation/config.php", self.__automation_config)
        if self.__epp_config is not None:
            node.setFile(
                "/opt/seedemu/namingo/epp-client.php", self._epp_client_config()
            )
            node.setFile(
                "/opt/seedemu/namingo/epp-ca.crt", self.__epp_config["ca"]
            )
            if self.__epp_config["client_certificate"] is not None:
                node.setFile(
                    "/opt/seedemu/namingo/epp-client.crt",
                    self.__epp_config["client_certificate"],
                )
                node.setFile(
                    "/opt/seedemu/namingo/epp-client.key",
                    self.__epp_config["client_key"],
                )
            node.setFile(
                "/usr/local/bin/seedemu-epp-client", self._epp_client_script()
            )
        node.setFile("/usr/local/bin/seedemu-start-namingo", self._start_script())
        node.addBuildCommandAtEnd("chmod +x /usr/local/bin/seedemu-start-namingo")
        if self.__epp_config is not None:
            node.appendStartCommand(
                "chmod 0600 /opt/seedemu/namingo/epp-client.php"
            )
            node.appendStartCommand(
                "chmod 0644 /opt/seedemu/namingo/epp-ca.crt"
            )
            if self.__epp_config["client_key"] is not None:
                node.appendStartCommand(
                    "chmod 0600 /opt/seedemu/namingo/epp-client.key"
                )
                node.appendStartCommand(
                    "chmod 0644 /opt/seedemu/namingo/epp-client.crt"
                )
            node.appendStartCommand("chmod 0755 /usr/local/bin/seedemu-epp-client")
        node.appendStartCommand("/usr/local/bin/seedemu-start-namingo")

    def print(self, indent: int) -> str:
        return " " * indent + "NamingoRegistrarServer\n"


class NamingoRegistrarService(Service):
    def __init__(self):
        super().__init__()
        self.addDependency("Base", False, False)

    def getName(self) -> str:
        return "NamingoRegistrarService"

    def _createServer(self) -> NamingoRegistrarServer:
        return NamingoRegistrarServer()

    def print(self, indent: int) -> str:
        return " " * indent + "NamingoRegistrarService\n"
