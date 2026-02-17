#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXAMPLE_DIR="${ROOT_DIR}/examples/kubernetes"
OUTPUT_DIR="${EXAMPLE_DIR}/output_kubevirt_hybrid"
CLUSTER_NAME="${SEED_CLUSTER_NAME:-seedemu-kvtest}"
NAMESPACE="${SEED_NAMESPACE:-seedemu-kvtest}"
KUBECONTEXT="kind-${CLUSTER_NAME}"
ARTIFACT_DIR="${SEED_ARTIFACT_DIR:-${ROOT_DIR}/output/kubevirt_validation}"
DEPLOY_WAIT_TIMEOUT="${DEPLOY_WAIT_TIMEOUT:-1200s}"
VMI_WAIT_TIMEOUT="${VMI_WAIT_TIMEOUT:-480s}"
BGP_WAIT_TIMEOUT_SECONDS="${BGP_WAIT_TIMEOUT_SECONDS:-300}"
RUNTIME_PROFILE="${SEED_RUNTIME_PROFILE:-auto}"
CLEAN_NAMESPACE="${SEED_CLEAN_NAMESPACE:-true}"

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

echo ">>> Using kube context ${KUBECONTEXT}"
kubectl config use-context "${KUBECONTEXT}" >/dev/null

NODE_ARCH="$(kubectl get nodes -o jsonpath='{.items[0].status.nodeInfo.architecture}')"
HOST_HAS_KVM="false"
if [ -e /dev/kvm ]; then
    HOST_HAS_KVM="true"
fi

if [ "${NODE_ARCH}" = "arm64" ] && [ "${HOST_HAS_KVM}" = "false" ]; then
    echo ">>> Warning: arm64 host without /dev/kvm detected; auto profile will switch to degraded mode"
fi

CONTROL_NODE="$(kubectl get nodes -l node-role.kubernetes.io/control-plane -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
WORKER_NODES="$(kubectl get nodes --no-headers | awk '$3 !~ /control-plane/ {print $1}')"
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

echo ">>> Compiling hybrid topology with runtime profile '${RUNTIME_PROFILE}'"
(
    cd "${EXAMPLE_DIR}" && \
    SEED_CLUSTER_NAME="${CLUSTER_NAME}" \
    SEED_NAMESPACE="${NAMESPACE}" \
    SEED_VM_NODE="${VM_NODE}" \
    SEED_WORKER_A="${CONTAINER_NODE_A}" \
    SEED_WORKER_B="${CONTAINER_NODE_B}" \
    SEED_RUNTIME_PROFILE="${RUNTIME_PROFILE}" \
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
grep -q '"kind": "Deployment"' "${MANIFEST_PATH}"

if [ "${EXPECT_VM}" = "true" ]; then
    grep -q '/usr/local/bin/replace_address.sh' "${MANIFEST_PATH}"
    grep -q '"kind": "VirtualMachine"' "${MANIFEST_PATH}"
    grep -q 'cloudInitNoCloud' "${MANIFEST_PATH}"
else
    if grep -q '"kind": "VirtualMachine"' "${MANIFEST_PATH}"; then
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
if [ "${NODE_COUNT}" -lt 2 ]; then
    echo "Expected pods on at least 2 nodes, got ${NODE_COUNT}" >&2
    exit 1
fi

WEB150_POD="$(kubectl -n "${NAMESPACE}" get pods -l seedemu.io/name=web,seedemu.io/asn=150 -o jsonpath='{.items[0].metadata.name}')"
WEB151_POD="$(kubectl -n "${NAMESPACE}" get pods -l seedemu.io/name=web,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"
WEB151_IP="$(kubectl -n "${NAMESPACE}" get pod "${WEB151_POD}" -o jsonpath='{.status.podIP}')"

echo ">>> Connectivity check: ${WEB150_POD} -> ${WEB151_IP}"
kubectl -n "${NAMESPACE}" exec "${WEB150_POD}" -- ping -c 4 "${WEB151_IP}"

ROUTER151_POD="$(kubectl -n "${NAMESPACE}" get pods -l seedemu.io/name=router0,seedemu.io/asn=151 -o jsonpath='{.items[0].metadata.name}')"

echo ">>> Protocol check: BGP established"
BGP_DEADLINE=$((SECONDS + BGP_WAIT_TIMEOUT_SECONDS))
while true; do
    kubectl -n "${NAMESPACE}" exec "${ROUTER151_POD}" -- birdc s p | tee "${ARTIFACT_DIR}/bird_protocols.txt"
    if grep -q 'Established' "${ARTIFACT_DIR}/bird_protocols.txt"; then
        break
    fi

    if [ "${SECONDS}" -ge "${BGP_DEADLINE}" ]; then
        echo "BGP did not reach Established within ${BGP_WAIT_TIMEOUT_SECONDS}s" >&2
        collect_failure_diagnostics
        exit 1
    fi

    sleep 5
    echo ">>> BGP not Established yet, retrying..."
done

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
