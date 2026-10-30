#!/usr/bin/env python3
"""Reusable synthetic HTTP service for denial-of-service demonstrations."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    max_bandwidth_bytes = 1024 * 1024

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if parsed.path == "/bandwidth":
            try:
                requested = int(parse_qs(parsed.query).get("bytes", ["0"])[0])
            except ValueError:
                requested = 0
            if requested < 1 or requested > self.max_bandwidth_bytes:
                self._send_json(
                    400,
                    {"error": f"bytes must be between 1 and {self.max_bandwidth_bytes}"},
                )
                return
            self._send_bytes(200, b"0" * requested)
            return
        self._send_json(404, {"error": "not found"})

    def log_message(self, _format: str, *_args: Any) -> None:
        pass

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def _send_bytes(self, status: int, body: bytes) -> None:
        self._send(status, "application/octet-stream", body)

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a synthetic victim HTTP service.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--max-bandwidth-bytes", type=int, default=1024 * 1024)
    args = parser.parse_args()
    if args.max_bandwidth_bytes < 1:
        parser.error("--max-bandwidth-bytes must be greater than zero")

    Handler.max_bandwidth_bytes = args.max_bandwidth_bytes
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Victim HTTP service listening on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
