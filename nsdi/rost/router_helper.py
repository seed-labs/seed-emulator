#!/usr/bin/env python3
"""Router-local runtime policy controller for the RoST SEED example."""

import argparse
import ipaddress
import json
import subprocess
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 18081
ROST_POLICY_PATH = Path("/etc/bird/rost_policy.conf")
ROST_POLICY_STATE_PATH = Path("/etc/bird/rost_policy_state.json")
DEFAULT_ROUTEID_COMMUNITY = [65000, 100]


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


def canonicalize_prefix(prefix):
    network = ipaddress.ip_network(prefix, strict=False)
    if network.version != 4:
        raise ValueError("only IPv4 prefixes are supported")
    return str(network)


def normalize_state(raw_state):
    state = {
        "enabled": bool(raw_state.get("enabled", False)),
        "allowed_prefixes": [],
        "suppressed_prefixes": [],
        "routeid_prefixes": [],
        "invalid_prefixes": [],
    }

    for key in ("allowed_prefixes", "suppressed_prefixes", "routeid_prefixes", "invalid_prefixes"):
        prefixes = raw_state.get(key, [])
        if not isinstance(prefixes, list):
            raise ValueError(f"{key} must be a list")
        state[key] = sorted({canonicalize_prefix(prefix) for prefix in prefixes})

    return state


def render_prefix_match(prefixes, indent):
    joined = ", ".join(prefixes)
    return f'{" " * indent}if net ~ [ {joined} ] then return true;'


def render_policy_conf(state):
    enabled_value = "true" if state["enabled"] else "false"
    lines = [
        "# Managed by the RoST router helper.",
        "# This file is regenerated from /etc/bird/rost_policy_state.json.",
        "",
        "function rost_is_enabled()",
        "{",
        f"    return {enabled_value};",
        "}",
        "",
        "function rost_export_is_suppressed()",
        "{",
    ]

    if state["suppressed_prefixes"]:
        lines.append(render_prefix_match(state["suppressed_prefixes"], 4))
    lines.append("    return false;")
    lines.extend(
        [
            "}",
            "",
            "function rost_export_is_allowed()",
            "{",
        ]
    )

    if state["allowed_prefixes"]:
        lines.append(render_prefix_match(state["allowed_prefixes"], 4))
    lines.extend(
        [
            "    return false;",
            "}",
            "",
            "function rost_apply_export_attributes()",
            "{",
        ]
    )

    if state["routeid_prefixes"]:
        lines.extend(
            [
                f'    if net ~ [ {", ".join(state["routeid_prefixes"])} ] then {{',
                "        bgp_community.add(({}, {}));".format(*DEFAULT_ROUTEID_COMMUNITY),
                "    }",
            ]
        )

    lines.extend(
        [
            "}",
            "",
            "function rost_import_is_invalid()",
            "{",
        ]
    )

    if state["invalid_prefixes"]:
        lines.append(render_prefix_match(state["invalid_prefixes"], 4))
    lines.append("    return false;")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def list_bgp_protocols():
    ok, detail = run_command(["birdc", "show", "protocols"])
    if not ok:
        return False, detail

    protocols = []
    for raw_line in detail.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) >= 2 and parts[1] == "BGP":
            protocols.append(parts[0])

    return True, protocols


def refresh_bgp_protocols():
    ok, protocols = list_bgp_protocols()
    if not ok:
        return False, {
            "protocols": [],
            "detail": protocols,
            "results": [],
        }

    results = []
    for protocol in protocols:
        disable_ok, disable_detail = run_command(["birdc", "disable", protocol])
        enable_ok, enable_detail = run_command(["birdc", "enable", protocol])
        results.append(
            {
                "protocol": protocol,
                "disable": {
                    "ok": disable_ok,
                    "detail": disable_detail,
                },
                "enable": {
                    "ok": enable_ok,
                    "detail": enable_detail,
                },
            }
        )

    refresh_ok = all(
        entry["disable"]["ok"] and entry["enable"]["ok"]
        for entry in results
    )
    detail = "refreshed {} BGP protocol(s)".format(len(protocols))
    return refresh_ok, {
        "protocols": protocols,
        "detail": detail,
        "results": results,
    }


class PolicyManager:
    def __init__(self, state_path=ROST_POLICY_STATE_PATH, policy_path=ROST_POLICY_PATH, preserve_state=False):
        self._state_path = Path(state_path)
        self._policy_path = Path(policy_path)
        self._preserve_state = preserve_state
        self._lock = threading.Lock()
        self._state = self._load_state()
        self._write_state()
        self._write_policy_conf()

    def snapshot(self):
        with self._lock:
            return json.loads(json.dumps(self._state))

    def apply(self, mutator=None, refresh_bgp=False):
        with self._lock:
            if mutator is not None:
                mutator(self._state)

            self._write_state()
            self._write_policy_conf()
            ok, detail = run_command(["birdc", "configure"])
            refresh_ok = True
            refresh_payload = None
            if ok and refresh_bgp:
                refresh_ok, refresh_payload = refresh_bgp_protocols()

            payload = {
                "status": "ok" if ok and refresh_ok else "error",
                "bird_configure": {
                    "ok": ok,
                    "detail": detail,
                },
                "state": json.loads(json.dumps(self._state)),
            }
            if refresh_payload is not None:
                payload["bgp_refresh"] = {
                    "ok": refresh_ok,
                    **refresh_payload,
                }

            status = HTTPStatus.OK if ok and refresh_ok else HTTPStatus.INTERNAL_SERVER_ERROR
            return status, payload

    def _load_state(self):
        if not self._preserve_state or not self._state_path.exists():
            return normalize_state({})

        with self._state_path.open("r", encoding="utf-8") as handle:
            return normalize_state(json.load(handle))

    def _write_state(self):
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        with self._state_path.open("w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def _write_policy_conf(self):
        self._policy_path.parent.mkdir(parents=True, exist_ok=True)
        self._policy_path.write_text(render_policy_conf(self._state), encoding="utf-8")


class RouterHelperServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_cls, policy_manager):
        super().__init__(server_address, handler_cls)
        self.policy_manager = policy_manager


