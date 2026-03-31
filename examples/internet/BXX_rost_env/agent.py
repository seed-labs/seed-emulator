#!/usr/bin/env python3
"""Minimal one-shot agent for the RoST-style SEED example."""

import argparse
import json
import sys
import urllib.error
import urllib.request


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a one-shot repository/routing capability check."
    )
    parser.add_argument("--repo-host", required=True)
    parser.add_argument("--repo-port", type=int, required=True)
    parser.add_argument("--router-host", required=True)
    parser.add_argument("--router-port", type=int, required=True)
    return parser.parse_args()


def log_step(name, ok, detail):
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")


def http_get_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def http_post_json(url, payload, timeout=5):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def main():
    args = parse_args()
    repo_base = f"http://{args.repo_host}:{args.repo_port}"
    router_base = f"http://{args.router_host}:{args.router_port}"

    print("RoST demo agent starting")
    print(f"Repository target: {repo_base}")
    print(f"Router helper target: {router_base}")
    print("This is a one-shot capability check only; no RoST logic is implemented.")

    try:
        status, payload = http_get_json(f"{repo_base}/healthz")
        log_step("Repository health check", status == 200, payload)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        log_step("Repository health check", False, str(exc))

    message = {
        "message": "hello from adopting AS agent",
        "purpose": "seed capability demonstration",
    }
    try:
        status, payload = http_post_json(f"{repo_base}/", message)
        log_step("Repository message POST", status == 200, payload)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        log_step("Repository message POST", False, str(exc))

    router_checks = [
        ("Router helper health check", "/healthz"),
        ("Router BIRD protocols", "/bird/protocols"),
        ("Router BIRD routes", "/bird/route"),
    ]

    for name, path in router_checks:
        try:
            status, payload = http_get_json(f"{router_base}{path}")
            log_step(name, status == 200, payload)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            log_step(name, False, str(exc))

    print("Future placeholder: router-control logic would be added via the router helper.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
