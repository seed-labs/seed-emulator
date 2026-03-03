#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/env_seedemu.sh"

NS="${1:-${SEED_NAMESPACE:-seedemu-k3s-mini-mn4}}"
OUT_DIR="${2:-${REPO_ROOT}/output/mini_observe/$(date +%Y%m%d_%H%M%S)}"
KCFG_DEFAULT="${REPO_ROOT}/output/kubeconfigs/seedemu-k3s.yaml"
KUBECONFIG="${KUBECONFIG:-${KCFG_DEFAULT}}"

mkdir -p "${OUT_DIR}"
export KUBECONFIG

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd kubectl

if [ ! -f "${KUBECONFIG}" ]; then
  echo "KUBECONFIG not found: ${KUBECONFIG}" >&2
  echo "Run ./scripts/k3s_fetch_kubeconfig.sh first." >&2
  exit 1
fi

if ! kubectl get ns "${NS}" >/dev/null 2>&1; then
  echo "Namespace not found: ${NS}" >&2
  exit 1
fi

log "Collecting cluster and namespace snapshots to ${OUT_DIR}"

kubectl get nodes -o wide > "${OUT_DIR}/nodes_wide.txt"
kubectl -n "${NS}" get pods -o wide > "${OUT_DIR}/pods_wide.txt"
kubectl -n "${NS}" get deploy -o wide > "${OUT_DIR}/deploy_wide.txt"
kubectl -n "${NS}" get network-attachment-definitions.k8s.cni.cncf.io > "${OUT_DIR}/nad.txt"

kubectl -n "${NS}" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.seedemu\.io/asn}{"\t"}{.spec.nodeName}{"\n"}{end}' \
  > "${OUT_DIR}/placement.tsv"

{
  echo "Node distribution:"
  awk -F'\t' 'NF>=3 {print $3}' "${OUT_DIR}/placement.tsv" | sort | uniq -c
} > "${OUT_DIR}/placement_summary.txt"

R151="$(kubectl -n "${NS}" get pods -l seedemu.io/name=router0,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"
R150="$(kubectl -n "${NS}" get pods -l seedemu.io/name=router0,seedemu.io/asn=150 -o jsonpath='{.items[0].metadata.name}')"
RS100="$(kubectl -n "${NS}" get pods -l seedemu.io/name=ix100,seedemu.io/asn=100 -o jsonpath='{.items[0].metadata.name}')"
H150="$(kubectl -n "${NS}" get pods -l seedemu.io/name=host_0,seedemu.io/asn=150 -o jsonpath='{.items[0].metadata.name}')"
H151="$(kubectl -n "${NS}" get pods -l seedemu.io/name=host_0,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"

cat > "${OUT_DIR}/key_pods.env" <<EOF
NS=${NS}
R150=${R150}
R151=${R151}
RS100=${RS100}
H150=${H150}
H151=${H151}
EOF

kubectl -n "${NS}" get pod "${R151}" -o jsonpath='{.metadata.annotations.k8s\.v1\.cni\.cncf\.io/networks}' \
  > "${OUT_DIR}/r151_networks_annotation.txt"
echo >> "${OUT_DIR}/r151_networks_annotation.txt"

kubectl -n "${NS}" exec "${R151}" -- sh -c 'ip -o -4 addr show; echo "---"; ip route' 2>/dev/null \
  > "${OUT_DIR}/r151_ip_route.txt"
kubectl -n "${NS}" exec "${R150}" -- sh -c 'ip -o -4 addr show; echo "---"; ip route' 2>/dev/null \
  > "${OUT_DIR}/r150_ip_route.txt"
kubectl -n "${NS}" exec "${H150}" -- sh -c 'ip -o -4 addr show; echo "---"; ip route' 2>/dev/null \
  > "${OUT_DIR}/h150_ip_route.txt"

kubectl -n "${NS}" exec "${R151}" -- birdc s p 2>/dev/null > "${OUT_DIR}/bird_r151.txt"
kubectl -n "${NS}" exec "${RS100}" -- birdc s p 2>/dev/null > "${OUT_DIR}/bird_rs100.txt"

# Ping may return non-zero on partial packet loss; keep evidence collection stable.
kubectl -n "${NS}" exec "${H150}" -- ping -I net0 -c 3 -W 2 10.151.0.71 2>/dev/null > "${OUT_DIR}/ping_150_to_151.txt" || true
kubectl -n "${NS}" exec "${H151}" -- ping -I net0 -c 3 -W 2 10.150.0.71 2>/dev/null > "${OUT_DIR}/ping_151_to_150.txt" || true

python3 - <<PY
import json
import re
from pathlib import Path

out = Path(${OUT_DIR@Q})
dist = {}
for line in (out / "placement.tsv").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    pod, asn, node = line.split("\t")
    dist[node] = dist.get(node, 0) + 1

bird_r151 = (out / "bird_r151.txt").read_text(encoding="utf-8")
bird_rs100 = (out / "bird_rs100.txt").read_text(encoding="utf-8")
ping_150_151 = (out / "ping_150_to_151.txt").read_text(encoding="utf-8")

bgp_r151_ok = "Established" in bird_r151
bgp_rs100_ok = all(
    re.search(rf"p_as{asn}\\s+BGP.*Established", bird_rs100) for asn in ("2", "3", "4")
)

tx = rx = None
ping_match = re.search(r"(\\d+) packets transmitted, (\\d+) received", ping_150_151)
if ping_match:
    tx = int(ping_match.group(1))
    rx = int(ping_match.group(2))

summary = {
    "namespace": ${NS@Q},
    "kubeconfig": ${KUBECONFIG@Q},
    "node_distribution": dist,
    "nodes_used_count": len(dist),
    "bgp_established_router151": bgp_r151_ok,
    "bgp_established_rs100": bgp_rs100_ok,
    "ping_150_to_151": {
        "tx": tx,
        "rx": rx,
        "has_reply": (rx is not None and rx > 0),
    },
    "artifacts": sorted(p.name for p in out.iterdir()),
}
(out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY

log "Done. Key files:"
echo "  - ${OUT_DIR}/summary.json"
echo "  - ${OUT_DIR}/placement_summary.txt"
echo "  - ${OUT_DIR}/r151_ip_route.txt"
echo "  - ${OUT_DIR}/bird_r151.txt"
echo "  - ${OUT_DIR}/ping_150_to_151.txt"
