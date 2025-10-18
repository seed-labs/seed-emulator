#!/usr/bin/env python3
# encoding: utf-8
"""
B29 Email Auto Generator (transport-map)
- Quickly generate N mail providers with simple transport maps (no DNS) for rapid demos.
- Intended to live with B29 to avoid scattering scripts.

Notes:
- For robustness, default ASN range starts at 150 (<=255) to avoid 'auto' prefix limitation in SEED when ASN>255.
- If you need more providers, adjust --asn-start accordingly but keep it <= 250.

Examples:
  python tools/email_autogen.py --platform arm --domains seedemail.net corporate.local smallbiz.org --asn-start 150
  python tools/email_autogen.py --platform arm --providers 8 --asn-start 150

Then:
  cd output && docker-compose up -d
"""

import argparse
import os
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
    ap = argparse.ArgumentParser(description='B29 Email Auto Generator (transport-map)')
    ap.add_argument('--platform', choices=['amd', 'arm'], default='arm')
    ap.add_argument('--providers', type=int, default=None, help='number of providers to create (overridden by --domains)')
    ap.add_argument('--domains', nargs='*', default=None, help='explicit domain list (overrides providers count)')
    ap.add_argument('--asn-start', type=int, default=150, help='starting ASN for providers (<=250 recommended)')
    return ap.parse_args()


def make_safe_name(domain: str) -> str:
    return domain.replace('.', '-').replace('_', '-')


def run():
    args = parse_args()
    if args.asn_start > 250:
        raise SystemExit('asn-start must be <= 250 to avoid SEED auto-prefix limitation (asn>255 not supported by auto).')

    platform = Platform.ARM64 if args.platform == 'arm' else Platform.AMD64
    platform_str = 'linux/arm64' if args.platform == 'arm' else 'linux/amd64'

    # Domains
    if args.domains and len(args.domains) > 0:
        domains: List[str] = args.domains
    else:
        defaults = [
            'seedemail.net', 'corporate.local', 'smallbiz.org',
            'p4.local', 'p5.local', 'p6.local', 'p7.local', 'p8.local'
        ]
        n = args.providers if args.providers else 3
        domains = defaults[: n]

    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    ibgp = Ibgp()
    ospf = Ospf()

    # One IX and a single ISP
    base.createInternetExchange(100)
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
            'ports': {
                'smtp': str(2500 + idx),
                'submission': str(5800 + idx),
                'imap': str(1400 + idx),
                'imaps': str(9900 + idx),
            },
        })

    # Peer each provider with the ISP and RS
    for m in mailservers:
        ebgp.addPrivatePeering(100, 2, m['asn'], PeerRelationship.Provider)
    ebgp.addRsPeers(100, [2] + [m['asn'] for m in mailservers])

    # Add layers and render
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
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

    # Compile under tools/output to avoid colliding with B29 main output
    script_dir = os.path.dirname(__file__)
    out_dir = os.path.join(script_dir, 'output')
    emu.compile(docker, out_dir, override=True)

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
    print("\n" + "=" * 70)

if __name__ == '__main__':
    run()
