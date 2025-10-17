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
from typing import Dict, List, Optional


MAILSERVER_COMPOSE_TEMPLATE_TRANSPORT = """\
    {name}:
        image: mailserver/docker-mailserver:edge
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
        image: mailserver/docker-mailserver:edge
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
                dns_block = ""
                if self._dns_nameserver:
                    # The template provides 8 leading spaces before {dns_block} (service-level indent).
                    # YAML requires the list items to be indented further than the key.
                    # Therefore, indent list items by 10 spaces.
                    dns_block = "dns:\n          - {}\n".format(self._dns_nameserver)
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
