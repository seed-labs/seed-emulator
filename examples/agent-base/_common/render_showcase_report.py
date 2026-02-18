#!/usr/bin/env python
"""Render showcase run artifacts/logs into a Markdown report."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _tail(path: Path, lines: int) -> str:
    if not path.exists():
        return "[missing]"
    raw = path.read_text(encoding="utf-8", errors="replace")
    clean = _ANSI_RE.sub("", raw)
    content = clean.splitlines()
    if not content:
        return "[empty]"
    return "\n".join(content[-lines:])


def _md_escape(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def build_report(summary: dict[str, Any], logs_dir: Path, tail_lines: int, title: str) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    exit_codes = summary.get("exit_codes") or {}
    statuses = summary.get("statuses") or {}
    artifacts = summary.get("artifacts") or {}
    runtime = summary.get("runtime") or {}
    modes = summary.get("modes") or {}

    lines: list[str] = [
        f"# {title}",
        "",
        f"- generated_at_utc: `{generated_at}`",
        f"- running_services_b00: `{runtime.get('running_services_b00', '')}`",
        f"- running_services_b29: `{runtime.get('running_services_b29', '')}`",
        f"- s01_mode: `{modes.get('s01_mode', '')}`",
        f"- s04_mode: `{modes.get('s04_mode', '')}`",
        "",
        "## Exit Codes",
        "",
        "| Scenario | Exit Code |",
        "|---|---:|",
    ]

    for scenario in ["S01", "S02", "S03", "S04"]:
        lines.append(f"| {scenario} | {_md_escape(exit_codes.get(scenario, ''))} |")

    lines.extend(
        [
            "",
            "## Status Snapshot",
            "",
            "| Key | Status | Job Status | Job ID | First Error |",
            "|---|---|---|---|---|",
        ]
    )

    for key in sorted(statuses.keys()):
        row = statuses.get(key) or {}
        summary_row = row.get("summary") or {}
        errors = row.get("errors") or []
        first_error = errors[0] if errors else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_escape(key),
                    _md_escape(row.get("status", "")),
                    _md_escape(summary_row.get("job_status", "")),
                    _md_escape(summary_row.get("job_id", "")),
                    _md_escape(first_error),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
        ]
    )
    for key in ["S01_latest", "S02_latest", "S03_latest", "S04_latest"]:
        lines.append(f"- {key}: `{artifacts.get(key, '')}`")

    log_files = [
        ("s01.log", "S01 Log Tail"),
        ("s02.log", "S02 Log Tail"),
        ("s03.log", "S03 Log Tail"),
        ("s04.log", "S04 Log Tail"),
        ("seedagent.log", "SeedAgent MCP Log Tail"),
        ("seedops.log", "SeedOps MCP Log Tail"),
    ]

    lines.extend(["", "## Log Tails", ""])
    for file_name, section_title in log_files:
        path = logs_dir / file_name
        lines.extend(
            [
                f"### {section_title}",
                "",
                "```text",
                _tail(path, tail_lines),
                "```",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render showcase logs and summary into Markdown")
    parser.add_argument("--summary", required=True, help="Path to real_showcase_summary.json")
    parser.add_argument("--logs-dir", required=True, help="Path to logs directory")
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--tail-lines", type=int, default=25, help="Tail lines per log section")
    parser.add_argument("--title", default="Seed-Agent Showcase Run Report", help="Report title")
    args = parser.parse_args()

    summary_path = Path(args.summary).expanduser().resolve()
    logs_dir = Path(args.logs_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary = _load_json(summary_path)
    markdown = build_report(summary, logs_dir, int(args.tail_lines), args.title)
    output_path.write_text(markdown, encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
