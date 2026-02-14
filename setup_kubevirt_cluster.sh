#!/bin/bash
set -euo pipefail

CLUSTER_NAME="${SEED_CLUSTER_NAME:-seedemu-kvtest}"
REGISTRY_NAME="${REGISTRY_NAME:-kind-registry}"
REGISTRY_PORT="${REGISTRY_PORT:-5001}"
KIND_VERSION="${KIND_VERSION:-v0.27.0}"
K8S_NODE_IMAGE="${K8S_NODE_IMAGE:-kindest/node:v1.32.2}"
WORKER_COUNT="${WORKER_COUNT:-2}"
MULTUS_VERSION="${MULTUS_VERSION:-v4.1.0}"
KUBEVIRT_VERSION="${KUBEVIRT_VERSION:-v1.7.0}"
CNI_PLUGINS_VERSION="${CNI_PLUGINS_VERSION:-v1.8.0}"

MULTUS_MANIFEST_URL="https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/${MULTUS_VERSION}/deployments/multus-daemonset-thick.yml"
KUBEVIRT_OPERATOR_URL="https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-operator.yaml"
KUBEVIRT_CR_URL="https://github.com/kubevirt/kubevirt/releases/download/${KUBEVIRT_VERSION}/kubevirt-cr.yaml"

kind_arch=""
cni_arch=""

resolve_arch() {
    case "$(uname -m)" in
        x86_64)
            kind_arch="amd64"
            cni_arch="amd64"
            ;;
        aarch64|arm64)
            kind_arch="arm64"
            cni_arch="arm64"
            ;;
        *)
            echo "Unsupported architecture: $(uname -m)" >&2
            exit 1
            ;;
    esac
}

install_kind_if_missing() {
    if command -v kind >/dev/null 2>&1; then
        return
    fi

    echo ">>> Installing kind ${KIND_VERSION}"
    curl -fsSL -o ./kind "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-${kind_arch}"
    chmod +x ./kind

    if command -v sudo >/dev/null 2>&1; then
        sudo mv ./kind /usr/local/bin/kind
    else
        mv ./kind /usr/local/bin/kind
    fi
}

ensure_local_registry() {
    if [ "$(docker inspect -f '{{.State.Running}}' "${REGISTRY_NAME}" 2>/dev/null || true)" != 'true' ]; then
        echo ">>> Creating local registry ${REGISTRY_NAME}:${REGISTRY_PORT}"
        docker run -d --restart=always -p "127.0.0.1:${REGISTRY_PORT}:5000" --name "${REGISTRY_NAME}" registry:2 >/dev/null
    else
        echo ">>> Registry ${REGISTRY_NAME} already running"
    fi
}

create_kind_cluster_if_needed() {
    if kind get clusters | grep -qx "${CLUSTER_NAME}"; then
        echo ">>> Cluster ${CLUSTER_NAME} already exists"
        return
    fi

    echo ">>> Creating kind cluster ${CLUSTER_NAME} with ${K8S_NODE_IMAGE}"
    {
    cat <<KINDCFG
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."localhost:${REGISTRY_PORT}"]
    endpoint = ["http://${REGISTRY_NAME}:5000"]
nodes:
- role: control-plane
  image: ${K8S_NODE_IMAGE}
KINDCFG
    for _ in $(seq 1 "${WORKER_COUNT}"); do
        cat <<KINDCFG
- role: worker
  image: ${K8S_NODE_IMAGE}
KINDCFG
    done
    } | kind create cluster --name "${CLUSTER_NAME}" --config=-
}

ensure_registry_network_connectivity() {
    if [ "$(docker inspect -f '{{json .NetworkSettings.Networks.kind}}' "${REGISTRY_NAME}")" = 'null' ]; then
        docker network connect kind "${REGISTRY_NAME}"
    fi
}

ensure_cni_plugins_for_multus() {
    local nodes
    nodes="$(kind get nodes --name "${CLUSTER_NAME}")"

    if [ -z "${nodes}" ]; then
        echo "Failed to discover kind nodes for ${CLUSTER_NAME}" >&2
        exit 1
    fi

    local first_node
    first_node="$(printf '%s\n' "${nodes}" | head -n 1)"

    if docker exec "${first_node}" test -x /opt/cni/bin/bridge; then
        echo ">>> CNI bridge plugin already present on kind nodes"
        return
    fi

    echo ">>> Installing CNI bridge plugin ${CNI_PLUGINS_VERSION} into kind nodes"
    local tmpdir
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "${tmpdir}"' RETURN

    local archive_name
    archive_name="cni-plugins-linux-${cni_arch}-${CNI_PLUGINS_VERSION}.tgz"

    curl -fsSL -o "${tmpdir}/${archive_name}" "https://github.com/containernetworking/plugins/releases/download/${CNI_PLUGINS_VERSION}/${archive_name}"
    tar -xzf "${tmpdir}/${archive_name}" -C "${tmpdir}"

    local plugin
    for plugin in bridge tuning macvlan vlan; do
        if [ ! -f "${tmpdir}/${plugin}" ]; then
            echo "Missing plugin binary in archive: ${plugin}" >&2
            exit 1
        fi
    done

    local node
    while IFS= read -r node; do
        [ -z "${node}" ] && continue
        docker cp "${tmpdir}/bridge" "${node}:/opt/cni/bin/bridge"
        docker cp "${tmpdir}/tuning" "${node}:/opt/cni/bin/tuning"
        docker cp "${tmpdir}/macvlan" "${node}:/opt/cni/bin/macvlan"
        docker cp "${tmpdir}/vlan" "${node}:/opt/cni/bin/vlan"
        docker exec "${node}" chmod +x /opt/cni/bin/bridge /opt/cni/bin/tuning /opt/cni/bin/macvlan /opt/cni/bin/vlan
    done <<< "${nodes}"

    trap - RETURN
    rm -rf "${tmpdir}"
}

