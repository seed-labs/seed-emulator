#!/usr/bin/env python3
"""Call canonical Seed-Agent MCP tools and return parsed JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from typing import Any

from mcp.client.session_group import ClientSessionGroup, StreamableHttpParameters


def _error_payload(tool_name: str, message: str, *, raw_response: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "request_id": f"local-{uuid.uuid4()}",
        "status": "upstream_error",
        "warnings": [],
        "errors": [message],
        "tool": tool_name,
    }
    if raw_response:
        payload["raw_response"] = raw_response[:1000]
    return payload


def _parse_tool_json(tool_name: str, text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except Exception as exc:
        return _error_payload(tool_name, f"Tool returned non-JSON response: {exc}", raw_response=text)
    if not isinstance(parsed, dict):
        return _error_payload(tool_name, "Tool returned non-object JSON", raw_response=text)
    if "status" not in parsed:
        parsed["status"] = "error"
        parsed.setdefault("errors", []).append("Missing status field in tool response")
    return parsed


async def _call_tool_text(*, url: str, token: str, tool_name: str, arguments: dict[str, Any]) -> str:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = StreamableHttpParameters(url=url, headers=headers)
    async with ClientSessionGroup() as group:
        await group.connect_to_server(params)
        result = await group.call_tool(tool_name, arguments=arguments)

    texts: list[str] = []
    for item in getattr(result, "content", []) or []:
        if getattr(item, "type", "") == "text":
            texts.append(getattr(item, "text", ""))
    if not texts:
        raise RuntimeError("MCP tool returned no text content")
    return "\n".join(texts).strip()


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _run_command(tool_name: str, arguments: dict[str, Any], *, url: str, token: str) -> int:
    try:
        text = asyncio.run(_call_tool_text(url=url, token=token, tool_name=tool_name, arguments=arguments))
        payload = _parse_tool_json(tool_name, text)
    except BaseException as exc:
        payload = _error_payload(tool_name, str(exc))
    _emit(payload)
    return 0


def _add_common_endpoint_args(parser: argparse.ArgumentParser, *, default_url: str, default_token: str) -> None:
    parser.add_argument("--url", default=default_url, help="Seed-Agent MCP URL")
    parser.add_argument("--token", default=default_token, help="Seed-Agent MCP bearer token")


def build_parser() -> argparse.ArgumentParser:
    default_url = os.environ.get("SEED_AGENT_MCP_URL", "http://127.0.0.1:8100/mcp")
    default_token = os.environ.get("SEED_AGENT_MCP_TOKEN", "")

    parser = argparse.ArgumentParser(description="Invoke canonical Seed-Agent MCP tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Call seed_agent_run")
    _add_common_endpoint_args(run_p, default_url=default_url, default_token=default_token)
    run_p.add_argument("--request", required=True)
    run_p.add_argument("--workspace-name", default="lab1")
    run_p.add_argument("--attach-output-dir")
    run_p.add_argument("--attach-name-regex")
    run_p.add_argument("--policy-profile", default="read_only")
    run_p.add_argument("--follow-job", action=argparse.BooleanOptionalAction, default=True)
    run_p.add_argument("--download-artifacts", action=argparse.BooleanOptionalAction, default=False)
    run_p.add_argument("--artifacts-dir", default="./seedops_artifacts")

    plan_p = sub.add_parser("plan", help="Call seed_agent_plan")
    _add_common_endpoint_args(plan_p, default_url=default_url, default_token=default_token)
    plan_p.add_argument("--request", required=True)
    plan_p.add_argument("--workspace-name", default="lab1")
    plan_p.add_argument("--attach-output-dir")
    plan_p.add_argument("--attach-name-regex")
    plan_p.add_argument("--policy-profile", default="read_only")

    policy_p = sub.add_parser("policy-check", help="Call seed_agent_policy_check")
    _add_common_endpoint_args(policy_p, default_url=default_url, default_token=default_token)
    policy_p.add_argument("--command", required=True)
    policy_p.add_argument("--policy-profile", default="read_only")

    artifacts_p = sub.add_parser("artifacts-download", help="Call seed_agent_artifacts_download")
    _add_common_endpoint_args(artifacts_p, default_url=default_url, default_token=default_token)
    artifacts_p.add_argument("--job-id", required=True)
    artifacts_p.add_argument("--out-dir", default="./seedops_artifacts")
    artifacts_p.add_argument("--limit", type=int, default=200)
    artifacts_p.add_argument("--chunk-bytes", type=int, default=65536)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "run":
        return _run_command(
            "seed_agent_run",
            {
                "request": args.request,
                "workspace_name": args.workspace_name,
                "attach_output_dir": args.attach_output_dir,
                "attach_name_regex": args.attach_name_regex,
                "policy_profile": args.policy_profile,
                "follow_job": bool(args.follow_job),
                "download_artifacts": bool(args.download_artifacts),
                "artifacts_dir": args.artifacts_dir,
            },
            url=args.url,
            token=args.token,
        )

    if args.cmd == "plan":
        return _run_command(
            "seed_agent_plan",
            {
                "request": args.request,
                "workspace_name": args.workspace_name,
                "attach_output_dir": args.attach_output_dir,
                "attach_name_regex": args.attach_name_regex,
                "policy_profile": args.policy_profile,
            },
            url=args.url,
            token=args.token,
        )

    if args.cmd == "policy-check":
        return _run_command(
            "seed_agent_policy_check",
            {
                "command": args.command,
                "policy_profile": args.policy_profile,
            },
            url=args.url,
            token=args.token,
        )

    if args.cmd == "artifacts-download":
        return _run_command(
            "seed_agent_artifacts_download",
            {
                "job_id": args.job_id,
                "out_dir": args.out_dir,
                "limit": int(args.limit),
                "chunk_bytes": int(args.chunk_bytes),
            },
            url=args.url,
            token=args.token,
        )

    parser.error(f"Unsupported command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
