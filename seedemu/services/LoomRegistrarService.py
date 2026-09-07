from __future__ import annotations

import re
import json
from seedemu.services.LoomSourceAuth import SOURCE_AUTH_BOOTSTRAP, SOURCE_AUTH_ENDPOINT

from seedemu.core import Node, Server, Service

LOOM_REPOSITORY = "https://github.com/getnamingo/loom.git"
LOOM_INSTALL_DIR = "/opt/loom"

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


class LoomRegistrarServer(Server):
    """Deploy Loom with optional TLS and a source-token authentication adapter.

    This initial wrapper deliberately treats Loom's version-specific ``.env``
    and bootstrap procedure as scenario inputs.  It owns deployment and
    discovery metadata, while Loom owns sessions, forms, orders, and EPP logic.
    """

    def __init__(self):
        super().__init__()
        self.__commit: str | None = None
        self.__environment: str | None = None
        self.__port = 80
        self.__web_tls: tuple[str, str] | None = None
        self.__source_accounts: dict[str, dict[str, str | float]] = {}
        self.__credential_ref: str | None = None
        self.__bootstrap_commands: list[str] = []

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
        self.__environment = environment.rstrip() + "\n"
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

    def addSourceAccount(self, source_id: str, address: str, token_sha256: str,
                         email: str, username: str,
                         credit_limit: float = 0.0) -> LoomRegistrarServer:
        """Provision one verified ordinary account; store only its token hash."""
        assert re.fullmatch(r"[0-9a-f]{64}", token_sha256)
        assert 0 <= credit_limit <= 1_000_000
        assert source_id not in self.__source_accounts
        self.__source_accounts[source_id] = dict(address=address, token_sha256=token_sha256,
                                                email=email, username=username,
                                                credit_limit=credit_limit)
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
"""

    def install(self, node: Node):
        assert self.__commit is not None, "setCommit() is required"
        assert self.__environment is not None, "setEnvironment() is required"
        assert self.__bootstrap_commands, (
            "at least one Loom bootstrap command is required"
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
        node.setFile(f"{LOOM_INSTALL_DIR}/.env", self.__environment)
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

    def _createServer(self) -> LoomRegistrarServer:
        return LoomRegistrarServer()

    def print(self, indent: int) -> str:
        return " " * indent + "LoomRegistrarService\n"


__all__ = ["LoomRegistrarServer", "LoomRegistrarService"]
