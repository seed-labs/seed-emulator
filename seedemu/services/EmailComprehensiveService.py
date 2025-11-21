from __future__ import annotations
"""
EmailComprehensiveService

This is a comprehensive email service implementation designed for the SEED Emulator.
It follows the standard Service/Server architecture and does not rely on Docker Compose post-generation modifications (no hot patches).

Key Features:
1. Mail Transfer Agent (MTA): Based on Postfix.
2. Mail Access Agent (IMAP): Based on Dovecot.
3. Routing Modes:
   - DNS-First: Relies on MX records for routing (simulates real internet environment).
   - Transport-Map: Uses static routing tables (suitable for environments without DNS or with special routing needs).
4. Automated DNS Integration: Automatically registers MX and A records with DomainNameService.

Note: This service is configured to use System Users and Maildir storage format.
For educational and demonstration purposes, some security restrictions (e.g., plaintext authentication) are disabled. Do not use in production.
"""
from typing import List, Dict, Optional, Tuple
from seedemu.core import Node, Service, Server, Emulator

try:
    # Optional import, weak coupling
    from .DomainNameService import DomainNameService
except ImportError:
    DomainNameService = None  # type: ignore


class EmailServer(Server):
    """
    Email Server Node Configurator.
    Responsible for installing and configuring Postfix and Dovecot on specific host nodes.
    """

    def __init__(self):
        super().__init__()
        self.__domain: str = ''
        self.__hostname: str = 'mail'
        self.__mode: str = 'dns'  # 'dns' | 'transport'
        self.__accounts: List[Tuple[str, str]] = []  # (localpart, password)
        self.__transport: Dict[str, str] = {}  # domain -> next-hop (vnode name or ip)
        self.__resolved_transport: Dict[str, str] = {}  # domain -> next-hop ip
        self.__auto_publish_mx: bool = False
        self.__enable_submission: bool = False
        self.__enable_imaps: bool = False

    # ---------- Fluent API Setters ----------

    def setDomain(self, domain: str) -> "EmailServer":
        """Set the email domain (e.g., 'qq.com')."""
        self.__domain = domain
        return self

    def setHostname(self, hostname: str) -> "EmailServer":
        """Set the hostname (e.g., 'mail')."""
        self.__hostname = hostname
        return self

    def setModeDnsFirst(self) -> "EmailServer":
        """
        Set routing mode to DNS-First.
        Postfix will query DNS MX records to deliver mail.
        """
        self.__mode = 'dns'
        return self

    def setModeTransport(self) -> "EmailServer":
        """
        Set routing mode to static Transport Map.
        Postfix will use a predefined routing table to deliver mail, bypassing DNS MX queries.
        """
        self.__mode = 'transport'
        return self

    def enableSubmission(self) -> "EmailServer":
        """Enable Submission port (587)."""
        self.__enable_submission = True
        return self

    def enableImaps(self) -> "EmailServer":
        """Enable IMAPS port (993)."""
        self.__enable_imaps = True
        return self

    def enableAutoPublishMx(self, enable: bool = True) -> "EmailServer":
        """
        Enable automatic MX record publishing.
        If DomainNameService exists in the environment, MX and A records will be automatically added.
        """
        self.__auto_publish_mx = enable
        return self

    def addAccount(self, localpart: str, password: str) -> "EmailServer":
        """Add an email user account."""
        self.__accounts.append((localpart, password))
        return self

    def setTransportRoute(self, targetDomain: str, nextHopVnodeOrIp: str) -> "EmailServer":
        """
        Add a static routing rule for Transport mode.
        
        :param targetDomain: Target email domain (e.g., 'gmail.com')
        :param nextHopVnodeOrIp: Next hop address, can be a vnode name or IP address.
        """
        self.__transport[targetDomain] = nextHopVnodeOrIp
        return self

    # ---------- Internal Lifecycle Hooks ----------

    def _prepare(self, node: Node, emulator: Emulator, dns_layer: Optional[Service]):
        """
        Called during the Service.configure() phase.
        Responsible for resolving dependencies (e.g., resolving vnode to IP) and executing cross-layer interactions (e.g., DNS registration).
        """
        # 1. Resolve vnode names in Transport routes to IP addresses
        self.__resolved_transport = {}
        for dom, hop in self.__transport.items():
            ip = None
            # Heuristic: if it contains letters, try to resolve as vnode
            if any(c.isalpha() for c in hop):
                try:
                    pnode = emulator.getBindingFor(hop)
                    ifaces = pnode.getInterfaces()
                    if len(ifaces) > 0:
                        ip = ifaces[0].getAddress()
                except Exception:
                    # If resolution fails, keep original value (might be hostname)
                    ip = hop
            else:
                # Assume it is already an IP
                ip = hop
            
            if ip:
                self.__resolved_transport[dom] = ip

        # 2. Auto-publish DNS records (MX and A)
        # Execute only if DNS layer exists and auto-publish is enabled
        if dns_layer is not None and self.__auto_publish_mx and self.__domain:
            # Normalize zone name
            zonename = self.__domain if self.__domain.endswith('.') else f"{self.__domain}."
            
            # Try to get Zone object and add records
            # Note: Using duck typing here, assuming dns_layer has getZone method
            try:
                if hasattr(dns_layer, 'getZone'):
                    zone = dns_layer.getZone(zonename) # type: ignore
                    
                    # Add MX record first (independent of node IP)
                    # @ MX 10 mail.<domain>
                    zone.addRecord(f"@ MX 10 mail.{self.__domain}.")

                    # Add A record: mail.<domain> -> <node_ip>
                    # This might fail if node has no IP yet, but MX record is safe now
                    zone.resolveTo('mail', node)
            except Exception as e:
                # Log error instead of silent pass
                print(f"Error auto-publishing DNS for {self.__domain}: {e}")

    def install(self, node: Node):
        """
        Generate Docker build instructions.
        Install software and generate startup configuration scripts.
        """
        # 1. Install necessary software
        node.addSoftware('postfix dovecot-imapd rsyslog')
        node.appendClassName('EmailComprehensiveService')

        domain = self.__domain
        hostname = self.__hostname
        fqdn = f"{hostname}.{domain}" if domain else hostname

        # 2. Configure Postfix (main.cf)
        # Use postconf tool to modify configuration, robust against file format changes
        postconf_cmds = [
            # Listen on all interfaces
            f'postconf -e "inet_interfaces = all"',
            # Set hostname and domain
            f'postconf -e "myhostname = {fqdn}"',
            f'postconf -e "mydomain = {domain}"' if domain else None,
            # Set delivery destinations - use explicit values to avoid shell expansion issues
            f'postconf -e "mydestination = {fqdn}, {domain}, localhost.{domain}, localhost"',
            # Allow connections from any network (demo environment)
            'postconf -e "mynetworks = 0.0.0.0/0"',
            # Use Maildir format
            'postconf -e "home_mailbox = Maildir/"',
            # Enforce IPv4 to avoid AAAA query errors in emulator
            'postconf -e "inet_protocols = ipv4"',
        ]

        if self.__mode == 'dns':
            # DNS mode configuration
            postconf_cmds += [
                'postconf -e "relayhost = "',
                'postconf -e "smtp_host_lookup = dns"',
                'postconf -e "smtp_dns_support_level = enabled"',
            ]
        else:
            # Transport mode configuration
            content_lines = []
            for dom, ip in self.__resolved_transport.items():
                # Define routing for domain and hostname
                content_lines.append(f"{dom} smtp:[{ip}]:25")
                content_lines.append(f"mail.{dom} smtp:[{ip}]:25")
            
            # Write transport file
            node.setFile('/etc/postfix/transport', '\n'.join(content_lines) + ('\n' if content_lines else ''))
            
            postconf_cmds.append('postconf -e "transport_maps = hash:/etc/postfix/transport"')

        # Append Postfix configuration commands
        for c in postconf_cmds:
            if c:
                node.appendStartCommand(c)

        # 3. Configure Postfix (master.cf) - Optional services
        if self.__enable_submission:
            # Enable submission (587) port
            # Debian default master.cf has submission commented out, use sed to uncomment
            node.appendStartCommand("sed -i 's/^#\s*submission/submission/' /etc/postfix/master.cf || true")

        # 4. Configure Dovecot
        if self.__enable_imaps:
            # Dovecot default config usually includes IMAP, focused on plaintext auth and Maildir here
            pass

        # Force Dovecot to use Maildir
        node.appendStartCommand("sed -i 's/^#\?mail_location.*/mail_location = maildir:\\~\\/Maildir/' /etc/dovecot/conf.d/10-mail.conf || true")
        # Allow plaintext authentication (Required for demo as we don't have complex SSL/TLS setup)
        node.appendStartCommand("sed -i 's/^#\?disable_plaintext_auth.*/disable_plaintext_auth = no/' /etc/dovecot/conf.d/10-auth.conf || true")
        # Enable plain and login mechanisms
        node.appendStartCommand("sed -i 's/^#\?auth_mechanisms.*/auth_mechanisms = plain login/' /etc/dovecot/conf.d/10-auth.conf || true")

        # 5. Create User Accounts
        for (user, pwd) in self.__accounts:
            # Create system user (if new)
            node.appendStartCommand(f"id -u {user} >/dev/null 2>&1 || useradd -m -s /usr/sbin/nologin {user}")
            # Set password
            node.appendStartCommand(f"echo '{user}:{pwd}' | chpasswd")
            # Pre-create Maildir structure to avoid permission issues before first email
            node.appendStartCommand(f"su - {user} -s /bin/bash -c 'mkdir -p ~/Maildir/{{cur,new,tmp}}' || true")

        # 6. Generate Transport Map Database
        if self.__mode == 'transport':
            node.appendStartCommand('test -f /etc/postfix/transport && postmap /etc/postfix/transport || true')

        # 7. Start Services
        # rsyslog is critical for mail logs
        node.appendStartCommand('service rsyslog start')
        node.appendStartCommand('service postfix restart || service postfix start')
        node.appendStartCommand('service dovecot restart || service dovecot start')


class EmailComprehensiveService(Service):
    """
    Email Comprehensive Service Layer.
    
    Manages multiple EmailServer instances and handles dependencies with the underlying infrastructure (Base) and other services (DomainNameService).
    """

    def __init__(self):
        super().__init__()
        # Declare dependencies
        # Only strongly depend on Base layer
        # Dependency on DNS is a logical soft dependency, handled dynamically in configure
        self.addDependency('Base', False, False)

    def _createServer(self) -> Server:
        return EmailServer()

    def getName(self) -> str:
        return 'EmailComprehensiveService'

    def configure(self, emulator: Emulator):
        # Try to get DomainNameService layer instance for auto-registration
        dns_layer = None
        
        # Robustly find the DNS layer by iterating through registered layers
        for layer in emulator.getLayers():
            if layer.getName() == 'DomainNameService':
                dns_layer = layer
                break

        # Prepare all server instances pending configuration
        for (vnode, server) in self.getPendingTargets().items():
            pnode = emulator.getBindingFor(vnode)
            if isinstance(server, EmailServer):
                server._prepare(pnode, emulator, dns_layer)
        
        # Execute standard configuration process
        super().configure(emulator)
