"""The CLI report must distinguish submission from actual execution."""

import sys
from pathlib import Path


BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCHMARKS_DIR))

from benchmark_cli import generate_report  # noqa: E402


report_path = Path(__file__).with_name(".report_audit_test.md")
result = {
    "scenario": "audit",
    "topology": "test",
    "fault_type": "expected",
    "ai_diagnosis": "wrong",
    "ai_confidence": 0.5,
    "correct_diagnosis": False,
    "fix_verified": False,
    "repair_evaluation": True,
    "repair_submitted": True,
    "repair_authorized": False,
    "repair_verified": False,
    "repair_commands_proposed": ["docker ps -a"],
    "repair_commands_executed": [],
    "repair_commands_rejected": ["docker ps -a"],
    "diagnostic_commands_executed": ["docker ps -a"],
    "diagnostic_commands_rejected": ["docker start target"],
    "root_cause": "test root cause",
    "error": "test infrastructure error",
    "turns": 2,
    "standard_cleanup_verified": True,
    "isolation_recreated": True,
    "topology_tainted": False,
    "blind_mode": True,
    "max_turns": 20,
    "duration": 0,
    "generated_suite_id": "audit_suite",
    "generation_fingerprint": "abc123",
    "generation_contract_sha256": "def456",
}

try:
    generate_report([result], str(report_path), "ai")
    report = report_path.read_text(encoding="utf-8")
    assert "Agent 提交修复**: 1/1" in report
    assert "至少一条命令通过白名单并执行**: 0/1" in report
    assert "诊断阶段拒绝的非只读命令" in report
    assert "test root cause" in report
    assert "test infrastructure error" in report
    assert "audit_suite" in report
    assert "abc123" in report
    assert "def456" in report
finally:
    report_path.unlink(missing_ok=True)
