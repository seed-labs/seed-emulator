#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from aiohttp import web


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KUBECONFIG = REPO_ROOT / "output" / "kubeconfigs" / "seedemu-k3s.yaml"
STATIC_INDEX = REPO_ROOT / "tools" / "showcase" / "index.html"
MAX_EVIDENCE_BYTES = 50000


def _ensure_kubeconfig() -> None:
    if "KUBECONFIG" not in os.environ and DEFAULT_KUBECONFIG.exists():
        os.environ["KUBECONFIG"] = str(DEFAULT_KUBECONFIG)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _safe_read_text(path: Path, fallback: str = "") -> str:
    if not path.exists():
        return fallback
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback


def _run(
    args: List[str],
    *,
    timeout: int = 20,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if check:
        result.check_returncode()
    return result


def _run_shell(command: str, *, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-lc", command],
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _split_columns(line: str) -> List[str]:
    return [chunk for chunk in re.split(r"\s{2,}", line.strip()) if chunk]


def _parse_top_table(raw: str) -> List[Dict[str, str]]:
    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    headers = _split_columns(lines[0])
    rows: List[Dict[str, str]] = []
    for line in lines[1:]:
        cols = _split_columns(line)
        if not cols:
            continue
        row = {headers[index]: cols[index] if index < len(cols) else "" for index in range(len(headers))}
        rows.append(row)
    return rows


def _parse_protocol_rows(raw: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("BIRD ", "Name ", "Access restricted", "Error from server")):
            continue
        if ".go:" in stripped and stripped.startswith(("I0", "W0", "E0")):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        proto_name = parts[0]
        proto_type = parts[1]
        established = "Established" in stripped
        rows.append(
            {
                "name": proto_name,
                "type": proto_type,
                "state": parts[3] if len(parts) > 3 else "",
                "info": parts[-1] if len(parts) > 4 else "",
                "established": established,
                "raw": stripped,
            }
        )
    return rows


def _strip_kubectl_exec_noise(raw: str) -> str:
    cleaned: List[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if ".go:" in stripped and stripped.startswith(("I0", "W0", "E0")):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _summarize_rr_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    by_as: List[Dict[str, Any]] = []
    totals = {
        "ases": 0,
        "rrs": 0,
        "clients": 0,
        "clusters": 0,
        "internal_links": 0,
    }

    for asn, item in sorted(plan.items(), key=lambda pair: int(pair[0]) if str(pair[0]).isdigit() else pair[0]):
        clusters = item.get("clusters", {}) if isinstance(item, dict) else {}
        cluster_rrs = item.get("cluster_rrs", {}) if isinstance(item, dict) else {}
        internal_links = item.get("internal_links", []) if isinstance(item, dict) else []
        clients = sum(len(value) for value in clusters.values()) - len(cluster_rrs)
        summary = {
            "asn": str(asn),
            "rrs": len(cluster_rrs),
            "clients": max(clients, 0),
            "clusters": len(clusters),
            "internal_links": len(internal_links),
        }
        by_as.append(summary)
        totals["ases"] += 1
        totals["rrs"] += summary["rrs"]
        totals["clients"] += summary["clients"]
        totals["clusters"] += summary["clusters"]
        totals["internal_links"] += summary["internal_links"]

    return {"totals": totals, "by_as": by_as[:20]}


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except Exception:
        return str(path)


def _read_artifact_tree(paths: List[Tuple[str, Path]]) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for section, root in paths:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                items.append({"section": section, "path": _relative(path)})
    return items


def _read_artifact_content(root: Path, relative_path: str) -> Dict[str, Any]:
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root.resolve())
    except Exception as exc:
        raise ValueError(f"evidence path escapes run directory: {exc}") from exc

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"evidence file not found: {relative_path}")

    raw = target.read_text(encoding="utf-8", errors="replace")
    truncated = len(raw.encode("utf-8")) > MAX_EVIDENCE_BYTES
    if truncated:
        content = raw[:MAX_EVIDENCE_BYTES] + "\n\n...[truncated]..."
    else:
        content = raw
    return {
        "path": relative_path,
        "content": content,
        "truncated": truncated,
    }


def _resolve_run_dir(profile: str, run_id: str) -> Tuple[Path, str]:
    profile_root = REPO_ROOT / "output" / "profile_runs" / profile
    if not profile_root.exists():
        raise FileNotFoundError(f"profile run directory not found: {profile_root}")

    if run_id == "latest":
        latest = profile_root / "latest"
        if latest.exists():
            return latest.resolve(), latest.resolve().name
        runs = sorted([path for path in profile_root.iterdir() if path.is_dir() and path.name != "latest"], reverse=True)
        if runs:
            return runs[0], runs[0].name
        raise FileNotFoundError(f"no runs found under {profile_root}")

    target = profile_root / run_id
    if not target.exists():
        raise FileNotFoundError(f"run not found: {target}")
    return target.resolve(), target.resolve().name


@dataclass(frozen=True)
class RunContext:
    profile: str
    run_id: str
    base_dir: Path
    namespace_override: str

    @property
    def validation_dir(self) -> Path:
        return self.base_dir / "validation"

    @property
    def observe_dir(self) -> Path:
        return self.base_dir / "observe"

    @property
    def report_dir(self) -> Path:
        return self.base_dir / "report"

    @property
    def compiled_dir(self) -> Path:
        return self.base_dir / "compiled"

    @property
    def namespace(self) -> str:
        if self.namespace_override:
            return self.namespace_override
        summary = _load_json(self.validation_dir / "summary.json")
        if summary.get("namespace"):
            return str(summary["namespace"])
        report = _load_json(self.report_dir / "report.json")
        if report.get("namespace"):
            return str(report["namespace"])
        return ""


def _kubectl_json(namespace: str, args: List[str], *, timeout: int = 20) -> Dict[str, Any]:
    cmd = ["kubectl"]
    if namespace:
        cmd.extend(["-n", namespace])
    cmd.extend(args)
    result = _run(cmd, timeout=timeout)
    if result.returncode != 0:
        return {}
    try:
        data = json.loads(result.stdout)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _collect_nodes() -> Dict[str, Any]:
    nodes_json = _kubectl_json("", ["get", "nodes", "-o", "json"])
    top_raw = _run(["kubectl", "top", "nodes"], timeout=20)
    top_rows = {row.get("NAME", ""): row for row in _parse_top_table(top_raw.stdout)}

    nodes: List[Dict[str, Any]] = []
    for item in nodes_json.get("items", []):
        metadata = item.get("metadata", {}) or {}
        status = item.get("status", {}) or {}
        name = str(metadata.get("name", ""))
        ready = any(
            condition.get("type") == "Ready" and condition.get("status") == "True"
            for condition in status.get("conditions", []) or []
        )
        node_info = status.get("nodeInfo", {}) or {}
        allocatable = status.get("allocatable", {}) or {}
        top = top_rows.get(name, {})
        nodes.append(
            {
                "name": name,
                "ready": ready,
                "os_image": str(node_info.get("osImage", "")),
                "kernel_version": str(node_info.get("kernelVersion", "")),
                "runtime": str(node_info.get("containerRuntimeVersion", "")),
                "cpu_allocatable": str(allocatable.get("cpu", "")),
                "memory_allocatable": str(allocatable.get("memory", "")),
                "cpu_used": top.get("CPU(cores)", ""),
                "cpu_percent": top.get("CPU(%)", ""),
                "memory_used": top.get("MEMORY(bytes)", ""),
                "memory_percent": top.get("MEMORY(%)", ""),
            }
        )

    return {
        "items": nodes,
        "ready_count": sum(1 for item in nodes if item["ready"]),
        "total_count": len(nodes),
        "top_available": bool(top_rows),
    }


def _collect_pods(namespace: str) -> Dict[str, Any]:
    pods_json = _kubectl_json(namespace, ["get", "pods", "-o", "json"])
    top_raw = _run(["kubectl", "-n", namespace, "top", "pods"], timeout=20)
    top_rows = {row.get("NAME", ""): row for row in _parse_top_table(top_raw.stdout)}

    pods: List[Dict[str, Any]] = []
    by_node: Dict[str, int] = {}
    by_role: Dict[str, int] = {}

    for item in pods_json.get("items", []):
        metadata = item.get("metadata", {}) or {}
        spec = item.get("spec", {}) or {}
        status = item.get("status", {}) or {}
        labels = metadata.get("labels", {}) or {}
        name = str(metadata.get("name", ""))
        node = str(spec.get("nodeName", ""))
        role = str(labels.get("seedemu.io/role", ""))
        ready_count = sum(1 for container in status.get("containerStatuses", []) or [] if container.get("ready"))
        total_count = len(status.get("containerStatuses", []) or [])
        top = top_rows.get(name, {})
        pod = {
            "name": name,
            "namespace": namespace,
            "phase": str(status.get("phase", "")),
            "node": node,
            "pod_ip": str(status.get("podIP", "")),
            "asn": str(labels.get("seedemu.io/asn", "")),
            "logical_name": str(labels.get("seedemu.io/name", "")),
            "role": role,
            "workload": str(labels.get("seedemu.io/workload", "")),
            "ready": f"{ready_count}/{total_count}",
            "restarts": sum(int(container.get("restartCount", 0)) for container in status.get("containerStatuses", []) or []),
            "cpu_used": top.get("CPU(cores)", ""),
            "memory_used": top.get("MEMORY(bytes)", ""),
        }
        pods.append(pod)
        by_node[node] = by_node.get(node, 0) + 1
        by_role[role or "unknown"] = by_role.get(role or "unknown", 0) + 1

    pods.sort(key=lambda item: (item["node"], item["asn"], item["logical_name"], item["name"]))
    return {
        "items": pods,
        "total_count": len(pods),
        "running_count": sum(1 for pod in pods if pod["phase"] == "Running"),
        "nodes": by_node,
        "roles": by_role,
        "top_available": bool(top_rows),
    }


def _collect_services(namespace: str) -> List[Dict[str, Any]]:
    services_json = _kubectl_json(namespace, ["get", "svc", "-o", "json"])
    services: List[Dict[str, Any]] = []
    for item in services_json.get("items", []):
        metadata = item.get("metadata", {}) or {}
        spec = item.get("spec", {}) or {}
        services.append(
            {
                "name": str(metadata.get("name", "")),
                "type": str(spec.get("type", "")),
                "cluster_ip": str(spec.get("clusterIP", "")),
                "ports": spec.get("ports", []) or [],
            }
        )
    return services


def _collect_events(namespace: str) -> str:
    result = _run(
        ["kubectl", "-n", namespace, "get", "events", "--sort-by=.lastTimestamp"],
        timeout=20,
    )
    output = result.stdout or result.stderr
    if not output.strip():
        return "No recent events."
    lines = output.splitlines()
    return "\n".join(lines[-25:])


def _collect_system_snapshot() -> Dict[str, str]:
    os_release = _safe_read_text(Path("/etc/os-release"))
    host_os = ""
    for line in os_release.splitlines():
        if line.startswith("PRETTY_NAME="):
            host_os = line.split("=", 1)[1].strip().strip('"')
            break
    uptime = _run_shell("uptime", timeout=5)
    memory = _run_shell("free -h", timeout=5)
    top = _run_shell("top -bn1 | head -20", timeout=5)
    return {
        "host_os": host_os,
        "uptime": (uptime.stdout or uptime.stderr).strip(),
        "memory": (memory.stdout or memory.stderr).strip(),
        "top": (top.stdout or top.stderr).strip(),
    }


def _pod_exec(namespace: str, pod: str, command: str, *, timeout: int = 20) -> Dict[str, Any]:
    result = _run(
        ["kubectl", "-n", namespace, "exec", pod, "--", "sh", "-lc", command],
        timeout=timeout,
    )
    raw = "\n".join(chunk for chunk in [result.stdout, result.stderr] if chunk).strip()
    raw = _strip_kubectl_exec_noise(raw)
    return {"returncode": result.returncode, "output": raw}


def _collect_probe(namespace: str, pod: str, mode: str, expr: str = "", count: int = 20) -> Dict[str, Any]:
    if mode == "protocols":
        probe = _pod_exec(namespace, pod, "birdc show protocols", timeout=20)
        probe["protocols"] = _parse_protocol_rows(probe["output"])
        return probe
    if mode == "routes":
        return _pod_exec(namespace, pod, "ip route && printf '\\n---\\n' && ip -br addr", timeout=20)
    if mode == "sniff":
        safe_expr = shlex.quote(expr.strip()) if expr.strip() else ""
        capped_count = max(1, min(count, 50))
        if safe_expr:
            command = f"timeout 8 tcpdump -ni any -c {capped_count} {safe_expr}"
        else:
            command = f"timeout 8 tcpdump -ni any -c {capped_count}"
        probe = _pod_exec(namespace, pod, command, timeout=20)
        probe["command"] = command
        return probe
    raise ValueError(f"unsupported probe mode: {mode}")


def _build_overview(context: RunContext) -> Dict[str, Any]:
    summary = _load_json(context.validation_dir / "summary.json")
    report = _load_json(context.report_dir / "report.json")
    observe_summary = _load_json(context.observe_dir / "summary.json")
    bgp_summary = _load_json(context.validation_dir / "bgp_health_summary.json")
    if not bgp_summary:
        bgp_summary = _load_json(context.observe_dir / "bgp_health_summary.json")
    rr_plan = _load_json(context.compiled_dir / "rr_plan.json")
    if not rr_plan:
        rr_plan = _load_json(context.observe_dir / "rr_plan.json")

    pods = _collect_pods(context.namespace) if context.namespace else {"items": [], "total_count": 0, "running_count": 0, "nodes": {}, "roles": {}}
    nodes = _collect_nodes()

    timeline = {
        "total": summary.get("pipeline_duration_seconds", summary.get("duration_seconds", 0)),
        "build": summary.get("build_duration_seconds", 0),
        "up": summary.get("up_duration_seconds", 0),
        "phase_start": summary.get("phase_start_duration_seconds", 0),
        "verify": summary.get("validation_duration_seconds", summary.get("duration_seconds", 0)),
    }

    return {
        "profile": context.profile,
        "run_id": context.run_id,
        "run_dir": _relative(context.base_dir),
        "namespace": context.namespace,
        "summary": summary,
        "report": report,
        "observe_summary": observe_summary,
        "bgp_summary": bgp_summary,
        "rr_plan_summary": _summarize_rr_plan(rr_plan) if rr_plan else {},
        "live": {
            "pods_total": pods.get("total_count", 0),
            "pods_running": pods.get("running_count", 0),
            "nodes_total": nodes.get("total_count", 0),
            "nodes_ready": nodes.get("ready_count", 0),
            "pod_distribution": pods.get("nodes", {}),
            "role_distribution": pods.get("roles", {}),
        },
        "timeline": timeline,
    }


def _json_response(result: Any, *, ok: bool = True, status: int = 200) -> web.Response:
    return web.json_response({"ok": ok, "result": result}, status=status)


async def _index(_: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_INDEX)


async def _health(_: web.Request) -> web.Response:
    return _json_response({"status": "ok"})


async def _api_overview(request: web.Request) -> web.Response:
    context: RunContext = request.app["context"]
    return _json_response(_build_overview(context))


async def _api_nodes(request: web.Request) -> web.Response:
    return _json_response(_collect_nodes())


async def _api_pods(request: web.Request) -> web.Response:
    context: RunContext = request.app["context"]
    return _json_response(_collect_pods(context.namespace))


async def _api_services(request: web.Request) -> web.Response:
    context: RunContext = request.app["context"]
    return _json_response({"items": _collect_services(context.namespace)})


async def _api_events(request: web.Request) -> web.Response:
    context: RunContext = request.app["context"]
    return _json_response({"tail": _collect_events(context.namespace)})


async def _api_system(request: web.Request) -> web.Response:
    return _json_response(_collect_system_snapshot())


async def _api_evidence(request: web.Request) -> web.Response:
    context: RunContext = request.app["context"]
    files = _read_artifact_tree(
        [
            ("validation", context.validation_dir),
            ("observe", context.observe_dir),
            ("report", context.report_dir),
            ("compiled", context.compiled_dir),
        ]
    )
    return _json_response({"files": files})


async def _api_evidence_content(request: web.Request) -> web.Response:
    context: RunContext = request.app["context"]
    relative_path = request.query.get("path", "").strip()
    if not relative_path:
        return _json_response({"error": "missing path"}, ok=False, status=400)
    try:
        result = _read_artifact_content(context.base_dir, relative_path)
    except Exception as exc:
        return _json_response({"error": str(exc)}, ok=False, status=400)
    return _json_response(result)


async def _api_probe(request: web.Request) -> web.Response:
    context: RunContext = request.app["context"]
    pod = request.match_info["pod"]
    mode = request.match_info["mode"]
    expr = request.query.get("expr", "")
    count = int(request.query.get("count", "20"))
    try:
        result = await asyncio.to_thread(_collect_probe, context.namespace, pod, mode, expr, count)
    except Exception as exc:
        return _json_response({"error": str(exc)}, ok=False, status=400)
    return _json_response(result, ok=result.get("returncode", 0) == 0)


def _build_app(context: RunContext) -> web.Application:
    app = web.Application()
    app["context"] = context
    app.router.add_get("/", _index)
    app.router.add_get("/healthz", _health)
    app.router.add_get("/api/overview", _api_overview)
    app.router.add_get("/api/nodes", _api_nodes)
    app.router.add_get("/api/pods", _api_pods)
    app.router.add_get("/api/services", _api_services)
    app.router.add_get("/api/events", _api_events)
    app.router.add_get("/api/system", _api_system)
    app.router.add_get("/api/evidence", _api_evidence)
    app.router.add_get("/api/evidence/content", _api_evidence_content)
    app.router.add_get("/api/pods/{pod}/{mode:protocols|routes|sniff}", _api_probe)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Live academic showcase for SEED K3s runs")
    parser.add_argument("--profile", default="real_topology_rr")
    parser.add_argument("--run-id", default="latest")
    parser.add_argument("--namespace", default="")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SEED_SHOWCASE_PORT", "8088")))
    args = parser.parse_args()

    _ensure_kubeconfig()

    base_dir, resolved_run_id = _resolve_run_dir(args.profile, args.run_id)
    context = RunContext(
        profile=args.profile,
        run_id=resolved_run_id,
        base_dir=base_dir,
        namespace_override=args.namespace,
    )

    print("=" * 72)
    print("SEED K3s Academic Showcase")
    print("=" * 72)
    print(f"Profile:   {context.profile}")
    print(f"Run ID:    {context.run_id}")
    print(f"Run Dir:   {_relative(context.base_dir)}")
    print(f"Namespace: {context.namespace or '(unresolved)'}")
    print(f"URL:       http://{args.host if args.host != '0.0.0.0' else '127.0.0.1'}:{args.port}/")
    print("")
    print("Live panels:")
    print("  - cluster/node/pod resource usage")
    print("  - BGP / RR evidence summary")
    print("  - live bird protocols / route table / packet sample")
    print("  - evidence file index")

    app = _build_app(context)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
