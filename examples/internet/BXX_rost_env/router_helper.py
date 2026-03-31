#!/usr/bin/env python3
"""Minimal router-local helper for the RoST-style SEED example."""

import argparse
import json
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 18081


def run_command(argv):
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except FileNotFoundError as exc:
        return False, f"command not found: {exc.filename}"
    except subprocess.TimeoutExpired:
        return False, "command timed out"
    except Exception as exc:  # pragma: no cover - defensive reporting
        return False, str(exc)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "no stderr"
        return False, f"exit {result.returncode}: {stderr}"

    return True, result.stdout.strip() or "(no output)"


class RouterHelperHandler(BaseHTTPRequestHandler):
    server_version = "RoSTRouterHelper/0.1"

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json({"status": "ok"})
            return

        if self.path == "/bird/protocols":
            self._send_command_result(["birdc", "show", "protocols"])
            return

        if self.path == "/bird/route":
            self._send_command_result(["birdc", "show", "route"])
            return

        self.send_error(HTTPStatus.NOT_FOUND, "not found")

    def log_message(self, fmt, *args):
        return

    def _send_command_result(self, argv):
        ok, detail = run_command(argv)
        if ok:
            self._send_json({"status": "ok", "output": detail})
            return

        self._send_json({"status": "error", "error": detail}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the minimal RoST router helper."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main():
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), RouterHelperHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
