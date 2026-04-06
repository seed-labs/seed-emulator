#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import textwrap

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Ebgp, PeerRelationship
from examples.internet.B00_mini_internet import mini_internet


SERVICE_DOMAIN = "www.example.com"
SERVICE_ZONE = "example.com"
SERVICE_ZONE_FQDN = "example.com."
OUTPUT_RELATIVE_PATH = "nsdi/CDN/output"

CLIENT_REGION_BY_ASN = {
    150: "east",
    151: "east",
    152: "west",
    153: "west",
    154: "central",
    160: "east",
    161: "east",
    162: "east",
    163: "east",
    164: "east",
    170: "central",
    171: "central",
}

DNS_SERVERS = [
    {"id": "dns_east", "asn": 150, "node_name": "cdn_dns_east", "ip": "10.150.0.53"},
    {"id": "dns_west", "asn": 152, "node_name": "cdn_dns_west", "ip": "10.152.0.53"},
    {"id": "dns_central", "asn": 154, "node_name": "cdn_dns_central", "ip": "10.154.0.53"},
]

DNS_ORDER_BY_REGION = {
    "east": ["10.150.0.53", "10.154.0.53", "10.152.0.53"],
    "west": ["10.152.0.53", "10.154.0.53", "10.150.0.53"],
    "central": ["10.154.0.53", "10.150.0.53", "10.152.0.53"],
}

CDN_SITES = [
    {
        "site_id": "nyc",
        "region": "east",
        "ix": 100,
        "asn": 181,
        "prefix": "10.181.0.0/24",
        "edge_ip": "10.181.0.100",
        "upstreams": [2, 3, 4],
    },
    {
        "site_id": "sjc",
        "region": "west",
        "ix": 101,
        "asn": 182,
        "prefix": "10.182.0.0/24",
        "edge_ip": "10.182.0.100",
        "upstreams": [2, 12],
    },
    {
        "site_id": "chi",
        "region": "central",
        "ix": 102,
        "asn": 183,
        "prefix": "10.183.0.0/24",
        "edge_ip": "10.183.0.100",
        "upstreams": [2, 4, 11],
    },
]

EDGE_IP_BY_REGION = {site["region"]: site["edge_ip"] for site in CDN_SITES}

