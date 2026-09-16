from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import secrets
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple
from seedemu.services.LoomSourceAuth import SOURCE_AUTH_BOOTSTRAP, SOURCE_AUTH_ENDPOINT
from seedemu.services.RegistrarIdentity import RegistrarIdentity

from seedemu.core import Node, Server, Service

LOOM_REPOSITORY = "https://github.com/getnamingo/loom.git"
LOOM_INSTALL_DIR = "/opt/loom"


class LoomWebTlsCredentials(NamedTuple):
    certificate: str
    private_key: str


def _sql_string(value: str) -> str:
    return "'{}'".format(value.replace("\\", "\\\\").replace("'", "''"))


def _dotenv_string(value: str) -> str:
    return "'{}'".format(value.replace("\\", "\\\\").replace("'", "\\'"))

FORCE_GENERIC_EPP = r"""<?php
$path = '/opt/loom/bootstrap/helper.php';
$contents = file_get_contents($path);
if ($contents === false) {
    throw new RuntimeException("Cannot read $path");
}
$replacements = [
    'return $tldMap[$last];' => "return 'generic';",
    "return \$tldMap[\$tld] ?? 'generic';" => "return 'generic';",
];
foreach ($replacements as $from => $to) {
    if (substr_count($contents, $from) !== 1) {
        throw new RuntimeException("Pinned Loom EPP selector context mismatch");
    }
    $contents = str_replace($from, $to, $contents);
}
if (file_put_contents($path, $contents) === false) {
    throw new RuntimeException("Cannot write $path");
}
"""

ENABLE_NAMESERVER_GLUE = r"""<?php
$edits = [
    '/opt/loom/app/Controllers/OrdersController.php' => [
        "            \$nameservers = \$data['nameserver'] ?? [];" =>
            "            \$nameservers = \$data['nameserver'] ?? [];\n"
            . "            \$nameserverAddresses = \$data['nameserver_ipv4'] ?? [];",
        "                    'nameservers' => array_values(\$nameservers)," =>
            "                    'nameservers' => array_values(\$nameservers),\n"
            . "                    'nameserver_addresses' => array_values(\$nameserverAddresses),",
    ],
    '/opt/loom/app/Services/Provisioning/DomainProvisioner.php' => [
        "                    foreach (\$nameservers as \$host) {\n"
            . "                        // Registries commonly return \"already exists\" during a retry;\n"
            . "                        // preserve the previous best-effort host creation behavior.\n"
            . "                        \$epp->hostCreate(['hostname' => strtolower(\$host)]);\n"
            . "                    }" =>
            "                    \$addresses = is_array(\$serviceData['nameserver_addresses'] ?? null)\n"
            . "                        ? array_values(\$serviceData['nameserver_addresses']) : [];\n"
            . "                    \$pendingNameservers = [];\n"
            . "                    foreach (\$nameservers as \$index => \$host) {\n"
            . "                        \$address = trim((string)(\$addresses[\$index] ?? ''));\n"
            . "                        \$pendingNameservers[] = [\n"
            . "                            'hostname' => strtolower(\$host),\n"
            . "                            'ipaddress' => \$address,\n"
            . "                        ];\n"
            . "                    }\n"
            . "                    // Namingo requires the superordinate domain before in-bailiwick hosts.\n"
            . "                    \$domainParams['nss'] = [];",
        "            if (\$error !== null) {\n"
            . "                throw new \\RuntimeException('DomainCreate Error: ' . \$error);\n"
            . "            }" =>
            "            if (\$error !== null) {\n"
            . "                throw new \\RuntimeException('DomainCreate Error: ' . \$error);\n"
            . "            }\n"
            . "\n"
            . "            if (!empty(\$pendingNameservers)) {\n"
            . "                \$update = ['domainname' => \$domainName];\n"
            . "                foreach (\$pendingNameservers as \$index => \$host) {\n"
            . "                    \$hostCreate = \$epp->hostCreate(\$host);\n"
            . "                    \$hostError = \$this->responseError(\$hostCreate);\n"
            . "                    if (\$hostError !== null) {\n"
            . "                        throw new \\RuntimeException('HostCreate Error: ' . \$hostError);\n"
            . "                    }\n"
            . "                    \$update['ns' . (\$index + 1)] = \$host['hostname'];\n"
            . "                }\n"
            . "                \$domainUpdate = \$epp->domainUpdateNS(\$update);\n"
            . "                \$updateError = \$this->responseError(\$domainUpdate);\n"
            . "                if (\$updateError !== null) {\n"
            . "                    throw new \\RuntimeException('DomainUpdateNS Error: ' . \$updateError);\n"
            . "                }\n"
            . "            }",
    ],
];
foreach ($edits as $path => $replacements) {
    $contents = file_get_contents($path);
    if ($contents === false) {
        throw new RuntimeException("Cannot read $path");
    }
    foreach ($replacements as $from => $to) {
        if (substr_count($contents, $from) !== 1) {
            throw new RuntimeException("Pinned Loom glue patch context mismatch in $path");
        }
        $contents = str_replace($from, $to, $contents);
    }
    if (file_put_contents($path, $contents) === false) {
        throw new RuntimeException("Cannot write $path");
    }
}
"""