class RouterHelperHandler(BaseHTTPRequestHandler):
    server_version = "RoSTRouterHelper/0.2"

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json({"status": "ok"})
            return

        if self.path == "/rost/state":
            self._send_json({"status": "ok", "state": self.server.policy_manager.snapshot()})
            return

        if self.path == "/bird/protocols":
            self._send_command_result(["birdc", "show", "protocols"])
            return

        if self.path == "/bird/route":
            self._send_command_result(["birdc", "show", "route"])
            return

        self.send_error(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self):
        routes = {
            "/rost/enable": self._post_enable,
            "/rost/disable": self._post_disable,
            "/rost/allow": self._post_allow,
            "/rost/disallow": self._post_disallow,
            "/rost/suppress": self._post_suppress,
            "/rost/unsuppress": self._post_unsuppress,
            "/rost/routeid": self._post_routeid,
            "/rost/unrouteid": self._post_unrouteid,
            "/rost/invalidate": self._post_invalidate,
            "/rost/clear-invalid": self._post_clear_invalid,
            "/bird/configure": self._post_bird_configure,
        }

        handler = routes.get(self.path)
        if handler is None:
            self.send_error(HTTPStatus.NOT_FOUND, "not found")
            return

        try:
            payload = self._read_json_payload()
            status, response = handler(payload)
        except ValueError as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json(response, status=status)

    def log_message(self, fmt, *args):
        return

    def _post_enable(self, _payload):
        return self.server.policy_manager.apply(
            lambda state: state.__setitem__("enabled", True)
        )

    def _post_disable(self, _payload):
        return self.server.policy_manager.apply(
            lambda state: state.__setitem__("enabled", False)
        )

    def _post_allow(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._add_prefix(state["allowed_prefixes"], prefix),
            refresh_bgp=True,
        )

    def _post_disallow(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._remove_prefix(state["allowed_prefixes"], prefix),
            refresh_bgp=True,
        )

    def _post_suppress(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._add_prefix(state["suppressed_prefixes"], prefix),
            refresh_bgp=True,
        )

    def _post_unsuppress(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._remove_prefix(state["suppressed_prefixes"], prefix),
            refresh_bgp=True,
        )

    def _post_routeid(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._add_prefix(state["routeid_prefixes"], prefix)
        )

    def _post_unrouteid(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._remove_prefix(state["routeid_prefixes"], prefix)
        )

    def _post_invalidate(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._add_prefix(state["invalid_prefixes"], prefix),
            refresh_bgp=True,
        )

    def _post_clear_invalid(self, payload):
        prefix = self._require_prefix(payload)
        return self.server.policy_manager.apply(
            lambda state: self._remove_prefix(state["invalid_prefixes"], prefix),
            refresh_bgp=True,
        )

    def _post_bird_configure(self, _payload):
        return self.server.policy_manager.apply()

    def _send_command_result(self, argv):
        ok, detail = run_command(argv)
        if ok:
            self._send_json({"status": "ok", "output": detail})
            return

        self._send_json(
            {"status": "error", "error": detail},
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_payload(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}

        body = self.rfile.read(content_length).decode("utf-8")
        if not body.strip():
            return {}

        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")
        return payload

    def _require_prefix(self, payload):
        prefix = payload.get("prefix")
        if prefix is None:
            raise ValueError('missing required field "prefix"')
        return canonicalize_prefix(prefix)

    @staticmethod
    def _add_prefix(prefixes, prefix):
        if prefix not in prefixes:
            prefixes.append(prefix)
            prefixes.sort()

    @staticmethod
    def _remove_prefix(prefixes, prefix):
        if prefix in prefixes:
            prefixes.remove(prefix)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the RoST router helper."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--policy-state", default=str(ROST_POLICY_STATE_PATH))
    parser.add_argument("--policy-conf", default=str(ROST_POLICY_PATH))
    parser.add_argument(
        "--preserve-state",
        action="store_true",
        help="load existing policy state on startup instead of resetting to an empty default state",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    policy_manager = PolicyManager(
        state_path=args.policy_state,
        policy_path=args.policy_conf,
        preserve_state=args.preserve_state,
    )
    server = RouterHelperServer((args.host, args.port), RouterHelperHandler, policy_manager)
    server.serve_forever()


if __name__ == "__main__":
    main()
