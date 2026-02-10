from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .artifacts import ArtifactManager
from .jobs import JobManager
from .playbooks import SUPPORTED_ACTIONS, SUPPORTED_PLAYBOOK_VERSION, parse_playbook_yaml
from .store import SeedOpsStore
from .workspaces import WorkspaceManager
from .ops import OpsService


class SeedOpsServices:
    def __init__(self):
        cfg = load_config(require_token=False)
        self.config = cfg
        os.makedirs(cfg.data_dir, exist_ok=True)
        self.store = SeedOpsStore(cfg.db_path)
        self.workspaces = WorkspaceManager(store=self.store)
        self.ops = OpsService(store=self.store, workspaces=self.workspaces)
        self.artifacts = ArtifactManager(base_dir=cfg.data_dir, store=self.store)
        self.jobs = JobManager(store=self.store, workspaces=self.workspaces, ops=self.ops, artifacts=self.artifacts)


_services: SeedOpsServices | None = None


def get_services() -> SeedOpsServices:
    global _services
    if _services is None:
        _services = SeedOpsServices()
    return _services


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def register_tools(mcp: FastMCP, services: SeedOpsServices | None = None) -> None:
    """Register SeedOps Phase 1 tools on a FastMCP instance."""
    svcs = services or get_services()

    tool_names = [
        "seedops_capabilities",
        "workspace_create",
        "workspace_list",
        "workspace_get",
        "workspace_attach_compose",
        "workspace_attach_labels",
        "workspace_refresh",
        "events_list",
        "inventory_list_nodes",
        "inventory_get_node",
        "ops_exec",
        "ops_logs",
        "routing_bgp_summary",
        "playbook_validate",
        "playbook_run",
        "jobs_list",
        "job_get",
        "job_steps_list",
        "job_cancel",
        "collector_start",
        "snapshots_list",
        "artifacts_list",
        "artifact_read",
        "artifact_read_chunk",
        "maintenance_prune_workspace",
    ]

    def _audit_error(workspace_id: str, *, tool: str, error: Exception, data: dict[str, Any] | None = None) -> None:
        try:
            # Only write an audit event if the workspace exists.
            if svcs.workspaces.get(workspace_id) is None:
                return
            svcs.store.insert_event(
                workspace_id,
                level="error",
                event_type="error",
                message=f"{tool} failed: {error}",
                data={"tool": tool, "error": str(error), **(data or {})},
            )
        except Exception:
            # Never let audit logging break tool execution.
            return

    @mcp.tool()
    def seedops_capabilities() -> str:
        """Return capability metadata for SeedOps clients and planners."""

        return _json(
            {
                "seedops_version": "phase2",
                "playbook_version": SUPPORTED_PLAYBOOK_VERSION,
                "supported_actions": sorted(SUPPORTED_ACTIONS),
                "default_limits": {
                    "timeout_seconds": 30,
                    "parallelism": 20,
                    "max_output_chars": 8000,
                    "artifact_chunk_bytes": 65536,
                },
                "tool_names": tool_names,
            }
        )

    @mcp.tool()
    def workspace_create(name: str) -> str:
        """Create a persistent workspace for operating an existing running simulation."""
        try:
            ws = svcs.workspaces.create(name)
            return _json({"workspace_id": ws.workspace_id, "name": ws.name, "created_at": ws.created_at})
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def workspace_list() -> str:
        """List all workspaces."""
        try:
            items = svcs.workspaces.list()
            return _json(
                {
                    "workspaces": [
                        {
                            "workspace_id": w.workspace_id,
                            "name": w.name,
                            "attach_type": w.attach_type,
                            "updated_at": w.updated_at,
                        }
                        for w in items
                    ]
                }
            )
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def workspace_get(workspace_id: str) -> str:
        """Get workspace metadata including attach configuration."""
        try:
            ws = svcs.workspaces.get(workspace_id)
            if not ws:
                return _json({"error": "not found"})
            return _json(
                {
                    "workspace": {
                        "workspace_id": ws.workspace_id,
                        "name": ws.name,
                        "attach_type": ws.attach_type,
                        "created_at": ws.created_at,
                        "updated_at": ws.updated_at,
                    },
                    "attach_config": ws.attach_config,
                }
            )
        except Exception as e:
            _audit_error(workspace_id, tool="workspace_get", error=e)
            return _json({"error": str(e)})

    @mcp.tool()
    def workspace_attach_compose(workspace_id: str, output_dir: str) -> str:
        """Attach a workspace to a running SEED simulation compiled to docker-compose output_dir."""
        try:
            summary = svcs.workspaces.attach_compose(workspace_id, output_dir)
            return _json({"attached": True, "workspace_id": workspace_id, "inventory_summary": summary})
        except Exception as e:
            _audit_error(workspace_id, tool="workspace_attach_compose", error=e, data={"output_dir": output_dir})
            return _json({"error": str(e)})

    @mcp.tool()
    def workspace_attach_labels(
        workspace_id: str,
        name_regex: str,
        label_prefix: str = "org.seedsecuritylabs.seedemu.meta.",
    ) -> str:
        """Attach a workspace by scanning running Docker containers with a name regex and SEED meta labels."""
        try:
            summary = svcs.workspaces.attach_labels(workspace_id, name_regex=name_regex, label_prefix=label_prefix)
            return _json({"attached": True, "workspace_id": workspace_id, "inventory_summary": summary})
        except Exception as e:
            _audit_error(
                workspace_id,
                tool="workspace_attach_labels",
                error=e,
                data={"name_regex": name_regex, "label_prefix": label_prefix},
            )
            return _json({"error": str(e)})

    @mcp.tool()
    def workspace_refresh(workspace_id: str) -> str:
        """Refresh inventory cache for a workspace by re-scanning the runtime backend."""
        try:
            summary = svcs.workspaces.refresh(workspace_id)
            return _json(summary)
        except Exception as e:
            _audit_error(workspace_id, tool="workspace_refresh", error=e)
            return _json({"error": str(e)})

    @mcp.tool()
    def events_list(workspace_id: str, since_ts: int = 0, limit: int = 200) -> str:
        """List audit events for a workspace."""
        try:
            rows = svcs.workspaces.list_events(workspace_id, since_ts=since_ts, limit=limit)
            return _json(
                {
                    "events": [
                        {
                            "event_id": ev.event_id,
                            "ts": ev.ts,
                            "level": ev.level,
                            "event_type": ev.event_type,
                            "message": ev.message,
                            "data": ev.data,
                        }
                        for ev in rows
                    ]
                }
            )
        except Exception as e:
            _audit_error(workspace_id, tool="events_list", error=e, data={"since_ts": since_ts, "limit": limit})
            return _json({"error": str(e)})

    @mcp.tool()
    def inventory_list_nodes(workspace_id: str, selector: dict = {}) -> str:
        """List nodes in the workspace inventory, optionally filtered by selector."""
        try:
            nodes = svcs.workspaces.list_nodes(workspace_id, selector=selector)
            return _json({"nodes": nodes})
        except Exception as e:
            _audit_error(workspace_id, tool="inventory_list_nodes", error=e, data={"selector": selector})
            return _json({"error": str(e)})

    @mcp.tool()
    def inventory_get_node(workspace_id: str, node_id: str) -> str:
        """Get a single node by node_id (e.g., 'as150/router0')."""
        try:
            node = svcs.workspaces.get_node(workspace_id, node_id)
            if not node:
                return _json({"error": "not found"})
            return _json({"node": node})
        except Exception as e:
            _audit_error(workspace_id, tool="inventory_get_node", error=e, data={"node_id": node_id})
            return _json({"error": str(e)})

    @mcp.tool()
    def ops_exec(
        workspace_id: str,
        selector: dict,
        command: str,
        timeout_seconds: int = 30,
        parallelism: int = 20,
        max_output_chars: int = 8000,
    ) -> str:
        """Execute a shell command across multiple containers selected from inventory."""
        try:
            result = svcs.ops.exec(
                workspace_id,
                selector=selector,
                command=command,
                timeout_seconds=timeout_seconds,
                parallelism=parallelism,
                max_output_chars=max_output_chars,
            )
            return _json(result)
        except Exception as e:
            _audit_error(
                workspace_id,
                tool="ops_exec",
                error=e,
                data={
                    "selector": selector,
                    "command": command,
                    "timeout_seconds": timeout_seconds,
                    "parallelism": parallelism,
                },
            )
            return _json({"error": str(e)})

    @mcp.tool()
    def ops_logs(
        workspace_id: str,
        selector: dict,
        tail: int = 200,
        since_seconds: int = 0,
        parallelism: int = 20,
        max_output_chars: int = 8000,
    ) -> str:
        """Fetch docker logs across multiple containers selected from inventory."""
        try:
            result = svcs.ops.logs(
                workspace_id,
                selector=selector,
                tail=tail,
                since_seconds=since_seconds,
                parallelism=parallelism,
                max_output_chars=max_output_chars,
            )
            return _json(result)
        except Exception as e:
            _audit_error(
                workspace_id,
                tool="ops_logs",
                error=e,
                data={
                    "selector": selector,
                    "tail": tail,
                    "since_seconds": since_seconds,
                    "parallelism": parallelism,
                },
            )
            return _json({"error": str(e)})

    @mcp.tool()
    def routing_bgp_summary(workspace_id: str, selector: dict) -> str:
        """Summarize BGP protocol status for selected router containers (BIRD)."""
        try:
            result = svcs.ops.bgp_summary(workspace_id, selector=selector)
            return _json(result)
        except Exception as e:
            _audit_error(workspace_id, tool="routing_bgp_summary", error=e, data={"selector": selector})
            return _json({"error": str(e)})

    # --------------------------------------------------------------------------
    # Phase 2: Jobs / Playbooks / Collector / Snapshots / Artifacts
    # --------------------------------------------------------------------------

    @mcp.tool()
    def playbook_validate(playbook_yaml: str) -> str:
        """Validate a YAML playbook (Phase 2)."""
        try:
            pb = parse_playbook_yaml(playbook_yaml)
            return _json(
                {
                    "valid": True,
                    "playbook": {
                        "version": pb.version,
                        "name": pb.name,
                        "defaults": pb.defaults,
                        "steps": [
                            {
                                "id": s.step_id,
                                "action": s.action,
                                "save_as": s.save_as,
                                "on_error": s.on_error,
                                "retries": s.retries,
                                "retry_delay_seconds": s.retry_delay_seconds,
                            }
                            for s in pb.steps
                        ],
                    },
                }
            )
        except Exception as e:
            return _json({"valid": False, "error": str(e)})

    @mcp.tool()
    def playbook_run(workspace_id: str, playbook_yaml: str) -> str:
        """Run a YAML playbook as an async job (Phase 2)."""
        try:
            job = svcs.jobs.start_playbook(workspace_id, playbook_yaml=playbook_yaml)
            return _json(
                {
                    "job_id": job.job_id,
                    "workspace_id": job.workspace_id,
                    "kind": job.kind,
                    "name": job.name,
                    "status": job.status,
                    "progress": {"current": job.progress_current, "total": job.progress_total},
                    "created_at": job.created_at,
                }
            )
        except Exception as e:
            _audit_error(workspace_id, tool="playbook_run", error=e)
            return _json({"error": str(e)})

    @mcp.tool()
    def jobs_list(workspace_id: str, status: str = "", limit: int = 50) -> str:
        """List jobs for a workspace (Phase 2)."""
        try:
            rows = svcs.store.list_jobs(workspace_id, status=(status or None), limit=limit)
            return _json(
                {
                    "jobs": [
                        {
                            "job_id": j.job_id,
                            "workspace_id": j.workspace_id,
                            "kind": j.kind,
                            "name": j.name,
                            "status": j.status,
                            "created_at": j.created_at,
                            "started_at": j.started_at,
                            "finished_at": j.finished_at,
                            "progress": {"current": j.progress_current, "total": j.progress_total},
                            "message": j.message,
                            "data": j.data,
                        }
                        for j in rows
                    ]
                }
            )
        except Exception as e:
            _audit_error(workspace_id, tool="jobs_list", error=e, data={"status": status, "limit": limit})
            return _json({"error": str(e)})

    @mcp.tool()
    def job_get(job_id: str) -> str:
        """Get a job by job_id (Phase 2)."""
        try:
            j = svcs.store.get_job(job_id)
            if not j:
                return _json({"error": "not found"})
            return _json(
                {
                    "job": {
                        "job_id": j.job_id,
                        "workspace_id": j.workspace_id,
                        "kind": j.kind,
                        "name": j.name,
                        "status": j.status,
                        "created_at": j.created_at,
                        "started_at": j.started_at,
                        "finished_at": j.finished_at,
                        "progress": {"current": j.progress_current, "total": j.progress_total},
                        "message": j.message,
                        "data": j.data,
                    }
                }
            )
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def job_steps_list(job_id: str, since_step_id: int = 0, limit: int = 200) -> str:
        """List job step events (Phase 2)."""
        try:
            rows = svcs.store.list_job_steps(job_id, since_step_id=since_step_id, limit=limit)
            return _json(
                {
                    "steps": [
                        {
                            "step_id": s.step_id,
                            "ts": s.ts,
                            "level": s.level,
                            "step_index": s.step_index,
                            "step_name": s.step_name,
                            "event_type": s.event_type,
                            "message": s.message,
                            "data": s.data,
                        }
                        for s in rows
                    ]
                }
            )
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def job_cancel(job_id: str) -> str:
        """Cancel a running job (Phase 2)."""
        try:
            ok = svcs.jobs.cancel_job(job_id)
            return _json({"canceled": bool(ok), "job_id": job_id})
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def collector_start(
        workspace_id: str,
        interval_seconds: int = 30,
        selector: dict = {},
        include_bgp_summary: bool = True,
    ) -> str:
        """Start a periodic collector that writes snapshots (Phase 2)."""
        try:
            job = svcs.jobs.start_collector(
                workspace_id,
                interval_seconds=interval_seconds,
                selector=selector,
                include_bgp_summary=include_bgp_summary,
            )
            return _json(
                {
                    "job_id": job.job_id,
                    "workspace_id": job.workspace_id,
                    "kind": job.kind,
                    "status": job.status,
                    "created_at": job.created_at,
                    "interval_seconds": int(interval_seconds),
                }
            )
        except Exception as e:
            _audit_error(workspace_id, tool="collector_start", error=e)
            return _json({"error": str(e)})

    @mcp.tool()
    def snapshots_list(workspace_id: str, snapshot_type: str = "", since_ts: int = 0, limit: int = 200) -> str:
        """List snapshots captured by collectors (Phase 2)."""
        try:
            rows = svcs.store.list_snapshots(
                workspace_id,
                snapshot_type=(snapshot_type or None),
                since_ts=since_ts,
                limit=limit,
            )
            return _json(
                {
                    "snapshots": [
                        {
                            "snapshot_id": s.snapshot_id,
                            "ts": s.ts,
                            "snapshot_type": s.snapshot_type,
                            "data": s.data,
                        }
                        for s in rows
                    ]
                }
            )
        except Exception as e:
            _audit_error(workspace_id, tool="snapshots_list", error=e)
            return _json({"error": str(e)})

    @mcp.tool()
    def artifacts_list(job_id: str, limit: int = 200) -> str:
        """List artifacts produced by a job (Phase 2)."""
        try:
            rows = svcs.store.list_artifacts(job_id, limit=limit)
            return _json(
                {
                    "artifacts": [
                        {
                            "artifact_id": a.artifact_id,
                            "job_id": a.job_id,
                            "workspace_id": a.workspace_id,
                            "name": a.name,
                            "kind": a.kind,
                            "path": a.path,
                            "size_bytes": a.size_bytes,
                            "created_at": a.created_at,
                        }
                        for a in rows
                    ]
                }
            )
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def artifact_read(artifact_id: str, max_chars: int = 8000) -> str:
        """Read an artifact content (Phase 2)."""
        try:
            res = svcs.artifacts.read(artifact_id, max_chars=max_chars)
            if res is None:
                return _json({"error": "not found"})
            return _json(
                {
                    "artifact": {
                        "artifact_id": res.artifact.artifact_id,
                        "job_id": res.artifact.job_id,
                        "workspace_id": res.artifact.workspace_id,
                        "name": res.artifact.name,
                        "kind": res.artifact.kind,
                        "path": res.artifact.path,
                        "size_bytes": res.artifact.size_bytes,
                        "created_at": res.artifact.created_at,
                    },
                    "content": res.content,
                    "truncated": res.truncated,
                }
            )
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def artifact_read_chunk(artifact_id: str, offset: int = 0, max_bytes: int = 65536) -> str:
        """Read an artifact chunk as base64 (Phase 2, remote-friendly)."""
        try:
            res = svcs.artifacts.read_chunk_base64(artifact_id, offset=offset, max_bytes=max_bytes)
            if res is None:
                return _json({"error": "not found"})
            return _json(
                {
                    "artifact": {
                        "artifact_id": res.artifact.artifact_id,
                        "job_id": res.artifact.job_id,
                        "workspace_id": res.artifact.workspace_id,
                        "name": res.artifact.name,
                        "kind": res.artifact.kind,
                        "path": res.artifact.path,
                        "size_bytes": res.artifact.size_bytes,
                        "created_at": res.artifact.created_at,
                    },
                    "encoding": "base64",
                    "offset": res.offset,
                    "bytes_read": res.bytes_read,
                    "file_size": res.file_size,
                    "eof": res.eof,
                    "content_b64": res.content_b64,
                }
            )
        except Exception as e:
            return _json({"error": str(e)})

    @mcp.tool()
    def maintenance_prune_workspace(
        workspace_id: str,
        keep_events: int = 5000,
        keep_snapshots: int = 5000,
        keep_terminal_jobs: int = 200,
    ) -> str:
        """Prune old events/snapshots/jobs/artifacts to control disk usage (Phase 2)."""
        try:
            if svcs.workspaces.get(workspace_id) is None:
                return _json({"error": "workspace not found"})

            job_ids = svcs.store.list_terminal_job_ids_to_prune(workspace_id, keep_last=keep_terminal_jobs)
            artifacts = svcs.store.list_artifacts_for_job_ids(job_ids)
            file_counts = svcs.artifacts.delete_files(artifacts)
            db_counts = svcs.store.delete_jobs_and_related(job_ids)

            events_deleted = svcs.store.prune_events(workspace_id, keep_last=keep_events)
            snapshots_deleted = svcs.store.prune_snapshots(workspace_id, keep_last=keep_snapshots)

            payload = {
                "workspace_id": workspace_id,
                "keep": {
                    "events": int(keep_events),
                    "snapshots": int(keep_snapshots),
                    "terminal_jobs": int(keep_terminal_jobs),
                },
                "deleted": {
                    "events": int(events_deleted),
                    "snapshots": int(snapshots_deleted),
                    "jobs": int(db_counts.get("jobs_deleted", 0)),
                    "job_steps": int(db_counts.get("job_steps_deleted", 0)),
                    "artifacts": int(db_counts.get("artifacts_deleted", 0)),
                    "artifact_files": file_counts,
                },
            }

            svcs.store.insert_event(
                workspace_id,
                level="info",
                event_type="maintenance.prune",
                message="Workspace pruned",
                data=payload,
            )
            return _json(payload)
        except Exception as e:
            _audit_error(workspace_id, tool="maintenance_prune_workspace", error=e)
            return _json({"error": str(e)})
