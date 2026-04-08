#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import textwrap

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.layers import Ebgp, PeerRelationship
from examples.internet.B00_mini_internet import mini_internet


SERVICE_DOMAIN = "www.example.com"
SERVICE_ZONE = "example.com"
SERVICE_ZONE_FQDN = "example.com."
OBJECT_PATH = "/large.bin"
OBJECT_SIZE_BYTES = 8 * 1024 * 1024
OUTPUT_RELATIVE_PATH = "nsdi/CDN/amplification_attack/output"

CLIENT_ASNS = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]

DNS_SERVER = {"asn": 150, "node_name": "rangeamp_dns", "ip": "10.150.0.53"}

ATTACK_SITE = {
    "site_id": "nyc",
    "ix": 100,
    "asn": 181,
    "prefix": "10.181.0.0/24",
    "edge_ip": "10.181.0.100",
    "origin_ip": "10.181.0.10",
    "upstreams": [2, 3, 4],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a RangeAmp SBR experiment on top of mini_internet"
    )
    parser.add_argument("platform", nargs="?", default="amd", choices=["amd", "arm"])
    return parser.parse_args()


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


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


def build_bind_patch_script(answer_ip: str, dns_ip: str) -> str:
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
        f'zone "{SERVICE_ZONE}" {{ type master; file "/etc/bind/zones/{SERVICE_ZONE}.db"; }};\n'
        "EOF_LOCAL\n\n"
        f"cat > /etc/bind/zones/{SERVICE_ZONE}.db <<'EOF_ZONE'\n"
        f"{build_dns_zone(answer_ip, dns_ip)}"
        "EOF_ZONE\n\n"
        "chown -R bind:bind /etc/bind/zones\n"
        "service named restart || service named start\n"
    )


def build_origin_server_script(site: dict) -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import json
        import os
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from urllib.parse import urlsplit

        OBJECT_PATH = "{OBJECT_PATH}"
        OBJECT_FILE = "/srv/cdn/large.bin"
        OBJECT_SIZE = {OBJECT_SIZE_BYTES}

        stats = {{
            "requests": 0,
            "bytes_sent": 0,
            "last_path": "",
            "object_size": OBJECT_SIZE,
            "site_id": "{site["site_id"]}",
            "role": "origin",
        }}
        lock = threading.Lock()

        def ensure_object():
            os.makedirs("/srv/cdn", exist_ok=True)
            if os.path.exists(OBJECT_FILE) and os.path.getsize(OBJECT_FILE) == OBJECT_SIZE:
                return
            chunk = b"RANGEAMP" * 8192
            remaining = OBJECT_SIZE
            with open(OBJECT_FILE, "wb") as handle:
                while remaining > 0:
                    data = chunk[: min(len(chunk), remaining)]
                    handle.write(data)
                    remaining -= len(data)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == "/__stats":
                    with lock:
                        payload = json.dumps(stats).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path != OBJECT_PATH:
                    self.send_error(404, "not found")
                    return

                size = os.path.getsize(OBJECT_FILE)
                with lock:
                    stats["requests"] += 1
                    stats["bytes_sent"] += size
                    stats["last_path"] = self.path

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(OBJECT_FILE, "rb") as handle:
                    while True:
                        data = handle.read(64 * 1024)
                        if not data:
                            break
                        self.wfile.write(data)

            def log_message(self, fmt, *args):
                return

        ensure_object()
        ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
        """
    )


def build_edge_server_script(site: dict) -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import hashlib
        import http.client
        import json
        import os
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from urllib.parse import urlsplit

        OBJECT_PATH = "{OBJECT_PATH}"
        ORIGIN_HOST = "{site["origin_ip"]}"
        ORIGIN_PORT = 8080
        CACHE_DIR = "/var/cache/rangeamp"

        stats = {{
            "client_requests": 0,
            "range_requests": 0,
            "client_bytes_sent": 0,
            "origin_fetches": 0,
            "origin_bytes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "site_id": "{site["site_id"]}",
            "role": "edge",
            "attack_model": "Deletion-based SBR",
        }}
        lock = threading.Lock()

        def cache_path_for(key: str) -> str:
            digest = hashlib.sha256(key.encode()).hexdigest()
            return os.path.join(CACHE_DIR, digest + ".bin")

        def read_cached_object(target: str):
            os.makedirs(CACHE_DIR, exist_ok=True)
            path = cache_path_for(target)
            if os.path.exists(path):
                with lock:
                    stats["cache_hits"] += 1
                with open(path, "rb") as handle:
                    return handle.read(), True

            conn = http.client.HTTPConnection(ORIGIN_HOST, ORIGIN_PORT, timeout=30)
            conn.request("GET", target, headers={{"Host": "{SERVICE_DOMAIN}"}})
            response = conn.getresponse()
            body = response.read()
            conn.close()

            if response.status != 200:
                raise RuntimeError(f"origin fetch failed: {{response.status}}")

            with open(path, "wb") as handle:
                handle.write(body)

            with lock:
                stats["cache_misses"] += 1
                stats["origin_fetches"] += 1
                stats["origin_bytes"] += len(body)

            return body, False

        def parse_single_range(value: str, size: int):
            if not value.startswith("bytes=") or "," in value:
                return None
            body = value[len("bytes="):]
            if "-" not in body:
                return None
            start_text, end_text = body.split("-", 1)

            if start_text == "":
                suffix = int(end_text)
                if suffix <= 0:
                    return None
                start = max(size - suffix, 0)
                end = size - 1
                return start, end

            start = int(start_text)
            end = size - 1 if end_text == "" else int(end_text)
            if start < 0 or end < start or start >= size:
                return None
            end = min(end, size - 1)
            return start, end

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == "/__stats":
                    with lock:
                        snapshot = dict(stats)
                    snapshot["amplification"] = (
                        0 if snapshot["client_bytes_sent"] == 0
                        else round(snapshot["origin_bytes"] / snapshot["client_bytes_sent"], 2)
                    )
                    payload = json.dumps(snapshot).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path != OBJECT_PATH:
                    self.send_error(404, "not found")
                    return

                target = self.path
                range_header = self.headers.get("Range")
                with lock:
                    stats["client_requests"] += 1
                    if range_header:
                        stats["range_requests"] += 1

                try:
                    body, cache_hit = read_cached_object(target)
                except Exception as exc:
                    self.send_error(502, f"origin error: {{exc}}")
                    return

                if range_header:
                    byte_range = parse_single_range(range_header, len(body))
                    if byte_range is None:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{{len(body)}}")
                        self.end_headers()
                        return

                    start, end = byte_range
                    payload = body[start : end + 1]
                    with lock:
                        stats["client_bytes_sent"] += len(payload)

                    self.send_response(206)
                    self.send_header("X-RangeAmp-Cache", "HIT" if cache_hit else "MISS")
                    self.send_header("X-RangeAmp-Origin-Bytes", str(len(body)))
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("Content-Range", f"bytes {{start}}-{{end}}/{{len(body)}}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                with lock:
                    stats["client_bytes_sent"] += len(body)

                self.send_response(200)
                self.send_header("X-RangeAmp-Cache", "HIT" if cache_hit else "MISS")
                self.send_header("X-RangeAmp-Origin-Bytes", str(len(body)))
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        os.makedirs(CACHE_DIR, exist_ok=True)
        ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
        """
    )


