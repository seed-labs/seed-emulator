#!/usr/bin/env python3
"""Python entrypoint for validateClusterPreflight with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Validate that compile output, kubeconfig, registry, remote Docker/buildx, and
# all Kubernetes nodes are ready before running make build/up.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
CONFIG_PATH="${SCRIPT_DIR}/configRunning.yaml"
HELPER="${SCRIPT_DIR}/manageK8sManifest.py"

usage() {
    cat <<EOF
Usage: $0 [--config configRunning.yaml]

Validate the running-stage YAML config and the cluster it points to.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

OUTPUT_DIR="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key outputDir)"
MANIFEST="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key manifest)"
IMAGES_YAML="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key imagesYaml)"
KUBECONFIG_PATH="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key kubeconfig)"
REGISTRY_PREFIX="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key registryPrefix)"
IMAGE_REGISTRY_PREFIX="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key imageRegistryPrefix)"
SSH_USER="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key sshUser)"
SSH_KEY="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key sshKey)"
MASTER_CONNECTION="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key masterConnection)"
NETWORK_BACKEND="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key networkBackend)"

ssh_args=(-n -i "${SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=8)

fail() {
    echo "[preflight][ERROR] $*" >&2
    exit 1
}

requireCommand() {
    # Args:
    #   $1: command name expected in PATH
    command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

requireFile() {
    # Args:
    #   $1: required file path
    [ -f "$1" ] || fail "missing file: $1"
}

registry_ref="${REGISTRY_PREFIX#http://}"
registry_ref="${registry_ref#https://}"
registry_ref="${registry_ref%%/*}"
registry_host="${registry_ref%%:*}"
registry_url="http://${registry_ref}"

declare -A node_config_ip=()
declare -A node_connection=()
declare -A node_user=()
declare -A node_key=()
while IFS=$'\t' read -r access_name access_ip access_connection access_user access_key; do
    [ -n "${access_name}" ] || continue
    node_config_ip["${access_name}"]="${access_ip}"
    node_connection["${access_name}"]="${access_connection}"
    node_user["${access_name}"]="${access_user}"
    node_key["${access_name}"]="${access_key}"
done < <(python3 "${HELPER}" node-access --config "${CONFIG_PATH}")

echo "=== native-k8s preflight ==="
echo "config=${CONFIG_PATH}"
echo "output_dir=${OUTPUT_DIR}"
echo "manifest=${MANIFEST}"
echo "images_yaml=${IMAGES_YAML}"
echo "kubeconfig=${KUBECONFIG_PATH}"
echo "registry_prefix=${REGISTRY_PREFIX}"
echo "image_registry_prefix=${IMAGE_REGISTRY_PREFIX}"
echo "network_backend=${NETWORK_BACKEND}"

echo "[1/7] Local tools and compile output"
requireCommand python3
requireCommand kubectl
requireCommand curl
requireCommand ssh
requireFile "${HELPER}"
requireFile "${MANIFEST}"
requireFile "${IMAGES_YAML}"
requireFile "${KUBECONFIG_PATH}"
[ -d "${OUTPUT_DIR}" ] || fail "missing output directory: ${OUTPUT_DIR}"
[ -s "${MANIFEST}" ] || fail "empty manifest: ${MANIFEST}"
[ -s "${IMAGES_YAML}" ] || fail "empty images yaml: ${IMAGES_YAML}"

namespace="$(python3 "${HELPER}" namespace --manifest "${MANIFEST}")"
[ -n "${namespace}" ] || fail "cannot determine namespace from ${MANIFEST}"
image_count="$(python3 "${HELPER}" mapped-images --images-yaml "${IMAGES_YAML}" --image-registry-prefix "${IMAGE_REGISTRY_PREFIX}" --registry-prefix "${REGISTRY_PREFIX}" | wc -l)"
[ "${image_count}" -gt 0 ] || fail "no images found in ${IMAGES_YAML}"
echo "namespace=${namespace}"
echo "image_count=${image_count}"

echo "[2/7] Kubeconfig and API server"
kubectl --kubeconfig "${KUBECONFIG_PATH}" version --client=true >/dev/null
kubectl --kubeconfig "${KUBECONFIG_PATH}" get nodes -o wide

echo "[3/7] Node readiness"
not_ready="$(
    kubectl --kubeconfig "${KUBECONFIG_PATH}" get nodes \
        -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.conditions[?(@.type=="Ready")]}{.status}{end}{"\n"}{end}' \
    | awk '$2 != "True" {print $1}'
)"
[ -z "${not_ready}" ] || fail "not-ready nodes: ${not_ready//$'\n'/ }"

echo "[4/7] kube-system baseline"
kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system get pods -o wide
bad_system_pods="$(
    kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system get pods --no-headers 2>/dev/null \
    | awk '$3 !~ /^(Running|Completed)$/ {print $1 ":" $3}'
)"
[ -z "${bad_system_pods}" ] || fail "kube-system has unhealthy pods: ${bad_system_pods//$'\n'/ }"
if [ "${NETWORK_BACKEND}" = "kube-ovn" ]; then
    kubectl --kubeconfig "${KUBECONFIG_PATH}" wait --for=condition=Established crd/subnets.kubeovn.io --timeout=120s
    kubectl --kubeconfig "${KUBECONFIG_PATH}" wait --for=condition=Established crd/vpcs.kubeovn.io --timeout=120s
    kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system rollout status deployment/kube-ovn-controller --timeout=300s
    kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system rollout status daemonset/kube-ovn-cni --timeout=300s
    kubectl --kubeconfig "${KUBECONFIG_PATH}" -n kube-system rollout status daemonset/ovs-ovn --timeout=300s
fi

echo "[5/7] Namespace baseline"
if kubectl --kubeconfig "${KUBECONFIG_PATH}" get namespace "${namespace}" >/dev/null 2>&1; then
    workload_count="$(
        kubectl --kubeconfig "${KUBECONFIG_PATH}" -n "${namespace}" \
            get pods,deployments.apps,replicasets.apps,statefulsets.apps,daemonsets.apps,jobs.batch,cronjobs.batch \
            --ignore-not-found --no-headers 2>/dev/null | wc -l
    )"
    if [ "${workload_count}" -gt 0 ]; then
        fail "namespace ${namespace} already has ${workload_count} workload resources; run make clean or wait for previous cleanup before make up"
    fi
    echo "namespace ${namespace} already exists without workload resources; continuing"
else
    echo "namespace ${namespace} is absent"
fi

echo "[6/7] Registry health"
code="$(curl -s -o /dev/null -w '%{http_code}' "${registry_url}/v2/" || true)"
case "${code}" in
    200|401) echo "local registry_http=${code}" ;;
    *) fail "registry ${registry_url}/v2/ is not healthy from local host, http=${code}" ;;
esac

ssh_target="${SSH_USER}@${registry_host}"
if [ "${MASTER_CONNECTION}" = "local" ]; then
    echo "registry-host local registry_http=${code}"
else
    requireFile "${SSH_KEY}"
    ssh "${ssh_args[@]}" "${ssh_target}" "curl -s -o /dev/null -w '%{http_code}' '${registry_url}/v2/'" \
        | awk '{print "registry-host registry_http="$0; if ($0 != "200" && $0 != "401") exit 1}' \
        || fail "registry ${registry_url}/v2/ is not healthy from ${ssh_target}"
fi

echo "[7/7] Remote build prerequisites and node registry reachability"
if [ "${MASTER_CONNECTION}" = "local" ]; then
    sudo -n docker version >/dev/null && sudo -n docker buildx version >/dev/null \
        || fail "docker/buildx is not ready on local registry host"
else
    ssh "${ssh_args[@]}" "${ssh_target}" "sudo -n docker version >/dev/null && sudo -n docker buildx version >/dev/null" \
        || fail "docker/buildx is not ready on ${ssh_target}"
fi
echo "registry-host docker/buildx ok"

while IFS=$'\t' read -r node_name node_ip; do
    [ -n "${node_name}" ] || continue
    node_access="${node_connection[$node_name]:-}"
    [ -n "${node_access}" ] || fail "node ${node_name} is not present in configK3s.yaml"
    target_ip="${node_ip:-${node_config_ip[$node_name]}}"
    [ -n "${target_ip}" ] || fail "cannot determine InternalIP for node ${node_name}"
    if [ "${node_access}" = "local" ]; then
        code="$(curl -s -o /dev/null -w '%{http_code}' "${registry_url}/v2/" || true)"
    else
        requireFile "${node_key[$node_name]}"
        node_target="${node_user[$node_name]}@${target_ip}"
        node_ssh_args=(-n -i "${node_key[$node_name]}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o BatchMode=yes -o ConnectTimeout=8)
        code="$(ssh "${node_ssh_args[@]}" "${node_target}" "curl -s -o /dev/null -w '%{http_code}' '${registry_url}/v2/' || true")"
    fi
    printf '%s\t%s\tregistry_http=%s\n' "${node_name}" "${node_ip}" "${code}"
    case "${code}" in
        200|401) ;;
        *) fail "registry ${registry_url}/v2/ is not reachable from ${node_name} (${node_ip}), http=${code}" ;;
    esac
done < <(
    kubectl --kubeconfig "${KUBECONFIG_PATH}" get nodes \
        -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.addresses[?(@.type=="InternalIP")].address}{"\n"}{end}'
)

echo "Preflight completed"
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
