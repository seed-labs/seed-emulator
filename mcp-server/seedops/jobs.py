from __future__ import annotations

import shlex
import threading
import time
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

    def _summarize_result(self, action: str, result: Any) -> dict[str, Any]:
        if action == "inventory_list_nodes" and isinstance(result, list):
            sample = []
            for n in result[:10]:
                if isinstance(n, dict) and "node_id" in n:
                    sample.append(str(n["node_id"]))
            return {"count": len(result), "sample_node_ids": sample}
        if action in {"ops_exec", "ping", "traceroute", "inject_fault", "capture_evidence"} and isinstance(result, dict):
            summary = self._summarize_exec_like(result)
            if action in {"ping", "traceroute"}:
                summary["dst"] = result.get("dst")
            if action == "ping":
                summary["count"] = result.get("count")
            if action == "inject_fault":
                summary["fault_type"] = result.get("fault_type")
                summary["params"] = result.get("params")
                summary["interface"] = result.get("interface")
            if action == "capture_evidence":
                summary["evidence_type"] = result.get("evidence_type")
            return summary
        if action == "ops_logs" and isinstance(result, dict):
            return {"counts": result.get("counts"), "fail_reasons": result.get("fail_reasons")}
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
            "routing_bgp_summary",
            "ping",
            "traceroute",
            "inject_fault",
            "capture_evidence",
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

                cmd = f"ping -c {count} {shlex.quote(dst)}"
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

                script = f"traceroute -n {shlex.quote(dst)} || tracepath -n {shlex.quote(dst)}"
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
                interface = str(step_args.get("interface") or "eth0").strip() or "eth0"

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
                return {"fault_type": fault_type, "params": params, "interface": interface, **res}

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
                    parts.append("birdc show protocol 2>/dev/null || echo 'No BIRD'")
                    parts.append("echo ''")
                    parts.append("echo '=== BGP ROUTES ==='")
                    parts.append("birdc 'show route' 2>/dev/null || echo 'No BIRD'")

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
                inv_summary = self._workspaces.refresh(workspace_id)
                inv_snapshot_id = self._store.insert_snapshot(
                    workspace_id,
                    snapshot_type="inventory_summary",
                    data={"job_id": job_id, "tick": tick, **inv_summary},
                )

                bgp_snapshot_id = None
                if include_bgp_summary:
                    bgp = self._ops.bgp_summary(workspace_id, selector=selector)
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
