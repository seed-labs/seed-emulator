from __future__ import annotations
"""
EmailService (skeleton)

A lightweight helper to programmatically attach email servers to a SEED Emulator
Docker compilation in either 'transport' mode (explicit Postfix transport maps)
or 'dns' mode (DNS-first, using smtp_host_lookup = dns).

This is a utility class intended to be used by example scripts. It does not
subclass Service; instead, it generates Docker compose entries and attaches
containers via the Docker compiler API.

Example usage:

    svc = EmailService(platform="linux/arm64", mode="transport")
    svc.add_provider(domain="seedemail.net", asn=150, ip="10.150.0.10", gateway="10.150.0.254",
                     ports={"smtp": "2525", "submission": "5870", "imap": "1430", "imaps": "9930"})
    svc.add_provider(domain="corporate.local", asn=151, ip="10.151.0.10", gateway="10.151.0.254",
                     ports={"smtp": "2526", "submission": "5871", "imap": "1431", "imaps": "9931"})
    svc.attach_to_docker(docker)

"""
from typing import Dict, List, Optional, Callable
import os


MAILSERVER_COMPOSE_TEMPLATE_TRANSPORT = """\
    {name}:
        image: mailserver/docker-mailserver:12.1
        platform: {platform}
        container_name: {name}
        hostname: {hostname}
        domainname: {domain}
        restart: unless-stopped
        privileged: true
        environment:
            - OVERRIDE_HOSTNAME={hostname}.{domain}
            - PERMIT_DOCKER=connected-networks
            - ONE_DIR=1
            - ENABLE_CLAMAV=0
            - ENABLE_FAIL2BAN=0
            - ENABLE_POSTGREY=0
            - ENABLE_OPENDKIM=0
            - ENABLE_OPENDMARC=0
            - ENABLE_POLICYD_SPF=0
            - DMS_DEBUG=1
        volumes:
            - ./{name}-data/mail-data/:/var/mail/
            - ./{name}-data/mail-state/:/var/mail-state/
            - ./{name}-data/mail-logs/:/var/log/mail/
            - ./{name}-data/config/:/tmp/docker-mailserver/
            - /etc/localtime:/etc/localtime:ro
        ports:
            - "{smtp_port}:25"
            - "{submission_port}:587"
            - "{imap_port}:143"
            - "{imaps_port}:993"
        cap_add:
            - NET_ADMIN
            - SYS_PTRACE
        command: >
            sh -c "
            echo 'Starting mailserver setup...' &&
            ip route del default 2>/dev/null || true &&
            ip route add default via {gateway} dev eth0 &&
            echo 'Configuring Postfix transport for cross-domain mail...' &&
{transport_entries}            
            postmap /etc/postfix/transport &&
            postconf -e 'transport_maps = hash:/etc/postfix/transport' &&
            sleep 10 &&
            supervisord -c /etc/supervisor/supervisord.conf
            "
"""

MAILSERVER_COMPOSE_TEMPLATE_DNS = """\
    {name}:
        image: mailserver/docker-mailserver:12.1
        platform: {platform}
        container_name: {name}
        hostname: {hostname}
        domainname: {domain}
        restart: unless-stopped
        privileged: true
        {dns_block}
        environment:
            - OVERRIDE_HOSTNAME={hostname}.{domain}
            - PERMIT_DOCKER=connected-networks
            - ONE_DIR=1
            - ENABLE_CLAMAV=0
            - ENABLE_FAIL2BAN=0
            - ENABLE_POSTGREY=0
            - ENABLE_OPENDKIM=0
            - ENABLE_OPENDMARC=0
            - ENABLE_POLICYD_SPF=0
            - DMS_DEBUG=1
        volumes:
            - ./{name}-data/mail-data/:/var/mail/
            - ./{name}-data/mail-state/:/var/mail-state/
            - ./{name}-data/mail-logs/:/var/log/mail/
            - ./{name}-data/config/:/tmp/docker-mailserver/
            - /etc/localtime:/etc/localtime:ro
        ports:
            - "{smtp_port}:25"
            - "{imap_port}:143"
        cap_add:
            - NET_ADMIN
            - SYS_PTRACE
        command: >
            sh -c "
            echo 'Starting mailserver setup...' &&
            ip route del default 2>/dev/null || true &&
            ip route add default via {gateway} dev eth0 &&
            echo 'Configuring Postfix for DNS-first routing...' &&
            postconf -e 'relayhost =' &&
            postconf -e 'smtp_host_lookup = dns' &&
            postconf -e 'smtp_dns_support_level = enabled' &&
            sleep 10 &&
            supervisord -c /etc/supervisor/supervisord.conf
            "
"""


