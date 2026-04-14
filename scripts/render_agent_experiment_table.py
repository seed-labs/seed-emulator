#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = REPO_ROOT / "examples" / "agent-specific"
MANIFEST_PATH = CATALOG_DIR / "manifest.yaml"

_MANUAL_CHECKS = {
    "Z12": "Map: check A12 topology loads; FRR drill: confirm FRR node, rollback, and post-check artifacts.",
    "Z13": "Map: check topology loads; page: open ExaBGP dashboard :5000 and confirm event/log surfaces.",
    "Z14": "Map: check topology loads; pages: classic LG and ExaBGP event dashboard both reachable.",
    "Z02": "Map: check MPLS topology loads; verify control-plane/router roles look sane before FRR questions.",
    "Z00": "Map: inspect mini-Internet structure; use it for general routing/runtime diagnostics.",
    "Z28": "Map: inspect generator/receiver placement; verify runtime role discovery matches topology behavior.",
    "Z29": "Map: inspect mail/DNS nodes; verify service wiring before mail/DNS troubleshooting.",
    "Z01": "Map: inspect hijack lab context; use only when you want a security drill rather than a stable first demo.",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected YAML object: {path}")
    return data


def _bundle_rows(selected: set[str] | None = None) -> list[dict[str, Any]]:
    manifest = _load_yaml(MANIFEST_PATH)
    rows: list[dict[str, Any]] = []
    for item in manifest.get("bundles") or []:
        if not isinstance(item, dict):
            continue
        bundle_id = str(item.get("id") or "")
        if selected and bundle_id not in selected:
            continue
        slug = str(item.get("slug") or "")
        bundle = _load_yaml(CATALOG_DIR / slug / "bundle.yaml")
        status = bundle.get("status") if isinstance(bundle.get("status"), dict) else {}
        command = bundle.get("command_contract") if isinstance(bundle.get("command_contract"), dict) else {}
        source_examples = bundle.get("source_examples") if isinstance(bundle.get("source_examples"), list) else []
        output_dir = ""
        source_name = ""
        if source_examples:
            first = source_examples[0] if isinstance(source_examples[0], dict) else {}
            output_dir = str(first.get("output_dir") or "")
            source_name = str(first.get("example_id") or "")
        rows.append(
            {
                "bundle": bundle_id,
                "title": str(bundle.get("title") or ""),
                "source": source_name,
                "output_dir": output_dir,
                "live_readiness": str(status.get("live_readiness") or ""),
                "best_for": " / ".join(str(x) for x in (status.get("best_for") or [])[:2]),
                "interactive_ui": str(command.get("interactive_ui") or ""),
                "read_only_probe": str(command.get("read_only_probe") or ""),
                "missions": " | ".join(str(x) for x in (command.get("mission_examples") or [])),
                "manual_checks": _MANUAL_CHECKS.get(bundle_id, "Map: verify the topology loads and the target runtime looks healthy."),
            }
        )
    return rows


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = [
        "Bundle",
        "Source",
        "Status",
        "Focus",
        "Output",
        "Manual Checks",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["bundle"],
                    row["source"],
                    row["live_readiness"],
                    row["best_for"],
                    row["output_dir"],
                    row["manual_checks"],
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a markdown/json table for SEED agent experiment bundles.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--bundles", default="", help="Comma-separated bundle ids, e.g. Z12,Z13,Z14")
    args = parser.parse_args()

    selected = {item.strip() for item in args.bundles.split(",") if item.strip()} or None
    rows = _bundle_rows(selected)
    if args.format == "json":
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    print(_markdown_table(rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
