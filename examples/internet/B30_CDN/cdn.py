#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Action, Binding, Emulator, Filter
from seedemu.layers import Ebgp, PeerRelationship
from seedemu.services import CDNService, DomainNameService

from examples.internet.B00_mini_internet import mini_internet


SERVICE_DOMAIN = 'www.example.com'
SERVICE_ZONE = 'example.com.'
OUTPUT_RELATIVE_PATH = 'examples/internet/B30_CDN/output'
DNS_INCLUDE_PATH = '/etc/bind/include/cdn_views.local'

DNS_VNODE = 'dns-auth'
DNS_NODE_NAME = 'cdn_dns'
DNS_IP = '10.150.0.53'

ORIGIN_VNODE = 'origin-main'
ORIGIN_SITE = {
    'asn': 184,
    'node_name': 'global_origin',
    'router_name': 'origin_br',
    'net_name': 'origin_net',
    'prefix': '10.184.0.0/24',
    'ip': '10.184.0.10',
    'ix': 102,
    'upstreams': [2, 4, 11],
}

EDGE_SITES = [
    {
        'vnode': 'edge-east',
        'region': 'east',
        'asn': 181,
        'node_name': 'nyc_edge',
        'router_name': 'nyc_br',
        'net_name': 'nyc_net',
        'prefix': '10.181.0.0/24',
        'ip': '10.181.0.100',
        'ix': 100,
        'upstreams': [2, 3, 4],
    },
    {
        'vnode': 'edge-west',
        'region': 'west',
        'asn': 182,
        'node_name': 'sjc_edge',
        'router_name': 'sjc_br',
        'net_name': 'sjc_net',
        'prefix': '10.182.0.0/24',
        'ip': '10.182.0.100',
        'ix': 101,
        'upstreams': [2, 12],
    },
    {
        'vnode': 'edge-central',
        'region': 'central',
        'asn': 183,
        'node_name': 'chi_edge',
        'router_name': 'chi_br',
        'net_name': 'chi_net',
        'prefix': '10.183.0.0/24',
        'ip': '10.183.0.100',
        'ix': 102,
        'upstreams': [2, 4, 11],
    },
]

CLIENT_REGION_BY_ASN = {
    150: 'east',
    151: 'east',
    152: 'west',
    153: 'west',
    154: 'central',
    160: 'east',
    161: 'east',
    162: 'east',
    163: 'east',
    164: 'east',
    170: 'central',
    171: 'central',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build a baseline CDN using CDNService')
    parser.add_argument('platform', nargs='?', default='amd', choices=['amd', 'arm'])
    return parser.parse_args()


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == 'amd' else Platform.ARM64


def add_edge_sites(base, ebgp: Ebgp):
    for site in EDGE_SITES:
        site_as = base.createAutonomousSystem(site['asn'])
        site_as.createNetwork(site['net_name'], site['prefix'])
        site_as.createHost(site['node_name']).joinNetwork(site['net_name'], address=site['ip'])
        site_as.createRouter(site['router_name']).joinNetwork(site['net_name']).joinNetwork(f'ix{site["ix"]}')
        ebgp.addPrivatePeerings(site['ix'], site['upstreams'], [site['asn']], PeerRelationship.Provider)


def add_origin_site(base, ebgp: Ebgp):
    origin_as = base.createAutonomousSystem(ORIGIN_SITE['asn'])
    origin_as.createNetwork(ORIGIN_SITE['net_name'], ORIGIN_SITE['prefix'])
    origin_as.createHost(ORIGIN_SITE['node_name']).joinNetwork(ORIGIN_SITE['net_name'], address=ORIGIN_SITE['ip'])
    origin_as.createRouter(ORIGIN_SITE['router_name']).joinNetwork(ORIGIN_SITE['net_name']).joinNetwork(f'ix{ORIGIN_SITE["ix"]}')
    ebgp.addPrivatePeerings(ORIGIN_SITE['ix'], ORIGIN_SITE['upstreams'], [ORIGIN_SITE['asn']], PeerRelationship.Provider)


def add_dns_host(base):
    dns_as = base.getAutonomousSystem(150)
    dns_as.createHost(DNS_NODE_NAME).joinNetwork('net0', address=DNS_IP)
    base.setNameServers([DNS_IP])


def create_dns_layer() -> DomainNameService:
    dns = DomainNameService()
    dns.install(DNS_VNODE).addZone(SERVICE_ZONE).setMaster().setInclude(SERVICE_ZONE, DNS_INCLUDE_PATH)
    return dns


def create_cdn_layer() -> CDNService:
    cdn = CDNService()

    cdn.createOrigin(ORIGIN_VNODE).setPort(8080).setServerName(SERVICE_DOMAIN).setIndexContent(
        '<h1>SEED CDN origin</h1>'
    )

    for site in EDGE_SITES:
        cdn.createEdge(site['vnode']).setRegion(site['region']).addOrigin(ORIGIN_VNODE)

    cdn.setDomain(
        SERVICE_DOMAIN,
        dnsVnode=DNS_VNODE,
        edges=[site['vnode'] for site in EDGE_SITES],
        mode='region',
        zone=SERVICE_ZONE,
    )
    cdn.setIncludeContent(SERVICE_DOMAIN, DNS_INCLUDE_PATH)

    for site in EDGE_SITES:
        cdn.mapRegion(SERVICE_DOMAIN, site['region'], [site['vnode']])

    region_members = {}
    for asn, region in CLIENT_REGION_BY_ASN.items():
        region_members.setdefault(region, []).append(asn)

    for region, asns in region_members.items():
        cdn.setRegionMembers(region, asns)

    return cdn


def add_bindings(emu: Emulator):
    emu.addBinding(Binding(DNS_VNODE, filter=Filter(asn=150, nodeName=DNS_NODE_NAME), action=Action.FIRST))
    emu.addBinding(
        Binding(
            ORIGIN_VNODE,
            filter=Filter(asn=ORIGIN_SITE['asn'], nodeName=ORIGIN_SITE['node_name']),
            action=Action.FIRST,
        )
    )

    for site in EDGE_SITES:
        emu.addBinding(
            Binding(site['vnode'], filter=Filter(asn=site['asn'], nodeName=site['node_name']), action=Action.FIRST)
        )


def build_emulator() -> Emulator:
    base_bin = SCRIPT_DIR / 'base_internet.bin'
    mini_internet.run(dumpfile=str(base_bin), hosts_per_as=1)

    emu = Emulator()
    emu.load(str(base_bin))

    base = emu.getLayer('Base')
    ebgp = emu.getLayer('Ebgp')

    add_edge_sites(base, ebgp)
    add_origin_site(base, ebgp)
    add_dns_host(base)

    dns = create_dns_layer()
    cdn = create_cdn_layer()

    emu.addLayer(dns)
    emu.addLayer(cdn)
    add_bindings(emu)

    return emu


def run():
    args = parse_args()
    output_dir = SCRIPT_DIR / 'output'
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    emu = build_emulator()
    emu.render()
    emu.compile(
        Docker(selfManagedNetwork=True, platform=resolve_platform(args.platform)),
        str(output_dir),
        override=True,
    )

    print(f'Generated Docker output in: {OUTPUT_RELATIVE_PATH}')


if __name__ == '__main__':
    run()
