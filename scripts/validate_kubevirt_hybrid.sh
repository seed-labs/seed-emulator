#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXAMPLE_DIR="${ROOT_DIR}/examples/kubernetes"
OUTPUT_DIR="${EXAMPLE_DIR}/output_kubevirt_hybrid"
CLUSTER_NAME="${SEED_CLUSTER_NAME:-seedemu-kvtest}"
NAMESPACE="${SEED_NAMESPACE:-seedemu-kvtest}"
KUBECONTEXT="${SEED_KUBECONTEXT:-kind-${CLUSTER_NAME}}"
ARTIFACT_DIR="${SEED_ARTIFACT_DIR:-${ROOT_DIR}/output/kubevirt_validation}"
DEPLOY_WAIT_TIMEOUT="${DEPLOY_WAIT_TIMEOUT:-1200s}"
VMI_WAIT_TIMEOUT="${VMI_WAIT_TIMEOUT:-480s}"
BGP_WAIT_TIMEOUT_SECONDS="${BGP_WAIT_TIMEOUT_SECONDS:-300}"
RUNTIME_PROFILE="${SEED_RUNTIME_PROFILE:-auto}"
CLEAN_NAMESPACE="${SEED_CLEAN_NAMESPACE:-true}"
AUTO_FIX_MULTUS_TEXT_BUSY="${SEED_AUTO_FIX_MULTUS_TEXT_BUSY:-true}"
CONNECTIVITY_TARGET_IP="${SEED_WEB151_SIM_IP:-10.151.0.71}"
CONNECTIVITY_RETRY="${CONNECTIVITY_RETRY:-24}"
CONNECTIVITY_RETRY_INTERVAL_SECONDS="${CONNECTIVITY_RETRY_INTERVAL_SECONDS:-5}"
COLOCATE_IX_PEERS="${SEED_COLOCATE_IX_PEERS:-true}"
CNI_TYPE="${SEED_CNI_TYPE:-bridge}"
CNI_MASTER_INTERFACE="${SEED_CNI_MASTER_INTERFACE:-eth0}"
MASQ_EXEMPT_CIDRS="${SEED_KIND_MASQ_EXEMPT_CIDRS:-10.100.0.0/24,10.150.0.0/24,10.151.0.0/24}"
KIND_FIX_MASQ="${SEED_KIND_FIX_MASQ:-true}"

