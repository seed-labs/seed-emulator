#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

RUN_ID="${SEED_RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${REPO_ROOT}/output/opencode_agent_eval/${RUN_ID}"
TIMEOUT_SECONDS="${OPENCODE_EVAL_TIMEOUT_SECONDS:-60}"

mkdir -p "${OUT_DIR}"

export OUT_DIR
export TIMEOUT_SECONDS

python3 - <<'PY'
import json
import os
import re
import subprocess
from pathlib import Path

out_dir = Path(os.environ["OUT_DIR"])
timeout_s = int(os.environ["TIMEOUT_SECONDS"])

ansi_re = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

cases = [
    {
        "id": "docker_compose_migration",
        "prompt": (
            "不要执行任何命令，不要读取文件。场景：用户熟悉docker-compose旧版SEED。"
            "请固定四段输出：目标、命令、成功判据、与docker-compose对应关系。"
            "命令必须体现compile->build->deploy->verify。"
        ),
        "must_contain": [
            "目标",
            "命令",
            "成功判据",
            "docker-compose",
            "compile",
            "deploy",
            "verify",
        ],
    },
    {
        "id": "macro_user_minimal_path",
        "prompt": (
            "不要执行任何命令，不要读取文件。场景：用户只懂宏观框架。"
            "请给最小可跑路径，固定三段输出：目标、命令、看到什么证据。"
            "必须包含 output/profile_runs 和 report.json。"
        ),
        "must_contain": [
            "目标",
            "命令",
            "证据",
            "output/profile_runs",
            "report.json",
        ],
    },
    {
        "id": "kcfg_failure_guidance",
        "prompt": (
            "不要执行任何命令，不要读取文件。"
            "场景：kubectl 报错 localhost:8080 refused。"
            "请严格输出5元组字段：failed_stage, failure_code, first_evidence_file, minimal_retry_command, fallback_command。"
            "failure_code 必须使用仓库标准值。"
        ),
        "must_contain": [
            "failed_stage",
            "failure_code",
            "KCFG_MISSING",
            "k3s_fetch_kubeconfig.sh",
            "setup_k3s_cluster.sh",
        ],
    },
    {
        "id": "placement_failure_guidance",
        "prompt": (
            "不要执行任何命令，不要读取文件。"
            "场景：strict3 调度未命中，placement_check.json 报错。"
            "请严格输出5元组字段：failed_stage, failure_code, first_evidence_file, minimal_retry_command, fallback_command。"
            "failure_code 必须使用仓库标准值。"
        ),
        "must_contain": [
            "failed_stage",
            "failure_code",
            "PLACEMENT_FAILED",
            "placement_check.json",
            "validate_k3s_mini_internet_multinode.sh verify",
        ],
    },
]

results = []

for case in cases:
    cid = case["id"]
    raw_path = out_dir / f"{cid}.raw.txt"
    clean_path = out_dir / f"{cid}.clean.txt"

    cmd = [
        "timeout",
        f"{timeout_s}s",
        "opencode",
        "run",
        "--agent",
        "seed-lab",
        case["prompt"],
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    raw = (proc.stdout or "") + (proc.stderr or "")
    raw_path.write_text(raw, encoding="utf-8")
    clean = ansi_re.sub("", raw)
    clean_path.write_text(clean, encoding="utf-8")

    missing = [s for s in case["must_contain"] if s not in clean]
    status = "PASS" if proc.returncode == 0 and not missing else "FAIL"

    results.append(
        {
            "id": cid,
            "status": status,
            "returncode": proc.returncode,
            "missing_tokens": missing,
            "raw_file": str(raw_path),
            "clean_file": str(clean_path),
        }
    )

summary = {
    "run_id": out_dir.name,
    "out_dir": str(out_dir),
    "cases_total": len(results),
    "cases_passed": sum(1 for r in results if r["status"] == "PASS"),
    "cases_failed": sum(1 for r in results if r["status"] == "FAIL"),
    "results": results,
}

(out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

lines = [
    "# SEED-lab Non-toy Guidance Eval",
    "",
    f"- run_id: `{summary['run_id']}`",
    f"- cases_total: `{summary['cases_total']}`",
    f"- cases_passed: `{summary['cases_passed']}`",
    f"- cases_failed: `{summary['cases_failed']}`",
    "",
    "| case | status | returncode | missing_tokens | clean_output |",
    "|---|---|---:|---|---|",
]
for r in results:
    missing = ", ".join(r["missing_tokens"]) if r["missing_tokens"] else "-"
    lines.append(
        f"| `{r['id']}` | `{r['status']}` | `{r['returncode']}` | `{missing}` | `{r['clean_file']}` |"
    )

(out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps(summary, indent=2))
if summary["cases_failed"] > 0:
    raise SystemExit(1)
PY

echo "Evaluation artifacts: ${OUT_DIR}"
echo "Summary: ${OUT_DIR}/summary.json"
echo "Summary: ${OUT_DIR}/summary.md"
