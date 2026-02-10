from __future__ import annotations

import threading
import time
from typing import Any

from .artifacts import ArtifactManager
from .ops import OpsService
from .playbooks import Playbook, PlaybookStep, parse_playbook_yaml
from .store import JobRow, SeedOpsStore
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

    def _effective_selector(self, playbook: Playbook, step: PlaybookStep) -> tuple[dict[str, Any] | None, bool]:
        # Return (selector, explicitly_provided)
        if "selector" in step.args:
            sel = step.args.get("selector")
            return (sel if isinstance(sel, dict) else None), True
        defaults_sel = playbook.defaults.get("selector")
        if isinstance(defaults_sel, dict):
            return defaults_sel, False
        return None, False

    def _summarize_result(self, action: str, result: Any) -> dict[str, Any]:
        if action == "inventory_list_nodes" and isinstance(result, list):
            sample = []
            for n in result[:10]:
                if isinstance(n, dict) and "node_id" in n:
                    sample.append(str(n["node_id"]))
            return {"count": len(result), "sample_node_ids": sample}
        if action == "ops_exec" and isinstance(result, dict):
            return {
                "command": result.get("command"),
                "command_hash": result.get("command_hash"),
                "backend": result.get("backend"),
                "counts": result.get("counts"),
                "fail_reasons": result.get("fail_reasons"),
            }
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

    def _execute_step(self, workspace_id: str, playbook: Playbook, step: PlaybookStep, cancel: threading.Event) -> Any:
        action = step.action

        if action == "sleep":
            seconds = float(step.args.get("seconds", 0))
            _sleep_interruptible(cancel, seconds)
            return {"slept_seconds": seconds}

        if cancel.is_set():
            raise RuntimeError("canceled")

        if action == "workspace_refresh":
            return self._workspaces.refresh(workspace_id)

        if action == "inventory_list_nodes":
            sel, _explicit = self._effective_selector(playbook, step)
            selector = sel or {}
            return self._workspaces.list_nodes(workspace_id, selector=selector)

        if action in {"ops_exec", "ops_logs", "routing_bgp_summary"}:
            sel, explicit = self._effective_selector(playbook, step)
            if sel is None and not explicit:
                raise ValueError(f"{action} requires selector via step.selector or defaults.selector (use {{}} to select all).")
            selector = sel if isinstance(sel, dict) else {}

            if action == "ops_exec":
                command = str(step.args.get("command") or "").strip()
                if not command:
                    raise ValueError("ops_exec requires non-empty command.")
                timeout_seconds = int(step.args.get("timeout_seconds") or playbook.defaults.get("timeout_seconds") or 30)
                parallelism = int(step.args.get("parallelism") or playbook.defaults.get("parallelism") or 20)
                max_output_chars = int(step.args.get("max_output_chars") or playbook.defaults.get("max_output_chars") or 8000)
                return self._ops.exec(
                    workspace_id,
                    selector=selector,
                    command=command,
                    timeout_seconds=timeout_seconds,
                    parallelism=parallelism,
                    max_output_chars=max_output_chars,
                )

            if action == "ops_logs":
                tail = int(step.args.get("tail") or playbook.defaults.get("tail") or 200)
                since_seconds = int(step.args.get("since_seconds") or playbook.defaults.get("since_seconds") or 0)
                parallelism = int(step.args.get("parallelism") or playbook.defaults.get("parallelism") or 20)
                max_output_chars = int(step.args.get("max_output_chars") or playbook.defaults.get("max_output_chars") or 8000)
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

                result = self._execute_step(workspace_id, playbook, step, cancel)
                summary = self._summarize_result(step.action, result)

                artifact_id = None
                if step.save_as:
                    artifact = self._artifacts.write_json(
                        workspace_id=workspace_id,
                        job_id=job_id,
                        name=step.save_as,
                        data=result,
                    )
                    artifact_id = artifact.artifact_id

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
            self._store.update_job(job_id, status="succeeded", finished_at=finished_at, message="succeeded")
            self._store.insert_event(
                workspace_id,
                level="info",
                event_type="job.succeeded",
                message=f"Job succeeded: {playbook.name}",
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