install_multus() {
    echo ">>> Installing Multus ${MULTUS_VERSION}"
    kubectl apply -f "${MULTUS_MANIFEST_URL}" >/dev/null
    kubectl -n kube-system rollout status daemonset/kube-multus-ds --timeout=300s
}

install_kubevirt() {
    echo ">>> Installing KubeVirt ${KUBEVIRT_VERSION}"
    kubectl apply -f "${KUBEVIRT_OPERATOR_URL}" >/dev/null
    kubectl -n kubevirt rollout status deployment/virt-operator --timeout=600s
    kubectl apply -f "${KUBEVIRT_CR_URL}" >/dev/null

    until kubectl -n kubevirt get kubevirt kubevirt >/dev/null 2>&1; do
        sleep 2
    done

    local virt_support
    virt_support="$(egrep -c '(vmx|svm)' /proc/cpuinfo || true)"
    if [ "${virt_support}" -eq 0 ] || [ ! -e /dev/kvm ]; then
        echo ">>> Hardware virtualization unavailable, enabling KubeVirt software emulation"
        kubectl -n kubevirt patch kubevirt kubevirt --type merge -p '{"spec":{"configuration":{"developerConfiguration":{"useEmulation":true}}}}' >/dev/null
    fi

    kubectl -n kubevirt wait --for=condition=Available --timeout=900s kubevirt/kubevirt
    kubectl -n kubevirt rollout status deployment/virt-api --timeout=600s
    kubectl -n kubevirt rollout status deployment/virt-controller --timeout=600s
    if ! kubectl -n kubevirt rollout status daemonset/virt-handler --timeout=600s; then
        kubectl -n kubevirt get pods -o wide
        kubectl -n kubevirt logs -l kubevirt.io=virt-handler --tail=50 || true
        echo "virt-handler rollout failed. If this host has low inotify limits, retry with WORKER_COUNT=1." >&2
        exit 1
    fi
}

validate_registry_pull_chain() {
    echo ">>> Validating registry pull chain"
    local registry_check_image
    registry_check_image="localhost:${REGISTRY_PORT}/seedemu/registry-check:latest"

    docker pull --quiet busybox:1.36 >/dev/null
    docker tag busybox:1.36 "${registry_check_image}"
    docker push "${registry_check_image}" >/dev/null

    kubectl -n kube-system delete pod registry-self-check --ignore-not-found >/dev/null
    kubectl -n kube-system run registry-self-check --image="${registry_check_image}" --restart=Never --command -- sh -c 'echo registry-ok' >/dev/null
    kubectl -n kube-system wait --for=jsonpath='{.status.phase}'=Succeeded --timeout=180s pod/registry-self-check
    kubectl -n kube-system logs pod/registry-self-check
    kubectl -n kube-system delete pod registry-self-check --ignore-not-found >/dev/null
}

write_local_registry_configmap() {
    cat <<CFG | kubectl apply -f - >/dev/null
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-registry-hosting
  namespace: kube-public
data:
  localRegistryHosting.v1: |
    host: "localhost:${REGISTRY_PORT}"
    help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
CFG
}

echo ">>> Starting SEED Emulator Kind + Multus + KubeVirt setup"

command -v docker >/dev/null 2>&1 || { echo "Docker is required." >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required." >&2; exit 1; }

resolve_arch
install_kind_if_missing
ensure_local_registry
create_kind_cluster_if_needed
ensure_registry_network_connectivity

kubectl config use-context "kind-${CLUSTER_NAME}" >/dev/null
kubectl taint nodes -l node-role.kubernetes.io/control-plane node-role.kubernetes.io/control-plane:NoSchedule- >/dev/null 2>&1 || true
write_local_registry_configmap

ensure_cni_plugins_for_multus
install_multus
install_kubevirt
validate_registry_pull_chain

echo ">>> Setup complete"
kubectl get nodes -o wide
kubectl -n kube-system get pods -l name=multus
kubectl -n kubevirt get pods
