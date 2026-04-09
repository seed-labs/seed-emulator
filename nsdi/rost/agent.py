#!/usr/bin/env python3
"""RoST demo agent with repository checks and router-helper controls."""

import argparse
import json
import sys
import urllib.error
import urllib.request


DEFAULT_ROUTER_PORT = 18081


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the RoST demo agent."
    )
    parser.add_argument("--repo-host")
    parser.add_argument("--repo-port", type=int)
    parser.add_argument("--router-host")
    parser.add_argument("--router-port", type=int)
    parser.add_argument("--router-ip")

    controls = parser.add_mutually_exclusive_group()
    controls.add_argument("--enable", action="store_true")
    controls.add_argument("--disable", action="store_true")
    controls.add_argument("--allow", metavar="PREFIX")
    controls.add_argument("--disallow", metavar="PREFIX")
    controls.add_argument("--suppress", metavar="PREFIX")
    controls.add_argument("--unsuppress", metavar="PREFIX")
    controls.add_argument("--routeid", metavar="PREFIX")
    controls.add_argument("--unrouteid", metavar="PREFIX")
    controls.add_argument("--invalidate", metavar="PREFIX")
    controls.add_argument("--clear-invalid", dest="clear_invalid", metavar="PREFIX")
    controls.add_argument("--state", action="store_true")

    args = parser.parse_args()

    if has_control_command(args):
        if not args.router_ip:
            parser.error("--router-ip is required for control commands")
        if args.router_port is None:
            args.router_port = DEFAULT_ROUTER_PORT
        return args

    required = {
        "--repo-host": args.repo_host,
        "--repo-port": args.repo_port,
        "--router-host": args.router_host,
        "--router-port": args.router_port,
    }
    missing = [flag for flag, value in required.items() if value is None]
    if missing:
        parser.error("missing required arguments for capability check: " + ", ".join(missing))

    return args


def has_control_command(args):
    return any(
        [
            args.enable,
            args.disable,
            args.allow is not None,
            args.disallow is not None,
            args.suppress is not None,
            args.unsuppress is not None,
            args.routeid is not None,
            args.unrouteid is not None,
            args.invalidate is not None,
            args.clear_invalid is not None,
            args.state,
        ]
    )


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


def http_request_json(url, method="GET", payload=None, timeout=5):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def router_get_json(base_url, path, timeout=5):
    return http_request_json(f"{base_url}{path}", method="GET", timeout=timeout)


def router_post_json(base_url, path, payload=None, timeout=5):
    return http_request_json(
        f"{base_url}{path}",
        method="POST",
        payload=payload or {},
        timeout=timeout,
    )


def run_control_command(args):
    router_base = f"http://{args.router_ip}:{args.router_port}"

    action_map = [
        (args.enable, "POST", "/rost/enable", None),
        (args.disable, "POST", "/rost/disable", None),
        (args.allow, "POST", "/rost/allow", {"prefix": args.allow} if args.allow else None),
        (
            args.disallow,
            "POST",
            "/rost/disallow",
            {"prefix": args.disallow} if args.disallow else None,
        ),
        (args.suppress, "POST", "/rost/suppress", {"prefix": args.suppress} if args.suppress else None),
        (
            args.unsuppress,
            "POST",
            "/rost/unsuppress",
            {"prefix": args.unsuppress} if args.unsuppress else None,
        ),
        (args.routeid, "POST", "/rost/routeid", {"prefix": args.routeid} if args.routeid else None),
        (
            args.unrouteid,
            "POST",
            "/rost/unrouteid",
            {"prefix": args.unrouteid} if args.unrouteid else None,
        ),
        (
            args.invalidate,
            "POST",
            "/rost/invalidate",
            {"prefix": args.invalidate} if args.invalidate else None,
        ),
        (
            args.clear_invalid,
            "POST",
            "/rost/clear-invalid",
            {"prefix": args.clear_invalid} if args.clear_invalid else None,
        ),
        (args.state, "GET", "/rost/state", None),
    ]

    for selected, method, path, payload in action_map:
        if not selected:
            continue

        try:
            if method == "GET":
                status, response = router_get_json(router_base, path)
            else:
                status, response = router_post_json(router_base, path, payload)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
            return 1
        except json.JSONDecodeError as exc:
            print(json.dumps({"status": "error", "error": f"invalid JSON response: {exc}"}, indent=2, sort_keys=True))
            return 1

        print(json.dumps(response, indent=2, sort_keys=True))
        return 0 if 200 <= status < 300 else 1

    print(json.dumps({"status": "error", "error": "no control command selected"}, indent=2, sort_keys=True))
    return 1


def run_capability_check(args):
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

    print("Capability check complete.")
    return 0


def main():
    args = parse_args()
    if has_control_command(args):
        return run_control_command(args)
    return run_capability_check(args)


if __name__ == "__main__":
    sys.exit(main())
