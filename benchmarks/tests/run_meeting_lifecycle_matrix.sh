#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 <meeting-report-directory> [--verify-only]" >&2
  exit 2
fi
verify_only=false
if [ "${2:-}" = "--verify-only" ]; then
  verify_only=true
elif [ "$#" -eq 2 ]; then
  echo "unknown option: $2" >&2
  exit 2
fi

repo="$(cd "$(dirname "$0")/.." && pwd)"
report="$(realpath "$1")"
case "$report" in
  "$repo"/meeting_reports/*) ;;
  *) echo "report must be under $repo/meeting_reports" >&2; exit 2 ;;
esac

mkdir -p "$report/raw" "$report/lifecycles" "$report/inputs"
cp "$repo/reports/mimo_dns_6as_bundle_qualified_20260825/request.json" \
  "$report/inputs/mimo_six_as_dns_request.json"

names=(
  mimo_six_as_dns
  ipv6_connected_route
  ospf_wrong_area
  docker_network_disconnect
  software_config_replace
  software_executable_disabled
  cascading_compound
)
requests=(
  "$report/inputs/mimo_six_as_dns_request.json"
  "$repo/generator/bundle/examples/boundary_validation/boundary_ipv6_bundle.json"
  "$repo/generator/bundle/examples/boundary_validation/boundary_ospf_bundle.json"
  "$repo/generator/bundle/examples/boundary_validation/boundary_docker_network_bundle.json"
  "$repo/generator/bundle/examples/boundary_validation/boundary_software_config_bundle.json"
  "$repo/generator/bundle/examples/boundary_validation/boundary_software_executable_bundle.json"
  "$repo/generator/bundle/examples/boundary_validation/boundary_cascading_compound_bundle.json"
)

cd "$repo"
if [ "$verify_only" = false ]; then
  printf 'name\texit_code\n' >"$report/raw/lifecycle_exit_codes.tsv"
  for ((start=0; start<${#names[@]}; start+=2)); do
  pids=()
  indexes=()
  for ((index=start; index<start+2 && index<${#names[@]}; index++)); do
    name="${names[$index]}"
    workspace="$report/lifecycles/$name"
    if [ -e "$workspace" ]; then
      echo "workspace already exists: $workspace" >&2
      exit 2
    fi
    python3 -m generator.bundle.cli generate \
      --request "${requests[$index]}" \
      --workspace "$workspace" \
      >"$report/raw/${name}.stdout.log" \
      2>"$report/raw/${name}.stderr.log" &
    pids+=("$!")
    indexes+=("$index")
  done
  failed=0
  for position in "${!pids[@]}"; do
    index="${indexes[$position]}"
    name="${names[$index]}"
    status=0
    wait "${pids[$position]}" || status=$?
    printf '%s\t%s\n' "$name" "$status" | tee -a \
      "$report/raw/lifecycle_exit_codes.tsv"
    if [ "$status" -ne 0 ]; then
      tail -80 "$report/raw/${name}.stderr.log" >&2
      failed=1
    fi
  done
    [ "$failed" -eq 0 ] || exit 1
  done
fi

python3 - "$report" <<'PY'
import glob
import json
from pathlib import Path
import subprocess
import sys

report = Path(sys.argv[1])
rows = []
projects = []
for workspace in sorted((report / "lifecycles").iterdir()):
    if not (workspace / "summary.json").is_file():
        continue
    summary = json.loads((workspace / "summary.json").read_text())
    isolation = json.loads((workspace / "isolation.json").read_text())
    receipts = [
        json.loads(Path(path).read_text())
        for path in sorted(glob.glob(str(workspace / "lifecycle_round_*.json")))
    ]
    assert summary["qualification_status"] == "qualified"
    assert summary["quality_passed"] and summary["scale_passed"]
    assert len(receipts) == 2
    assert all(item["passed"] and not item["ai_invoked"] for item in receipts)
    assert all(item["convergence"]["passed"] for item in receipts)
    assert isolation["status"] == "cleaned"
    assert isolation["cleanup_verified"] is True
    assert isolation["runtime_context_removed"] is True
    project = isolation["compose_project"]
    projects.append(project)
    rows.append({
        "name": workspace.name,
        "request_id": summary["request_id"],
        "qualification_status": summary["qualification_status"],
        "lifecycle_rounds": len(receipts),
        "all_rounds_passed": True,
        "ai_invoked": False,
        "convergence_passed": True,
        "compose_project": project,
        "runtime_containers": len(isolation["containers"]),
        "network_rebindings": isolation["network_rebindings"],
        "cleanup_verified": True,
    })
assert len(projects) == len(set(projects))
for project in projects:
    containers = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    networks = subprocess.run(
        ["docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert not containers and not networks
result = {
    "schema_version": 1,
    "all_qualified": True,
    "all_no_ai": True,
    "zero_docker_residue": True,
    "runs": rows,
}
(report / "lifecycle_matrix_summary.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(result, indent=2, sort_keys=True))
PY
