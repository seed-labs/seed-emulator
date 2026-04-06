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


ZONE_NAME = "example.com"
ZONE_FQDN = "example.com."
OUTPUT_RELATIVE_PATH = "nsdi/CDN/c2dn/output"
SERVICE_PORT = 8080
BASE_OBJECT_SIZE = 64 * 1024

CLIENT_ASNS = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]

DNS_SERVER = {"asn": 150, "node_name": "c2dn_dns", "ip": "10.150.0.53"}

EDGE_CLUSTER = {
    "asn": 191,
    "ix": 100,
    "prefix": "10.191.0.0/24",
    "frontend_ip": "10.191.0.10",
    "cache_ips": ["10.191.0.11", "10.191.0.12", "10.191.0.13", "10.191.0.14"],
    "upstreams": [2, 3, 4],
}

ORIGIN_SITE = {
    "asn": 192,
    "ix": 102,
    "prefix": "10.192.0.0/24",
    "origin_ip": "10.192.0.10",
    "upstreams": [2, 4, 11],
}

BASELINE_HOST = "baseline.example.com"
C2DN_HOST = "c2dn.example.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an upgraded C2DN experiment")
    parser.add_argument("platform", nargs="?", default="amd", choices=["amd", "arm"])
    return parser.parse_args()


def resolve_platform(name: str) -> Platform:
    return Platform.AMD64 if name == "amd" else Platform.ARM64


def build_dns_zone(answer_ip: str, dns_ip: str) -> str:
    return textwrap.dedent(
        f"""\
        $TTL 60
        $ORIGIN {ZONE_FQDN}
        @ IN SOA ns1.{ZONE_FQDN} admin.{ZONE_FQDN} 1 300 300 300 60
        @ IN NS ns1.{ZONE_FQDN}
        ns1 IN A {dns_ip}
        baseline IN A {answer_ip}
        c2dn IN A {answer_ip}
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
        f'zone "{ZONE_NAME}" {{ type master; file "/etc/bind/zones/{ZONE_NAME}.db"; }};\n'
        "EOF_LOCAL\n\n"
        f"cat > /etc/bind/zones/{ZONE_NAME}.db <<'EOF_ZONE'\n"
        f"{build_dns_zone(answer_ip, dns_ip)}"
        "EOF_ZONE\n\n"
        "chown -R bind:bind /etc/bind/zones\n"
        "service named restart || service named start\n"
    )


def build_cache_server_script() -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import json
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from urllib.parse import parse_qs, urlsplit

        store = {{}}
        state = {{"up": True, "reads": 0, "writes": 0, "write_bytes": 0}}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)

                if parsed.path == "/__stats":
                    payload = json.dumps({{
                        "up": state["up"],
                        "reads": state["reads"],
                        "writes": state["writes"],
                        "write_bytes": state["write_bytes"],
                        "keys": len(store),
                    }}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path == "/__set":
                    state["up"] = query.get("up", ["1"])[0] != "0"
                    payload = json.dumps({{"up": state["up"]}}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path == "/__reset":
                    store.clear()
                    state["reads"] = 0
                    state["writes"] = 0
                    state["write_bytes"] = 0
                    state["up"] = True
                    payload = b'{{"reset": true}}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path != "/chunk":
                    self.send_error(404, "not found")
                    return

                if not state["up"]:
                    self.send_error(503, "cache node unavailable")
                    return

                key = query.get("key", [""])[0]
                part = query.get("part", [""])[0]
                storage_key = f"{{key}}|{{part}}"
                if storage_key not in store:
                    self.send_error(404, "cache miss")
                    return

                body = store[storage_key]
                state["reads"] += 1
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_PUT(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)

                if parsed.path != "/chunk":
                    self.send_error(404, "not found")
                    return

                if not state["up"]:
                    self.send_error(503, "cache node unavailable")
                    return

                key = query.get("key", [""])[0]
                part = query.get("part", [""])[0]
                storage_key = f"{{key}}|{{part}}"
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                store[storage_key] = body
                state["writes"] += 1
                state["write_bytes"] += len(body)
                self.send_response(200)
                self.end_headers()

            def log_message(self, fmt, *args):
                return

        ThreadingHTTPServer(("0.0.0.0", {SERVICE_PORT}), Handler).serve_forever()
        """
    )


