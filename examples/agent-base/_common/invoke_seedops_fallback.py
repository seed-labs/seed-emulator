#!/usr/bin/env python
"""Run deterministic SeedOps fallback flows for agent-base scenarios."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from mcp.client.session_group import ClientSessionGroup, StreamableHttpParameters


TERMINAL_STATUSES = {"succeeded", "succeeded_with_errors", "failed", "canceled", "interrupted"}


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(name or "").strip())
    return cleaned or "artifact"


class SeedOpsSession:
    def __init__(self, *, url: str, token: str):
        self.url = url
        self.token = token
        self.group: ClientSessionGroup | None = None

    async def __aenter__(self) -> "SeedOpsSession":
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        params = StreamableHttpParameters(url=self.url, headers=headers)
        self.group = ClientSessionGroup()
        await self.group.__aenter__()
        await self.group.connect_to_server(params)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.group is not None:
            await self.group.__aexit__(exc_type, exc, tb)
            self.group = None

    async def call_json(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.group is None:
            raise RuntimeError("SeedOps session is not connected")
        result = await self.group.call_tool(tool_name, arguments=arguments)
        texts: list[str] = []
        for item in getattr(result, "content", []) or []:
            if getattr(item, "type", "") == "text":
                texts.append(getattr(item, "text", ""))
        if not texts:
            raise RuntimeError(f"{tool_name} returned no text content")
        raw = "\n".join(texts).strip()
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise RuntimeError(f"{tool_name} returned non-JSON output: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"{tool_name} returned non-object JSON")
        if payload.get("error"):
            raise RuntimeError(f"{tool_name} failed: {payload['error']}")
        return payload


async def _ensure_workspace(api: SeedOpsSession, workspace_name: str) -> str:
    rows = (await api.call_json("workspace_list", {})).get("workspaces", [])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("name") == workspace_name:
                return str(row.get("workspace_id"))
    created = await api.call_json("workspace_create", {"name": workspace_name})
    workspace_id = str(created.get("workspace_id") or "")
    if not workspace_id:
        raise RuntimeError("workspace_create did not return workspace_id")
    return workspace_id


async def _follow_job(
    api: SeedOpsSession,
    *,
    job_id: str,
    poll_seconds: float,
    timeout_seconds: float,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    deadline = time.monotonic() + max(1.0, float(timeout_seconds))
    while True:
        job_res = await api.call_json("job_get", {"job_id": job_id})
        status = str(((job_res.get("job") or {}).get("status")) or "")
        if status in TERMINAL_STATUSES:
            steps = await api.call_json("job_steps_list", {"job_id": job_id, "since_step_id": 0, "limit": 200})
            return status, job_res, steps
        if time.monotonic() > deadline:
            raise TimeoutError(f"job follow timed out for job_id={job_id}, status={status}")
        await asyncio.sleep(max(0.1, float(poll_seconds)))


async def _download_artifact(
    api: SeedOpsSession,
    *,
    artifact_id: str,
    out_path: Path,
    chunk_bytes: int,
) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    offset = 0
    bytes_written = 0
    with out_path.open("wb") as f:
        while True:
            chunk = await api.call_json(
                "artifact_read_chunk",
                {
                    "artifact_id": artifact_id,
                    "offset": int(offset),
                    "max_bytes": int(chunk_bytes),
                },
            )
            data = base64.b64decode(str(chunk.get("content_b64") or "").encode("ascii")) if chunk.get("content_b64") else b""
            if data:
                f.write(data)
                bytes_written += len(data)
            read_n = int(chunk.get("bytes_read") or len(data))
            offset += max(0, read_n)
            if bool(chunk.get("eof")):
                break
            if read_n <= 0:
                raise RuntimeError("artifact_read_chunk returned zero bytes without eof=true")
    return {
        "artifact_id": artifact_id,
        "out_path": str(out_path),
        "bytes_written": int(bytes_written),
    }


async def _run_playbook_flow(args: argparse.Namespace) -> dict[str, Any]:
    request_id = f"fallback-{uuid.uuid4()}"
    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.exists():
        return {
            "request_id": request_id,
            "status": "needs_input",
            "warnings": [],
            "errors": [f"output_dir does not exist: {output_dir}"],
            "workspace": {"name": args.workspace_name},
            "job": {},
            "artifacts": {},
            "summary": {
                "workspace_id": "",
                "job_id": "",
                "job_status": "",
                "artifact_count": 0,
                "downloaded_count": 0,
            },
        }

    if args.playbook_file:
        playbook_yaml = Path(args.playbook_file).read_text(encoding="utf-8")
    else:
        playbook_yaml = str(args.playbook_text or "").strip()

    if not playbook_yaml:
        return {
            "request_id": request_id,
            "status": "error",
            "warnings": [],
            "errors": ["empty playbook content"],
            "workspace": {"name": args.workspace_name},
            "job": {},
            "artifacts": {},
            "summary": {
                "workspace_id": "",
                "job_id": "",
                "job_status": "",
                "artifact_count": 0,
                "downloaded_count": 0,
            },
        }

    warnings: list[str] = []
    try:
        async with SeedOpsSession(url=args.url, token=args.token) as api:
            workspace_id = await _ensure_workspace(api, args.workspace_name)
            attach = await api.call_json(
                "workspace_attach_compose",
                {"workspace_id": workspace_id, "output_dir": str(output_dir)},
            )

            validation = await api.call_json("playbook_validate", {"playbook_yaml": playbook_yaml})
            if not bool(validation.get("valid", False)):
                return {
                    "request_id": request_id,
                    "status": "error",
                    "warnings": warnings,
                    "errors": [str(validation.get("error") or "playbook_validate failed")],
                    "workspace": {
                        "workspace_id": workspace_id,
                        "name": args.workspace_name,
                        "attach": attach,
                    },
                    "job": {},
                    "artifacts": {},
                    "summary": {
                        "workspace_id": workspace_id,
                        "job_id": "",
                        "job_status": "",
                        "artifact_count": 0,
                        "downloaded_count": 0,
                    },
                }

            run_result = await api.call_json(
                "playbook_run",
                {"workspace_id": workspace_id, "playbook_yaml": playbook_yaml},
            )
            job_id = str(run_result.get("job_id") or "")
            if not job_id:
                raise RuntimeError("playbook_run did not return job_id")

            terminal_status, final_job, job_steps = await _follow_job(
                api,
                job_id=job_id,
                poll_seconds=float(args.poll_seconds),
                timeout_seconds=float(args.timeout_seconds),
            )

            artifacts_list = await api.call_json(
                "artifacts_list",
                {"job_id": job_id, "limit": int(args.artifact_limit)},
            )
            downloaded: list[dict[str, Any]] = []
            if args.download_artifacts:
                out_root = Path(args.artifacts_dir).expanduser().resolve()
                out_root.mkdir(parents=True, exist_ok=True)
                for row in artifacts_list.get("artifacts", []) or []:
                    if not isinstance(row, dict):
                        continue
                    artifact_id = str(row.get("artifact_id") or "")
                    if not artifact_id:
                        continue
                    file_name = _safe_name(str(row.get("name") or artifact_id))
                    out_path = out_root / file_name
                    downloaded.append(
                        await _download_artifact(
                            api,
                            artifact_id=artifact_id,
                            out_path=out_path,
                            chunk_bytes=int(args.chunk_bytes),
                        )
                    )

            status = "ok" if terminal_status in {"succeeded", "succeeded_with_errors"} else "error"
            return {
                "request_id": request_id,
                "status": status,
                "warnings": warnings,
                "errors": [] if status == "ok" else [f"job finished with status={terminal_status}"],
                "workspace": {
                    "workspace_id": workspace_id,
                    "name": args.workspace_name,
                    "attach": attach,
                },
                "playbook": {
                    "source": "file" if args.playbook_file else "inline",
                    "path": args.playbook_file or "",
                    "validation": validation,
                },
                "job": {
                    "run": run_result,
                    "final": final_job,
                    "steps": job_steps,
                },
                "artifacts": {
                    "list": artifacts_list,
                    "downloaded": downloaded,
                },
                "summary": {
                    "workspace_id": workspace_id,
                    "job_id": job_id,
                    "job_status": terminal_status,
                    "artifact_count": len(artifacts_list.get("artifacts", []) or []),
                    "downloaded_count": len(downloaded),
                },
            }
    except TimeoutError as exc:
        return {
            "request_id": request_id,
            "status": "timeout",
            "warnings": warnings,
            "errors": [str(exc)],
            "workspace": {"name": args.workspace_name},
            "job": {},
            "artifacts": {},
            "summary": {
                "workspace_id": "",
                "job_id": "",
                "job_status": "",
                "artifact_count": 0,
                "downloaded_count": 0,
            },
        }
    except Exception as exc:
        return {
            "request_id": request_id,
            "status": "upstream_error",
            "warnings": warnings,
            "errors": [str(exc)],
            "workspace": {"name": args.workspace_name},
            "job": {},
            "artifacts": {},
            "summary": {
                "workspace_id": "",
                "job_id": "",
                "job_status": "",
                "artifact_count": 0,
                "downloaded_count": 0,
            },
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic SeedOps fallback flows")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run-playbook-flow", help="Ensure workspace, attach, validate, run, follow, download artifacts")
    run.add_argument("--url", default=os.environ.get("SEEDOPS_MCP_URL", os.environ.get("SEED_MCP_URL", "http://127.0.0.1:8000/mcp")))
    run.add_argument("--token", default=os.environ.get("SEEDOPS_MCP_TOKEN", os.environ.get("SEED_MCP_TOKEN", "")))
    run.add_argument("--workspace-name", required=True)
    run.add_argument("--output-dir", required=True)
    group = run.add_mutually_exclusive_group(required=True)
    group.add_argument("--playbook-file")
    group.add_argument("--playbook-text")
    run.add_argument("--poll-seconds", type=float, default=0.5)
    run.add_argument("--timeout-seconds", type=float, default=300.0)
    run.add_argument("--artifact-limit", type=int, default=200)
    run.add_argument("--download-artifacts", action=argparse.BooleanOptionalAction, default=True)
    run.add_argument("--artifacts-dir", default="./seedops_artifacts")
    run.add_argument("--chunk-bytes", type=int, default=65536)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd != "run-playbook-flow":
        parser.error(f"Unsupported command: {args.cmd}")
        return 2

    try:
        payload = asyncio.run(_run_playbook_flow(args))
    except BaseException as exc:
        payload = {
            "request_id": f"fallback-{uuid.uuid4()}",
            "status": "upstream_error",
            "warnings": [],
            "errors": [str(exc)],
            "workspace": {"name": getattr(args, "workspace_name", "")},
            "job": {},
            "artifacts": {},
            "summary": {
                "workspace_id": "",
                "job_id": "",
                "job_status": "",
                "artifact_count": 0,
                "downloaded_count": 0,
            },
        }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
