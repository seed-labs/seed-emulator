#!/usr/bin/env python3
# encoding: utf-8
"""
Email Auto Generator (MVP)
- Quickly generate N mail providers with simple routing via transport maps (no DNS).
- Produces a working multi-domain email system similar to 29, with unique host ports.

Usage examples:
  python email_autogen.py --platform amd --providers 3 \
    --domains seedemail.net corporate.local smallbiz.org \
    --users-per-server 2 --user-prefix user --start-index 1

Then:
  cd output && docker-compose up -d
  # After containers are up, create accounts with your own script or interactively:
  #   printf "pass\npass\n" | docker exec -i mail-seedemail-net setup email add user1@seedemail.net
"""

import os, sys, argparse
from typing import List

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.utilities import Makers

MAILSERVER_COMPOSE_TEMPLATE = """\
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
            echo 'Fixing network gateway...' &&
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


def parse_args():
    ap = argparse.ArgumentParser(description='Email Auto Generator (MVP)')
    ap.add_argument('--platform', choices=['amd', 'arm'], default='arm')
    ap.add_argument('--providers', type=int, default=3, help='number of providers to create')
    ap.add_argument('--domains', nargs='*', default=None, help='explicit domain list (overrides providers count)')
    ap.add_argument('--asn-start', type=int, default=300, help='starting ASN for providers')
    ap.add_argument('--users-per-server', type=int, default=0, help='if >0, print example account creation commands')
    ap.add_argument('--user-prefix', default='user', help='prefix for generated users')
    ap.add_argument('--start-index', type=int, default=1, help='starting index for users')
    return ap.parse_args()


def make_safe_name(domain: str) -> str:
    return domain.replace('.', '-').replace('_', '-')


def run():
    args = parse_args()
    platform = Platform.ARM64 if args.platform == 'arm' else Platform.AMD64
    platform_str = 'linux/arm64' if args.platform == 'arm' else 'linux/amd64'

    # Domains
    if args.domains and len(args.domains) > 0:
        domains: List[str] = args.domains
    else:
        # simple defaults
        defaults = [
            'seedemail.net', 'corporate.local', 'smallbiz.org',
            'p4.local', 'p5.local', 'p6.local', 'p7.local', 'p8.local'
        ]
        domains = defaults[: args.providers]

    # Emulator + topology
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    ibgp = Ibgp()
    ospf = Ospf()

    # One IX and a single ISP
    ix100 = base.createInternetExchange(100)
    ix100.getPeeringLan().setDisplayName('Email-Auto-IX')
    Makers.makeTransitAs(base, 2, [100], [])

    # Create provider ASes (1 host for mailserver)
    mailservers = []
    for idx, dom in enumerate(domains, start=0):
        asn = args.asn_start + idx
        Makers.makeStubAsWithHosts(emu, base, asn, 100, 1)
        ms_ip = f'10.{asn}.0.10'
        gw_ip = f'10.{asn}.0.254'

        name = f"mail-{make_safe_name(dom)}"
        mailservers.append({
            'name': name,
            'hostname': 'mail',
            'domain': dom,
            'asn': asn,
            'network': 'net0',
            'ip': ms_ip,
            'gateway': gw_ip,
            # Unique host ports per server
            'ports': {
                'smtp': str(2500 + idx),
                'submission': str(5800 + idx),
                'imap': str(1400 + idx),
                'imaps': str(9900 + idx),
            },
        })

    # Peer each provider with the ISP
    for m in mailservers:
        ebgp.addPrivatePeering(100, 2, m['asn'], PeerRelationship.Provider)

    # Also add RS peering at IX for simplicity/visibility
    ebgp.addRsPeers(100, [2] + [m['asn'] for m in mailservers])

    # Add layers
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)

    # Render
    emu.render()

    docker = Docker(platform=platform)

    # Precompute domain->IP mapping for transport map generation
    domain_map = { m['domain']: m['ip'] for m in mailservers }

    # Attach mailserver containers
    for mail in mailservers:
        transport_lines = ''
        for dom, ip in domain_map.items():
            if dom == mail['domain']:
                continue
            transport_lines += f"            echo '{dom} smtp:[{ip}]:25' >> /etc/postfix/transport &&\n"
            transport_lines += f"            echo 'mail.{dom} smtp:[{ip}]:25' >> /etc/postfix/transport &&\n"

        compose_entry = MAILSERVER_COMPOSE_TEMPLATE.format(
            name=mail['name'],
            platform=platform_str,
            hostname=mail['hostname'],
            domain=mail['domain'],
            gateway=mail['gateway'],
            smtp_port=mail['ports']['smtp'],
            submission_port=mail['ports']['submission'],
            imap_port=mail['ports']['imap'],
            imaps_port=mail['ports']['imaps'],
            transport_entries=transport_lines,
        )

        docker.attachCustomContainer(
            compose_entry=compose_entry,
            asn=mail['asn'],
            net=mail['network'],
            ip_address=mail['ip'],
        )

    # Compile
    emu.compile(docker, './output', override=True)

    # Summary
    print("\n" + "=" * 70)
    print("Email Auto Generator - Output")
    print("=" * 70)
    for mail in mailservers:
        print(f"\n📧 {mail['domain']} (AS{mail['asn']})")
        print(f"   Container: {mail['name']}")
        print(f"   Internal IP: {mail['ip']}")
        print(f"   SMTP Port: localhost:{mail['ports']['smtp']}")
        print(f"   IMAP Port: localhost:{mail['ports']['imap']}")
    print("\nTo start:")
    print("  cd output && docker-compose up -d")

    # Optionally print example accounts
    if args.users_per_server > 0:
        print("\nExample account creation commands (run after up):")
        for mail in mailservers:
            dom = mail['domain']
            for i in range(args.start_index, args.start_index + args.users_per_server):
                user = f"{args.user_prefix}{i}@{dom}"
                print(f"  printf 'password123\\npassword123\\n' | docker exec -i {mail['name']} setup email add {user}")
    print("\n" + "=" * 70)


if __name__ == '__main__':
    run()