def build_origin_server_script() -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import json
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from urllib.parse import urlsplit

        BASE_OBJECT_SIZE = {BASE_OBJECT_SIZE}
        stats = {{"requests": 0, "bytes_sent": 0}}

        def object_index(key: str) -> int:
            digits = "".join(ch for ch in key if ch.isdigit())
            return int(digits) if digits else 0

        def object_size(key: str) -> int:
            return BASE_OBJECT_SIZE * (1 + (object_index(key) % 4))

        def build_object(key: str) -> bytes:
            size = object_size(key)
            seed = f"OBJECT:{{key}}|".encode()
            repeats = (size // len(seed)) + 1
            return (seed * repeats)[:size]

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == "/__stats":
                    payload = json.dumps(stats).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path == "/__reset":
                    stats["requests"] = 0
                    stats["bytes_sent"] = 0
                    payload = b'{{"reset": true}}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if not parsed.path.startswith("/object/"):
                    self.send_error(404, "not found")
                    return

                key = parsed.path.split("/object/", 1)[1]
                body = build_object(key)
                stats["requests"] += 1
                stats["bytes_sent"] += len(body)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Object-Bytes", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        ThreadingHTTPServer(("0.0.0.0", {SERVICE_PORT}), Handler).serve_forever()
        """
    )


def build_frontend_script() -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import http.client
        import json
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from urllib.parse import parse_qs, urlsplit

        SERVICE_PORT = {SERVICE_PORT}
        BASELINE_HOST = "{BASELINE_HOST}"
        C2DN_HOST = "{C2DN_HOST}"
        ORIGIN_IP = "{ORIGIN_SITE["origin_ip"]}"
        CACHE_IPS = {EDGE_CLUSTER["cache_ips"]!r}

        def new_mode_stats():
            return {{
                "requests": 0,
                "hits": 0,
                "misses": 0,
                "recoveries": 0,
                "origin_fetches": 0,
                "origin_bytes": 0,
                "client_bytes": 0,
                "write_ops_by_node": [0, 0, 0, 0],
                "write_bytes_by_node": [0, 0, 0, 0],
            }}

        stats = {{"baseline": new_mode_stats(), "c2dn": new_mode_stats()}}

        def object_index(key: str) -> int:
            digits = "".join(ch for ch in key if ch.isdigit())
            return int(digits) if digits else 0

        def placement_seed(key: str) -> int:
            # Use a deterministic string hash that is independent from the
            # object-size class. This avoids the artificial coupling where
            # node placement becomes a simple permutation of index % 4.
            value = 2166136261
            for byte in key.encode():
                value ^= byte
                value = (value * 16777619) & 0xFFFFFFFF
            return value

        def zipf_keys(num_objects: int):
            weighted = []
            for i in range(num_objects):
                weight = max(1, num_objects // (i + 1))
                weighted.extend([f"video-{{i}}"] * weight)
            return weighted

        def primary_node(key: str) -> int:
            return placement_seed(key) % len(CACHE_IPS)

        def baseline_nodes(key: str):
            first = primary_node(key)
            return [first]

        def c2dn_nodes(key: str):
            base = primary_node(key)
            return [(base + offset) % len(CACHE_IPS) for offset in range(4)]

        def object_size(key: str) -> int:
            return 65536 * (1 + (object_index(key) % 4))

        def http_get(ip: str, path: str, timeout: int = 4):
            conn = http.client.HTTPConnection(ip, SERVICE_PORT, timeout=timeout)
            conn.request("GET", path)
            resp = conn.getresponse()
            body = resp.read()
            headers = dict(resp.getheaders())
            status = resp.status
            conn.close()
            return status, body, headers

        def http_put(ip: str, path: str, body: bytes, timeout: int = 4):
            conn = http.client.HTTPConnection(ip, SERVICE_PORT, timeout=timeout)
            conn.request("PUT", path, body=body, headers={{"Content-Length": str(len(body))}})
            resp = conn.getresponse()
            resp.read()
            status = resp.status
            conn.close()
            return status

        def reset_backend_state():
            for ip in CACHE_IPS:
                try:
                    http_get(ip, "/__reset")
                except Exception:
                    pass
            try:
                http_get(ORIGIN_IP, "/__reset")
            except Exception:
                pass

        def set_cache_up(node: int, up: bool):
            value = "1" if up else "0"
            status, body, _ = http_get(CACHE_IPS[node], f"/__set?up={{value}}")
            if status != 200:
                raise RuntimeError("cache state update failed")
            return json.loads(body.decode())

        def reset_frontend_state():
            stats["baseline"] = new_mode_stats()
            stats["c2dn"] = new_mode_stats()

        def fetch_from_origin(key: str, mode_name: str) -> bytes:
            status, body, headers = http_get(ORIGIN_IP, f"/object/{{key}}", timeout=5)
            if status != 200:
                raise RuntimeError("origin fetch failed")
            stats[mode_name]["origin_fetches"] += 1
            stats[mode_name]["origin_bytes"] += int(headers.get("X-Object-Bytes", str(len(body))))
            return body

        def xor_bytes(a: bytes, b: bytes) -> bytes:
            return bytes(x ^ y for x, y in zip(a, b))

        def encode_c2dn(body: bytes):
            half = len(body) // 2
            left = body[:half]
            right = body[half:]
            parity = xor_bytes(left, right)
            # store two identical parity chunks to keep the layout simple while
            # preserving single-node-failure recoverability.
            return {{"d0": left, "d1": right, "p0": parity, "p1": parity}}

        def decode_c2dn(chunks):
            if "d0" in chunks and "d1" in chunks:
                return chunks["d0"] + chunks["d1"]
            if "d0" in chunks and ("p0" in chunks or "p1" in chunks):
                parity = chunks.get("p0", chunks.get("p1"))
                return chunks["d0"] + xor_bytes(chunks["d0"], parity)
            if "d1" in chunks and ("p0" in chunks or "p1" in chunks):
                parity = chunks.get("p0", chunks.get("p1"))
                return xor_bytes(chunks["d1"], parity) + chunks["d1"]
            raise RuntimeError("not enough chunks to reconstruct")

        def record_write(mode_name: str, node_idx: int, body: bytes):
            stats[mode_name]["write_ops_by_node"][node_idx] += 1
            stats[mode_name]["write_bytes_by_node"][node_idx] += len(body)

        def handle_baseline(key: str) -> bytes:
            mode_name = "baseline"
            stats[mode_name]["requests"] += 1
            node_idx = baseline_nodes(key)[0]
            try:
                status, body, _ = http_get(CACHE_IPS[node_idx], f"/chunk?key={{key}}&part=full")
            except Exception:
                status, body = 503, b""
            if status == 200:
                stats[mode_name]["hits"] += 1
                stats[mode_name]["client_bytes"] += len(body)
                return body

            stats[mode_name]["misses"] += 1
            body = fetch_from_origin(key, mode_name)
            try:
                if http_put(CACHE_IPS[node_idx], f"/chunk?key={{key}}&part=full", body) == 200:
                    record_write(mode_name, node_idx, body)
            except Exception:
                pass
            stats[mode_name]["client_bytes"] += len(body)
            return body

        def handle_c2dn(key: str) -> bytes:
            mode_name = "c2dn"
            stats[mode_name]["requests"] += 1
            chunks = {{}}
            node_order = c2dn_nodes(key)
            part_order = ["d0", "d1", "p0", "p1"]

            for node_idx, part_name in zip(node_order, part_order):
                try:
                    status, body, _ = http_get(CACHE_IPS[node_idx], f"/chunk?key={{key}}&part={{part_name}}")
                except Exception:
                    status, body = 503, b""
                if status == 200:
                    chunks[part_name] = body

            if len(chunks) >= 2 and ("d0" in chunks or "d1" in chunks):
                stats[mode_name]["hits"] += 1
                if len(chunks) < 4:
                    stats[mode_name]["recoveries"] += 1
                body = decode_c2dn(chunks)
                stats[mode_name]["client_bytes"] += len(body)
                return body

            stats[mode_name]["misses"] += 1
            body = fetch_from_origin(key, mode_name)
            encoded = encode_c2dn(body)
            for node_idx, part_name in zip(node_order, part_order):
                chunk = encoded[part_name]
                try:
                    if http_put(CACHE_IPS[node_idx], f"/chunk?key={{key}}&part={{part_name}}", chunk) == 200:
                        record_write(mode_name, node_idx, chunk)
                except Exception:
                    pass
            stats[mode_name]["client_bytes"] += len(body)
            return body

        def run_workload(mode_name: str, num_objects: int, num_requests: int, failure_node: int, failure_at: int):
            if mode_name not in stats:
                raise RuntimeError("invalid mode")

            def snapshot_mode(mode):
                return {{
                    "requests": mode["requests"],
                    "hits": mode["hits"],
                    "misses": mode["misses"],
                    "recoveries": mode["recoveries"],
                    "origin_fetches": mode["origin_fetches"],
                    "origin_bytes": mode["origin_bytes"],
                    "client_bytes": mode["client_bytes"],
                }}

            def delta_mode(after, before):
                return {{
                    "requests": after["requests"] - before["requests"],
                    "hits": after["hits"] - before["hits"],
                    "misses": after["misses"] - before["misses"],
                    "recoveries": after["recoveries"] - before["recoveries"],
                    "origin_fetches": after["origin_fetches"] - before["origin_fetches"],
                    "origin_bytes": after["origin_bytes"] - before["origin_bytes"],
                    "client_bytes": after["client_bytes"] - before["client_bytes"],
                }}

            def summarize_phase(phase):
                requests = phase["requests"]
                client_bytes = phase["client_bytes"]
                return {{
                    "requests": requests,
                    "hits": phase["hits"],
                    "misses": phase["misses"],
                    "recoveries": phase["recoveries"],
                    "origin_fetches": phase["origin_fetches"],
                    "origin_bytes": phase["origin_bytes"],
                    "client_bytes": client_bytes,
                    "request_miss_ratio": round(0 if requests == 0 else phase["misses"] / requests, 4),
                    "byte_miss_ratio": round(0 if client_bytes == 0 else phase["origin_bytes"] / client_bytes, 4),
                }}

            reset_backend_state()
            reset_frontend_state()
            for idx in range(len(CACHE_IPS)):
                set_cache_up(idx, True)

            keys = zipf_keys(num_objects)
            failure_snapshot = None
            for req_idx in range(num_requests):
                if failure_at >= 0 and req_idx == failure_at:
                    failure_snapshot = snapshot_mode(stats[mode_name])
                    set_cache_up(failure_node, False)

                key = keys[req_idx % len(keys)]
                if mode_name == "baseline":
                    handle_baseline(key)
                else:
                    handle_c2dn(key)

            mode = stats[mode_name]
            initial_snapshot = {{
                "requests": 0,
                "hits": 0,
                "misses": 0,
                "recoveries": 0,
                "origin_fetches": 0,
                "origin_bytes": 0,
                "client_bytes": 0,
            }}
            if failure_snapshot is None:
                failure_snapshot = snapshot_mode(mode)
            pre_failure = summarize_phase(delta_mode(failure_snapshot, initial_snapshot))
            post_failure = summarize_phase(delta_mode(mode, failure_snapshot))
            request_miss_ratio = 0 if mode["requests"] == 0 else mode["misses"] / mode["requests"]
            byte_miss_ratio = 0 if mode["client_bytes"] == 0 else mode["origin_bytes"] / mode["client_bytes"]
            write_values = mode["write_bytes_by_node"]
            write_skew = 0 if max(write_values) == 0 else max(write_values) - min(write_values)

            origin_status, origin_body, _ = http_get(ORIGIN_IP, "/__stats")
            origin_stats = json.loads(origin_body.decode()) if origin_status == 200 else {{}}
            cache_stats = []
            for ip in CACHE_IPS:
                status, body, _ = http_get(ip, "/__stats")
                cache_stats.append(json.loads(body.decode()) if status == 200 else {{"up": False}})

            return {{
                "mode": mode_name,
                "num_objects": num_objects,
                "num_requests": num_requests,
                "failure_node": failure_node,
                "failure_at": failure_at,
                "request_miss_ratio": round(request_miss_ratio, 4),
                "byte_miss_ratio": round(byte_miss_ratio, 4),
                "origin_fetches": mode["origin_fetches"],
                "origin_bytes": mode["origin_bytes"],
                "recoveries": mode["recoveries"],
                "write_bytes_by_node": mode["write_bytes_by_node"],
                "write_skew_bytes": write_skew,
                "pre_failure": pre_failure,
                "post_failure": post_failure,
                "frontend_stats": mode,
                "origin_stats": origin_stats,
                "cache_stats": cache_stats,
            }}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                host = self.headers.get("Host", "").split(":", 1)[0]

                if parsed.path == "/__stats":
                    payload = json.dumps(stats).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path == "/__reset":
                    reset_backend_state()
                    reset_frontend_state()
                    payload = b'{{"reset": true}}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path == "/__set_cache":
                    node = int(query.get("node", ["0"])[0])
                    up = query.get("up", ["1"])[0] != "0"
                    payload = json.dumps(set_cache_up(node, up)).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if parsed.path == "/__run_workload":
                    mode_name = query.get("mode", ["baseline"])[0]
                    num_objects = int(query.get("objects", ["100"])[0])
                    num_requests = int(query.get("requests", ["1000"])[0])
                    failure_node = int(query.get("failure_node", ["0"])[0])
                    failure_at = int(query.get("failure_at", ["500"])[0])
                    payload = json.dumps(
                        run_workload(mode_name, num_objects, num_requests, failure_node, failure_at)
                    ).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if not parsed.path.startswith("/object/"):
                    self.send_error(404, "not found")
                    return

                key = parsed.path.split("/object/", 1)[1]
                if host == BASELINE_HOST:
                    body = handle_baseline(key)
                    mode_name = "baseline"
                elif host == C2DN_HOST:
                    body = handle_c2dn(key)
                    mode_name = "c2dn"
                else:
                    self.send_error(400, "unknown host")
                    return

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Mode", mode_name)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        ThreadingHTTPServer(("0.0.0.0", SERVICE_PORT), Handler).serve_forever()
        """
    )


