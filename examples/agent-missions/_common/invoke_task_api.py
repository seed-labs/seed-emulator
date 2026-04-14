#!/usr/bin/env python
"""Invoke Seed-Agent mission APIs over MCP Streamable HTTP."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from typing import Any

from mcp.client.session_group import ClientSessionGroup, StreamableHttpParameters


def _error_payload(tool_name: str, message: str, *, raw: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "request_id": f"local-{uuid.uuid4()}",
        "status": "upstream_error",
        "warnings": [],
        "errors": [message],
        "tool": tool_name,
    }
    if raw:
        payload["raw_response"] = raw[:1000]
    return payload


def _parse_json(tool_name: str, text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except Exception as exc:
        return _error_payload(tool_name, f"invalid JSON from tool: {exc}", raw=text)
    if not isinstance(data, dict):
        return _error_payload(tool_name, "tool response is not JSON object", raw=text)
    return data


async def _call_tool(*, url: str, token: str, tool_name: str, arguments: dict[str, Any]) -> str:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = StreamableHttpParameters(url=url, headers=headers)
    async with ClientSessionGroup() as group:
        await group.connect_to_server(params)
        result = await group.call_tool(tool_name, arguments=arguments)

    chunks: list[str] = []
    for item in getattr(result, "content", []) or []:
        if getattr(item, "type", "") == "text":
            chunks.append(getattr(item, "text", ""))
    if not chunks:
        raise RuntimeError("MCP tool returned no text payload")
    return "\n".join(chunks).strip()


def _run(tool_name: str, args: dict[str, Any], *, url: str, token: str) -> int:
    try:
        text = asyncio.run(_call_tool(url=url, token=token, tool_name=tool_name, arguments=args))
        payload = _parse_json(tool_name, text)
    except BaseException as exc:
        payload = _error_payload(tool_name, str(exc))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _add_endpoint_args(parser: argparse.ArgumentParser, *, default_url: str, default_token: str) -> None:
    parser.add_argument("--url", default=default_url)
    parser.add_argument("--token", default=default_token)


def build_parser() -> argparse.ArgumentParser:
    default_url = os.environ.get("SEED_AGENT_MCP_URL", "http://127.0.0.1:8100/mcp")
    default_token = os.environ.get("SEED_AGENT_MCP_TOKEN", "")

    parser = argparse.ArgumentParser(description="Invoke Seed-Agent mission APIs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    catalog_p = sub.add_parser("catalog")
    _add_endpoint_args(catalog_p, default_url=default_url, default_token=default_token)
    catalog_p.add_argument("--track", default="all")
    catalog_p.add_argument("--baseline", default="all")

    begin_p = sub.add_parser("begin")
    _add_endpoint_args(begin_p, default_url=default_url, default_token=default_token)
    begin_p.add_argument("--task-id", required=True)
    begin_p.add_argument("--objective", required=True)
    begin_p.add_argument("--workspace-name", default="lab1")
    begin_p.add_argument("--attach-output-dir")
    begin_p.add_argument("--attach-name-regex")
    begin_p.add_argument("--context-json", default="{}")

    reply_p = sub.add_parser("reply")
    _add_endpoint_args(reply_p, default_url=default_url, default_token=default_token)
    reply_p.add_argument("--session-id", required=True)
    reply_p.add_argument("--answers-json", required=True)

    execute_p = sub.add_parser("execute")
    _add_endpoint_args(execute_p, default_url=default_url, default_token=default_token)
    execute_p.add_argument("--session-id", required=True)
    execute_p.add_argument("--approval-token")
    execute_p.add_argument("--follow-job", action=argparse.BooleanOptionalAction, default=True)
    execute_p.add_argument("--download-artifacts", action=argparse.BooleanOptionalAction, default=False)
    execute_p.add_argument("--artifacts-dir", default="./seedops_artifacts")

    status_p = sub.add_parser("status")
    _add_endpoint_args(status_p, default_url=default_url, default_token=default_token)
    status_p.add_argument("--session-id", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "catalog":
        return _run(
            "seed_agent_task_catalog",
            {"track": args.track, "baseline": args.baseline},
            url=args.url,
            token=args.token,
        )
    if args.cmd == "begin":
        return _run(
            "seed_agent_task_begin",
            {
                "task_id": args.task_id,
                "objective": args.objective,
                "workspace_name": args.workspace_name,
                "attach_output_dir": args.attach_output_dir,
                "attach_name_regex": args.attach_name_regex,
                "context_json": args.context_json,
            },
            url=args.url,
            token=args.token,
        )
    if args.cmd == "reply":
        return _run(
            "seed_agent_task_reply",
            {"session_id": args.session_id, "answers_json": args.answers_json},
            url=args.url,
            token=args.token,
        )
    if args.cmd == "execute":
        return _run(
            "seed_agent_task_execute",
            {
                "session_id": args.session_id,
                "approval_token": args.approval_token,
                "follow_job": bool(args.follow_job),
                "download_artifacts": bool(args.download_artifacts),
                "artifacts_dir": args.artifacts_dir,
            },
            url=args.url,
            token=args.token,
        )
    if args.cmd == "status":
        return _run(
            "seed_agent_task_status",
            {"session_id": args.session_id},
            url=args.url,
            token=args.token,
        )

    parser.error(f"Unsupported command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

