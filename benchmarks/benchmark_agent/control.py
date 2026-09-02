"""Benchmark-owned session and candidate grant policy documents."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from benchmark_agent.scenario import Scenario


def create_session_contract(
    session_id: str, project: str, service: str, inventory: dict[str, Any]
) -> dict[str, Any]:
    fingerprint = hashlib.sha256(
        json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": 1,
        "session_id": session_id,
        "project": project,
        "service": service,
        "owner": "benchmark_agent",
        "inventory": inventory,
        "inventory_fingerprint": fingerprint,
    }


def create_candidate_grant_contract(
    session_id: str, scenario: Scenario
) -> dict[str, Any]:
    expires_at = datetime.now(UTC) + timedelta(seconds=scenario.grant.ttl_seconds)
    return {
        "schema_version": 1,
        "benchmark_id": session_id,
        "project": scenario.project,
        "service": scenario.fault.target_service,
        "tools": scenario.grant.tools,
        "max_calls": scenario.grant.max_calls,
        "expires_at": expires_at.isoformat(),
        "enforced_by": "candidate_adapter",
    }