def install_origin_service(host, site: dict):
    host.addSoftware("python3")
    host.setFile("/root/origin_server.py", build_origin_server_script(site))
    host.appendStartCommand("chmod +x /root/origin_server.py")
    host.appendStartCommand("nohup /root/origin_server.py >/var/log/origin_server.log 2>&1 &")


def install_edge_service(host, site: dict):
    host.addSoftware("python3")
    host.setFile("/root/edge_server.py", build_edge_server_script(site))
    host.appendStartCommand("chmod +x /root/edge_server.py")
    host.appendStartCommand("nohup /root/edge_server.py >/var/log/edge_server.log 2>&1 &")


def install_dns_service(host, answer_ip: str, dns_ip: str):
    host.addSoftware("bind9")
    host.setFile("/root/patch_bind_rangeamp.sh", build_bind_patch_script(answer_ip, dns_ip))
    host.appendStartCommand("chmod +x /root/patch_bind_rangeamp.sh")
    host.appendStartCommand("/root/patch_bind_rangeamp.sh")


def add_attack_site(base, ebgp: Ebgp):
    site = ATTACK_SITE
    site_as = base.createAutonomousSystem(site["asn"])
    net_name = f'{site["site_id"]}_net'
    edge_name = f'{site["site_id"]}_edge'
    origin_name = f'{site["site_id"]}_origin'
    router_name = f'{site["site_id"]}_br'

    site_as.createNetwork(net_name, site["prefix"])
    site_as.createHost(edge_name).joinNetwork(net_name, address=site["edge_ip"])
    site_as.createHost(origin_name).joinNetwork(net_name, address=site["origin_ip"])
    site_as.createRouter(router_name).joinNetwork(net_name).joinNetwork(f'ix{site["ix"]}')

    install_edge_service(site_as.getHost(edge_name), site)
    install_origin_service(site_as.getHost(origin_name), site)
    ebgp.addPrivatePeerings(site["ix"], site["upstreams"], [site["asn"]], PeerRelationship.Provider)


def add_dns(base):
    dns_as = base.getAutonomousSystem(DNS_SERVER["asn"])
    dns_as.createHost(DNS_SERVER["node_name"]).joinNetwork("net0", address=DNS_SERVER["ip"])
    install_dns_service(dns_as.getHost(DNS_SERVER["node_name"]), ATTACK_SITE["edge_ip"], DNS_SERVER["ip"])

    for asn in CLIENT_ASNS:
        base.getAutonomousSystem(asn).setNameServers([DNS_SERVER["ip"]])


def build_emulator() -> Emulator:
    base_bin = SCRIPT_DIR / "rangeamp_sbr_base_internet.bin"
    mini_internet.run(dumpfile=str(base_bin), hosts_per_as=1)

    emu = Emulator()
    emu.load(str(base_bin))

    base = emu.getLayer("Base")
    ebgp = emu.getLayer("Ebgp")

    add_attack_site(base, ebgp)
    add_dns(base)
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
    print("This topology reproduces a deletion-based RangeAmp SBR attack.")
    print("Docker was not started automatically.")


if __name__ == "__main__":
    run()