ORIGIN_SITE = {
    "site_id": "origin",
    "asn": 184,
    "ix": 102,
    "prefix": "10.184.0.0/24",
    "origin_ip": "10.184.0.10",
    "upstreams": [2, 4, 11],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a simple CDN example on top of mini_internet")
    parser.add_argument("platform", nargs="?", default="amd", choices=["amd", "arm"])
    return parser.parse_args()


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_origin_nginx_conf() -> str:
    return textwrap.dedent(
        f"""\
        server {{
            listen 8080 default_server;
            server_name _;

            location / {{
                default_type application/json;
                return 200 '{{"site_id":"$http_x_cdn_site","region":"$http_x_cdn_region","role":"origin","origin_site":"{ORIGIN_SITE["site_id"]}","origin_asn":{ORIGIN_SITE["asn"]},"edge_ip":"$http_x_cdn_edge_ip","origin_ip":"{ORIGIN_SITE["origin_ip"]}","service_domain":"{SERVICE_DOMAIN}"}}';
            }}
        }}
        """
    )


def build_edge_nginx_conf(site: dict) -> str:
    upstream_name = f"{site['site_id']}_origin"
    return textwrap.dedent(
        f"""\
        upstream {upstream_name} {{
            server {ORIGIN_SITE["origin_ip"]}:8080;
            keepalive 16;
        }}

        server {{
            listen 8080 default_server;
            server_name {SERVICE_DOMAIN} _;

            location / {{
                proxy_http_version 1.1;
                proxy_set_header Connection "";
                proxy_set_header Host $host;
                proxy_set_header X-CDN-Site {site["site_id"]};
                proxy_set_header X-CDN-Region {site["region"]};
                proxy_set_header X-CDN-Edge-IP {site["edge_ip"]};
                proxy_pass http://{upstream_name};
            }}
        }}
        """
    )


def install_origin_service(host):
    host.addSoftware("nginx-light")
    host.setFile("/etc/nginx/sites-available/default", build_origin_nginx_conf())
    host.appendStartCommand("service nginx start")


def install_edge_service(host, site: dict):
    host.addSoftware("nginx-light")
    host.setFile("/etc/nginx/sites-available/default", build_edge_nginx_conf(site))
    host.appendStartCommand("service nginx start")


def build_dns_zone(answer_ip: str, dns_ip: str) -> str:
    return textwrap.dedent(
        f"""\
        $TTL 60
        $ORIGIN {SERVICE_ZONE_FQDN}
        @ IN SOA ns1.{SERVICE_ZONE_FQDN} admin.{SERVICE_ZONE_FQDN} 1 300 300 300 60
        @ IN NS ns1.{SERVICE_ZONE_FQDN}
        @ IN A {answer_ip}
        ns1 IN A {dns_ip}
        www IN A {answer_ip}
        """
    )


def build_bind_patch_script(dns_ip: str) -> str:
    subnets_by_region = {"east": [], "west": [], "central": []}
    for asn, region in CLIENT_REGION_BY_ASN.items():
        subnets_by_region[region].append(f"10.{asn}.0.0/24;")

    named_conf_local = textwrap.dedent(
        f"""\
        acl east_clients {{ {' '.join(subnets_by_region['east'])} }};
        acl west_clients {{ {' '.join(subnets_by_region['west'])} }};
        acl central_clients {{ {' '.join(subnets_by_region['central'])} }};

        view "east" {{
            match-clients {{ east_clients; }};
            recursion no;
            zone "{SERVICE_ZONE}" {{ type master; file "/etc/bind/zones/{SERVICE_ZONE}.east"; }};
        }};

        view "west" {{
            match-clients {{ west_clients; }};
            recursion no;
            zone "{SERVICE_ZONE}" {{ type master; file "/etc/bind/zones/{SERVICE_ZONE}.west"; }};
        }};

        view "central" {{
            match-clients {{ central_clients; }};
            recursion no;
            zone "{SERVICE_ZONE}" {{ type master; file "/etc/bind/zones/{SERVICE_ZONE}.central"; }};
        }};

        view "default" {{
            match-clients {{ any; }};
            recursion no;
            zone "{SERVICE_ZONE}" {{ type master; file "/etc/bind/zones/{SERVICE_ZONE}.default"; }};
        }};
        """
    )

    return (
        "#!/bin/sh\n"
        "set -eu\n\n"
        "mkdir -p /etc/bind/zones\n\n"
        "cat > /etc/bind/named.conf <<'EOF_NAMED'\n"
        'include "/etc/bind/named.conf.options";\n'
        'include "/etc/bind/named.conf.local";\n'
        "EOF_NAMED\n\n"
        "cat > /etc/bind/named.conf.options <<'EOF_OPTIONS'\n"
        "options {\n"
        '    directory "/var/cache/bind";\n'
        "    recursion no;\n"
        "    dnssec-validation no;\n"
        "    empty-zones-enable no;\n"
        "    allow-query { any; };\n"
        "    listen-on { any; };\n"
        "    listen-on-v6 { any; };\n"
        "};\n"
        "EOF_OPTIONS\n\n"
        "cat > /etc/bind/named.conf.local <<'EOF_LOCAL'\n"
        f"{named_conf_local}"
        "EOF_LOCAL\n\n"
        f"cat > /etc/bind/zones/{SERVICE_ZONE}.east <<'EOF_EAST'\n"
        f"{build_dns_zone(EDGE_IP_BY_REGION['east'], dns_ip)}"
        "EOF_EAST\n\n"
        f"cat > /etc/bind/zones/{SERVICE_ZONE}.west <<'EOF_WEST'\n"
        f"{build_dns_zone(EDGE_IP_BY_REGION['west'], dns_ip)}"
        "EOF_WEST\n\n"
        f"cat > /etc/bind/zones/{SERVICE_ZONE}.central <<'EOF_CENTRAL'\n"
        f"{build_dns_zone(EDGE_IP_BY_REGION['central'], dns_ip)}"
        "EOF_CENTRAL\n\n"
        f"cat > /etc/bind/zones/{SERVICE_ZONE}.default <<'EOF_DEFAULT'\n"
        f"{build_dns_zone(EDGE_IP_BY_REGION['central'], dns_ip)}"
        "EOF_DEFAULT\n\n"
        "chown -R bind:bind /etc/bind/zones\n"
        "service named restart || service named start\n"
    )


def install_dns_service(host, dns_ip: str):
    host.addSoftware("bind9")
    host.setFile("/root/patch_bind_cdn.sh", build_bind_patch_script(dns_ip))
    host.appendStartCommand("chmod +x /root/patch_bind_cdn.sh")
    host.appendStartCommand("/root/patch_bind_cdn.sh")


def add_cdn_sites(base, ebgp: Ebgp):
    for site in CDN_SITES:
        site_as = base.createAutonomousSystem(site["asn"])
        net_name = f'{site["site_id"]}_net'
        edge_name = f'{site["site_id"]}_edge'
        router_name = f'{site["site_id"]}_br'

        site_as.createNetwork(net_name, site["prefix"])
        site_as.createHost(edge_name).joinNetwork(net_name, address=site["edge_ip"])
        site_as.createRouter(router_name).joinNetwork(net_name).joinNetwork(f'ix{site["ix"]}')

        install_edge_service(site_as.getHost(edge_name), site)
        ebgp.addPrivatePeerings(site["ix"], site["upstreams"], [site["asn"]], PeerRelationship.Provider)


def add_origin_site(base, ebgp: Ebgp):
    site_as = base.createAutonomousSystem(ORIGIN_SITE["asn"])
    net_name = "origin_net"
    origin_name = "global_origin"
    router_name = "origin_br"

    site_as.createNetwork(net_name, ORIGIN_SITE["prefix"])
    site_as.createHost(origin_name).joinNetwork(net_name, address=ORIGIN_SITE["origin_ip"])
    site_as.createRouter(router_name).joinNetwork(net_name).joinNetwork(f'ix{ORIGIN_SITE["ix"]}')

    install_origin_service(site_as.getHost(origin_name))
    ebgp.addPrivatePeerings(ORIGIN_SITE["ix"], ORIGIN_SITE["upstreams"], [ORIGIN_SITE["asn"]], PeerRelationship.Provider)


def add_dns_servers(base):
    for dns in DNS_SERVERS:
        dns_as = base.getAutonomousSystem(dns["asn"])
        dns_as.createHost(dns["node_name"]).joinNetwork("net0", address=dns["ip"])
        install_dns_service(dns_as.getHost(dns["node_name"]), dns["ip"])

    for asn, region in CLIENT_REGION_BY_ASN.items():
        base.getAutonomousSystem(asn).setNameServers(DNS_ORDER_BY_REGION[region])


def build_emulator() -> Emulator:
    base_bin = SCRIPT_DIR / "base_internet.bin"
    mini_internet.run(dumpfile=str(base_bin), hosts_per_as=1)

    emu = Emulator()
    emu.load(str(base_bin))

    base = emu.getLayer("Base")
    ebgp = emu.getLayer("Ebgp")

    add_cdn_sites(base, ebgp)
    add_origin_site(base, ebgp)
    add_dns_servers(base)
    return emu


def run():
    args = parse_args()
    output_dir = SCRIPT_DIR / "output"
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    emu = build_emulator()
    emu.render()
    emu.compile(
        Docker(selfManagedNetwork=True, platform=resolve_platform(args.platform)),
        str(output_dir),
        override=True,
    )

    print(f"Generated Docker output in: {OUTPUT_RELATIVE_PATH}")
    print("Docker was not started automatically.")


if __name__ == "__main__":
    run()