def install_python_service(host, script_path: str, script_content: str, log_path: str):
    host.addSoftware("python3")
    host.setFile(script_path, script_content)
    host.appendStartCommand(f"chmod +x {script_path}")
    host.appendStartCommand(f"nohup {script_path} >{log_path} 2>&1 &")


def install_cache_service(host):
    install_python_service(host, "/root/cache_node.py", build_cache_server_script(), "/var/log/cache_node.log")


def install_origin_service(host):
    install_python_service(host, "/root/origin_service.py", build_origin_server_script(), "/var/log/origin_service.log")


def install_frontend_service(host):
    install_python_service(host, "/root/frontend_service.py", build_frontend_script(), "/var/log/frontend_service.log")


def install_dns_service(host, answer_ip: str, dns_ip: str):
    host.addSoftware("bind9")
    host.setFile("/root/patch_bind_c2dn.sh", build_bind_patch_script(answer_ip, dns_ip))
    host.appendStartCommand("chmod +x /root/patch_bind_c2dn.sh")
    host.appendStartCommand("/root/patch_bind_c2dn.sh")


def add_edge_cluster(base, ebgp: Ebgp):
    cluster_as = base.createAutonomousSystem(EDGE_CLUSTER["asn"])
    cluster_as.createNetwork("cluster_net", EDGE_CLUSTER["prefix"])
    cluster_as.createHost("frontend").joinNetwork("cluster_net", address=EDGE_CLUSTER["frontend_ip"])
    for idx, ip in enumerate(EDGE_CLUSTER["cache_ips"]):
        cluster_as.createHost(f"cache{idx}").joinNetwork("cluster_net", address=ip)
    cluster_as.createRouter("cluster_br").joinNetwork("cluster_net").joinNetwork(f'ix{EDGE_CLUSTER["ix"]}')

    install_frontend_service(cluster_as.getHost("frontend"))
    for idx in range(len(EDGE_CLUSTER["cache_ips"])):
        install_cache_service(cluster_as.getHost(f"cache{idx}"))

    ebgp.addPrivatePeerings(
        EDGE_CLUSTER["ix"], EDGE_CLUSTER["upstreams"], [EDGE_CLUSTER["asn"]], PeerRelationship.Provider
    )