USE_CONFIGURED_API_DATABASE_HOST = r"""<?php
$path = '/opt/loom/routes/web.php';
$contents = file_get_contents($path);
if ($contents === false) {
    throw new RuntimeException("Cannot read $path");
}
$from = "        \$db_address = 'localhost';";
$to = "        \$db_address = \$db['mysql']['host'];";
if (substr_count($contents, $from) < 1) {
    throw new RuntimeException("Pinned Loom API database context mismatch");
}
$contents = preg_replace('/^' . preg_quote($from, '/') . '$/m', $to, $contents, 1);
if (file_put_contents($path, $contents) === false) {
    throw new RuntimeException("Cannot write $path");
}
"""

IMPORT_PROVIDER_SQL = r"""<?php
require '/opt/loom/vendor/autoload.php';
Dotenv\Dotenv::createImmutable('/opt/loom')->load();
$dsn = 'mysql:host=' . $_ENV['DB_HOST'] . ';port=' . $_ENV['DB_PORT']
    . ';dbname=' . $_ENV['DB_DATABASE'] . ';charset=utf8mb4';
$pdo = new PDO($dsn, $_ENV['DB_USERNAME'], $_ENV['DB_PASSWORD'], [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
]);
$sql = file_get_contents('/opt/seedemu/loom/provider.sql');
if ($sql === false || trim($sql) === '') {
    throw new RuntimeException('Loom provider SQL is empty');
}
$pdo->exec($sql);
"""

LOOM_EPP_PROBE = r'''<?php
declare(strict_types=1);

require '/opt/loom/vendor/autoload.php';
Dotenv\Dotenv::createImmutable('/opt/loom')->load();
require '/opt/loom/bootstrap/helper.php';

$config = json_decode(
    file_get_contents('/opt/seedemu/loom/epp-probe.json'),
    true,
    16,
    JSON_THROW_ON_ERROR
);
$pdo = new PDO(
    'mysql:host=' . $_ENV['DB_HOST'] . ';port=' . $_ENV['DB_PORT']
        . ';dbname=' . $_ENV['DB_DATABASE'] . ';charset=utf8mb4',
    $_ENV['DB_USERNAME'],
    $_ENV['DB_PASSWORD'],
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
);
$find = $pdo->prepare("SELECT api_endpoint, credentials FROM providers
    WHERE tld = ? AND status = 'active'");
$find->execute([$config['tld']]);
$provider = $find->fetch(PDO::FETCH_ASSOC);
if (!$provider) {
    throw new RuntimeException('Active Loom EPP provider not found');
}
$credentials = json_decode($provider['credentials'], true, 64, JSON_THROW_ON_ERROR);
[$host, $port] = explode(':', $provider['api_endpoint'], 2);
$epp = connectEpp(
    'generic', $host, (int)$port,
    $credentials['cafile'], $credentials['cert_file'], $credentials['key_file'],
    $credentials['passphrase'], $credentials['auth']['username'],
    $credentials['auth']['password']
);
$reply = $epp->domainCheck(['domains' => [$config['domain']]]);
$epp->logout();
if (isset($reply['error'])) {
    throw new RuntimeException((string)$reply['error']);
}
echo json_encode([
    'status' => 'ok',
    'transport' => 'epp-over-tls',
    'client' => 'loom',
    'peer' => $provider['api_endpoint'],
    'operation' => 'domain-check',
    'resource' => $config['domain'],
], JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . PHP_EOL;
'''


