#!/usr/bin/env python3
"""Python entrypoint for installKubeOvnFabric with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Install Kube-OVN as a non-primary CNI for SeedEMU secondary networks.
#
# Args:
#   $1: Optional configK3s.yaml path. Defaults to ../configK3s.yaml.
#
# Inputs:
#   configK3s.yaml with fabric.type=ovn and optional ovn.* settings.
#
# Outputs/side effects:
#   Installs the Kube-OVN Helm release into the configured K3s cluster. K3s
#   flannel remains the primary CNI for eth0; Kube-OVN only serves Multus
#   secondary interfaces used by SeedEMU simulated networks.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
SETUP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${1:-${SETUP_DIR}/configK3s.yaml}"
HELPER="${SETUP_DIR}/manageK3sConfig.py"

if [ ! -s "${CONFIG_PATH}" ]; then
    echo "Missing config file: ${CONFIG_PATH}" >&2
    exit 1
fi

eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" shell-vars)"
eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" ovn-shell-vars)"

if [ "${fabricType}" != "ovn" ] && [ "${fabricType}" != "kube-ovn" ]; then
    echo "No Kube-OVN fabric configured; skipping OVN install."
    exit 0
fi

requireCommand() {
    # Args:
    #   $1: Command name required by this script.
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required command: $1" >&2
        exit 1
    }
}

runWithTimeout() {
    # Args:
    #   $1: duration accepted by timeout, remaining args: command to run.
    local duration="$1"
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "${duration}" "$@"
    else
        "$@"
    fi
}

sshOptions() {
    # Args:
    #   $1: SSH private key used for the target node.
    local ssh_key="$1"
    printf '%s\n' \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        -o ConnectTimeout=10 \
        -i "$ssh_key"
}

runNodeScript() {
    # Args:
    #   $1: node name, $2: management IP, $3: connection mode, $4: SSH user,
    #   $5: SSH key, $6: shell script to execute on the node.
    local name="$1"
    local ip="$2"
    local connection="$3"
    local ssh_user="$4"
    local ssh_key="$5"
    local script="$6"
    if [ "${connection}" = "local" ]; then
        bash -s <<<"${script}"
        return
    fi
    # shellcheck disable=SC2046
    ssh $(sshOptions "${ssh_key}") "${ssh_user}@${ip}" "bash -s" <<<"${script}"
}

preloadKubeOvnImage() {
    # Pull Kube-OVN once on the setup host, then import the image tar into each
    # K3s node's containerd. This avoids repeated node-side Docker Hub pulls.
    local image="docker.io/kubeovn/kube-ovn:${ovnChartVersion}"
    local mirror_image="docker.m.daocloud.io/kubeovn/kube-ovn:${ovnChartVersion}"
    local tar_path="${ovnHelmCacheDir}/kube-ovn_${ovnChartVersion}.tar"
    mkdir -p "$(dirname "${tar_path}")"
    echo "[ovn] preloading ${image} into K3s containerd nodes"
    if ! runWithTimeout 180s sudo -n docker pull "${image}"; then
        sudo -n docker pull "${mirror_image}"
        sudo -n docker tag "${mirror_image}" "${image}"
    fi
    sudo -n docker save "${image}" -o "${tar_path}"
    sudo -n chmod 0644 "${tar_path}"

    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" node-ssh-vars --name "${name}")"
        echo "  import ${image} to ${name}"
        if [ "${nodeConnection}" = "local" ]; then
            sudo -n k3s ctr images import "${tar_path}"
        else
            local remote_tar="/tmp/$(basename "${tar_path}")"
            # shellcheck disable=SC2046
            scp $(sshOptions "${nodeSshKey}") "${tar_path}" "${nodeSshUser}@${ip}:${remote_tar}"
            # shellcheck disable=SC2046
            ssh -n $(sshOptions "${nodeSshKey}") "${nodeSshUser}@${ip}" \
                "sudo -n k3s ctr images import '${remote_tar}' >/dev/null && rm -f '${remote_tar}'"
        fi
    done < <(python3 "${HELPER}" --config "${CONFIG_PATH}" nodes-tsv)
}

prepareKubeOvnCniBinDir() {
    # Prepare each node's K3s CNI binary directory for Kube-OVN install-cni.
    # Args: none. Reads nodes and ovnCniBinDir from configK3s.yaml.
    #
    # K3s often keeps CNI plugins as symlinks under /var/lib/rancher/k3s/data/cni.
    # Kube-OVN's install-cni init container copies these exact binaries into
    # that same mounted path and fails if a target is a dangling symlink inside
    # the container mount. Remove only the known overwrite targets.
    echo "[ovn] preparing K3s CNI binary directory on all nodes: ${ovnCniBinDir}"
    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" node-ssh-vars --name "${name}")"
        echo "  prepare ${name}"
        runNodeScript "${name}" "${ip}" "${nodeConnection}" "${nodeSshUser}" "${nodeSshKey}" "$(cat <<EOF
set -euo pipefail
sudo -n mkdir -p '${ovnCniBinDir}'
sudo -n rm -f \
    '${ovnCniBinDir}/loopback' \
    '${ovnCniBinDir}/portmap' \
    '${ovnCniBinDir}/kube-ovn' \
    '${ovnCniBinDir}/macvlan' \
    '${ovnCniBinDir}/ipvlan'
EOF
)"
    done < <(python3 "${HELPER}" --config "${CONFIG_PATH}" nodes-tsv)
}

ensureHelm() {
    # Print a helm binary path. If helm is not installed on the host, download a
    # private copy under ovn.helmCacheDir so no system package is modified.
    helmUsable() {
        # Args:
        #   $1: helm binary candidate.
        # A partial curl/tar extraction can leave an executable that segfaults.
        # Validate by running `helm version` before trusting any cached binary.
        local candidate="$1"
        [ -x "${candidate}" ] || return 1
        "${candidate}" version --short >/dev/null 2>&1
    }

    if command -v helm >/dev/null 2>&1 && helmUsable "$(command -v helm)"; then
        command -v helm
        return
    fi

    local helm_dir="${ovnHelmCacheDir}/bin"
    local helm_bin="${helm_dir}/helm"
    if helmUsable "${helm_bin}"; then
        echo "${helm_bin}"
        return
    fi

    mkdir -p "${helm_dir}" "${ovnHelmCacheDir}/download"
    rm -f "${helm_bin}"
    local archive="${ovnHelmCacheDir}/download/helm-v3.15.4-linux-amd64.tar.gz"
    local archive_tmp="${archive}.tmp"
    echo "[ovn] downloading private helm binary to ${helm_bin}" >&2
    rm -f "${archive_tmp}"
    curl --fail --location --show-error --retry 5 --retry-delay 2 --retry-all-errors \
        https://get.helm.sh/helm-v3.15.4-linux-amd64.tar.gz -o "${archive_tmp}"
    tar -tzf "${archive_tmp}" >/dev/null
    mv "${archive_tmp}" "${archive}"
    rm -rf "${ovnHelmCacheDir}/download/linux-amd64"
    tar -xzf "${archive}" -C "${ovnHelmCacheDir}/download"
    cp "${ovnHelmCacheDir}/download/linux-amd64/helm" "${helm_bin}"
    chmod +x "${helm_bin}"
    if ! helmUsable "${helm_bin}"; then
        rm -f "${helm_bin}"
        echo "Downloaded helm binary is not usable: ${helm_bin}" >&2
        exit 1
    fi
    echo "${helm_bin}"
}

installKubeOvn() {
    # Install Kube-OVN in non-primary mode. Kube-OVN's CNI binary is placed into
    # the K3s CNI bin dir so Multus can invoke type=kube-ovn delegates.
    local helm_bin="$1"

    "${helm_bin}" repo add "${ovnHelmRepoName}" "${ovnHelmRepoUrl}" >/dev/null 2>&1 || true
    "${helm_bin}" repo update >/dev/null

    kubectl --kubeconfig "${outputKubeconfig}" label node "${k3sMasterName}" kube-ovn/role=master --overwrite

    echo "[ovn] installing Kube-OVN ${ovnChartVersion} in non-primary CNI mode"
    "${helm_bin}" upgrade --install "${ovnReleaseName}" "${ovnHelmRepoName}/kube-ovn" \
        --kubeconfig "${outputKubeconfig}" \
        --namespace "${ovnNamespace}" \
        --version "${ovnChartVersion}" \
        --set cni_conf.NON_PRIMARY_CNI=true \
        --set cni_conf.CNI_CONF_DIR="${ovnCniConfDir}" \
        --set cni_conf.MOUNT_CNI_CONF_DIR="${ovnMountCniConfDir}" \
        --set cni_conf.CNI_BIN_DIR="${ovnCniBinDir}" \
        --set networking.TUNNEL_TYPE="${ovnTunnelType}" \
        --set networking.IFACE="${ovnIface}" \
        --set ipv4.POD_CIDR="${ovnPodCidr}" \
        --set ipv4.POD_GATEWAY="${ovnPodGateway}" \
        --set ipv4.SVC_CIDR="${ovnServiceCidr}" \
        --set ipv4.JOIN_CIDR="${ovnJoinCidr}" \
        --set MASTER_NODES="${ovnMasterNodes}" \
        --wait \
        --timeout 10m
}

waitKubeOvnReady() {
    # Confirm the controller, OVS/OVN daemonset, and CNI daemonset are rolled
    # out before the running stage creates Kube-OVN NAD/Subnet resources.
    local resources=(
        "deployment/kube-ovn-controller"
        "deployment/ovn-central"
        "daemonset/ovs-ovn"
        "daemonset/kube-ovn-cni"
    )
    for resource in "${resources[@]}"; do
        if kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" get "${resource}" >/dev/null 2>&1; then
            kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" rollout status "${resource}" --timeout=600s
        fi
    done
    kubectl --kubeconfig "${outputKubeconfig}" wait --for=condition=Established crd/subnets.kubeovn.io --timeout=300s
    kubectl --kubeconfig "${outputKubeconfig}" wait --for=condition=Established crd/vpcs.kubeovn.io --timeout=300s
}

repairK3sCniBinDirAfterKubeOvnInstall() {
    # Kube-OVN's install-cni init container runs inside a container mount of
    # the K3s CNI bin dir. On K3s this can leave the host dir without the
    # primary loopback/portmap links or without the kube-ovn delegate binary.
    # Use a short-lived hostNetwork pod per node so this repair does not depend
    # on the CNI plugin path that it is fixing.
    echo "[ovn] verifying K3s CNI binaries after Kube-OVN install"
    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        local pod_name
        pod_name="seedemu-ovn-cni-repair-$(printf '%s' "${name}" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9-' '-')"
        pod_name="${pod_name%-}"
        echo "  repair ${name} with pod/${pod_name}"
        kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" delete pod "${pod_name}" \
            --ignore-not-found=true --wait=false >/dev/null 2>&1 || true
        cat <<EOF | kubectl --kubeconfig "${outputKubeconfig}" apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${pod_name}
  namespace: ${ovnNamespace}
spec:
  restartPolicy: Never
  hostNetwork: true
  nodeName: ${name}
  tolerations:
    - operator: Exists
  containers:
    - name: repair
      image: docker.io/kubeovn/kube-ovn:${ovnChartVersion}
      imagePullPolicy: IfNotPresent
      command:
        - /bin/sh
        - -xec
        - |
          target=\$(readlink /host-cni/bridge || true)
          if [ -z "\${target}" ]; then
            target=/var/lib/rancher/k3s/data/current/bin/cni
          fi
          ln -sf "\${target}" /host-cni/loopback
          ln -sf "\${target}" /host-cni/portmap
          cp -f /kube-ovn/kube-ovn /host-cni/kube-ovn
          chmod 0755 /host-cni/kube-ovn
          ls -l /host-cni | egrep 'loopback|portmap|bridge|flannel|host-local|kube-ovn' || true
      securityContext:
        privileged: true
        runAsUser: 0
      volumeMounts:
        - name: host-cni
          mountPath: /host-cni
  volumes:
    - name: host-cni
      hostPath:
        path: ${ovnCniBinDir}
        type: DirectoryOrCreate
EOF
        for _ in $(seq 1 60); do
            local phase
            phase="$(kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" get pod "${pod_name}" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
            if [ "${phase}" = "Succeeded" ]; then
                kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" logs "${pod_name}" --tail=80 || true
                break
            fi
            if [ "${phase}" = "Failed" ]; then
                kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" logs "${pod_name}" --tail=120 || true
                return 1
            fi
            sleep 2
        done
        local final_phase
        final_phase="$(kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" get pod "${pod_name}" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
        if [ "${final_phase}" != "Succeeded" ]; then
            kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" describe pod "${pod_name}" || true
            return 1
        fi
        kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" delete pod "${pod_name}" --wait=false >/dev/null 2>&1 || true
    done < <(python3 "${HELPER}" --config "${CONFIG_PATH}" nodes-tsv)
}

main() {
    requireCommand curl
    requireCommand kubectl
    requireCommand python3
    requireCommand scp
    requireCommand ssh
    requireCommand docker
    requireCommand tar

    if [ ! -s "${outputKubeconfig}" ]; then
        echo "Kubeconfig not found: ${outputKubeconfig}" >&2
        echo "Run applyK3sCluster.py or k8sTools.py build before installing Kube-OVN." >&2
        exit 1
    fi

    local helm_bin
    helm_bin="$(ensureHelm)"
    preloadKubeOvnImage
    prepareKubeOvnCniBinDir
    installKubeOvn "${helm_bin}"
    waitKubeOvnReady
    repairK3sCniBinDirAfterKubeOvnInstall
    echo "Kube-OVN non-primary CNI is ready."
}

main "$@"
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
