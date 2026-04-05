from __future__ import annotations

import ipaddress
import os
import re
import shlex
import shutil
import subprocess
import selectors as _selectors
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .artifacts import ArtifactManager
from .ops import OpsService
from .playbooks import Playbook, PlaybookStep, SUPPORTED_ON_ERROR, parse_playbook_yaml
from .store import JobRow, SeedOpsStore
from .template import TemplateError, render_value
from .workspaces import WorkspaceManager


def _sleep_interruptible(cancel: threading.Event, seconds: float) -> None:
    deadline = time.monotonic() + float(seconds)
    while True:
        if cancel.is_set():
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.2, remaining))


def _validate_prefix(prefix: str) -> str:
    text = str(prefix or "").strip()
    if not text:
        raise ValueError("prefix must be non-empty.")
    try:
        net = ipaddress.ip_network(text, strict=False)
    except Exception as exc:
        raise ValueError(f"Invalid prefix: {text!r}") from exc
    return str(net)


def _sanitize_hijack_tag(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "seedops_hijack"
    tag = re.sub(r"[^a-zA-Z0-9_]", "_", raw)
    tag = re.sub(r"_+", "_", tag).strip("_")
    if not tag:
        tag = "seedops_hijack"
    if not re.match(r"^[A-Za-z_]", tag):
        tag = f"h_{tag}"
    return tag[:63]


def _build_hijack_protocol_block(*, prefix: str, table: str, protocol_id: str) -> str:
    return (
        f"# seedops-bgp-hijack:{protocol_id}:begin\n"
        f"protocol static {protocol_id} {{\n"
        f"    ipv4 {{ table {table}; }};\n"
        f"    route {prefix} blackhole;\n"
        "}\n"
        f"# seedops-bgp-hijack:{protocol_id}:end\n"
    )


def _build_bgp_hijack_command(
    *,
    mode: str,
    prefix: str,
    protocol_id: str,
    table: str,
) -> str:
    conf_path = "/etc/bird/bird.conf"
    begin_marker = f"# seedops-bgp-hijack:{protocol_id}:begin"
    end_marker = f"# seedops-bgp-hijack:{protocol_id}:end"
    tmp_path = "/tmp/bird.conf.seedops.tmp"
    protocol_block = _build_hijack_protocol_block(prefix=prefix, table=table, protocol_id=protocol_id)

    if mode == "announce":
        script = (
            f'CONF="{conf_path}"\n'
            f'BEGIN_MARK={shlex.quote(begin_marker)}\n'
            f'END_MARK={shlex.quote(end_marker)}\n'
            'if ! grep -qF "$BEGIN_MARK" "$CONF"; then\n'
            "cat >> \"$CONF\" <<'EOF_SEEDOPS_BGP_HIJACK'\n"
            f"{protocol_block}"
            "EOF_SEEDOPS_BGP_HIJACK\n"
            "fi\n"
            "birdc configure\n"
            f"birdc \"show route for {prefix} all\" || true\n"
        )
    elif mode == "withdraw":
        script = (
            f'CONF="{conf_path}"\n'
            f'TMP="{tmp_path}"\n'
            f'BEGIN_MARK={shlex.quote(begin_marker)}\n'
            f'END_MARK={shlex.quote(end_marker)}\n'
            'if grep -qF "$BEGIN_MARK" "$CONF"; then\n'
            "awk -v b=\"$BEGIN_MARK\" -v e=\"$END_MARK\" '\n"
            '$0 == b {skip=1; next}\n'
            '$0 == e {skip=0; next}\n'
            '!skip {print}\n'
            "' \"$CONF\" > \"$TMP\" && mv \"$TMP\" \"$CONF\"\n"
            "fi\n"
            "birdc configure || true\n"
            f"birdc \"show route for {prefix} all\" || true\n"
        )
    else:
        raise ValueError(f"unsupported hijack mode: {mode}")

    return f"sh -lc {shlex.quote(script)}"


def _capture_pcap_to_file(
    *,
    container_name: str,
    interface: str,
    duration_seconds: int,
    filter_expr: str,
    out_path: str,
    max_bytes: int,
) -> dict[str, Any]:
    """Capture a PCAP from a container to a local file via `docker exec`.

    This uses tcpdump with `-w -` to write PCAP bytes to stdout, then streams stdout to `out_path`.
    """
    if not shutil.which("docker"):
        raise RuntimeError("docker CLI not found; pcap_capture requires docker CLI.")

    dur = max(1, int(duration_seconds))
    iface = str(interface or "any").strip() or "any"
    filt = str(filter_expr or "").strip()
    max_bytes_i = max(0, int(max_bytes))

    tcpdump_cmd = f"tcpdump -i {shlex.quote(iface)} -U -w -"
    if filt:
        tcpdump_cmd += f" {filt}"
    shell_script = f"command -v timeout >/dev/null 2>&1 && timeout {dur}s {tcpdump_cmd} || {tcpdump_cmd}"

    cmd = ["docker", "exec", str(container_name), "sh", "-lc", shell_script]

    start = time.monotonic()
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    sel = _selectors.DefaultSelector()
    sel.register(proc.stdout, _selectors.EVENT_READ)
    sel.register(proc.stderr, _selectors.EVENT_READ)

    bytes_written = 0
    truncated = False
    timed_out = False
    stderr_buf = bytearray()
    stderr_max = 8192

    def read_chunk(f) -> bytes:
        try:
            return f.read1(4096)  # type: ignore[attr-defined]
        except Exception:
            return f.read(4096)

    with open(out_path, "wb") as out_f:
        try:
            while sel.get_map():
                if (time.monotonic() - start) > float(dur + 10):
                    timed_out = True
                    break

                events = sel.select(timeout=0.1)
                if not events:
                    if proc.poll() is not None:
                        # Drain remaining quickly.
                        for key in list(sel.get_map().values()):
                            chunk = read_chunk(key.fileobj)
                            if not chunk:
                                try:
                                    sel.unregister(key.fileobj)
                                except Exception:
                                    pass
                                continue
                            if key.fileobj is proc.stdout:
                                if max_bytes_i > 0 and bytes_written < max_bytes_i:
                                    remaining = max_bytes_i - bytes_written
                                    out_f.write(chunk[:remaining])
                                    bytes_written += min(len(chunk), remaining)
                                    if len(chunk) > remaining:
                                        truncated = True
                                else:
                                    truncated = True
                            else:
                                if len(stderr_buf) < stderr_max:
                                    remaining = stderr_max - len(stderr_buf)
                                    stderr_buf.extend(chunk[:remaining])
                        continue
                    continue

                for key, _mask in events:
                    chunk = read_chunk(key.fileobj)
                    if not chunk:
                        try:
                            sel.unregister(key.fileobj)
                        except Exception:
                            pass
                        continue

                    if key.fileobj is proc.stdout:
                        if truncated:
                            # Stop reading stdout once we hit the cap; terminate below.
                            continue
                        if max_bytes_i > 0 and bytes_written < max_bytes_i:
                            remaining = max_bytes_i - bytes_written
                            out_f.write(chunk[:remaining])
                            bytes_written += min(len(chunk), remaining)
                            if len(chunk) > remaining:
                                truncated = True
                        else:
                            truncated = True

                        if truncated:
                            break
                    else:
                        if len(stderr_buf) < stderr_max:
                            remaining = stderr_max - len(stderr_buf)
                            stderr_buf.extend(chunk[:remaining])

                if truncated:
                    break
        finally:
            try:
                sel.close()
            except Exception:
                pass

    if timed_out or truncated:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    exit_code = proc.wait() if proc.poll() is None else int(proc.returncode)
    if timed_out and exit_code == 0:
        exit_code = -1

    return {
        "exit_code": int(exit_code),
        "bytes_written": int(bytes_written),
        "truncated": bool(truncated),
        "timed_out": bool(timed_out),
        "stderr_head": stderr_buf.decode("utf-8", errors="replace").strip(),
    }


class JobManager:
    """Background jobs for long-running operations (playbooks, collectors)."""

    def __init__(
        self,
        *,
        store: SeedOpsStore,
        workspaces: WorkspaceManager,
        ops: OpsService,
        artifacts: ArtifactManager,
    ):
        self._store = store
        self._workspaces = workspaces
        self._ops = ops
        self._artifacts = artifacts

        self._lock = threading.RLock()
        self._cancel: dict[str, threading.Event] = {}
        self._threads: dict[str, threading.Thread] = {}

        # Any in-flight jobs are no longer running after a restart.
        self._store.mark_running_jobs_interrupted()

    def _register_thread(self, job_id: str, cancel: threading.Event, thread: threading.Thread) -> None:
        with self._lock:
            self._cancel[job_id] = cancel
            self._threads[job_id] = thread

    def _cleanup_thread(self, job_id: str) -> None:
        with self._lock:
            self._cancel.pop(job_id, None)
            self._threads.pop(job_id, None)

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            ev = self._cancel.get(job_id)
        if ev is None:
            job = self._store.get_job(job_id)
            if job and job.status in {"queued"}:
                self._store.update_job(job_id, status="canceled", finished_at=int(time.time()), message="canceled")
                return True
            return False
        ev.set()
        self._store.update_job(job_id, status="cancel_requested", message="cancel requested")
        return True

    def start_playbook(self, workspace_id: str, *, playbook_yaml: str) -> JobRow:
        playbook = parse_playbook_yaml(playbook_yaml)
        job = self._store.create_job(
            workspace_id,
            kind="playbook",
            name=playbook.name,
            status="queued",
            message="queued",
            data={"version": playbook.version, "name": playbook.name},
            progress_total=len(playbook.steps),
        )
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="job.created",
            message=f"Job created: {playbook.name}",
            data={"job_id": job.job_id, "kind": "playbook", "name": playbook.name},
        )

        cancel = threading.Event()
        thread = threading.Thread(
            target=self._run_playbook_job,
            args=(job.job_id, workspace_id, playbook, cancel),
            daemon=True,
        )
        self._register_thread(job.job_id, cancel, thread)
        thread.start()
        return job

    def start_collector(
        self,
        workspace_id: str,
        *,
        interval_seconds: int = 30,
        selector: dict[str, Any] | None = None,
        include_bgp_summary: bool = True,
    ) -> JobRow:
        sel = selector or {}
        job = self._store.create_job(
            workspace_id,
            kind="collector",
            name="collector",
            status="queued",
            message="queued",
            data={"interval_seconds": int(interval_seconds), "selector": sel, "include_bgp_summary": bool(include_bgp_summary)},
            progress_total=0,
        )
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="collector.created",
            message="Collector created",
            data={"job_id": job.job_id, "interval_seconds": int(interval_seconds), "include_bgp_summary": bool(include_bgp_summary)},
        )

        cancel = threading.Event()
        thread = threading.Thread(
            target=self._run_collector_job,
            args=(job.job_id, workspace_id, int(interval_seconds), sel, bool(include_bgp_summary), cancel),
            daemon=True,
        )
        self._register_thread(job.job_id, cancel, thread)
        thread.start()
        return job

    def _render_default(self, playbook: Playbook, key: str, context: dict[str, Any]) -> Any:
        if key not in playbook.defaults:
            return None
        try:
            return render_value(playbook.defaults.get(key), context)
        except TemplateError as e:
            raise ValueError(f"Template error in defaults.{key}: {e}") from None

    def _effective_selector(
        self,
        playbook: Playbook,
        *,
        step_args: dict[str, Any],
        context: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, bool]:
        # Return (selector, explicitly_provided)
        if "selector" in step_args:
            sel = step_args.get("selector")
            return (sel if isinstance(sel, dict) else None), True

        defaults_sel_raw = playbook.defaults.get("selector")
        if defaults_sel_raw is None:
            return None, False
        try:
            defaults_sel = render_value(defaults_sel_raw, context)
        except TemplateError as e:
            raise ValueError(f"Template error in defaults.selector: {e}") from None
        return (defaults_sel if isinstance(defaults_sel, dict) else None), False

    def _effective_on_error(self, playbook: Playbook, step: PlaybookStep) -> str:
        if step.on_error:
            return step.on_error
        val = playbook.defaults.get("on_error")
        if isinstance(val, str) and val.strip() in SUPPORTED_ON_ERROR:
            return val.strip()
        return "stop"

    def _effective_retries(self, playbook: Playbook, step: PlaybookStep) -> int:
        if step.retries is not None:
            return int(step.retries)
        val = playbook.defaults.get("retries")
        try:
            retries = int(val) if val is not None else 0
        except Exception:
            retries = 0
        return max(0, retries)

    def _effective_retry_delay_seconds(self, playbook: Playbook, step: PlaybookStep) -> float:
        if step.retry_delay_seconds is not None:
            return float(step.retry_delay_seconds)
        val = playbook.defaults.get("retry_delay_seconds")
        try:
            delay = float(val) if val is not None else 1.0
        except Exception:
            delay = 1.0
        return max(0.0, delay)

    def _resolve_fault_interface(self, workspace_id: str, *, selector: dict[str, Any]) -> str:
        try:
            nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
        except Exception:
            return "eth0"
        if not nodes:
            return "eth0"

        preferred_by_node: list[list[str]] = []
        for node in nodes:
            interfaces = node.get("interfaces") or []
            names = [
                str(iface.get("name") or "").strip()
                for iface in interfaces
                if isinstance(iface, dict)
            ]
            names = [name for name in names if name and name != "lo" and not name.startswith("dummy")]
            if names:
                preferred_by_node.append(names)

        if not preferred_by_node:
            return "eth0"

        common = set(preferred_by_node[0])
        for names in preferred_by_node[1:]:
            common &= set(names)
        if common:
            for candidate in preferred_by_node[0]:
                if candidate in common:
                    return candidate
        return preferred_by_node[0][0]

    def _summarize_result(self, action: str, result: Any) -> dict[str, Any]:
        if action == "inventory_list_nodes" and isinstance(result, list):
            sample = []
            for n in result[:10]:
                if isinstance(n, dict) and "node_id" in n:
                    sample.append(str(n["node_id"]))
            return {"count": len(result), "sample_node_ids": sample}
        if action in {
            "ops_exec",
            "ping",
            "traceroute",
            "inject_fault",
            "bgp_announce_prefix",
            "bgp_withdraw_prefix",
            "capture_evidence",
        } and isinstance(result, dict):
            summary = self._summarize_exec_like(result)
            if action in {"ping", "traceroute"}:
                summary["dst"] = result.get("dst")
            if action == "ping":
                summary["count"] = result.get("count")
            if action == "inject_fault":
                summary["fault_type"] = result.get("fault_type")
                summary["params"] = result.get("params")
                summary["interface"] = result.get("interface")
            if action in {"bgp_announce_prefix", "bgp_withdraw_prefix"}:
                summary["prefix"] = result.get("prefix")
                summary["table"] = result.get("table")
                summary["protocol_id"] = result.get("protocol_id")
                summary["mode"] = result.get("mode")
            if action == "capture_evidence":
                summary["evidence_type"] = result.get("evidence_type")
            return summary
        if action == "pcap_capture" and isinstance(result, dict):
            arts = result.get("artifacts") or []
            sample = []
            if isinstance(arts, list):
                for a in arts[:10]:
                    if isinstance(a, dict) and a.get("ok"):
                        sample.append({"node_id": a.get("node_id"), "artifact_id": a.get("artifact_id")})
            return {"counts": result.get("counts"), "sample": sample}
        if action == "ops_logs" and isinstance(result, dict):
            return {"counts": result.get("counts"), "fail_reasons": result.get("fail_reasons")}
        if action in {"routing_protocol_summary", "routing_looking_glass"} and isinstance(result, dict):
            summary = {
                "backend": result.get("backend"),
                "backend_counts": result.get("backend_counts"),
                "counts": result.get("counts"),
            }
            if action == "routing_looking_glass":
                summary["prefix"] = result.get("prefix")
            return summary
        if action == "routing_bgp_summary" and isinstance(result, dict):
            return {"backend": result.get("backend"), "counts": result.get("counts")}
        if action == "sleep" and isinstance(result, dict):
            return result
        if isinstance(result, dict):
            # workspace_refresh is already a compact summary
            return result
        return {"result_type": type(result).__name__}

    def _summarize_exec_like(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "command": result.get("command"),
            "command_hash": result.get("command_hash"),
            "backend": result.get("backend"),
            "counts": result.get("counts"),
            "fail_reasons": result.get("fail_reasons"),
        }

    def _execute_step(
        self,
        workspace_id: str,
        playbook: Playbook,
        step: PlaybookStep,
        *,
        step_args: dict[str, Any],
        cancel: threading.Event,
        context: dict[str, Any],
    ) -> Any:
        action = step.action

        if action == "sleep":
            seconds = float(step_args.get("seconds", 0))
            _sleep_interruptible(cancel, seconds)
            return {"slept_seconds": seconds}

        if cancel.is_set():
            raise RuntimeError("canceled")

        if action == "workspace_refresh":
            return self._workspaces.refresh(workspace_id)

        if action == "inventory_list_nodes":
            sel, explicit = self._effective_selector(playbook, step_args=step_args, context=context)
            if explicit and sel is None:
                raise ValueError("selector must be a dict (use {} to select all).")
            selector = sel or {}
            return self._workspaces.list_nodes(workspace_id, selector=selector)

        if action in {
            "ops_exec",
            "ops_logs",
            "routing_protocol_summary",
            "routing_looking_glass",
            "routing_bgp_summary",
            "ping",
            "traceroute",
            "inject_fault",
            "bgp_announce_prefix",
            "bgp_withdraw_prefix",
            "capture_evidence",
            "pcap_capture",
        }:
            sel, explicit = self._effective_selector(playbook, step_args=step_args, context=context)
            if sel is None and not explicit:
                raise ValueError(f"{action} requires selector via step.selector or defaults.selector (use {{}} to select all).")
            if explicit and sel is None:
                raise ValueError("selector must be a dict (use {} to select all).")
            selector = sel if isinstance(sel, dict) else {}

            if action == "ops_exec":
                command = str(step_args.get("command") or "").strip()
                if not command:
                    raise ValueError("ops_exec requires non-empty command.")
                timeout_seconds = int(step_args.get("timeout_seconds") or self._render_default(playbook, "timeout_seconds", context) or 30)
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 20)
                max_output_chars = int(step_args.get("max_output_chars") or self._render_default(playbook, "max_output_chars", context) or 8000)
                return self._ops.exec(
                    workspace_id,
                    selector=selector,
                    command=command,
                    timeout_seconds=timeout_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )

            if action == "ops_logs":
                tail = int(step_args.get("tail") or self._render_default(playbook, "tail", context) or 200)
                since_seconds = int(step_args.get("since_seconds") or self._render_default(playbook, "since_seconds", context) or 0)
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 20)
                max_output_chars = int(step_args.get("max_output_chars") or self._render_default(playbook, "max_output_chars", context) or 8000)
                return self._ops.logs(
                    workspace_id,
                    selector=selector,
                    tail=tail,
                    since_seconds=since_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )

            if action == "routing_protocol_summary":
                backend = str(step_args.get("backend") or "auto").strip() or "auto"
                return self._ops.routing_protocol_summary(
                    workspace_id,
                    selector=selector,
                    backend=backend,
                )

            if action == "routing_looking_glass":
                backend = str(step_args.get("backend") or "auto").strip() or "auto"
                prefix = str(step_args.get("prefix") or "").strip()
                return self._ops.routing_looking_glass(
                    workspace_id,
                    selector=selector,
                    prefix=prefix,
                    backend=backend,
                )

            if action == "routing_bgp_summary":
                return self._ops.bgp_summary(workspace_id, selector=selector)

            if action == "ping":
                dst = str(step_args.get("dst") or "").strip()
                if not dst:
                    raise ValueError("ping requires non-empty dst.")
                count = int(step_args.get("count") or 4)
                timeout_seconds = int(step_args.get("timeout_seconds") or self._render_default(playbook, "timeout_seconds", context) or 30)
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 20)
                max_output_chars = int(step_args.get("max_output_chars") or self._render_default(playbook, "max_output_chars", context) or 8000)

                script = (
                    f"if command -v ping >/dev/null 2>&1; then "
                    f"ping -c {count} {shlex.quote(dst)}; "
                    "elif command -v busybox >/dev/null 2>&1; then "
                    f"busybox ping -c {count} {shlex.quote(dst)}; "
                    "else echo 'ping command not found'; exit 127; fi"
                )
                cmd = f"sh -lc {shlex.quote(script)}"
                res = self._ops.exec(
                    workspace_id,
                    selector=selector,
                    command=cmd,
                    timeout_seconds=timeout_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )
                return {"dst": dst, "count": count, **res}

            if action == "traceroute":
                dst = str(step_args.get("dst") or "").strip()
                if not dst:
                    raise ValueError("traceroute requires non-empty dst.")
                timeout_seconds = int(step_args.get("timeout_seconds") or self._render_default(playbook, "timeout_seconds", context) or 30)
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 20)
                max_output_chars = int(step_args.get("max_output_chars") or self._render_default(playbook, "max_output_chars", context) or 8000)

                script = (
                    "if command -v traceroute >/dev/null 2>&1; then "
                    f"traceroute -n {shlex.quote(dst)}; "
                    "elif command -v tracepath >/dev/null 2>&1; then "
                    f"tracepath -n {shlex.quote(dst)}; "
                    "elif command -v ping >/dev/null 2>&1; then "
                    f"ping -c 4 {shlex.quote(dst)}; "
                    "elif command -v busybox >/dev/null 2>&1; then "
                    f"busybox ping -c 4 {shlex.quote(dst)}; "
                    "else echo 'traceroute/tracepath/ping command not found'; exit 127; fi"
                )
                cmd = f"sh -lc {shlex.quote(script)}"
                res = self._ops.exec(
                    workspace_id,
                    selector=selector,
                    command=cmd,
                    timeout_seconds=timeout_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )
                return {"dst": dst, **res}

            if action == "inject_fault":
                fault_type = str(step_args.get("fault_type") or "").strip().lower()
                if not fault_type:
                    raise ValueError("inject_fault requires non-empty fault_type.")
                params = str(step_args.get("params") or "").strip()
                interface = str(step_args.get("interface") or "").strip()
                if not interface or interface.lower() == "auto":
                    interface = self._resolve_fault_interface(workspace_id, selector=selector)
                interface = interface or "eth0"

                if fault_type == "packet_loss":
                    percent = params or "10"
                    cmd = f"tc qdisc add dev {shlex.quote(interface)} root netem loss {shlex.quote(percent)}%"
                elif fault_type == "latency":
                    ms = params or "100"
                    cmd = f"tc qdisc add dev {shlex.quote(interface)} root netem delay {shlex.quote(ms)}ms"
                elif fault_type == "bandwidth":
                    rate = params or "1mbit"
                    cmd = (
                        f"tc qdisc add dev {shlex.quote(interface)} root tbf rate {shlex.quote(rate)}"
                        " burst 32kbit latency 400ms"
                    )
                elif fault_type == "kill_process":
                    process = params or "bird"
                    cmd = f"pkill -9 {shlex.quote(process)} 2>/dev/null || echo 'Process not found'"
                elif fault_type == "disconnect":
                    iface = params or interface
                    cmd = f"ip link set {shlex.quote(iface)} down"
                elif fault_type == "reset":
                    cmd = f"tc qdisc del dev {shlex.quote(interface)} root 2>/dev/null || true"
                else:
                    raise ValueError(
                        "Unknown fault_type. Valid: packet_loss, latency, bandwidth, kill_process, disconnect, reset"
                    )

                timeout_seconds = int(step_args.get("timeout_seconds") or self._render_default(playbook, "timeout_seconds", context) or 30)
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 20)
                max_output_chars = int(step_args.get("max_output_chars") or self._render_default(playbook, "max_output_chars", context) or 8000)

                res = self._ops.exec(
                    workspace_id,
                    selector=selector,
                    command=cmd,
                    timeout_seconds=timeout_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )
                if fault_type != "reset" and int((res.get("counts") or {}).get("fail") or 0) > 0:
                    fail_reasons = dict(res.get("fail_reasons") or {})
                    raise RuntimeError(f"inject_fault failed on selected nodes: {fail_reasons}")
                return {"fault_type": fault_type, "params": params, "interface": interface, **res}

            if action in {"bgp_announce_prefix", "bgp_withdraw_prefix"}:
                prefix = _validate_prefix(str(step_args.get("prefix") or ""))
                table = str(step_args.get("table") or "t_direct").strip() or "t_direct"
                # protocol_id is persisted across announce/withdraw steps.
                protocol_id_input = str(step_args.get("protocol_id") or f"seedops_hijack_{prefix.replace('/', '_').replace('.', '_')}").strip()
                protocol_id = _sanitize_hijack_tag(protocol_id_input)
                mode = "announce" if action == "bgp_announce_prefix" else "withdraw"
                cmd = _build_bgp_hijack_command(
                    mode=mode,
                    prefix=prefix,
                    protocol_id=protocol_id,
                    table=table,
                )
                timeout_seconds = int(step_args.get("timeout_seconds") or self._render_default(playbook, "timeout_seconds", context) or 30)
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 20)
                max_output_chars = int(step_args.get("max_output_chars") or self._render_default(playbook, "max_output_chars", context) or 8000)
                res = self._ops.exec(
                    workspace_id,
                    selector=selector,
                    command=cmd,
                    timeout_seconds=timeout_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )
                return {
                    "prefix": prefix,
                    "table": table,
                    "protocol_id": protocol_id,
                    "mode": mode,
                    **res,
                }

            if action == "capture_evidence":
                evidence_type = str(step_args.get("evidence_type") or "").strip().lower()
                if not evidence_type:
                    raise ValueError("capture_evidence requires non-empty evidence_type.")

                parts: list[str] = []

                if evidence_type in {"routing_snapshot", "full"}:
                    parts.append("echo '=== ROUTING TABLE ==='")
                    parts.append("ip route || true")
                    parts.append("echo ''")
                    parts.append("echo '=== BGP STATUS ==='")
                    parts.append(
                        "if command -v birdc >/dev/null 2>&1; then "
                        "birdc show protocols 2>/dev/null || echo 'BIRD unavailable'; "
                        "elif command -v vtysh >/dev/null 2>&1; then "
                        "vtysh -c 'show bgp summary' 2>/dev/null || echo 'FRR unavailable'; "
                        "else echo 'No BIRD/FRR'; fi"
                    )
                    parts.append("echo ''")
                    parts.append("echo '=== BGP ROUTES ==='")
                    parts.append(
                        "if command -v birdc >/dev/null 2>&1; then "
                        "birdc 'show route' 2>/dev/null || echo 'BIRD routes unavailable'; "
                        "elif command -v vtysh >/dev/null 2>&1; then "
                        "vtysh -c 'show bgp ipv4 unicast' 2>/dev/null || vtysh -c 'show bgp' 2>/dev/null || echo 'FRR routes unavailable'; "
                        "else echo 'No BIRD/FRR'; fi"
                    )

                if evidence_type in {"network_state", "full"}:
                    parts.append("echo ''")
                    parts.append("echo '=== INTERFACES ==='")
                    parts.append("ip addr || true")
                    parts.append("echo ''")
                    parts.append("echo '=== ARP TABLE ==='")
                    parts.append("ip neigh || true")
                    parts.append("echo ''")
                    parts.append("echo '=== ACTIVE CONNECTIONS ==='")
                    parts.append("ss -tuln 2>/dev/null || netstat -tuln || true")

                if evidence_type in {"process_list", "full"}:
                    parts.append("echo ''")
                    parts.append("echo '=== PROCESSES ==='")
                    parts.append("ps aux || true")

                if evidence_type in {"logs", "full"}:
                    parts.append("echo ''")
                    parts.append("echo '=== SYSLOG (last 50 lines) ==='")
                    parts.append("tail -50 /var/log/syslog 2>/dev/null || echo 'No syslog'")
                    parts.append("echo ''")
                    parts.append("echo '=== DMESG (last 20 lines) ==='")
                    parts.append("dmesg | tail -20 2>/dev/null || echo 'No dmesg'")

                if not parts:
                    raise ValueError(
                        "Unknown evidence_type. Valid: routing_snapshot, network_state, process_list, logs, full"
                    )

                script = "\n".join(parts)
                cmd = f"sh -lc {shlex.quote(script)}"
                timeout_seconds = int(step_args.get("timeout_seconds") or self._render_default(playbook, "timeout_seconds", context) or 30)
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 20)
                max_output_chars = int(step_args.get("max_output_chars") or self._render_default(playbook, "max_output_chars", context) or 8000)
                res = self._ops.exec(
                    workspace_id,
                    selector=selector,
                    command=cmd,
                    timeout_seconds=timeout_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )
                return {"evidence_type": evidence_type, **res}

            if action == "pcap_capture":
                job_id = str(context.get("job_id") or "").strip()
                if not job_id:
                    raise RuntimeError("job_id missing from context")

                interface = str(step_args.get("interface") or "any").strip() or "any"
                duration_seconds = int(step_args.get("duration_seconds") or 10)
                filter_expr = str(step_args.get("filter") or "").strip()
                max_bytes = int(step_args.get("max_bytes") or (20 * 1024 * 1024))
                parallelism = int(step_args.get("parallelism") or self._render_default(playbook, "parallelism", context) or 5)

                nodes = self._workspaces.list_nodes(workspace_id, selector=selector)
                visibility_getter = getattr(self._workspaces, "get_visibility", None)
                redacted_fields: list[str] = []
                if callable(visibility_getter):
                    try:
                        visibility = visibility_getter(workspace_id)
                        fields = visibility.get("redacted_fields") if isinstance(visibility, dict) else []
                        if isinstance(fields, list):
                            redacted_fields = [str(field) for field in fields if str(field or "").strip()]
                    except Exception:
                        redacted_fields = []

                def worker(node: dict[str, Any]) -> dict[str, Any]:
                    node_id = str(node.get("node_id") or "")
                    cname = str(node.get("container_name") or "")
                    name = f"{step.step_id}_{node_id}"
                    path = self._artifacts.allocate_path(
                        workspace_id=workspace_id,
                        job_id=job_id,
                        name=name,
                        suffix=".pcap",
                    )
                    tmp = Path(str(path) + ".tmp")
                    try:
                        meta = _capture_pcap_to_file(
                            container_name=cname,
                            interface=interface,
                            duration_seconds=int(duration_seconds),
                            filter_expr=filter_expr,
                            out_path=str(tmp),
                            max_bytes=int(max_bytes),
                        )
                        if int(meta.get("bytes_written") or 0) <= 0:
                            try:
                                if tmp.exists():
                                    tmp.unlink()
                            except Exception:
                                pass
                            err = meta.get("stderr_head") or "no data captured"
                            return {
                                "node_id": node_id,
                                "container_name": cname,
                                "ok": False,
                                "error": str(err),
                                "meta": meta,
                            }

                        os.replace(tmp, path)
                        artifact = self._artifacts.register_file(
                            workspace_id=workspace_id,
                            job_id=job_id,
                            name=name,
                            kind="pcap",
                            path=str(path),
                        )
                        return {
                            "node_id": node_id,
                            "container_name": cname,
                            "ok": True,
                            "artifact_id": artifact.artifact_id,
                            "size_bytes": artifact.size_bytes,
                            "name": artifact.name,
                            "meta": meta,
                        }
                    except Exception as e:
                        try:
                            if tmp.exists():
                                tmp.unlink()
                        except Exception:
                            pass
                        try:
                            if path.exists():
                                path.unlink()
                        except Exception:
                            pass
                        return {"node_id": node_id, "container_name": cname, "ok": False, "error": str(e)}

                results: list[dict[str, Any]] = []
                with ThreadPoolExecutor(max_workers=max(1, int(parallelism))) as pool:
                    futs = [pool.submit(worker, n) for n in nodes]
                    for fut in as_completed(futs):
                        results.append(fut.result())

                results.sort(key=lambda r: str(r.get("node_id", "")))
                if redacted_fields:
                    redacted_results: list[dict[str, Any]] = []
                    for row in results:
                        item = dict(row)
                        for field in redacted_fields:
                            item.pop(field, None)
                        redacted_results.append(item)
                    results = redacted_results
                ok = sum(1 for r in results if r.get("ok"))
                fail = len(results) - ok

                payload = {
                    "interface": interface,
                    "duration_seconds": int(duration_seconds),
                    "filter": filter_expr,
                    "max_bytes": int(max_bytes),
                    "counts": {"total": len(results), "ok": ok, "fail": fail},
                    "artifacts": results,
                }
                self._store.insert_event(
                    workspace_id,
                    level="info",
                    event_type="ops.pcap_capture",
                    message=f"pcap_capture ({step.step_id})",
                    data={**payload["counts"], "interface": interface, "duration_seconds": int(duration_seconds), "filter": filter_expr},
                )
                return payload

        raise ValueError(f"Unsupported step action: {action}")

    def _run_playbook_job(self, job_id: str, workspace_id: str, playbook: Playbook, cancel: threading.Event) -> None:
        started_at = int(time.time())
        total = len(playbook.steps)
        self._store.update_job(job_id, status="running", started_at=started_at, progress_total=total, message="running")
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="job.started",
            message=f"Job started: {playbook.name}",
            data={"job_id": job_id, "kind": "playbook", "name": playbook.name},
        )

        try:
            had_errors = False
            context: dict[str, Any] = {
                "workspace_id": workspace_id,
                "job_id": job_id,
                "vars": playbook.vars,
                "playbook": {"version": playbook.version, "name": playbook.name, "defaults": playbook.defaults},
                "steps": {},
            }
            for idx, step in enumerate(playbook.steps, start=1):
                if cancel.is_set():
                    self._store.insert_job_step(
                        job_id,
                        level="warn",
                        step_index=idx,
                        step_name=step.step_id,
                        event_type="job.canceled",
                        message="Canceled",
                        data={},
                    )
                    self._store.update_job(job_id, status="canceled", finished_at=int(time.time()), message="canceled")
                    self._store.insert_event(
                        workspace_id,
                        level="warn",
                        event_type="job.canceled",
                        message=f"Job canceled: {playbook.name}",
                        data={"job_id": job_id},
                    )
                    return

                self._store.insert_job_step(
                    job_id,
                    level="info",
                    step_index=idx,
                    step_name=step.step_id,
                    event_type="step.started",
                    message=f"{step.action} started",
                    data={"action": step.action},
                )

                retries = self._effective_retries(playbook, step)
                delay = self._effective_retry_delay_seconds(playbook, step)
                on_error = self._effective_on_error(playbook, step)

                attempt = 0
                last_error: Exception | None = None
                result: Any | None = None
                while True:
                    if cancel.is_set():
                        raise RuntimeError("canceled")
                    attempt += 1
                    try:
                        context["now_ts"] = int(time.time())
                        context["step"] = {"id": step.step_id, "action": step.action, "index": idx, "attempt": attempt}
                        try:
                            rendered = render_value(step.args, context)
                        except TemplateError as e:
                            raise ValueError(f"Template error in step {step.step_id}: {e}") from None
                        if not isinstance(rendered, dict):
                            raise ValueError(f"Step args must be a dict after templating (step {step.step_id}).")
                        result = self._execute_step(
                            workspace_id,
                            playbook,
                            step,
                            step_args=rendered,
                            cancel=cancel,
                            context=context,
                        )
                        break
                    except Exception as e:
                        last_error = e
                        max_attempts = 1 + int(retries)
                        if attempt >= max_attempts:
                            break
                        self._store.insert_job_step(
                            job_id,
                            level="warn",
                            step_index=idx,
                            step_name=step.step_id,
                            event_type="step.retry",
                            message=str(e),
                            data={"action": step.action, "attempt": attempt, "max_attempts": max_attempts, "delay_seconds": delay},
                        )
                        _sleep_interruptible(cancel, delay)

                if result is None and last_error is not None:
                    had_errors = True
                    context["steps"][step.step_id] = {
                        "action": step.action,
                        "ok": False,
                        "error": str(last_error),
                        "attempts": attempt,
                    }
                    self._store.insert_job_step(
                        job_id,
                        level="error",
                        step_index=idx,
                        step_name=step.step_id,
                        event_type="step.failed",
                        message=str(last_error),
                        data={"action": step.action, "attempts": attempt, "retries": retries, "on_error": on_error},
                    )

                    if on_error != "continue":
                        raise last_error

                    # Continue to next step, but still update job progress.
                    self._store.update_job(
                        job_id,
                        progress_current=idx,
                        message=f"{step.step_id} failed (continuing) ({idx}/{total})",
                    )
                    continue

                assert result is not None
                summary = self._summarize_result(step.action, result)

                artifact_id = None
                if step.save_as:
                    try:
                        rendered_name = render_value(step.save_as, context)
                    except TemplateError as e:
                        raise ValueError(f"Template error in save_as for step {step.step_id}: {e}") from None
                    name_s = str(rendered_name).strip()
                    if not name_s:
                        raise ValueError(f"save_as resolved to empty name for step {step.step_id}.")
                    artifact = self._artifacts.write_json(
                        workspace_id=workspace_id,
                        job_id=job_id,
                        name=name_s,
                        data=result,
                    )
                    artifact_id = artifact.artifact_id

                context["steps"][step.step_id] = {
                    "action": step.action,
                    "ok": True,
                    "summary": summary,
                    "artifact_id": artifact_id,
                    "attempts": attempt,
                }
                self._store.insert_job_step(
                    job_id,
                    level="info",
                    step_index=idx,
                    step_name=step.step_id,
                    event_type="step.finished",
                    message=f"{step.action} finished",
                    data={"action": step.action, "summary": summary, "artifact_id": artifact_id},
                )

                self._store.update_job(
                    job_id,
                    progress_current=idx,
                    message=f"{step.step_id} ({idx}/{total})",
                )

            finished_at = int(time.time())
            final_status = "succeeded_with_errors" if had_errors else "succeeded"
            self._store.update_job(job_id, status=final_status, finished_at=finished_at, message=final_status)
            self._store.insert_event(
                workspace_id,
                level="info",
                event_type="job.succeeded" if final_status == "succeeded" else "job.succeeded_with_errors",
                message=f"Job {final_status}: {playbook.name}",
                data={"job_id": job_id},
            )
        except Exception as e:
            self._store.insert_job_step(
                job_id,
                level="error",
                step_index=int(self._store.get_job(job_id).progress_current if self._store.get_job(job_id) else 0),
                step_name="error",
                event_type="job.failed",
                message=str(e),
                data={"error": str(e)},
            )
            self._store.update_job(job_id, status="failed", finished_at=int(time.time()), message=str(e))
            self._store.insert_event(
                workspace_id,
                level="error",
                event_type="job.failed",
                message=f"Job failed: {playbook.name}",
                data={"job_id": job_id, "error": str(e)},
            )
        finally:
            self._cleanup_thread(job_id)

    def _run_collector_job(
        self,
        job_id: str,
        workspace_id: str,
        interval_seconds: int,
        selector: dict[str, Any],
        include_bgp_summary: bool,
        cancel: threading.Event,
    ) -> None:
        started_at = int(time.time())
        self._store.update_job(job_id, status="running", started_at=started_at, message="running")
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="collector.started",
            message="Collector started",
            data={"job_id": job_id, "interval_seconds": int(interval_seconds)},
        )

        tick = 0
        try:
            while not cancel.is_set():
                tick += 1
                inv_summary = self._workspaces.refresh(workspace_id, redacted=True)
                inv_snapshot_id = self._store.insert_snapshot(
                    workspace_id,
                    snapshot_type="inventory_summary",
                    data={"job_id": job_id, "tick": tick, **inv_summary},
                )

                bgp_snapshot_id = None
                if include_bgp_summary:
                    bgp = self._ops.routing_protocol_summary(workspace_id, selector=selector, backend="auto")
                    bgp_snapshot_id = self._store.insert_snapshot(
                        workspace_id,
                        snapshot_type="bgp_summary_counts",
                        data={"job_id": job_id, "tick": tick, **(bgp.get("counts") or {}), "backend": bgp.get("backend")},
                    )

                self._store.insert_job_step(
                    job_id,
                    level="info",
                    step_index=tick,
                    step_name="tick",
                    event_type="collector.tick",
                    message="collector tick",
                    data={"inventory_snapshot_id": inv_snapshot_id, "bgp_snapshot_id": bgp_snapshot_id},
                )
                self._store.update_job(job_id, message=f"tick {tick}")
                _sleep_interruptible(cancel, float(interval_seconds))

            self._store.update_job(job_id, status="canceled", finished_at=int(time.time()), message="stopped")
            self._store.insert_event(
                workspace_id,
                level="info",
                event_type="collector.stopped",
                message="Collector stopped",
                data={"job_id": job_id},
            )
        except Exception as e:
            self._store.insert_job_step(
                job_id,
                level="error",
                step_index=tick,
                step_name="tick",
                event_type="collector.error",
                message=str(e),
                data={"error": str(e)},
            )
            self._store.update_job(job_id, status="failed", finished_at=int(time.time()), message=str(e))
            self._store.insert_event(
                workspace_id,
                level="error",
                event_type="collector.failed",
                message="Collector failed",
                data={"job_id": job_id, "error": str(e)},
            )
        finally:
            self._cleanup_thread(job_id)
