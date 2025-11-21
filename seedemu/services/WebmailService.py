from __future__ import annotations
from seedemu.core import Node, Service, Server, Emulator
from typing import Optional


class WebmailServer(Server):
    """
    Webmail (Roundcube) Server Instance.
    
    Standard Service/Server implementation:
    - Uses node.addSoftware/setFile/appendStartCommand APIs exclusively.
    - Deploys Apache + PHP + Roundcube (SQLite backend) and serves Webmail via /roundcube path.
    - Supports flexible IMAP/SMTP target configuration (vnode name, hostname, or IP).
    """

    def __init__(self):
        super().__init__()
        self.__imap_target: str = "127.0.0.1"  # vnode name, hostname, or IP
        self.__smtp_target: str = "127.0.0.1"  # vnode name, hostname, or IP
        self.__smtp_port: int = 25
        self.__resolved_imap: Optional[str] = None
        self.__resolved_smtp: Optional[str] = None
        # Debian packaged roundcube defaults
        self.__alias_path: str = "/roundcube"

    # ---------- Fluent API Setters ----------

    def setImapTarget(self, target: str) -> "WebmailServer":
        """Set the IMAP server target address."""
        self.__imap_target = target
        return self

    def setSmtpTarget(self, target: str) -> "WebmailServer":
        """Set the SMTP server target address."""
        self.__smtp_target = target
        return self

    def setSmtpPort(self, port: int) -> "WebmailServer":
        """Set the SMTP server port."""
        self.__smtp_port = port
        return self

    def setAliasPath(self, path: str) -> "WebmailServer":
        """
        Set the URL path for Webmail access.
        Default is /roundcube. Debian package provides configuration for this path.
        """
        self.__alias_path = path if path.startswith('/') else '/' + path
        return self

    # ---------- Internal Lifecycle Hooks ----------

    def _prepare(self, emulator: Emulator):
        """
        Resolve IMAP/SMTP targets during configure phase.
        If target is a vnode name, it resolves to the node's IP address.
        If target contains dots or colons, it is treated as a hostname or IP and left unchanged.
        """
        def resolve_target(t: str) -> str:
            if ('.' in t) or (':' in t):
                return t
            try:
                pnode = emulator.getBindingFor(t)
                ifaces = pnode.getInterfaces()
                if len(ifaces) > 0:
                    return ifaces[0].getAddress()
            except Exception:
                pass
            return t

        self.__resolved_imap = resolve_target(self.__imap_target)
        self.__resolved_smtp = resolve_target(self.__smtp_target)

    # ---------- Install ----------

    def install(self, node: Node):
        """
        Install and configure Roundcube on the target node.
        """
        # 1. Install Software Stack
        node.addSoftware('apache2 php php-imap php-sqlite3 php-mbstring php-xml php-json php-intl php-gd php-curl roundcube sqlite3')
        node.appendClassName('WebmailService')

        alias = self.__alias_path
        imap_host = self.__resolved_imap or self.__imap_target
        smtp_host = self.__resolved_smtp or self.__smtp_target
        smtp_port = self.__smtp_port

        # 2. Configure Apache Alias
        # Explicitly point to /usr/share/roundcube where the Debian package installs the application code.
        # This avoids 404 errors by ensuring the alias maps correctly to the program files.
        apache_conf = f'''Alias {alias} /usr/share/roundcube
<Directory /usr/share/roundcube/>
    Options FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
'''
        node.setFile('/etc/apache2/conf-available/roundcube.conf', apache_conf)

        # 3. Configure Roundcube (config.inc.php)
        # Use SQLite as backend for simplicity and self-containment in demo environments.
        config_inc = f'''<?php
$config['db_dsnw'] = 'sqlite:////var/lib/roundcube/db/sqlite.db?mode=0646';
$config['default_host'] = '{imap_host}';
$config['smtp_server'] = '{smtp_host}';
$config['smtp_port'] = {smtp_port};

// Disable SSL certificate verification for demo purposes (self-signed certs)
$config['imap_conn_options'] = array('ssl' => array('verify_peer' => false, 'allow_self_signed' => true));

// Disable SMTP authentication (Relies on Postfix open relay for trusted networks or mynetworks)
$config['smtp_user'] = null;
$config['smtp_pass'] = null;
$config['smtp_auth_type'] = '';

$config['support_url'] = '';
$config['des_key'] = 'seedseedseedseed'; // Static key for session encryption
$config['plugins'] = array();
?>
'''
        node.setFile('/etc/roundcube/config.inc.php', config_inc)

        # 4. Initialize Database and Permissions
        # Create necessary directories for SQLite DB and logs
        node.appendStartCommand("mkdir -p /var/lib/roundcube/db /var/lib/roundcube/logs /var/lib/roundcube/temp")
        # Initialize SQLite DB schema if not present
        node.appendStartCommand("if [ -f /usr/share/roundcube/SQL/sqlite.initial.sql ] && [ ! -f /var/lib/roundcube/db/sqlite.db ]; then sqlite3 /var/lib/roundcube/db/sqlite.db < /usr/share/roundcube/SQL/sqlite.initial.sql; fi")
        # Ensure correct ownership for Apache user
        node.appendStartCommand('chown -R www-data:www-data /var/lib/roundcube')
        
        # 5. Enable Apache Configurations
        node.appendStartCommand('a2enconf roundcube || true')
        node.appendStartCommand('a2enmod rewrite || true')
        
        # 6. Start Apache Service
        node.appendStartCommand('service apache2 restart || service apache2 start')


class WebmailService(Service):
    """
    Webmail (Roundcube) Service Layer.
    """

    def __init__(self):
        super().__init__()
        self.addDependency('Base', False, False)
        self.addDependency('Routing', False, False)

    def _createServer(self) -> Server:
        return WebmailServer()

    def getName(self) -> str:
        return 'WebmailService'

    def configure(self, emulator: Emulator):
        for (vnode, server) in self.getPendingTargets().items():
            if isinstance(server, WebmailServer):
                server._prepare(emulator)
        super().configure(emulator)
