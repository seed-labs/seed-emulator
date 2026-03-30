#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


@dataclass(frozen=True)
class ComposeBaseline:
    compose_dir: str
    deployment_log_path: str
    deployment_summary_path: str
    compose_file_path: str
    deploy_date: str
    host: dict[str, Any]
    images_count: int | None
    services_count: int | None
    containers_running: int | None
    containers_exited: int | None
    containers_total: int | None
    networks_declared: str
    timeline_events: list[dict[str, str]]
    estimated_total_minutes: int | None
    known_issues: list[str]
    compose_yaml_counts: dict[str, Any]


def _parse_compose_deployment_log(text: str) -> dict[str, Any]:
    deploy_date = ""
    host: dict[str, Any] = {}
    images_count: int | None = None
    services_count: int | None = None
    containers_running: int | None = None
    containers_exited: int | None = None
    containers_total: int | None = None
    networks_declared = ""

    m = re.search(r"部署时间:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    if m:
        deploy_date = m.group(1)

    m = re.search(r"主机:\s*([^\(\n]+)\s*\((\d+)\s*核\s*CPU,\s*([0-9]+)GB\s*内存\)", text)
    if m:
        host = {
            "name": m.group(1).strip(),
            "cpu_cores": _safe_int(m.group(2)),
            "memory_gb": _safe_int(m.group(3)),
        }

    m = re.search(r"镜像数量:\s*(\d+)", text)
    if m:
        images_count = _safe_int(m.group(1))

    m = re.search(r"服务数量:\s*(\d+)", text)
    if m:
        services_count = _safe_int(m.group(1))

    m = re.search(r"运行中:\s*(\d+)\s*容器", text)
    if m:
        containers_running = _safe_int(m.group(1))

    m = re.search(r"已退出:\s*(\d+)\s*容器", text)
    if m:
        containers_exited = _safe_int(m.group(1))

    m = re.search(r"总计:\s*(\d+)\s*容器", text)
    if m:
        containers_total = _safe_int(m.group(1))

    m = re.search(r"创建网络数量:\s*([^\n]+)", text)
    if m:
        networks_declared = m.group(1).strip()

    events: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        m = re.match(r"\[(\d{2}:\d{2}:\d{2})\]\s*(.+)$", line)
        if not m:
            continue
        events.append({"time": m.group(1), "event": m.group(2).strip()})

    estimated_total_minutes: int | None = None
    start_ts = next((e["time"] for e in events if "开始部署" in e["event"]), "")
    end_ts = next((e["time"] for e in events if "部署完成" in e["event"]), "")
    if start_ts and end_ts:
        try:
            start = datetime.strptime(start_ts, "%H:%M:%S")
            end = datetime.strptime(end_ts, "%H:%M:%S")
            delta = end - start
            estimated_total_minutes = int(delta.total_seconds() // 60)
        except Exception:
            estimated_total_minutes = None

    known_issues: list[str] = []
    if "systemd cgroup 超时" in text:
        known_issues.append("systemd/cgroup timeout caused by too many simultaneous container starts -> use batched startup (100 at a time, 10s interval)")
    if "docker compose build --parallel 超时" in text:
        known_issues.append("compose parallel build timeout -> warm caches first and build in batches")

    return {
        "deploy_date": deploy_date,
        "host": host,
        "images_count": images_count,
        "services_count": services_count,
        "containers_running": containers_running,
        "containers_exited": containers_exited,
        "containers_total": containers_total,
        "networks_declared": networks_declared,
        "timeline_events": events,
        "estimated_total_minutes": estimated_total_minutes,
        "known_issues": known_issues,
    }


def _load_compose_baseline(compose_dir: Path) -> ComposeBaseline:
    log_path = compose_dir / "deployment_record" / "logs" / "deployment.log"
    summary_path = compose_dir / "deployment_record" / "SUMMARY.md"
    compose_file_path = compose_dir / "output" / "docker-compose.yml"

    parsed = _parse_compose_deployment_log(_read_text(log_path))

    compose_yaml_counts: dict[str, Any] = {}
    if compose_file_path.exists():
        try:
            loaded = yaml.safe_load(compose_file_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                services = loaded.get("services", {})
                networks = loaded.get("networks", {})
                compose_yaml_counts = {
                    "file_mtime": datetime.fromtimestamp(compose_file_path.stat().st_mtime, tz=timezone.utc).isoformat(),
                    "services": len(services) if isinstance(services, dict) else None,
                    "networks": len(networks) if isinstance(networks, dict) else None,
                }
        except Exception:
            compose_yaml_counts = {}

    return ComposeBaseline(
        compose_dir=str(compose_dir),
        deployment_log_path=str(log_path),
        deployment_summary_path=str(summary_path),
        compose_file_path=str(compose_file_path),
        deploy_date=str(parsed.get("deploy_date", "")),
        host=parsed.get("host", {}) if isinstance(parsed.get("host"), dict) else {},
        images_count=parsed.get("images_count"),
        services_count=parsed.get("services_count"),
        containers_running=parsed.get("containers_running"),
        containers_exited=parsed.get("containers_exited"),
        containers_total=parsed.get("containers_total"),
        networks_declared=str(parsed.get("networks_declared", "")),
        timeline_events=parsed.get("timeline_events", []) if isinstance(parsed.get("timeline_events"), list) else [],
        estimated_total_minutes=parsed.get("estimated_total_minutes"),
        known_issues=parsed.get("known_issues", []) if isinstance(parsed.get("known_issues"), list) else [],
        compose_yaml_counts=compose_yaml_counts,
    )


def _discover_k3s_run_dir(repo_root: Path, profile: str) -> Path:
    candidate = repo_root / "output" / "profile_runs" / profile / "latest"
    if candidate.exists():
        return candidate.resolve()
    raise SystemExit(f"cannot find latest run dir: {candidate}")


def _load_k3s_run(run_dir: Path) -> dict[str, Any]:
    summary = _load_json(run_dir / "validation" / "summary.json")
    report = _load_json(run_dir / "report" / "report.json")
    bgp = _load_json(run_dir / "validation" / "bgp_health_summary.json")
    placement = _read_text(run_dir / "validation" / "placement_by_as.tsv")

    return {
        "run_dir": str(run_dir),
        "summary_path": str(run_dir / "validation" / "summary.json"),
        "report_path": str(run_dir / "report" / "report.json"),
        "summary": summary,
        "report": report,
        "bgp_health": bgp,
        "placement_by_as_tsv": placement,
    }


def _fmt_duration(seconds: int | None) -> str:
    if not seconds:
        return "-"
    minutes = seconds // 60
    remain = seconds % 60
    if minutes == 0:
        return f"{remain}s"
    return f"{minutes}m{remain:02d}s"


def _render_markdown(
    *,
    generated_at: str,
    compose: ComposeBaseline,
    k3s: dict[str, Any],
    compare_json_path: Path,
) -> str:
    k3s_summary = k3s.get("summary", {}) if isinstance(k3s.get("summary"), dict) else {}
    k3s_report = k3s.get("report", {}) if isinstance(k3s.get("report"), dict) else {}

    profile = str(k3s_summary.get("profile", k3s_report.get("profile_id", "")) or "")
    namespace = str(k3s_summary.get("namespace", k3s_report.get("namespace", "")) or "")
    topology_size = _safe_int(k3s_summary.get("topology_size"))
    expected_nodes = _safe_int(k3s_summary.get("expected_nodes"))
    nodes_used = _safe_int(k3s_summary.get("nodes_used", k3s_report.get("nodes_used")))

    build_s = _safe_int(k3s_summary.get("build_duration_seconds", k3s_report.get("build_duration_seconds")))
    up_s = _safe_int(k3s_summary.get("up_duration_seconds", k3s_report.get("up_duration_seconds")))
    phase_s = _safe_int(k3s_summary.get("phase_start_duration_seconds", k3s_report.get("phase_start_duration_seconds")))
    start_bird_s = _safe_int(k3s_summary.get("start_bird_duration_seconds", k3s_report.get("start_bird_duration_seconds")))
    start_kernel_s = _safe_int(
        k3s_summary.get("start_kernel_duration_seconds", k3s_report.get("start_kernel_duration_seconds"))
    )
    verify_s = _safe_int(k3s_summary.get("validation_duration_seconds", k3s_report.get("validation_duration_seconds")))
    pipeline_s = _safe_int(k3s_summary.get("pipeline_duration_seconds", k3s_report.get("pipeline_duration_seconds")))

    compose_total = compose.estimated_total_minutes
    compose_total_str = f"{compose_total} min" if compose_total is not None else "about 1h 45m (from deployment log)"

    compose_yaml_note = ""
    if compose.compose_yaml_counts:
        yaml_services = compose.compose_yaml_counts.get("services")
        yaml_networks = compose.compose_yaml_counts.get("networks")
        yaml_mtime = compose.compose_yaml_counts.get("file_mtime", "")
        compose_yaml_note = (
            f"- Current compose file: `services={yaml_services}`, `networks={yaml_networks}` (mtime: `{yaml_mtime}`)\n"
        )
        if compose.services_count and yaml_services and int(compose.services_count) != int(yaml_services):
            compose_yaml_note += (
                f"  - Note: `deployment.log` recorded `{compose.services_count}` services, which no longer matches the current compose file; "
                "the compose file in that directory may have been regenerated later.\n"
            )

    k3s_os_host = str(k3s_report.get("host_os", "") or "")
    k3s_container_base = str(k3s_report.get("container_base_image", "") or "")
    image_distribution = str(k3s_report.get("image_distribution_mode", k3s_summary.get("image_distribution_mode", "")) or "")

    known_issues = compose.known_issues or ["No explicit legacy issue markers were parsed from the compose log."]

    return f"""# Historical Docker Compose vs Current K3s+KVM

Generated at: `{generated_at}`

This report does two things:

1. Reconstruct the historical large-scale Docker Compose path from evidence.
2. Map the current K3s+KVM workflow onto the same pipeline so the runtime and
   operational differences are easy to compare.

Quick summary:

- Historical Compose scaling relied on **batched startup** to avoid systemd and cgroup startup failures.
- The maintained K3s path relies on an explicit **evidence contract**:
  summary, report, protocol health, connectivity, recovery, resources, and
  relationship artifacts.
- Current K3s run directory: `{k3s.get('run_dir','')}`
- Machine-readable compare artifact: `{compare_json_path}`

```mermaid
flowchart LR
  subgraph Compose[Docker Compose]
    C1[generate compose.yml] --> C2[docker compose build]
    C2 --> C3[docker compose up -d]
    C3 --> C4[batched docker start]
    C4 --> C5[manual docker logs and exec]
  end

  subgraph K3s[K3s plus KVM]
    K1[profile_runner doctor] --> K2[compile -> k8s.yaml]
    K2 --> K3[build_images.sh]
    K3 --> K4[kubectl apply/wait]
    K4 --> K5[start-bird]
    K5 --> K6[start-kernel]
    K6 --> K7[verify: contract artifacts]
    K7 --> K8[showcase: read-only observation]
  end
```

---

## 1. Historical Docker Compose baseline

- Legacy experiment directory: `{compose.compose_dir}`
- Deployment log: `{compose.deployment_log_path}`
- Deployment summary: `{compose.deployment_summary_path}`
{compose_yaml_note.rstrip()}

Key values extracted from `deployment.log`:

- Deploy date: `{compose.deploy_date or '-'}`
- Host: `{compose.host.get('name','-')}` (CPU `{compose.host.get('cpu_cores','-')}` cores / memory `{compose.host.get('memory_gb','-')}` GB)
- Services: `{compose.services_count or '-'}`
- Containers: running `{compose.containers_running or '-'}` / exited `{compose.containers_exited or '-'}` / total `{compose.containers_total or '-'}`
- Images: `{compose.images_count or '-'}`
- Networks declared in log: `{compose.networks_declared or '-'}`
- Total deployment time: `{compose_total_str}`

Legacy issues recorded in the compose evidence:

{os.linesep.join([f'- {issue}' for issue in known_issues])}

---

## 2. Current K3s+KVM evidence

This comparison uses the current K3s run summarized by
`validation/summary.json` and `report/report.json`:

- profile: `{profile}`
- namespace: `{namespace}`
- topology size: `{topology_size if topology_size is not None else '-'}`
- expected nodes: `{expected_nodes if expected_nodes is not None else '-'}`
- nodes used: `{nodes_used if nodes_used is not None else '-'}`
- host OS: `{k3s_os_host or '-'}`
- container base image: `{k3s_container_base or '-'}`
- image distribution mode: `{image_distribution or '-'}`
- stage timing:
  - build: `{_fmt_duration(build_s)}`
  - deploy/up: `{_fmt_duration(up_s)}`
  - start-bird: `{_fmt_duration(start_bird_s)}`
  - start-kernel: `{_fmt_duration(start_kernel_s)}`
  - phase-start (compatibility aggregate): `{_fmt_duration(phase_s)}`
  - verify: `{_fmt_duration(verify_s)}`
  - full pipeline: `{_fmt_duration(pipeline_s)}`

Primary evidence files:

- summary: `{k3s.get('summary_path','')}`
- report: `{k3s.get('report_path','')}`
- BGP health: `{str(Path(k3s.get('run_dir','')) / 'validation' / 'bgp_health_summary.json')}`
- placement by AS: `{str(Path(k3s.get('run_dir','')) / 'validation' / 'placement_by_as.tsv')}`

---

## 3. One-to-one workflow mapping

### 3.1 Pipeline mapping

| Historical Compose | Current K3s workflow | Primary evidence |
|---|---|---|
| generate `compose.yml` | `compile` generates `k8s.yaml` | `output/profile_runs/<profile>/<run>/compiled/` |
| `docker compose build` | `build_images.sh` on the build node | `validation/remote_build.log` |
| `docker compose up -d` | `deploy` (`kubectl apply` + `kubectl wait`) | `validation/apply.log`, `validation/wait.log` |
| manual `start_bird0130.py` | `start-bird` | `validation/start_bird_summary.json` |
| manual `start_bird_kernel.py` | `start-kernel` | `validation/start_kernel_summary.json` |
| compatibility batched startup | `phase-start` | `validation/phased_startup_summary.json` |
| manual `logs/exec` checks | `verify` emits protocol, connectivity, recovery, and resource evidence | `validation/*.json`, `validation/*.tsv`, `validation/*.txt` |

### 3.2 Why K3s uses explicit phases

The Compose path used batched startup to avoid “too many services start at
once -> systemd/cgroup timeout”.

The maintained K3s path splits startup into three layers:

1. Kubernetes brings Pods up (`deploy`)
2. The runner starts `bird` (`start-bird`)
3. The runner switches the kernel-export stage (`start-kernel`)

That keeps failure triage clearer:

- `deploy` fails -> inspect scheduling, image distribution, registry, and CNI
- `start-bird` fails -> inspect BIRD startup
- `start-kernel` fails -> inspect kernel export switching
- `verify` fails -> inspect which required evidence artifact failed or went missing

---

## 4. What the K3s path improves next

The old Compose pain points become the K3s improvement checklist:

1. **Startup pressure**: keep protocol startup explicit and parameterizable.
2. **Image distribution**: keep both `registry` and `preload` modes available
   and make registry failures easier to classify.
3. **Verification cost**: prefer structured evidence over manual log-only
   inspection.
4. **Migration**: move environment-specific values into cluster inventory so
   the workflow shape stays stable across KVM and future physical clusters.

---

## 5. Minimum commands

Current K3s path:

```bash
cd <repo_root>
source scripts/env_seedemu.sh
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale compile
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale build
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale deploy
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale start-bird
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale start-kernel
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale verify
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale report
```

If you only want the evidence:

```bash
cat output/profile_runs/real_topology_rr_scale/latest/validation/summary.json
```

Historical Compose reference path:

```bash
cd <compose_root>
./run_workflow.sh
```

---

## 6. Regenerate this compare report

```bash
cd <repo_root>
python3 scripts/seed_k8s_compare_with_compose.py \\
  --compose-dir <compose_root> \\
  --profile real_topology_rr_scale
```

It writes into `output/compare/compose_vs_k3s/latest/`:

- `compare.json` (machine-readable)
- `compare.md` (human-readable)

"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare historical docker-compose baseline with current K3s artifacts.")
    parser.add_argument("--compose-dir", default="~/lxl_topology/autocoder_test")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile", default="real_topology_rr_scale")
    parser.add_argument("--k3s-run-dir", default="")
    parser.add_argument("--output-root", default="output/compare/compose_vs_k3s")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    compose_dir = Path(os.path.expanduser(args.compose_dir)).resolve()
    k3s_run_dir = Path(os.path.expanduser(args.k3s_run_dir)).resolve() if args.k3s_run_dir else _discover_k3s_run_dir(repo_root, args.profile)

    output_root = (repo_root / args.output_root).resolve()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_dir = output_root / ts
    _ensure_dir(out_dir)

    compose = _load_compose_baseline(compose_dir)
    k3s_run = _load_k3s_run(k3s_run_dir)

    compare = {
        "generated_at": _now(),
        "compose": {
            "compose_dir": compose.compose_dir,
            "deployment_log_path": compose.deployment_log_path,
            "deployment_summary_path": compose.deployment_summary_path,
            "compose_file_path": compose.compose_file_path,
            "deploy_date": compose.deploy_date,
            "host": compose.host,
            "images_count": compose.images_count,
            "services_count": compose.services_count,
            "containers_running": compose.containers_running,
            "containers_exited": compose.containers_exited,
            "containers_total": compose.containers_total,
            "networks_declared": compose.networks_declared,
            "estimated_total_minutes": compose.estimated_total_minutes,
            "timeline_events": compose.timeline_events,
            "known_issues": compose.known_issues,
            "compose_yaml_counts": compose.compose_yaml_counts,
        },
        "k3s": {
            "run_dir": k3s_run.get("run_dir", ""),
            "summary_path": k3s_run.get("summary_path", ""),
            "report_path": k3s_run.get("report_path", ""),
            "summary": k3s_run.get("summary", {}),
            "report": k3s_run.get("report", {}),
        },
    }

    compare_json_path = out_dir / "compare.json"
    compare_md_path = out_dir / "compare.md"
    _write_json(compare_json_path, compare)
    _write_text(compare_md_path, _render_markdown(generated_at=compare["generated_at"], compose=compose, k3s=k3s_run, compare_json_path=compare_json_path))

    latest_link = output_root / "latest"
    try:
        if latest_link.is_symlink() or latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(out_dir, target_is_directory=True)
    except Exception:
        pass

    print(str(compare_md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
