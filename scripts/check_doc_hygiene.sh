#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

fail=0

check_pattern() {
  local pattern="$1"
  local desc="$2"
  local matches existing
  matches="$(git ls-files | rg "${pattern}" || true)"
  existing=""
  if [ -n "${matches}" ]; then
    while IFS= read -r path; do
      if [ -e "${path}" ]; then
        existing+="${path}"$'\n'
      fi
    done <<< "${matches}"
  fi
  if [ -n "${existing}" ]; then
    echo "[doc-hygiene] FAIL: ${desc}"
    printf '%s' "${existing}"
    fail=1
  fi
}

check_pattern '^docs/thoughts/' 'private notes must not be tracked (docs/thoughts/)'
check_pattern '^docs/assessment_.*\.md$' 'private assessment notes must not be tracked (docs/assessment_*.md)'
check_pattern '^docs/TODO\.md$' 'repo-internal TODO must not be tracked (docs/TODO.md)'
check_pattern '^docs/runbooks/.*handoff.*\.md$' 'handoff-only runbooks must not be tracked'
check_pattern '^docs/runbooks/.*replay.*\.md$' 'local replay notes must not be tracked'
check_pattern '^docs/runbooks/.*variant_diff.*\.md$' 'repo-variant comparison notes must not be tracked'

# Dated runbooks/design drafts belong under output/private_docs (ignored), not in git.
check_pattern '^docs/runbooks/.*20[0-9]{6}.*\.md$' 'dated runbooks must not be tracked (docs/runbooks/*YYYYMMDD*)'
check_pattern '^docs/design/.*20[0-9]{6}.*\.md$' 'dated design drafts must not be tracked (docs/design/*YYYYMMDD*)'
check_pattern '^docs/designs/.*20[0-9]{6}.*\.md$' 'dated design drafts must not be tracked (docs/designs/*YYYYMMDD*)'
check_pattern '^\.env$' 'local env files must not be tracked (.env)'
check_pattern '^\.opencode/node_modules/' 'opencode local package state must not be tracked (.opencode/node_modules/)'
check_pattern '^\.opencode/package\.json$' 'opencode local package state must not be tracked (.opencode/package.json)'
check_pattern '^\.opencode/bun\.lock$' 'opencode local package state must not be tracked (.opencode/bun.lock)'

check_no_cjk() {
  local path="$1"
  local desc="$2"
  if ! git ls-files --error-unmatch "${path}" >/dev/null 2>&1; then
    return 0
  fi
  if python3 - "${path}" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
raise SystemExit(0 if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", text) else 1)
PY
  then
    echo "[doc-hygiene] FAIL: ${desc}"
    echo "${path}"
    fail=1
  fi
}

check_no_cjk 'docs/k8s_usage.md' 'public K8s operator manual must be English-only'
check_no_cjk 'docs/k3s_runtime_architecture.md' 'public K3s architecture manual must be English-only'
check_no_cjk 'examples/kubernetes/README.md' 'public Kubernetes examples index must be English-only'
check_no_cjk 'docs/runbooks/opencode_seed_lab_quickstart.md' 'public opencode quickstart must be English-only'
check_no_cjk 'docs/runbooks/seed_k3s_ai_evidence_manual.md' 'public AI evidence manual must be English-only'
check_no_cjk 'docs/runbooks/seed_k3s_long_term_optimization_roadmap.md' 'public K3s roadmap must be English-only'
check_no_cjk 'docs/runbooks/seed_k8s_academic_showcase.md' 'public showcase manual must be English-only'
check_no_cjk 'docs/developer_manual/20-migrating-examples-to-k8s.md' 'public K8s migration manual must be English-only'
check_no_cjk 'docs/runbooks/local_kind_quick_runbook.md' 'public local Kind runbook must be English-only'
check_no_cjk 'docs/design/kubevirt_hybrid_k8s.md' 'public KubeVirt hybrid design doc must be English-only'

if [ "${fail}" -ne 0 ]; then
  echo "[doc-hygiene] Hint: archive private docs under output/private_docs/ (ignored by .gitignore)."
  exit 1
fi

echo "[doc-hygiene] PASS"