mkdir -p "${ARTIFACT_DIR}"
rm -f "${ARTIFACT_DIR}"/*.txt "${ARTIFACT_DIR}"/*.log "${ARTIFACT_DIR}"/*.json 2>/dev/null || true

collect_failure_diagnostics() {
    echo ">>> Collecting failure diagnostics"
    kubectl -n "${NAMESPACE}" get deployment,pods,vm,vmi -o wide > "${ARTIFACT_DIR}/failure_overview.txt" || true
    kubectl -n "${NAMESPACE}" get events --sort-by=.lastTimestamp > "${ARTIFACT_DIR}/failure_events.txt" || true

    local vmi_name
    vmi_name="$(kubectl -n "${NAMESPACE}" get vmi -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    if [ -n "${vmi_name}" ]; then
        kubectl -n "${NAMESPACE}" describe vmi "${vmi_name}" > "${ARTIFACT_DIR}/failure_vmi_describe.txt" || true
    fi

    local vm_name
    vm_name="$(kubectl -n "${NAMESPACE}" get vm -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    if [ -n "${vm_name}" ]; then
        kubectl -n "${NAMESPACE}" describe vm "${vm_name}" > "${ARTIFACT_DIR}/failure_vm_describe.txt" || true
    fi

    local launcher_pod
    launcher_pod="$(kubectl -n "${NAMESPACE}" get pods -l kubevirt.io=virt-launcher -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    if [ -n "${launcher_pod}" ]; then
        kubectl -n "${NAMESPACE}" describe pod "${launcher_pod}" > "${ARTIFACT_DIR}/failure_virt_launcher_pod.txt" || true
        kubectl -n "${NAMESPACE}" logs "${launcher_pod}" -c compute --tail=200 > "${ARTIFACT_DIR}/failure_virt_launcher_compute.log" || true
    fi

    kubectl -n kubevirt get pods -o wide > "${ARTIFACT_DIR}/failure_kubevirt_pods.txt" || true
}

read_profile_summary() {
    local summary_path="$1"
    python3 - "$summary_path" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as profile_file:
    data = json.load(profile_file)

print(data.get("requested_profile", ""))
print(data.get("resolved_profile", ""))
print(data.get("router_virtualization_mode", ""))
print(data.get("reason", ""))
PY
}

ensure_multus_ready() {
    if ! kubectl -n kube-system get daemonset/kube-multus-ds >/dev/null 2>&1; then
        echo ">>> Multus not installed (kube-system/daemonset kube-multus-ds missing). This workflow requires Multus." >&2
        echo ">>> Fix: run ./setup_kubevirt_cluster.sh (Kind) or ./scripts/setup_k3s_cluster.sh (K3s)." >&2
        exit 1
    fi

    local desired ready
    desired="$(kubectl -n kube-system get daemonset/kube-multus-ds -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo 0)"
    ready="$(kubectl -n kube-system get daemonset/kube-multus-ds -o jsonpath='{.status.numberReady}' 2>/dev/null || echo 0)"

    if [ "${desired}" != "0" ] && [ "${ready}" = "${desired}" ]; then
        return
    fi

    echo ">>> Multus not ready: ${ready}/${desired}"

    if [ "${AUTO_FIX_MULTUS_TEXT_BUSY}" = "true" ]; then
        local cmd0
        cmd0="$(kubectl -n kube-system get daemonset/kube-multus-ds -o jsonpath='{.spec.template.spec.initContainers[?(@.name==\"install-multus-binary\")].command[0]}' 2>/dev/null || true)"
        if [ "${cmd0}" = "cp" ]; then
            echo ">>> Detected cp-based multus-shim installer; patching to atomic install (avoid 'Text file busy')"
            kubectl -n kube-system patch daemonset/kube-multus-ds --type='strategic' -p "$(
                cat <<'JSON'
{
  "spec": {
    "template": {
      "spec": {
        "initContainers": [
          {
            "name": "install-multus-binary",
            "command": ["/bin/sh", "-c"],
            "args": [
              "set -eu; src=/usr/src/multus-cni/bin/multus-shim; dst=/host/opt/cni/bin/multus-shim; tmp=/host/opt/cni/bin/.multus-shim.tmp.$$; cp \"$src\" \"$tmp\"; chmod 0755 \"$tmp\"; mv -f \"$tmp\" \"$dst\";"
            ]
          }
        ]
      }
    }
  }
}
JSON
            )" >/dev/null || true
        fi
    fi

    kubectl -n kube-system rollout status daemonset/kube-multus-ds --timeout=300s || true

    desired="$(kubectl -n kube-system get daemonset/kube-multus-ds -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo 0)"
    ready="$(kubectl -n kube-system get daemonset/kube-multus-ds -o jsonpath='{.status.numberReady}' 2>/dev/null || echo 0)"

    if [ "${desired}" = "0" ] || [ "${ready}" != "${desired}" ]; then
        echo ">>> Multus still not ready after remediation. Diagnostics:" >&2
        kubectl -n kube-system get daemonset/kube-multus-ds -o wide || true
        kubectl -n kube-system get pods -l name=multus -o wide || true
        kubectl -n kube-system get events --sort-by=.lastTimestamp | tail -n 40 || true
        exit 1
    fi
}

configure_kind_masq_exemptions() {
    if [ "${KIND_FIX_MASQ}" != "true" ]; then
        return
    fi

    if ! command -v docker >/dev/null 2>&1; then
        echo ">>> docker not found; skipping kind masq exemptions"
        return
    fi

    local node cidr
    local -a cidr_list

    IFS=',' read -r -a cidr_list <<< "${MASQ_EXEMPT_CIDRS}"
    if [ "${#cidr_list[@]}" -eq 0 ]; then
        return
    fi

    while IFS= read -r node; do
        [ -z "${node}" ] && continue
        for cidr in "${cidr_list[@]}"; do
            cidr="$(echo "${cidr}" | xargs)"
            [ -z "${cidr}" ] && continue

            if docker exec "${node}" iptables -t nat -C KIND-MASQ-AGENT -d "${cidr}" -j RETURN >/dev/null 2>&1; then
                continue
            fi

            echo ">>> Adding kind masq exemption on ${node}: ${cidr}"
            docker exec "${node}" iptables -t nat -I KIND-MASQ-AGENT 1 -d "${cidr}" -j RETURN >/dev/null
        done
    done < <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
}

echo ">>> Using kube context ${KUBECONTEXT}"
kubectl config use-context "${KUBECONTEXT}" >/dev/null

ensure_multus_ready

NODE_ARCH="$(kubectl get nodes -o jsonpath='{.items[0].status.nodeInfo.architecture}')"
HOST_HAS_KVM="false"
if [ -e /dev/kvm ]; then
    HOST_HAS_KVM="true"
fi

if [ "${NODE_ARCH}" = "arm64" ] && [ "${HOST_HAS_KVM}" = "false" ]; then
    echo ">>> Warning: arm64 host without /dev/kvm detected; auto profile will switch to degraded mode"
fi

LOCAL_BRIDGE_CNI="false"
if [ "${CNI_TYPE}" = "bridge" ] || [ "${CNI_TYPE}" = "host-local" ]; then
    # bridge/host-local behave like node-local L2 in this workflow.
    LOCAL_BRIDGE_CNI="true"
fi

configure_kind_masq_exemptions

CONTROL_NODE="$(kubectl get nodes -l node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
if [ -z "${CONTROL_NODE}" ]; then
    CONTROL_NODE="$(kubectl get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
fi
if [ -z "${CONTROL_NODE}" ]; then
    # Avoid SIGPIPE failures under `set -o pipefail` when awk exits early.
    nodes_txt="$(kubectl get nodes --no-headers 2>/dev/null || true)"
    CONTROL_NODE="$(awk '$3 ~ /(control-plane|master)/ {print $1; exit}' <<<"${nodes_txt}")"
fi

mapfile -t ALL_NODES < <(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
WORKER_NODES="$(printf '%s\n' "${ALL_NODES[@]}" | grep -vx "${CONTROL_NODE}" || true)"
WORKER_A_NODE="$(printf '%s\n' "${WORKER_NODES}" | sed -n '1p')"
WORKER_B_NODE="$(printf '%s\n' "${WORKER_NODES}" | sed -n '2p')"

if [ -z "${CONTROL_NODE}" ] || [ -z "${WORKER_A_NODE}" ]; then
    echo "Expected at least one control-plane and one worker node" >&2
    exit 1
fi

if [ -z "${WORKER_B_NODE}" ]; then
    WORKER_B_NODE="${CONTROL_NODE}"
fi

VM_NODE="${WORKER_A_NODE}"
CONTAINER_NODE_A="${CONTROL_NODE}"
CONTAINER_NODE_B="${WORKER_B_NODE}"

if [ "${COLOCATE_IX_PEERS}" = "true" ]; then
    # Stability knob: with node-local CNI (bridge/host-local), cross-node reachability
    # in kind can be fragile. Co-locating keeps the validation deterministic.
	if [ "${CONTAINER_NODE_B}" != "${CONTAINER_NODE_A}" ]; then
		echo ">>> Co-locating ix100 peers on ${CONTAINER_NODE_A} for bridge CNI reachability"
	fi
	CONTAINER_NODE_B="${CONTAINER_NODE_A}"

	if [ "${LOCAL_BRIDGE_CNI}" = "true" ]; then
		echo ">>> Co-locating VM router with ix100 peers on ${CONTAINER_NODE_A} for ${CNI_TYPE} CNI"
		VM_NODE="${CONTAINER_NODE_A}"
	fi
fi

echo ">>> Node assignment: vm=${VM_NODE}, worker_a=${CONTAINER_NODE_A}, worker_b=${CONTAINER_NODE_B}"
echo ">>> CNI type: ${CNI_TYPE}"

echo ">>> Compiling hybrid topology with runtime profile '${RUNTIME_PROFILE}'"
(
    cd "${EXAMPLE_DIR}" && \
    SEED_CLUSTER_NAME="${CLUSTER_NAME}" \
    SEED_NAMESPACE="${NAMESPACE}" \
    SEED_VM_NODE="${VM_NODE}" \
    SEED_WORKER_A="${CONTAINER_NODE_A}" \
    SEED_WORKER_B="${CONTAINER_NODE_B}" \
    SEED_RUNTIME_PROFILE="${RUNTIME_PROFILE}" \
    SEED_CNI_TYPE="${CNI_TYPE}" \
    SEED_CNI_MASTER_INTERFACE="${CNI_MASTER_INTERFACE}" \
    PYTHONPATH=../.. python3 k8s_hybrid_kubevirt_demo.py
)

MANIFEST_PATH="${OUTPUT_DIR}/k8s.yaml"
BUILD_SCRIPT_PATH="${OUTPUT_DIR}/build_images.sh"
PROFILE_SUMMARY_PATH="${OUTPUT_DIR}/runtime_profile.json"

test -f "${MANIFEST_PATH}"
test -x "${BUILD_SCRIPT_PATH}"
test -f "${PROFILE_SUMMARY_PATH}"

mapfile -t PROFILE_LINES < <(read_profile_summary "${PROFILE_SUMMARY_PATH}")
REQUESTED_PROFILE="${PROFILE_LINES[0]}"
RESOLVED_PROFILE="${PROFILE_LINES[1]}"
ROUTER_MODE="${PROFILE_LINES[2]}"
PROFILE_REASON="${PROFILE_LINES[3]}"

if [ "${RESOLVED_PROFILE}" != "full" ] && [ "${RESOLVED_PROFILE}" != "degraded" ]; then
    echo "Unexpected resolved profile: ${RESOLVED_PROFILE}" >&2
    exit 1
fi

if [ "${RESOLVED_PROFILE}" = "full" ]; then
    EXPECT_VM="true"
else
    EXPECT_VM="false"
fi

echo ">>> Profile resolved: ${REQUESTED_PROFILE} -> ${RESOLVED_PROFILE} (${PROFILE_REASON})"
echo ">>> Router mode: ${ROUTER_MODE}"
cp "${PROFILE_SUMMARY_PATH}" "${ARTIFACT_DIR}/runtime_profile.json"

echo ">>> Verifying compiled manifest"
grep -Eq '"kind": "Deployment"|kind: Deployment' "${MANIFEST_PATH}"

if [ "${EXPECT_VM}" = "true" ]; then
    grep -q '/usr/local/bin/replace_address.sh' "${MANIFEST_PATH}"
    grep -Eq '"kind": "VirtualMachine"|kind: VirtualMachine' "${MANIFEST_PATH}"
    grep -q 'cloudInitNoCloud' "${MANIFEST_PATH}"
else
    if grep -Eq '"kind": "VirtualMachine"|kind: VirtualMachine' "${MANIFEST_PATH}"; then
        echo "Manifest unexpectedly contains VirtualMachine in degraded mode" >&2
        exit 1
    fi
fi

echo ">>> Building and pushing container images"
(cd "${OUTPUT_DIR}" && ./build_images.sh)

if [ "${CLEAN_NAMESPACE}" = "true" ]; then
    echo ">>> Recreating namespace ${NAMESPACE} for clean validation"
    kubectl delete namespace "${NAMESPACE}" --ignore-not-found >/dev/null || true
    if kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
        kubectl wait --for=delete namespace/"${NAMESPACE}" --timeout=300s || true
    fi
fi

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl -n "${NAMESPACE}" delete -f "${MANIFEST_PATH}" --ignore-not-found >/dev/null || true

echo ">>> Deploying manifest"
kubectl apply -n "${NAMESPACE}" -f "${MANIFEST_PATH}" >/dev/null

echo ">>> Waiting for workloads"
if ! kubectl -n "${NAMESPACE}" wait --for=condition=Available --timeout="${DEPLOY_WAIT_TIMEOUT}" deployment --all; then
    collect_failure_diagnostics
    echo "Deployment readiness failed" >&2
    exit 1
fi

if [ "${EXPECT_VM}" = "true" ]; then
    if ! kubectl -n "${NAMESPACE}" wait --for=condition=Ready --timeout="${VMI_WAIT_TIMEOUT}" vmi --all; then
        collect_failure_diagnostics
        echo "VMI readiness failed" >&2
        exit 1
    fi
else
    VM_COUNT="$(kubectl -n "${NAMESPACE}" get vm --no-headers 2>/dev/null | wc -l | tr -d ' ')"
    if [ "${VM_COUNT}" -ne 0 ]; then
        echo "Expected no VM in degraded mode, but found ${VM_COUNT}" >&2
        collect_failure_diagnostics
        exit 1
    fi
fi

echo ">>> Verifying cross-node placement"
NODE_COUNT="$(kubectl -n "${NAMESPACE}" get pods -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort -u | sed '/^$/d' | wc -l)"
if [ "${COLOCATE_IX_PEERS}" = "true" ] && [ "${LOCAL_BRIDGE_CNI}" = "true" ]; then
	# Relaxed placement gate under kind + node-local CNI + colocate strategy.
	echo ">>> Cross-node check relaxed: colocated ix peers with ${CNI_TYPE} CNI (nodes used: ${NODE_COUNT})"
	if [ "${NODE_COUNT}" -lt 1 ]; then
		echo "Expected at least one scheduled node, got ${NODE_COUNT}" >&2
		exit 1
	fi
elif [ "${NODE_COUNT}" -lt 2 ]; then
	echo "Expected pods on at least 2 nodes, got ${NODE_COUNT}" >&2
	exit 1
fi

ROUTER151_POD="$(kubectl -n "${NAMESPACE}" get pods -l seedemu.io/name=router0,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"

echo ">>> Protocol check: BGP established"
BGP_START_EPOCH="$(date +%s)"
BGP_DEADLINE="$((BGP_START_EPOCH + BGP_WAIT_TIMEOUT_SECONDS))"
while true; do
	kubectl -n "${NAMESPACE}" exec "${ROUTER151_POD}" -- birdc s p | tee "${ARTIFACT_DIR}/bird_protocols.txt"
	if grep -q 'Established' "${ARTIFACT_DIR}/bird_protocols.txt"; then
		break
	fi

    NOW_EPOCH="$(date +%s)"
    if [ "${NOW_EPOCH}" -ge "${BGP_DEADLINE}" ]; then
        echo "BGP did not reach Established within ${BGP_WAIT_TIMEOUT_SECONDS}s" >&2
        collect_failure_diagnostics
        exit 1
    fi

	sleep 5
	echo ">>> BGP not Established yet, retrying..."
done

WEB150_POD="$(kubectl -n "${NAMESPACE}" get pods -l seedemu.io/name=web,seedemu.io/asn=150 -o jsonpath='{.items[0].metadata.name}')"
WEB151_POD="$(kubectl -n "${NAMESPACE}" get pods -l seedemu.io/name=web,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"
WEB151_POD_IP="$(kubectl -n "${NAMESPACE}" get pod "${WEB151_POD}" -o jsonpath='{.status.podIP}')"

echo ">>> Connectivity check: ${WEB150_POD} -> ${CONNECTIVITY_TARGET_IP} (web151 podIP=${WEB151_POD_IP})"
CONNECTIVITY_OK="false"
for ((attempt=1; attempt<=CONNECTIVITY_RETRY; attempt++)); do
	if kubectl -n "${NAMESPACE}" exec "${WEB150_POD}" -- ping -c 3 -W 2 "${CONNECTIVITY_TARGET_IP}"; then
		CONNECTIVITY_OK="true"
		break
	fi
	echo ">>> Connectivity attempt ${attempt}/${CONNECTIVITY_RETRY} failed; retrying in ${CONNECTIVITY_RETRY_INTERVAL_SECONDS}s"
	sleep "${CONNECTIVITY_RETRY_INTERVAL_SECONDS}"
done

if [ "${CONNECTIVITY_OK}" != "true" ]; then
	echo "Connectivity to ${CONNECTIVITY_TARGET_IP} failed after ${CONNECTIVITY_RETRY} attempts" >&2
	kubectl -n "${NAMESPACE}" exec "${WEB150_POD}" -- ip route > "${ARTIFACT_DIR}/failure_web150_routes.txt" || true
	kubectl -n "${NAMESPACE}" exec "${WEB150_POD}" -- ping -c 3 -W 2 "${WEB151_POD_IP}" > "${ARTIFACT_DIR}/failure_web150_to_web151_podip_ping.txt" 2>&1 || true
	collect_failure_diagnostics
	exit 1
fi

echo ">>> Self-healing check"
WEB151_DEPLOYMENT="$(kubectl -n "${NAMESPACE}" get pod "${WEB151_POD}" -o jsonpath='{.metadata.labels.app}')"
RECOVERY_CHECK_PATH="${ARTIFACT_DIR}/recovery_check.json"
RECOVERY_START_TS="$(date +%s)"
kubectl -n "${NAMESPACE}" delete pod "${WEB151_POD}" >/dev/null
if kubectl -n "${NAMESPACE}" rollout status deployment/"${WEB151_DEPLOYMENT}" --timeout=600s; then
    RECOVERY_END_TS="$(date +%s)"
    RECOVERY_SECONDS="$((RECOVERY_END_TS - RECOVERY_START_TS))"
    NEW_WEB151_POD="$(kubectl -n "${NAMESPACE}" get pods -l app="${WEB151_DEPLOYMENT}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    cat > "${RECOVERY_CHECK_PATH}" <<EOF
{"status":"recovered","deployment":"${WEB151_DEPLOYMENT}","old_pod":"${WEB151_POD}","new_pod":"${NEW_WEB151_POD}","recovery_seconds":${RECOVERY_SECONDS}}
EOF
else
    RECOVERY_END_TS="$(date +%s)"
    RECOVERY_SECONDS="$((RECOVERY_END_TS - RECOVERY_START_TS))"
    cat > "${RECOVERY_CHECK_PATH}" <<EOF
{"status":"timeout","deployment":"${WEB151_DEPLOYMENT}","old_pod":"${WEB151_POD}","new_pod":null,"recovery_seconds":${RECOVERY_SECONDS}}
EOF
    collect_failure_diagnostics
    echo "Self-healing check failed" >&2
    exit 1
fi

echo ">>> Capturing evidence"
kubectl -n "${NAMESPACE}" get pods -o wide > "${ARTIFACT_DIR}/pods_wide.txt"
kubectl -n "${NAMESPACE}" get deployment -o wide > "${ARTIFACT_DIR}/deployments_wide.txt"
kubectl -n "${NAMESPACE}" get vm,vmi > "${ARTIFACT_DIR}/vm_vmi.txt" 2>/dev/null || true
kubectl -n "${NAMESPACE}" get svc > "${ARTIFACT_DIR}/services.txt" 2>/dev/null || true

echo ">>> Validation completed successfully"
echo ">>> Evidence saved under ${ARTIFACT_DIR}"
