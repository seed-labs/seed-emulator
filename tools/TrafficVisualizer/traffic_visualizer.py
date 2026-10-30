#!/usr/bin/env python3
"""Reusable tcpdump packet counter with a small HTTP dashboard."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Any
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
IP_TOTAL_LENGTH = re.compile(r"\bIP\s+\(.*?\blength\s+(\d+)\)")


def parse_ip_total_length(line: str) -> int | None:
    """Return tcpdump's decoded IPv4 Total Length value."""
    match = IP_TOTAL_LENGTH.search(line)
    return int(match.group(1)) if match is not None else None


class PacketCounter:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.total = 0
        self.last_second = 0
        self.current_second = 0
        self.total_ip_bytes = 0
        self.ip_bytes_last_second = 0
        self.current_second_ip_bytes = 0
        self.status = "starting"
        self.error = ""

    def increment(self, ip_bytes: int) -> None:
        with self.lock:
            self.total += 1
            self.current_second += 1
            self.total_ip_bytes += ip_bytes
            self.current_second_ip_bytes += ip_bytes

    def finish_second(self) -> None:
        with self.lock:
            self.last_second = self.current_second
            self.ip_bytes_last_second = self.current_second_ip_bytes
            self.current_second = 0
            self.current_second_ip_bytes = 0

    def reset(self) -> None:
        with self.lock:
            self.total = 0
            self.last_second = 0
            self.current_second = 0
            self.total_ip_bytes = 0
            self.ip_bytes_last_second = 0
            self.current_second_ip_bytes = 0

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "total_packets": self.total,
                "packets_last_second": self.last_second,
                "total_ip_bytes": self.total_ip_bytes,
                "ip_bytes_last_second": self.ip_bytes_last_second,
                "average_ip_packet_size": (
                    round(self.total_ip_bytes / self.total) if self.total else 0
                ),
                "average_ip_packet_size_last_second": (
                    round(self.ip_bytes_last_second / self.last_second)
                    if self.last_second
                    else 0
                ),
                "status": self.status,
                "error": self.error,
            }


def capture_packets(config: dict[str, Any], counter: PacketCounter) -> None:
    command = [
        "tcpdump",
        "-i",
        str(config.get("interface", "any")),
        "-Q",
        "in",
        "-n",
        "-l",
        "-v",
        "-s",
        "96",
        str(config.get("capture_filter", "")),
    ]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except OSError as error:
        counter.status = "error"
        counter.error = str(error)
        return

    counter.status = "running"
    assert process.stdout is not None
    for line in process.stdout:
        ip_bytes = parse_ip_total_length(line)
        if ip_bytes is not None:
            counter.increment(ip_bytes)

    counter.status = "error"
    counter.error = f"tcpdump exited with status {process.wait()}"


def sample_each_second(counter: PacketCounter) -> None:
    event = threading.Event()
    while not event.wait(1.0):
        counter.finish_second()


def make_handler(
    counter: PacketCounter,
    dashboard: bytes,
    frontend_config: dict[str, Any],
    extension_js: bytes,
    extension_css: bytes,
):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                self._send(200, "text/html; charset=utf-8", dashboard)
            elif path == "/extension.js":
                self._send(200, "text/javascript; charset=utf-8", extension_js)
            elif path == "/extension.css":
                self._send(200, "text/css; charset=utf-8", extension_css)
            elif path == "/api/config":
                self._send_json(200, {"api_version": 1, "frontend": frontend_config})
            elif path == "/api/stats":
                self._send_json(200, counter.snapshot())
            elif path == "/healthz":
                status = 200 if counter.status != "error" else 503
                self._send_json(status, {"status": counter.status})
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/reset":
                counter.reset()
                self._send_json(200, {"status": "reset"})
                return
            self._send_json(404, {"error": "not found"})

        def log_message(self, _format: str, *_args: Any) -> None:
            pass

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self._send(status, "application/json; charset=utf-8", body)

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def load_frontend(config: dict[str, Any], config_path: Path):
    configured = config.get("frontend", {})
    if not isinstance(configured, dict):
        raise ValueError("frontend configuration must be a JSON object")

    frontend = {
        "title": str(configured.get("title", "Traffic Visualizer")),
        "subtitle": str(configured.get("subtitle", "Packets observed")),
        "accent_color": str(configured.get("accent_color", "#38bdf8")),
        "options": configured.get("options", {}),
    }
    if not isinstance(frontend["options"], dict):
        raise ValueError("frontend.options must be a JSON object")

    def read_optional(name: str) -> bytes:
        value = configured.get(name)
        if not value:
            return b""
        path = Path(str(value))
        if not path.is_absolute():
            path = config_path.parent / path
        return path.read_bytes()

    return frontend, read_optional("extension_js"), read_optional("extension_css")


def main() -> int:
    parser = argparse.ArgumentParser(description="Count packets observed by tcpdump.")
    parser.add_argument("--config", default=str(SCRIPT_DIR / "config.json"))
    parser.add_argument("--dashboard", default=str(SCRIPT_DIR / "dashboard.html"))
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    dashboard = Path(args.dashboard).read_bytes()
    frontend_config, extension_js, extension_css = load_frontend(config, config_path)
    counter = PacketCounter()

    threading.Thread(target=capture_packets, args=(config, counter), daemon=True).start()
    threading.Thread(target=sample_each_second, args=(counter,), daemon=True).start()

    address = (str(config.get("web_host", "0.0.0.0")), int(config.get("web_port", 8080)))
    server = ThreadingHTTPServer(
        address,
        make_handler(
            counter,
            dashboard,
            frontend_config,
            extension_js,
            extension_css,
        ),
    )
    print(f"Traffic Visualizer listening on http://{address[0]}:{address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