def add_origin_site(base, ebgp: Ebgp):
    site_as = base.createAutonomousSystem(ORIGIN_SITE["asn"])
    site_as.createNetwork("origin_net", ORIGIN_SITE["prefix"])
    site_as.createHost("origin").joinNetwork("origin_net", address=ORIGIN_SITE["origin_ip"])
    site_as.createRouter("origin_br").joinNetwork("origin_net").joinNetwork(f'ix{ORIGIN_SITE["ix"]}')
    install_origin_service(site_as.getHost("origin"))
    ebgp.addPrivatePeerings(
        ORIGIN_SITE["ix"], ORIGIN_SITE["upstreams"], [ORIGIN_SITE["asn"]], PeerRelationship.Provider
    )


def add_dns(base):
    dns_as = base.getAutonomousSystem(DNS_SERVER["asn"])
    dns_as.createHost(DNS_SERVER["node_name"]).joinNetwork("net0", address=DNS_SERVER["ip"])
    install_dns_service(dns_as.getHost(DNS_SERVER["node_name"]), EDGE_CLUSTER["frontend_ip"], DNS_SERVER["ip"])

    for asn in CLIENT_ASNS:
        base.getAutonomousSystem(asn).setNameServers([DNS_SERVER["ip"]])


def build_emulator() -> Emulator:
    base_bin = SCRIPT_DIR / "c2dn_base_internet.bin"
    mini_internet.run(dumpfile=str(base_bin), hosts_per_as=1)

    emu = Emulator()
    emu.load(str(base_bin))

    base = emu.getLayer("Base")
    ebgp = emu.getLayer("Ebgp")

    add_edge_cluster(base, ebgp)
    add_origin_site(base, ebgp)
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
    print("This topology reproduces an upgraded C2DN-style experiment.")
    print("Docker was not started automatically.")


if __name__ == "__main__":
    run()
