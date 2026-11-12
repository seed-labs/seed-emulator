#!/usr/bin/env python3
"""Read-only B61 Kubernetes placement, routing, and ping validation.

Inputs: compiler output, kubeconfig, and an optional artifact directory.
Outputs: runtime-summary.json containing checks and raw command evidence.
Uses kubectl API reads/exec; creates no resources and changes no Pod settings.
Run after K8sTools.py up, from any working directory.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import time

import yaml


META = "org.seedsecuritylabs.seedemu.meta."


def executeKubectl(args: argparse.Namespace, *command: str) -> dict:
    """Execute command against args.kubeconfig and retain exit/output evidence."""
    argv = ["kubectl", "--kubeconfig", str(args.kubeconfig), "--request-timeout=30s",
            "-n", args.namespace, *command]
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=45)
        return dict(command=list(command), exitCode=result.returncode,
                    stdout=result.stdout, stderr=result.stderr)
    except subprocess.TimeoutExpired as error:
        return dict(command=list(command), exitCode=124, stdout="", stderr=str(error))


def readKubernetes(args: argparse.Namespace, resource: str) -> list[dict]:
    """Read resource objects using args' cluster access settings."""
    result = executeKubectl(args, "get", resource, "-o", "json")
    if result["exitCode"]:
        raise RuntimeError(result["stderr"])
    return json.loads(result["stdout"])["items"]