class LoomRegistrarServer(Server):
    """Deploy Loom with optional TLS and a source-token authentication adapter.

    The scenario supplies Loom's version-specific ``.env`` and provider data.
    This wrapper owns their installation, common first-boot operations, and
    discovery metadata, while Loom owns sessions, forms, orders, and EPP logic.
    ``addBootstrapCommand`` remains available for scenario-specific extensions.
    """

    def __init__(self):
        super().__init__()
        self.__commit: str | None = None
        self.__environment: str | None = None
        self.__environment_config: dict[str, str | int] | None = None
        self.__port = 80
        self.__web_tls: tuple[str, str] | None = None
        self.__source_accounts: dict[str, dict[str, str | float]] = {}
        self.__credential_ref: str | None = None
        self.__bootstrap_commands: list[str] = []
        self.__database_access: tuple[str, str, str] | None = None
        self.__database_readers: list[tuple[str, str, str, str]] = []
        self.__database_initialization = False
        self.__provider_sql: str | None = None
        self.__epp_providers: list[dict] = []
        self.__admin_user_creation = False
        self.__epp_client_credentials: tuple[str, str, str] | None = None
        self.__epp_probe: dict[str, str | int] | None = None

    def setCommit(self, commit: str) -> LoomRegistrarServer:
        """Pin the exact upstream Loom commit used by the emulation."""
        assert re.fullmatch(r"[0-9a-f]{40}", commit), (
            "Loom commit must be 40 lowercase hex digits"
        )
        self.__commit = commit
        return self

    def setEnvironment(self, environment: str) -> LoomRegistrarServer:
        """Provide the complete Loom .env for the selected pinned version."""
        assert environment.strip(), "Loom environment cannot be empty"
        assert self.__environment_config is None, (
            "configureEnvironment() is already enabled"
        )
        self.__environment = environment.rstrip() + "\n"
        return self

    def configureEnvironment(
        self,
        identity: RegistrarIdentity,
        webauthn_secret: str,
        app_name: str = "SeedEmu Loom Registrar",
    ) -> LoomRegistrarServer:
        """Configure a standard Loom environment using service-owned defaults."""
        assert self.__environment is None, "setEnvironment() is already configured"
        assert self.__environment_config is None, "Loom environment is already configured"
        values: dict[str, str | int] = {
            "app_domain": identity.domain,
            "whois_server": identity.whois_host,
            "rdap_server": identity.rdap_host,
            "company_name": identity.company_name,
            "company_address": identity.address,
            "company_country_code": identity.country_code,
            "company_phone": identity.phone,
            "company_email": identity.email,
            "iana_id": identity.iana_id,
            "webauthn_secret": webauthn_secret,
            "app_name": app_name,
        }
        assert all(
            "\n" not in str(value) and "\r" not in str(value)
            for value in values.values()
        ), "Loom environment values cannot contain newlines"
        assert webauthn_secret, "Loom WebAuthn secret cannot be empty"
        self.__environment_config = values
        return self

    def setPort(self, port: int) -> LoomRegistrarServer:
        assert 1 <= port <= 65535, "invalid Loom frontend port"
        self.__port = port
        return self

    def setWebTls(self, certificate_pem: str, private_key_pem: str) -> LoomRegistrarServer:
        """Serve the frontend over HTTPS; callers distribute the trust anchor."""
        self.__web_tls = (certificate_pem, private_key_pem)
        self.__port = 443
        return self

    def provisionSourceAccount(
        self,
        source_node: Node,
        registrar_url: str,
        ca_certificate: str,
        source_id: str,
        address: str,
        email: str,
        username: str,
        credit_limit: float = 0.0,
    ) -> LoomRegistrarServer:
        """Create and install both halves of one source authentication pair."""
        assert registrar_url.startswith("https://"), "source authentication requires HTTPS"
        assert "-----BEGIN CERTIFICATE-----" in ca_certificate, "invalid Loom CA certificate"
        assert re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", source_id), "invalid source id"
        ipaddress.ip_address(address)
        assert 0 <= credit_limit <= 1_000_000
        assert source_id not in self.__source_accounts
        token = secrets.token_hex(32)
        token_sha256 = hashlib.sha256(token.encode()).hexdigest()
        self.__source_accounts[source_id] = dict(address=address, token_sha256=token_sha256,
                                                email=email, username=username,
                                                credit_limit=credit_limit)
        origin = registrar_url.rstrip("/")
        credential_dir = "/opt/seedemu/registrar/" + hashlib.sha256(
            origin.encode()
        ).hexdigest()
        source_node.setFile(credential_dir + "/source-id", source_id)
        source_node.setFile(credential_dir + "/token", token)
        source_node.setFile(credential_dir + "/ca.crt", ca_certificate)
        source_node.appendStartCommand(
            f"chmod 0700 {credential_dir}; chmod 0600 {credential_dir}/*"
        )
        return self

    def setCredentialRef(self, credential_ref: str) -> LoomRegistrarServer:
        """Publish an opaque principal credential reference, never a secret."""
        assert re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", credential_ref), (
            "invalid Loom credential reference"
        )
        self.__credential_ref = credential_ref
        return self

    def addBootstrapCommand(self, command: str) -> LoomRegistrarServer:
        """Add an explicit, version-matched first-boot command."""
        assert command.strip(), "Loom bootstrap command cannot be empty"
        self.__bootstrap_commands.append(command)
        return self

    def configureDatabase(
        self, database: str, app_username: str, app_password: str
    ) -> LoomRegistrarServer:
        """Create Loom's database and grant its local application user access."""
        identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        assert identifier.fullmatch(database), "invalid Loom database name"
        assert identifier.fullmatch(app_username), "invalid Loom database username"
        assert app_password, "Loom database password cannot be empty"
        assert self.__database_access is None, "Loom database access is already configured"
        self.__database_access = (database, app_username, app_password)
        self.__bootstrap_commands.append(
            "    mariadb < /opt/seedemu/loom/database-access.sql"
        )
        return self

    def addReadOnlyDatabaseUser(
        self,
        username: str,
        password: str,
        source: str,
        database: str = "loom",
    ) -> LoomRegistrarServer:
        """Grant a remote integration user read-only access to a Loom database."""
        identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        assert identifier.fullmatch(database), "invalid Loom database name"
        assert identifier.fullmatch(username), "invalid read-only database username"
        assert password, "read-only database password cannot be empty"
        try:
            ipaddress.ip_address(source)
        except ValueError:
            assert re.fullmatch(r"[A-Za-z0-9.-]{1,253}", source), (
                "invalid read-only database source"
            )
        reader = (database, username, password, source)
        assert reader not in self.__database_readers, (
            "read-only database user is already configured"
        )
        self.__database_readers.append(reader)
        return self

    def initializeDatabase(self) -> LoomRegistrarServer:
        """Initialize Loom's schema during the first container start."""
        assert not self.__database_initialization, "database initialization already enabled"
        self.__database_initialization = True
        self.__bootstrap_commands.append("    php /opt/loom/bin/install-db.php")
        return self

    def setProviderSql(self, provider_sql: str) -> LoomRegistrarServer:
        """Install and import scenario-owned provider SQL on first start."""
        assert provider_sql.strip(), "Loom provider SQL cannot be empty"
        assert not self.__epp_providers, "addEppProvider() is already configured"
        assert self.__provider_sql is None, "Loom provider SQL is already configured"
        self.__provider_sql = provider_sql.rstrip() + "\n"
        self.__bootstrap_commands.append(
            "    php /opt/seedemu/loom/import-provider-sql.php"
        )
        return self

    def addEppProvider(
        self,
        name: str,
        hostname: str,
        port: int,
        tld: str,
        clid: str,
        password: str,
        prices: dict[str, dict[int, float]],
        active: bool = True,
        contact_roles: tuple[str, ...] = (
            "registrant", "admin", "tech", "billing"
        ),
        contact_type: str = "int",
        auto_create_hosts: bool = True,
    ) -> LoomRegistrarServer:
        """Add a parameterized Loom domain provider backed by an EPP Registry."""
        assert self.__provider_sql is None, "setProviderSql() is already configured"
        assert self.__database_initialization, (
            "initializeDatabase() must be enabled before addEppProvider()"
        )
        assert name.strip(), "EPP provider name cannot be empty"
        assert "\n" not in name and "\r" not in name, "invalid EPP provider name"
        assert re.fullmatch(
            r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?",
            hostname,
        ), "invalid EPP provider hostname"
        assert 1 <= port <= 65535, "invalid EPP provider port"
        normalized_tld = "." + tld.lower().strip().strip(".")
        assert re.fullmatch(
            r"\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", normalized_tld
        ), "invalid EPP provider TLD"
        assert re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", clid), (
            "invalid EPP provider client id"
        )
        assert password, "EPP provider password cannot be empty"
        assert prices, "EPP provider prices cannot be empty"
        normalized_prices: dict[str, dict[str, float]] = {}
        allowed_operations = {"register", "renew", "transfer", "restore"}
        for operation, terms in prices.items():
            assert operation in allowed_operations, "invalid EPP provider price operation"
            assert terms, "EPP provider price terms cannot be empty"
            normalized_terms: dict[str, float] = {}
            for term, amount in terms.items():
                assert isinstance(term, int) and term >= 1, "invalid EPP provider price term"
                assert isinstance(amount, (int, float)) and amount >= 0, (
                    "invalid EPP provider price"
                )
                normalized_terms[str(term)] = amount
            normalized_prices[operation] = normalized_terms
        assert contact_roles, "EPP provider contact roles cannot be empty"
        assert all(
            re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", role)
            for role in contact_roles
        ), "invalid EPP provider contact role"
        assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", contact_type), (
            "invalid EPP provider contact type"
        )
        assert all(provider["tld"] != normalized_tld for provider in self.__epp_providers), (
            "EPP provider TLD is already configured"
        )
        if not self.__epp_providers:
            self.__bootstrap_commands.append(
                "    php /opt/seedemu/loom/import-provider-sql.php"
            )
        self.__epp_providers.append({
            "name": name.strip(),
            "endpoint": "{}:{}".format(hostname.lower(), port),
            "tld": normalized_tld,
            "clid": clid,
            "password": password,
            "pricing": {normalized_tld: normalized_prices},
            "active": active,
            "contact_roles": list(contact_roles),
            "contact_type": contact_type,
            "auto_create_hosts": auto_create_hosts,
        })
        return self

    def createAdminUser(self) -> LoomRegistrarServer:
        """Run Loom's pinned bootstrap-admin utility on first start."""
        assert not self.__admin_user_creation, "admin user creation already enabled"
        self.__admin_user_creation = True
        self.__bootstrap_commands.append("    php /opt/loom/bin/create-admin-user.php")
        return self

    def setEppClientCredentials(
        self,
        ca_certificate_pem: str,
        client_certificate_pem: str,
        client_private_key_pem: str,
    ) -> LoomRegistrarServer:
        """Install Loom EPP mutual-TLS credentials with safe key permissions."""
        assert "BEGIN CERTIFICATE" in ca_certificate_pem, "invalid EPP CA certificate"
        assert "BEGIN CERTIFICATE" in client_certificate_pem, (
            "invalid EPP client certificate"
        )
        assert "PRIVATE KEY" in client_private_key_pem, "invalid EPP client key"
        assert self.__epp_client_credentials is None, (
            "Loom EPP client credentials are already configured"
        )
        self.__epp_client_credentials = (
            ca_certificate_pem,
            client_certificate_pem,
            client_private_key_pem,
        )
        return self

    def enableEppProbe(
        self,
        tld: str,
        probe_domain: str = "seedemu-epp-probe.com",
        probe_interval: int = 30,
    ) -> LoomRegistrarServer:
        """Continuously verify Loom's configured provider through domainCheck."""
        normalized_tld = "." + tld.lower().strip().strip(".")
        normalized_domain = probe_domain.lower().rstrip(".")
        dns_name = re.compile(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        )
        assert re.fullmatch(r"\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", normalized_tld), (
            "invalid EPP probe TLD"
        )
        assert dns_name.fullmatch(normalized_domain), "invalid EPP probe domain"
        assert probe_interval >= 5, "EPP probe interval must be at least 5 seconds"
        assert self.__epp_probe is None, "Loom EPP probe is already enabled"
        self.__epp_probe = {
            "tld": normalized_tld,
            "domain": normalized_domain,
            "interval": probe_interval,
        }
        return self

    def _epp_provider_sql(self) -> str:
        statements = []
        for provider in self.__epp_providers:
            credentials = {
                "ssl": True,
                "cert_file": "/opt/loom-epp/client.crt",
                "key_file": "/opt/loom-epp/client.key",
                "cafile": "/opt/loom-epp/ca.crt",
                "passphrase": "",
                "auth": {
                    "username": provider["clid"],
                    "password": provider["password"],
                },
                "client_id": provider["clid"],
                "contactRoles": provider["contact_roles"],
                "contactType": provider["contact_type"],
                "autoCreateHosts": provider["auto_create_hosts"],
            }
            statements.append(
                "INSERT INTO providers "
                "(name,type,api_endpoint,credentials,pricing,status,tld) VALUES "
                "({name},'domain',{endpoint},{credentials},{pricing},{status},{tld}) "
                "ON DUPLICATE KEY UPDATE api_endpoint=VALUES(api_endpoint),"
                "credentials=VALUES(credentials),pricing=VALUES(pricing),"
                "status=VALUES(status);".format(
                    name=_sql_string(provider["name"]),
                    endpoint=_sql_string(provider["endpoint"]),
                    credentials=_sql_string(json.dumps(credentials, separators=(",", ":"))),
                    pricing=_sql_string(json.dumps(provider["pricing"], separators=(",", ":"))),
                    status=_sql_string("active" if provider["active"] else "inactive"),
                    tld=_sql_string(provider["tld"]),
                )
            )
        return "\n".join(statements) + "\n"

    def _database_access_sql(self) -> str:
        assert self.__database_access is not None
        database, app_username, app_password = self.__database_access
        statements = [
            "CREATE DATABASE IF NOT EXISTS `{}` CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci;".format(database),
            "CREATE USER IF NOT EXISTS {}@'127.0.0.1' IDENTIFIED BY {};".format(
                _sql_string(app_username), _sql_string(app_password)
            ),
            "GRANT ALL PRIVILEGES ON `{}`.* TO {}@'127.0.0.1';".format(
                database, _sql_string(app_username)
            ),
        ]
        for reader_database, username, password, source in self.__database_readers:
            statements.extend([
                "CREATE USER IF NOT EXISTS {}@{} IDENTIFIED BY {};".format(
                    _sql_string(username), _sql_string(source), _sql_string(password)
                ),
                "GRANT SELECT ON `{}`.* TO {}@{};".format(
                    reader_database, _sql_string(username), _sql_string(source)
                ),
            ])
        statements.append("FLUSH PRIVILEGES;")
        return "\n".join(statements) + "\n"

    def _configured_environment(self, address: str) -> str:
        assert self.__environment_config is not None
        assert self.__database_access is not None
        config = self.__environment_config
        database, app_username, app_password = self.__database_access
        scheme = "https" if self.__web_tls else "http"
        default_port = 443 if self.__web_tls else 80
        port = "" if self.__port == default_port else ":{}".format(self.__port)
        rendered = {
            key: _dotenv_string(str(value)) for key, value in config.items()
        }
        return """APP_NAME={app_name}
APP_ENV=local
APP_URL={app_url}
APP_DOMAIN={app_domain}
WHOIS_SERVER={whois_server}
RDAP_SERVER={rdap_server}
LANG=en_US
UI_LANG=us
DEFAULT_CURRENCY=USD
WEB_AUTHN_ENABLED=false
WEBAUTHN_DUMMY_SECRET={webauthn_secret}
DB_DRIVER=mysql
DB_HOST=127.0.0.1
DB_DATABASE={database}
DB_USERNAME={app_username}
DB_PASSWORD={app_password}
DB_PORT=3306
MAIL_DRIVER=none
ENABLED_GATEWAYS=balance
PASSWORD_EXPIRATION_SKIP_USERS=admin
COMPANY_NAME={company_name}
COMPANY_ADDRESS={company_address}
COMPANY_ADDRESS2=''
COMPANY_COUNTRY_CODE={company_country_code}
COMPANY_VAT_NUMBER=''
COMPANY_PHONE={company_phone}
COMPANY_EMAIL={company_email}
TLS=1.2
VERIFY_PEER=true
VERIFY_PEER_NAME=true
VERIFY_HOST=true
SELF_SIGNED=false
BIND=false
BIND_IP={bind_ip}
VALIDATE_PHONE=false
VALIDATE_EMAIL=false
VALIDATE_POSTAL=false
IANA_ID={iana_id}
MOSAPI_USERNAME=''
MOSAPI_PASSWORD=''
""".format(
            app_url=_dotenv_string("{}://{}{}".format(scheme, address, port)),
            bind_ip=_dotenv_string(address),
            database=_dotenv_string(database),
            app_username=_dotenv_string(app_username),
            app_password=_dotenv_string(app_password),
            **rendered,
        )

    def _nginx_config(self) -> str:
        tls = ""
        if self.__web_tls:
            tls = ("ssl_certificate /opt/seedemu/loom/web.crt;\n"
                   "    ssl_certificate_key /opt/seedemu/loom/web.key;\n"
                   "    ssl_protocols TLSv1.2 TLSv1.3;")
        listen = f"{self.__port} ssl" if self.__web_tls else str(self.__port)
        return rf"""server {{
    listen {listen};
    {tls}
    server_name _;
    root {LOOM_INSTALL_DIR}/public;
    index index.php index.html;

    location / {{
        try_files $uri $uri/ /index.php$is_args$args;
    }}

    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_pass unix:/run/php/php8.5-fpm.sock;
    }}
}}
"""

    def _start_script(self) -> str:
        bootstrap = "\n".join(self.__bootstrap_commands)
        source_bootstrap = ("php /opt/seedemu/loom/init-source-accounts.php"
                            if self.__source_accounts else "")
        epp_probe = ""
        if self.__epp_probe is not None:
            epp_probe = (
                "while true; do if php /opt/seedemu/loom/epp-probe.php "
                ">/run/seedemu-loom-epp-health.json.tmp "
                "2>/opt/loom/logs/seedemu-epp-probe.log; "
                "then mv /run/seedemu-loom-epp-health.json.tmp "
                "/run/seedemu-loom-epp-health.json; "
                "else rm -f /run/seedemu-loom-epp-health.json.tmp "
                "/run/seedemu-loom-epp-health.json; fi; sleep {}; done &"
            ).format(self.__epp_probe["interval"])
        return f"""#!/bin/sh
set -eu

service mariadb start
service php8.5-fpm start
if [ ! -e /var/lib/loom/.seedemu-initialized ]; then
{bootstrap}
    mkdir -p /var/lib/loom
    touch /var/lib/loom/.seedemu-initialized
fi
{source_bootstrap}
service nginx start
{epp_probe}
"""

    def install(self, node: Node):
        assert self.__commit is not None, "setCommit() is required"
        assert self.__environment is not None or self.__environment_config is not None, (
            "setEnvironment() or configureEnvironment() is required"
        )
        assert self.__environment_config is None or self.__database_access is not None, (
            "configureEnvironment() requires configureDatabase()"
        )
        assert not self.__epp_providers or self.__epp_client_credentials is not None, (
            "EPP providers require setEppClientCredentials()"
        )
        assert self.__bootstrap_commands, (
            "at least one Loom bootstrap command is required"
        )
        assert not self.__database_readers or self.__database_access is not None, (
            "read-only database users require configureDatabase()"
        )
        interfaces = node.getInterfaces()
        assert interfaces, "Loom frontend node must have a network interface"

        node.appendClassName("LoomRegistrarService")
        node.setLabel("loom.role", "registrar-frontend")
        node.setLabel(
            "agent.exposed.registrar_url",
            f"{'https' if self.__web_tls else 'http'}://{interfaces[0].getAddress()}:{self.__port}",
        )
        if self.__credential_ref is not None:
            node.setLabel(
                "agent.exposed.registrar_credential_ref", self.__credential_ref
            )

        node.addSoftware(
            "bzip2 ca-certificates composer curl git mariadb-client mariadb-server "
            "net-tools nginx-light redis-server software-properties-common unzip wget whois"
        )
        node.addBuildCommand("add-apt-repository -y ppa:ondrej/php")
        node.addBuildCommand("apt-get update")
        node.addBuildCommand(
            "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "
            "php8.5-apcu php8.5-bcmath php8.5-bz2 php8.5-cli php8.5-common php8.5-curl "
            "php8.5-ds php8.5-fpm php8.5-gd php8.5-gmp php8.5-igbinary "
            "php8.5-imap php8.5-intl php8.5-mbstring php8.5-mysql "
            "php8.5-readline php8.5-redis php8.5-soap php8.5-swoole "
            "php8.5-uuid php8.5-xml php8.5-yaml php8.5-zip"
        )
        node.addBuildCommand("update-alternatives --set php /usr/bin/php8.5")
        node.addBuildCommand(
            f"git clone --filter=blob:none {LOOM_REPOSITORY} {LOOM_INSTALL_DIR} && "
            f"git -C {LOOM_INSTALL_DIR} checkout {self.__commit} && "
            f'test "$(git -C {LOOM_INSTALL_DIR} rev-parse HEAD)" = {self.__commit}'
        )
        node.setFile("/opt/seedemu/loom/force-generic-epp.php", FORCE_GENERIC_EPP)
        node.addBuildCommandAtEnd("php /opt/seedemu/loom/force-generic-epp.php")
        node.setFile("/opt/seedemu/loom/enable-nameserver-glue.php", ENABLE_NAMESERVER_GLUE)
        node.addBuildCommandAtEnd("php /opt/seedemu/loom/enable-nameserver-glue.php")
        node.setFile("/opt/seedemu/loom/use-configured-api-db-host.php", USE_CONFIGURED_API_DATABASE_HOST)
        node.addBuildCommandAtEnd("php /opt/seedemu/loom/use-configured-api-db-host.php")
        node.addBuildCommand(
            "COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --no-interaction "
            f"--prefer-dist --working-dir={LOOM_INSTALL_DIR}"
        )
        node.addBuildCommand(
            f"mkdir -p {LOOM_INSTALL_DIR}/cache {LOOM_INSTALL_DIR}/logs /var/lib/loom && "
            f"chown -R www-data:www-data {LOOM_INSTALL_DIR}/cache {LOOM_INSTALL_DIR}/logs && "
            f"chmod -R 0775 {LOOM_INSTALL_DIR}/cache {LOOM_INSTALL_DIR}/logs"
        )
        if self.__web_tls:
            node.setFile("/opt/seedemu/loom/web.crt", self.__web_tls[0])
            node.setFile("/opt/seedemu/loom/web.key", self.__web_tls[1])
            node.appendStartCommand("chmod 0600 /opt/seedemu/loom/web.key")
        if self.__source_accounts:
            assert self.__web_tls is not None, "Source authentication requires HTTPS"
            node.setFile("/opt/seedemu/loom/source-auth.json", json.dumps(self.__source_accounts))
            node.setFile("/opt/seedemu/loom/init-source-accounts.php", SOURCE_AUTH_BOOTSTRAP)
            node.setFile("/opt/loom/public/seedemu-source-auth.php", SOURCE_AUTH_ENDPOINT)
            node.appendStartCommand("chown root:www-data /opt/seedemu/loom/source-auth.json && "
                                    "chmod 0640 /opt/seedemu/loom/source-auth.json")
        if self.__provider_sql is not None or self.__epp_providers:
            provider_sql = self.__provider_sql or self._epp_provider_sql()
            node.setFile("/opt/seedemu/loom/provider.sql", provider_sql)
            node.setFile(
                "/opt/seedemu/loom/import-provider-sql.php",
                IMPORT_PROVIDER_SQL,
            )
        if self.__database_access is not None:
            node.setFile(
                "/opt/seedemu/loom/database-access.sql",
                self._database_access_sql(),
            )
        if self.__database_readers:
            node.setFile(
                "/etc/mysql/mariadb.conf.d/99-seedemu-loom.cnf",
                "[mysqld]\nbind-address = 0.0.0.0\n",
            )
        if self.__epp_client_credentials is not None:
            ca_certificate, client_certificate, client_private_key = (
                self.__epp_client_credentials
            )
            node.setFile("/opt/loom-epp/ca.crt", ca_certificate)
            node.setFile("/opt/loom-epp/client.crt", client_certificate)
            node.setFile("/opt/loom-epp/client.key", client_private_key)
            node.appendStartCommand(
                "chown root:www-data /opt/loom-epp/client.key && "
                "chmod 0640 /opt/loom-epp/client.key"
            )
        if self.__epp_probe is not None:
            assert self.__provider_sql is not None or self.__epp_providers, (
                "Loom EPP probe requires setProviderSql() or addEppProvider()"
            )
            assert self.__epp_client_credentials is not None, (
                "Loom EPP probe requires setEppClientCredentials()"
            )
            node.setFile("/opt/seedemu/loom/epp-probe.php", LOOM_EPP_PROBE)
            node.setFile(
                "/opt/seedemu/loom/epp-probe.json",
                json.dumps({
                    "tld": self.__epp_probe["tld"],
                    "domain": self.__epp_probe["domain"],
                }),
            )
        environment = self.__environment or self._configured_environment(
            str(interfaces[0].getAddress())
        )
        node.setFile(f"{LOOM_INSTALL_DIR}/.env", environment)
        node.setFile("/etc/nginx/sites-available/default", self._nginx_config())
        node.setFile("/usr/local/bin/seedemu-start-loom", self._start_script())
        node.addBuildCommandAtEnd("chmod 0755 /usr/local/bin/seedemu-start-loom")
        node.appendStartCommand("chown root:www-data /opt/loom/.env && chmod 0640 /opt/loom/.env")
        node.appendStartCommand("/usr/local/bin/seedemu-start-loom")

    def print(self, indent: int) -> str:
        return " " * indent + "LoomRegistrarServer\n"


