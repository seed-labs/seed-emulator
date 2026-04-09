#!/usr/bin/env python3
"""Minimal mock repository service for the RoST-style SEED example."""

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 18080


class RepoRequestHandler(BaseHTTPRequestHandler):
    server_version = "RoSTRepo/0.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 0:
            self.rfile.read(length)

        self._send_json({"status": "received"})

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json({"status": "ok"})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "not found")

    def log_message(self, fmt, *args):
        return

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the minimal mock RoST repository service."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main():
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), RepoRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