def validateRuntime(args: argparse.Namespace) -> dict:
    """Validate args.output's deployed topology and save evidence in args.artifact_dir."""
    summary = dict(status="FAIL", checks=[], protocols=[], pings=[])
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    def recordCheck(name: str, passed: bool, details: object) -> None:
        """Record named assertion with its boolean result and supporting details."""
        summary["checks"].append(dict(name=name, passed=bool(passed), details=details))

    try:
        docs = [d for d in yaml.safe_load_all((args.output / "k8s.yaml").read_text()) if d]
        expected = {d["metadata"]["name"]: d for d in docs if d["kind"] == "Deployment"}
        partition = json.loads((args.output / "partitionApplied.json").read_text())
        pods = readKubernetes(args, "pods")
        (args.artifact_dir / "pods.json").write_text(json.dumps(pods, indent=2) + "\n")
        byApp = {p["metadata"].get("labels", {}).get("app"): p for p in pods}
        recordCheck("expected workload coverage", len(pods) == len(expected)
                    and set(byApp) == set(expected), dict(expected=len(expected), actual=len(pods)))
        if set(byApp) != set(expected):
            raise ValueError("Live Pods do not cover the compiled topology")
        badReady = []
        badNetworks = []
        badPlacement = []
        asNodes = defaultdict(set)
        hosts = []
        routers = {}
        for app, doc in expected.items():
            pod = byApp[app]
            labels = doc["metadata"]["labels"]
            statuses = pod.get("status", {}).get("containerStatuses", [])
            if not statuses or any(not c.get("ready") or c.get("restartCount", 0) for c in statuses):
                badReady.append(app)
            node = pod["spec"]["nodeName"]
            if node != partition["mapping"].get(app):
                badPlacement.append(app)
            asn = labels["seedemu.io/asn"]
            asNodes[asn].add(node)
            annotations = pod["metadata"].get("annotations", {})
            requested = json.loads(doc["spec"]["template"]["metadata"]["annotations"]
                                   ["k8s.v1.cni.cncf.io/networks"])
            actual = {n["name"].rsplit("/", 1)[-1]: {ip.split("/")[0] for ip in n.get("ips", [])}
                      for n in json.loads(annotations.get("k8s.v1.cni.cncf.io/network-status", "[]"))}
            if any(not {ip.split("/")[0] for ip in n.get("ips", [])}
                   <= actual.get(n["name"], set()) for n in requested):
                badNetworks.append(app)
            item = dict(app=app, pod=pod["metadata"]["name"], asn=asn, node=node,
                        address=annotations[META + "net.0.address"].split("/")[0])
            if labels["seedemu.io/role"] == "h":
                hosts.append(item)
            if (labels["seedemu.io/role"] in {"r", "brd"}
                    and annotations.get(META + "role") not in {"Route Server", "RouteServer"}):
                if asn not in routers or app < routers[asn]["app"]:
                    routers[asn] = item
        recordCheck("all Pods Ready without restarts", not badReady, badReady)
        recordCheck("secondary CNI addresses match topology", not badNetworks, badNetworks)
        recordCheck("default whole-AS nodeName placement", partition["algorithm"] == "nodeByAs"
                    and not badPlacement and all(len(ns) == 1 for ns in asNodes.values()),
                    {a: sorted(ns) for a, ns in asNodes.items()})
        recordCheck("multiple workers exercised", len(set(partition["mapping"].values())) >= 2,
                    sorted(set(partition["mapping"].values())))

        # Check one stable router per AS. Commands are read-only and preserve
        # raw protocols, route counts, and kernel exports for failure diagnosis.
        def checkRouter(item: dict) -> dict:
            """Read item router's VM load, BIRD protocols and exported Linux routes."""
            started = time.monotonic()
            while True:
                load_result = executeKubectl(args, "exec", item["pod"], "--", "cat", "/proc/loadavg")
                if load_result["exitCode"]:
                    return dict(**item, **load_result, passed=False, protocolsHealthy=False,
                                fibHealthy=False, load1=None, loadWaitSeconds=time.monotonic()-started)
                load = float(load_result["stdout"].split()[0])
                if load < 50:
                    break
                time.sleep(5)
            waited = round(time.monotonic()-started, 3)
            command = ('birdc show protocols; printf "\\nB61_RIB\\n"; '
                       'birdc show route count; printf "\\nB61_FIB_COUNT\\n"; '
                       'ip -4 route show | wc -l; printf "\\nB61_EXPORTS\\n"; '
                       'ip -4 route show proto bird')
            result = executeKubectl(args, "exec", item["pod"], "--", "sh", "-ec", command)
            lines = result["stdout"].splitlines()
            protocols = [line.split() for line in lines if len(line.split()) >= 5
                         and line.split()[1] in {"BGP", "OSPF", "Kernel", "Device", "Direct"}]
            healthy = result["exitCode"] == 0 and protocols and all(
                p[3] == "up" and (p[1] != "BGP" or "Established" in p) for p in protocols)
            # iproute2 suppresses the proto field when that protocol is selected.
            routes = bool(result["stdout"].partition("B61_EXPORTS\n")[2].strip())
            count = re.search(r"for (\d+) networks", result["stdout"])
            parse_mode = "networks"
            if count is None:
                count = re.search(r"(?:^|\n)(\d+) routes", result["stdout"])
                parse_mode = "routes-fallback"
            fib = re.search(r"B61_FIB_COUNT\s+(\d+)", result["stdout"])
            bird_count = int(count[1]) if count else None
            fib_count = int(fib[1]) if fib else None
            fib_healthy = (result["exitCode"] == 0 and bird_count is not None and fib_count is not None
                           and 0 < bird_count < fib_count and routes)
            return dict(**item, **result, load1=load, loadWaitSeconds=waited,
                        birdNetworkCount=bird_count, birdCountParseMode=parse_mode,
                        ipRouteCount=fib_count, protocolsHealthy=bool(healthy), fibHealthy=fib_healthy,
                        passed=result["exitCode"] == 0 and bool(healthy) and fib_healthy)

        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=4) as pool:
            summary["protocols"] = list(pool.map(checkRouter,
                [routers[a] for a in sorted(routers, key=int)]))
        elapsed = round(time.monotonic()-started, 3)
        for key, selected, field in [
            ("verify_after_start_bird", summary["protocols"][:10], "protocolsHealthy"),
            ("verify_after_fib_write", summary["protocols"], "fibHealthy"),
        ]:
            summary[key] = dict(success=bool(selected) and all(p[field] for p in selected),
                sample_count=len(selected), selected_containers=[p["app"] for p in selected],
                failed_samples=[p["app"] for p in selected if not p[field]],
                load1={p["node"]: p["load1"] for p in selected},
                load_wait_seconds=max((p["loadWaitSeconds"] for p in selected), default=0),
                duration_seconds=elapsed)
        recordCheck("BIRD protocols and kernel exports", bool(routers)
                    and all(p["passed"] for p in summary["protocols"]),
                    dict(checked=len(routers), failed=[p["app"] for p in summary["protocols"] if not p["passed"]]))

        hosts.sort(key=lambda h: (int(h["asn"]), h["app"]))
        pairs = {}
        for source in hosts:
            candidates = [h for h in hosts if h["asn"] != source["asn"] and h["node"] != source["node"]]
            if not candidates:
                raise ValueError("No host in another AS on another worker")
            destination = candidates[0]
            pairs[(source["app"], destination["app"])] = (source, destination)
            pairs[(destination["app"], source["app"])] = (destination, source)
            local = [h for h in hosts if h["asn"] == source["asn"] and h["app"] != source["app"]]
            if local:
                pairs[(source["app"], local[0]["app"])] = (source, local[0])

        def checkPing(pair: tuple[dict, dict]) -> dict:
            """Ping pair's destination from its source Pod, recording worker identities."""
            source, destination = pair
            result = executeKubectl(args, "exec", source["pod"], "--", "ping", "-n",
                                    "-c", "3", "-W", "2", destination["address"])
            return dict(source=source, destination=destination, **result,
                        crossWorker=source["node"] != destination["node"],
                        passed=result["exitCode"] == 0 and ", 0% packet loss" in result["stdout"])

        with ThreadPoolExecutor(max_workers=6) as pool:
            summary["pings"] = list(pool.map(checkPing, [pairs[k] for k in sorted(pairs)]))
        recordCheck("all hosts ping within and between ASes", bool(hosts)
                    and all(p["passed"] for p in summary["pings"]),
                    dict(hosts=len(hosts), pairs=len(pairs),
                         crossWorkerPairs=sum(p["crossWorker"] for p in summary["pings"])))
        summary["status"] = "PASS" if all(c["passed"] for c in summary["checks"]) else "FAIL"
    except Exception as error:
        summary["error"] = str(error)
    (args.artifact_dir / "runtime-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in {"protocols", "pings"}}, indent=2))
    return summary


def executeCli() -> int:
    """Parse local paths and cluster access arguments, then validate the live example."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "output")
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--namespace", default="seedemu")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    return 0 if validateRuntime(args)["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(executeCli())