class EmailService:
    def __init__(self, platform: str = "linux/amd64", mode: str = "transport", dns_nameserver: Optional[str] = None):
        assert mode in ("transport", "dns"), "mode must be 'transport' or 'dns'"
        self._platform = platform
        self._mode = mode
        self._dns_nameserver = dns_nameserver
        self._providers: List[Dict] = []
        self._use_build_wrappers = True  # build minimal local images to avoid docker-compose image inspect key error

    def add_provider(
        self,
        domain: str,
        asn: int,
        ip: str,
        gateway: str,
        net: str = "net0",
        hostname: str = "mail",
        name: Optional[str] = None,
        ports: Optional[Dict[str, str]] = None,
        dns: Optional[str] = None,
    ) -> "EmailService":
        """Register a provider/mailserver to be attached later.
        ports expected keys for transport-mode: smtp, submission, imap, imaps
        ports expected keys for dns-mode: smtp, imap (exposed sets only these two)
        """
        if name is None:
            safe = domain.replace(".", "-")
            name = f"mail-{safe}"
        if ports is None:
            # provide basic defaults
            ports = {
                "smtp": "2525",
                "submission": "5870",
                "imap": "1430",
                "imaps": "9930",
            }
        self._providers.append(
            {
                "name": name,
                "hostname": hostname,
                "domain": domain,
                "asn": asn,
                "network": net,
                "ip": ip,
                "gateway": gateway,
                "ports": ports,
                "dns": dns,
            }
        )
        return self

    def get_providers(self) -> List[Dict]:
        return list(self._providers)

    def attach_to_docker(self, docker) -> None:
        """Generate compose entries and attach containers to the Docker compiler.
        'docker' is expected to be an instance of seedemu.compiler.Docker.
        """
        # domain->IP map for transport maps
        domain_map = {p["domain"]: p["ip"] for p in self._providers}

        for p in self._providers:
            if self._mode == "transport":
                transport_lines = ""
                for dom, ip in domain_map.items():
                    if dom == p["domain"]:
                        continue
                    transport_lines += f"            echo '{dom} smtp:[{ip}]:25' >> /etc/postfix/transport &&\n"
                    transport_lines += f"            echo 'mail.{dom} smtp:[{ip}]:25' >> /etc/postfix/transport &&\n"
                if self._use_build_wrappers:
                    # use build wrappers
                    compose_entry = (
                        f"    {p['name']}:\n"
                        f"        build:\n"
                        f"            context: ./{p['name']}_wrapper\n"
                        f"        platform: {self._platform}\n"
                        f"        container_name: {p['name']}\n"
                        f"        hostname: {p['hostname']}\n"
                        f"        domainname: {p['domain']}\n"
                        f"        restart: unless-stopped\n"
                        f"        privileged: true\n"
                        f"        environment:\n"
                        f"            - OVERRIDE_HOSTNAME={p['hostname']}.{p['domain']}\n"
                        f"            - PERMIT_DOCKER=connected-networks\n"
                        f"            - ONE_DIR=1\n"
                        f"            - ENABLE_CLAMAV=0\n"
                        f"            - ENABLE_FAIL2BAN=0\n"
                        f"            - ENABLE_POSTGREY=0\n"
                        f"            - ENABLE_OPENDKIM=0\n"
                        f"            - ENABLE_OPENDMARC=0\n"
                        f"            - ENABLE_POLICYD_SPF=0\n"
                        f"            - DMS_DEBUG=1\n"
                        f"        ports:\n"
                        f"            - \"{p['ports'].get('smtp','25')}:25\"\n"
                        f"            - \"{p['ports'].get('submission','587')}:587\"\n"
                        f"            - \"{p['ports'].get('imap','143')}:143\"\n"
                        f"            - \"{p['ports'].get('imaps','993')}:993\"\n"
                        f"        cap_add:\n"
                        f"            - NET_ADMIN\n"
                        f"            - SYS_PTRACE\n"
                        f"        command: >\n"
                        f"            sh -c \"\n"
                        f"            echo 'Starting mailserver setup...' &&\n"
                        f"            ip route del default 2>/dev/null || true &&\n"
                        f"            ip route add default via {p['gateway']} dev eth0 &&\n"
                        f"            echo 'Configuring Postfix transport for cross-domain mail...' &&\n"
                        f"{transport_lines}"
                        f"            postmap /etc/postfix/transport &&\n"
                        f"            postconf -e 'transport_maps = hash:/etc/postfix/transport' &&\n"
                        f"            sleep 10 &&\n"
                        f"            supervisord -c /etc/supervisor/supervisord.conf\n"
                        f"            \"\n"
                    )
                else:
                    compose_entry = MAILSERVER_COMPOSE_TEMPLATE_TRANSPORT.format(
                        name=p["name"],
                        platform=self._platform,
                        hostname=p["hostname"],
                        domain=p["domain"],
                        gateway=p["gateway"],
                        smtp_port=p["ports"].get("smtp", "25"),
                        submission_port=p["ports"].get("submission", "587"),
                        imap_port=p["ports"].get("imap", "143"),
                        imaps_port=p["ports"].get("imaps", "993"),
                        transport_entries=transport_lines,
                    )
            else:
                dns_value = p.get("dns") or self._dns_nameserver
                dns_block = f"dns:\n          - {dns_value}\n" if dns_value else ""
                if self._use_build_wrappers:
                    compose_entry = (
                        f"    {p['name']}:\n"
                        f"        build:\n"
                        f"            context: ./{p['name']}_wrapper\n"
                        f"        platform: {self._platform}\n"
                        f"        container_name: {p['name']}\n"
                        f"        hostname: {p['hostname']}\n"
                        f"        domainname: {p['domain']}\n"
                        f"        restart: unless-stopped\n"
                        f"        privileged: true\n"
                        f"        {dns_block}"
                        f"        environment:\n"
                        f"            - OVERRIDE_HOSTNAME={p['hostname']}.{p['domain']}\n"
                        f"            - PERMIT_DOCKER=connected-networks\n"
                        f"            - ONE_DIR=1\n"
                        f"            - ENABLE_CLAMAV=0\n"
                        f"            - ENABLE_FAIL2BAN=0\n"
                        f"            - ENABLE_POSTGREY=0\n"
                        f"            - ENABLE_OPENDKIM=0\n"
                        f"            - ENABLE_OPENDMARC=0\n"
                        f"            - ENABLE_POLICYD_SPF=0\n"
                        f"            - DMS_DEBUG=1\n"
                        f"        ports:\n"
                        f"            - \"{p['ports'].get('smtp','25')}:25\"\n"
                        f"            - \"{p['ports'].get('imap','143')}:143\"\n"
                        f"        cap_add:\n"
                        f"            - NET_ADMIN\n"
                        f"            - SYS_PTRACE\n"
                        f"        command: >\n"
                        f"            sh -c \"\n"
                        f"            echo 'Starting mailserver setup...' &&\n"
                        f"            ip route del default 2>/dev/null || true &&\n"
                        f"            ip route add default via {p['gateway']} dev eth0 &&\n"
                        f"            echo 'Configuring Postfix for DNS-first routing...' &&\n"
                        f"            postconf -e 'relayhost =' &&\n"
                        f"            postconf -e 'smtp_host_lookup = dns' &&\n"
                        f"            postconf -e 'smtp_dns_support_level = enabled' &&\n"
                        f"            sleep 10 &&\n"
                        f"            supervisord -c /etc/supervisor/supervisord.conf\n"
                        f"            \"\n"
                    )
                else:
                    compose_entry = MAILSERVER_COMPOSE_TEMPLATE_DNS.format(
                        name=p["name"],
                        platform=self._platform,
                        hostname=p["hostname"],
                        domain=p["domain"],
                        gateway=p["gateway"],
                        smtp_port=p["ports"].get("smtp", "25"),
                        imap_port=p["ports"].get("imap", "143"),
                        dns_block=dns_block,
                    )

            docker.attachCustomContainer(
                compose_entry=compose_entry,
                asn=p["asn"],
                net=p["network"],
                ip_address=p["ip"],
            )

    def get_output_callbacks(self) -> List[Callable]:
        """Return file-writer callbacks to be executed in output/ to create wrapper Dockerfiles.
        These will be run via Emulator.updateOutputDirectory after compile.
        """
        if not self._use_build_wrappers:
            return []
        callbacks: List[Callable] = []
        for p in self._providers:
            wrapper_dir = f"{p['name']}_wrapper"
            def make_cb(dir_name=wrapper_dir):
                def cb(_compiler):
                    # We're likely running from the scenario folder, not output/
                    out_dir = os.path.join('output', dir_name)
                    os.makedirs(out_dir, exist_ok=True)
                    dockerfile_path = os.path.join(out_dir, 'Dockerfile')
                    with open(dockerfile_path, 'w') as f:
                        f.write('FROM mailserver/docker-mailserver:12.1\n')
                return cb
            callbacks.append(make_cb())
        return callbacks
