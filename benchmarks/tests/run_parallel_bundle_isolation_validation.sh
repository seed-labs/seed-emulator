#!/usr/bin/env bash
set -u

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <new-workspace-root>" >&2
  exit 2
fi

repo="$(cd "$(dirname "$0")/.." && pwd)"
root="$1"
case "$root" in
  "$repo"/reports/*) ;;
  *) echo "workspace root must be under $repo/reports" >&2; exit 2 ;;
esac
if [ -e "$root" ]; then
  echo "workspace root already exists: $root" >&2
  exit 2
fi
mkdir -p "$root"
cd "$repo"

python3 -m generator.bundle.cli generate \
  --request generator/bundle/examples/boundary_validation/boundary_docker_network_bundle.json \
  --workspace "$root/docker_network" \
  >"$root/docker_network.stdout.log" 2>"$root/docker_network.stderr.log" &
first_pid=$!

python3 -m generator.bundle.cli generate \
  --request generator/bundle/examples/boundary_validation/boundary_cascading_compound_bundle.json \
  --workspace "$root/cascading_compound" \
  >"$root/cascading_compound.stdout.log" 2>"$root/cascading_compound.stderr.log" &
second_pid=$!

first_status=0; second_status=0
wait "$first_pid" || first_status=$?
wait "$second_pid" || second_status=$?
if [ "$first_status" -ne 0 ] || [ "$second_status" -ne 0 ]; then
  tail -80 "$root/docker_network.stderr.log" >&2
  tail -80 "$root/cascading_compound.stderr.log" >&2
  exit 1
fi

python3 - "$root" <<'PY'
import glob
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1])
reports = []
container_sets = []
network_sets = []
projects = []
for name in ("docker_network", "cascading_compound"):
    workspace = root / name
    summary = json.loads((workspace / "summary.json").read_text())
    isolation = json.loads((workspace / "isolation.json").read_text())
    receipts = [
        json.loads(Path(path).read_text())
        for path in sorted(glob.glob(str(workspace / "lifecycle_round_*.json")))
    ]
    assert summary["qualification_status"] == "qualified"
    assert summary["quality_passed"] and summary["scale_passed"]
    assert isolation["status"] == "cleaned"
    assert isolation["cleanup_verified"] is True
    assert isolation["runtime_compose_removed"] is True
    assert isolation["runtime_context_removed"] is True
    assert len(isolation["container_rebindings"]) == 8
    assert len(receipts) == 2 and all(item["passed"] for item in receipts)
    assert all(item["convergence"]["passed"] for item in receipts)
    assert not any(item["ai_invoked"] for item in receipts)
    containers = set(isolation["container_rebindings"].values())
    container_sets.append(containers)
    networks = set(isolation["network_rebindings"].values())
    assert networks
    network_sets.append(networks)
    projects.append(isolation["compose_project"])
    reports.append({
        "request_id": summary["request_id"],
        "compose_project": isolation["compose_project"],
        "runtime_containers": len(containers),
        "qualified": True,
        "cleanup_verified": True,
    })
assert projects[0] != projects[1]
assert container_sets[0].isdisjoint(container_sets[1])
assert network_sets[0].isdisjoint(network_sets[1])
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
print(json.dumps({"parallel_sessions": reports, "zero_residue": True}, indent=2))
PY
