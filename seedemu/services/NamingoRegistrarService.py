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
""".format(
            database=self.__db_name,
            services="\n".join(services),
            automation=automation,
        )

    def install(self, node: Node):
        assert (
            self.__enable_whois
            or self.__enable_rdap
            or self.__enable_automation
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
        for component in components:
            node.addBuildCommand(
                "COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --no-interaction "
                "--prefer-dist --working-dir={}/{}".format(
                    NAMINGO_INSTALL_DIR, component
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
        node.setFile("/usr/local/bin/seedemu-start-namingo", self._start_script())
        node.addBuildCommandAtEnd("chmod +x /usr/local/bin/seedemu-start-namingo")
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