class LoomRegistrarService(Service):
    """SeedEmu service wrapper for the Loom Registrar customer portal."""

    def __init__(self):
        super().__init__()
        self.addDependency("Base", False, False)

    def getName(self) -> str:
        return "LoomRegistrarService"

    @staticmethod
    def generateWebTlsCredentials(
        server_name: str, validity_days: int = 3650
    ) -> LoomWebTlsCredentials:
        """Generate a self-signed Loom HTTPS certificate for one deployment."""
        assert validity_days > 0, "TLS certificate validity must be positive"
        try:
            ipaddress.ip_address(server_name)
            subject_alt_name = "IP:" + server_name
        except ValueError:
            assert re.fullmatch(r"[A-Za-z0-9.-]{1,253}", server_name), (
                "invalid Loom TLS server name"
            )
            subject_alt_name = "DNS:" + server_name
        with tempfile.TemporaryDirectory() as work:
            directory = Path(work)
            key_path = directory / "web.key"
            certificate_path = directory / "web.crt"
            subprocess.run(
                [
                    "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", str(key_path), "-out", str(certificate_path),
                    "-days", str(validity_days), "-subj", "/CN=SeedEmu Loom",
                    "-addext", "subjectAltName=" + subject_alt_name,
                ],
                check=True,
                capture_output=True,
            )
            return LoomWebTlsCredentials(
                certificate=certificate_path.read_text(),
                private_key=key_path.read_text(),
            )

    def _createServer(self) -> LoomRegistrarServer:
        return LoomRegistrarServer()

    def print(self, indent: int) -> str:
        return " " * indent + "LoomRegistrarService\n"


__all__ = ["LoomRegistrarServer", "LoomRegistrarService", "LoomWebTlsCredentials"]
