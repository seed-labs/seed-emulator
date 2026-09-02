"""Candidate-facing sandbox Adapter and benchmark authorization boundary."""

import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

from benchmark_adapter.grants import check_action, load_grant_spec
from benchmark_adapter.trace import TraceRecorder
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


def _build_app(spec: dict[str, Any]) -> FastAPI:
    trace = TraceRecorder(Path(spec["trace_path"]))
    tool_service_url = spec["tool_service_url"].rstrip("/")
    project = spec["project"]
    service = spec["target_service"]
    actions_spec = spec["actions"]
    terminal_action = spec["terminal_action"]
    calls_used = 0

    application = FastAPI(
        title="SEEDemu Benchmark Evaluation Adapter",
        version="0.1.0",
        description="Sandbox entry point for the candidate agent under evaluation.",
    )

    class ActionRequest(BaseModel):
        model_config = ConfigDict(extra="forbid")

        action: str
        reasoning: str = Field(min_length=1)

    def forward(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(arguments).encode("utf-8")
        request = urllib.request.Request(
            f"{tool_service_url}/api/v1/tools/{tool_name}/invoke",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("result", {})

    def redact(action_spec: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        fields = action_spec.get("fields") or []
        return {field: result.get(field) for field in fields}

    @application.get("/v1/agent_view")
    def agent_view() -> dict[str, Any]:
        return spec["agent_view"]

    @application.get("/v1/trace")
    def get_trace() -> list[dict[str, Any]]:
        return trace.entries()

    @application.post("/v1/actions")
    def actions(request: ActionRequest) -> dict[str, Any]:
        nonlocal calls_used
        reason = check_action(spec, request.action, calls_used)
        entry = {
            "timestamp": time.time(),
            "action": request.action,
            "reasoning": request.reasoning,
            "rejected": reason is not None,
        }
        if reason is not None:
            trace.append(entry)
            raise HTTPException(
                status_code=403,
                detail={"code": "grant_violation", "message": reason},
            )
        calls_used += 1
        entry["calls_used"] = calls_used
        if request.action == terminal_action:
            entry["observation"] = {"finished": True}
            trace.append(entry)
            return {"finished": True}
        action_spec = actions_spec[request.action]
        arguments: dict[str, Any] = {"project": project, "service": service}
        for key, value in action_spec.get("arguments", {}).items():
            arguments[key] = value
        result = forward(action_spec["tool"], arguments)
        observation = redact(action_spec, result)
        entry["observation"] = observation
        trace.append(entry)
        return {"observation": observation}

    return application


app = _build_app(load_grant_spec(os.environ["BENCHMARK_GRANT_SPEC"]))
