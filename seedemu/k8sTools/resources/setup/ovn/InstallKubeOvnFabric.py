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
HELPER="${SETUP_DIR}/ManageK3sConfig.py"

if [ ! -s "${CONFIG_PATH}" ]; then
    echo "Missing config file: ${CONFIG_PATH}" >&2
    exit 1
fi

eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" shell-vars)"
eval "$(python3 "${HELPER}" --config "${CONFIG_PATH}" ovn-shell-vars)"
seedemuOffline="${seedemuOffline:-false}"
export HELM_CONFIG_HOME="${HELM_CONFIG_HOME:-${ovnHelmCacheDir}/helm-home/config}"
export HELM_CACHE_HOME="${HELM_CACHE_HOME:-${ovnHelmCacheDir}/helm-home/cache}"
export HELM_DATA_HOME="${HELM_DATA_HOME:-${ovnHelmCacheDir}/helm-home/data}"
mkdir -p "${HELM_CONFIG_HOME}" "${HELM_CACHE_HOME}" "${HELM_DATA_HOME}"

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

isTrue() {
    # Args:
    #   $1: boolean-like shell/YAML value.
    case "${1,,}" in
        true|1|yes|on)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

validTarball() {
    # Args:
    #   $1: tar or tar.gz file path.
    local path="$1"
    [ -s "${path}" ] && tar -tf "${path}" >/dev/null 2>&1
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
    local image="${ovnImageRegistry}/${ovnImageRepository}:${ovnImageTag}"
    local mirror_image="${ovnImageMirror}"
    local cache_tag
    cache_tag="$(printf '%s_%s_%s' "${ovnImageRegistry}" "${ovnImageRepository}" "${ovnImageTag}" | tr '/:' '__')"
    local tar_path="${ovnHelmCacheDir}/${cache_tag}.tar"
    mkdir -p "$(dirname "${tar_path}")"
    echo "[ovn] preloading ${image} into K3s containerd nodes"
    if validTarball "${tar_path}"; then
        echo "  reuse Kube-OVN image cache ${tar_path}"
    else
        if sudo -n docker image inspect "${image}" >/dev/null 2>&1; then
            :
        elif isTrue "${seedemuOffline}"; then
            echo "Offline mode is enabled and Kube-OVN image cache is missing: ${tar_path}" >&2
            exit 1
        else
            if ! runWithTimeout 180s sudo -n docker pull "${image}"; then
                sudo -n docker pull "${mirror_image}"
                sudo -n docker tag "${mirror_image}" "${image}"
            fi
        fi
        local tar_tmp="${tar_path}.tmp"
        rm -f "${tar_tmp}"
        sudo -n docker save "${image}" -o "${tar_tmp}"
        sudo -n chmod 0644 "${tar_tmp}"
        validTarball "${tar_tmp}" || {
            echo "Saved Kube-OVN image tar is not readable: ${tar_tmp}" >&2
            exit 1
        }
        mv -f "${tar_tmp}" "${tar_path}"
    fi

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
    # the container mount. Some chart versions still touch /opt/cni/bin even
    # when CNI_BIN_DIR is configured, so sanitize that compatibility path too.
    # Remove only known Kube-OVN overwrite targets.
    echo "[ovn] preparing CNI binary directories on all nodes: ${ovnCniBinDir}, /opt/cni/bin"
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
sudo -n mkdir -p /opt/cni/bin
sudo -n rm -f \
    /opt/cni/bin/loopback \
    /opt/cni/bin/portmap \
    /opt/cni/bin/kube-ovn
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

    local helm_dir="${ovnHelmCacheDir}/bin"
    local helm_bin="${helm_dir}/helm"
    if helmUsable "${helm_bin}"; then
        echo "${helm_bin}"
        return
    fi

    local archive="${ovnHelmCacheDir}/download/helm-v3.15.4-linux-amd64.tar.gz"
    if validTarball "${archive}"; then
        mkdir -p "${helm_dir}"
        rm -rf "${ovnHelmCacheDir}/download/linux-amd64"
        tar -xzf "${archive}" -C "${ovnHelmCacheDir}/download"
        cp "${ovnHelmCacheDir}/download/linux-amd64/helm" "${helm_bin}"
        chmod +x "${helm_bin}"
        if helmUsable "${helm_bin}"; then
            echo "${helm_bin}"
            return
        fi
        rm -f "${helm_bin}"
    fi

    if command -v helm >/dev/null 2>&1 && helmUsable "$(command -v helm)"; then
        command -v helm
        return
    fi

    if isTrue "${seedemuOffline}"; then
        echo "Offline mode is enabled and no usable Helm binary/archive is cached under ${ovnHelmCacheDir}" >&2
        exit 1
    fi

    mkdir -p "${helm_dir}" "${ovnHelmCacheDir}/download"
    rm -f "${helm_bin}"
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

ensureKubeOvnChart() {
    # Args:
    #   $1: helm binary path.
    # Prints a local chart .tgz path, downloading it into ovn.helmCacheDir only
    # when no valid cached chart exists.
    local helm_bin="$1"
    local charts_dir="${ovnHelmCacheDir}/charts"
    local chart_path="${charts_dir}/kube-ovn-${ovnChartVersion}.tgz"
    mkdir -p "${charts_dir}"
    if validTarball "${chart_path}"; then
        echo "${chart_path}"
        return
    fi
    local existing_chart
    existing_chart="$(find "${charts_dir}" -maxdepth 1 -type f -name "kube-ovn*${ovnChartVersion}*.tgz" -print -quit 2>/dev/null || true)"
    if [ -n "${existing_chart}" ] && validTarball "${existing_chart}"; then
        if [ "${existing_chart}" != "${chart_path}" ]; then
            cp -f "${existing_chart}" "${chart_path}"
        fi
        echo "${chart_path}"
        return
    fi
    if isTrue "${seedemuOffline}"; then
        echo "Offline mode is enabled and Kube-OVN chart cache is missing: ${chart_path}" >&2
        exit 1
    fi
    "${helm_bin}" repo add "${ovnHelmRepoName}" "${ovnHelmRepoUrl}" >/dev/null 2>&1 || true
    "${helm_bin}" repo update >/dev/null
    rm -f "${chart_path}.tmp"
    "${helm_bin}" pull "${ovnHelmRepoName}/kube-ovn" \
        --version "${ovnChartVersion}" \
        --destination "${charts_dir}"
    existing_chart="$(find "${charts_dir}" -maxdepth 1 -type f -name "kube-ovn*${ovnChartVersion}*.tgz" -print -quit 2>/dev/null || true)"
    if [ -z "${existing_chart}" ] || ! validTarball "${existing_chart}"; then
        echo "Failed to cache Kube-OVN chart version ${ovnChartVersion} under ${charts_dir}" >&2
        exit 1
    fi
    if [ "${existing_chart}" != "${chart_path}" ]; then
        cp -f "${existing_chart}" "${chart_path}"
    fi
    echo "${chart_path}"
}

installKubeOvn() {
    # Install Kube-OVN in non-primary mode. Kube-OVN's CNI binary is placed into
    # the K3s CNI bin dir so Multus can invoke type=kube-ovn delegates.
    local helm_bin="$1"
    local chart_ref="$2"

    kubectl --kubeconfig "${outputKubeconfig}" label node "${k3sMasterName}" kube-ovn/role=master --overwrite

    echo "[ovn] installing Kube-OVN ${ovnChartVersion} in non-primary CNI mode"
    "${helm_bin}" upgrade --install "${ovnReleaseName}" "${chart_ref}" \
        --kubeconfig "${outputKubeconfig}" \
        --namespace "${ovnNamespace}" \
        --set global.registry.address="${ovnImageRegistry}" \
        --set global.images.kubeovn.repository="${ovnImageRepository}" \
        --set global.images.kubeovn.tag="${ovnImageTag}" \
        --set cni_conf.NON_PRIMARY_CNI=true \
        --set cni_conf.CNI_CONF_DIR="${ovnCniConfDir}" \
        --set cni_conf.MOUNT_CNI_CONF_DIR="${ovnMountCniConfDir}" \
        --set cni_conf.CNI_BIN_DIR="${ovnCniBinDir}" \
        --set networking.TUNNEL_TYPE="${ovnTunnelType}" \
        --set networking.IFACE="${ovnIface}" \
        --set networking.OVN_NORTHD_N_THREADS="${ovnNorthdThreads}" \
        --set performance.WORKER_NUM="${ovnControllerWorkerNum}" \
        --set func.ENABLE_LB="${ovnEnableLb}" \
        --set func.ENABLE_NP="${ovnEnableNp}" \
        --set networking.ENABLE_EIP_SNAT="${ovnEnableEipSnat}" \
        --set func.ENABLE_NAT_GW="${ovnEnableNatGw}" \
        --set func.ENABLE_LB_SVC="${ovnEnableLbSvc}" \
        --set func.ENABLE_EXTERNAL_VPC="${ovnEnableExternalVpc}" \
        --set func.CHECK_GATEWAY="${ovnCheckGateway}" \
        --set ipv4.POD_CIDR="${ovnPodCidr}" \
        --set ipv4.POD_GATEWAY="${ovnPodGateway}" \
        --set ipv4.SVC_CIDR="${ovnServiceCidr}" \
        --set ipv4.JOIN_CIDR="${ovnJoinCidr}" \
        --set MASTER_NODES="${ovnMasterNodes}" \
        --set kube-ovn-controller.requests.cpu="${ovnControllerRequestCpu}" \
        --set kube-ovn-controller.limits.cpu="${ovnControllerLimitCpu}" \
        --set kube-ovn-controller.requests.memory="${ovnControllerRequestMemory}" \
        --set kube-ovn-controller.limits.memory="${ovnControllerLimitMemory}" \
        --set ovn-central.requests.cpu="${ovnCentralRequestCpu}" \
        --set ovn-central.limits.cpu="${ovnCentralLimitCpu}" \
        --set ovn-central.requests.memory="${ovnCentralRequestMemory}" \
        --set ovn-central.limits.memory="${ovnCentralLimitMemory}" \
        --set ovs-ovn.requests.cpu="${ovnOvsRequestCpu}" \
        --set ovs-ovn.limits.cpu="${ovnOvsLimitCpu}" \
        --set ovs-ovn.requests.memory="${ovnOvsRequestMemory}" \
        --set ovs-ovn.limits.memory="${ovnOvsLimitMemory}" \
        --set kube-ovn-cni.requests.cpu="${ovnCniRequestCpu}" \
        --set kube-ovn-cni.limits.cpu="${ovnCniLimitCpu}" \
        --set kube-ovn-cni.requests.memory="${ovnCniRequestMemory}" \
        --set kube-ovn-cni.limits.memory="${ovnCniLimitMemory}" \
        --set performance.OVS_VSCTL_CONCURRENCY="${ovnCniOvsVsctlConcurrency}" \
        --wait \
        --timeout 10m
}

patchKubeOvnCniStartupForScale() {
    # Kube-OVN's bundled start-cniserver.sh uses ovs-appctl -T 1 while waiting
    # for OVS. At large SeedEMU scales ovs-vswitchd can legitimately take a
    # long time to answer appctl probes while it is still draining flow updates.
    # Treat socket/pid presence as the startup gate and let kube-ovn-daemon
    # serialize OVS updates with a tunable ovs-vsctl concurrency.
    echo "[ovn] patching kube-ovn-cni startup guard for large OVS state"
    kubectl --kubeconfig "${outputKubeconfig}" -n "${ovnNamespace}" patch daemonset kube-ovn-cni \
        --type=strategic \
        --patch "$(cat <<EOF
spec:
  template:
    spec:
      containers:
        - name: cni-server
          command:
            - /bin/bash
            - -ec
          args:
            - |
              set -euo pipefail
              CNI_SOCK=/run/openvswitch/kube-ovn-daemon.sock
              OVS_SOCK=/run/openvswitch/db.sock
              quit() {
                rm -f "\${CNI_SOCK}"
                exit 0
              }
              trap quit EXIT
              rm -f "\${CNI_SOCK}"
              while true; do
                if [ -S "\${OVS_SOCK}" ] \\
                    && [ -s /run/openvswitch/ovsdb-server.pid ] \\
                    && [ -s /run/openvswitch/ovs-vswitchd.pid ]; then
                  echo "ovs sockets and pid files are present"
                  ready=true
                  for component in ovsdb-server ovs-vswitchd; do
                    pid_file="/run/openvswitch/\${component}.pid"
                    if ! read -r pid _ < "\${pid_file}" 2>/dev/null || [ -z "\${pid}" ]; then
                      ready=false
                      break
                    fi
                    if [ ! -S "/run/openvswitch/\${component}.\${pid}.ctl" ]; then
                      ready=false
                      break
                    fi
                  done
                  if [ "\${ready}" = "true" ]; then
                    break
                  fi
                else
                  echo "waiting for ovs ready"
                fi
                sleep 5
              done
              iptables -V
              set +e
              iptables -P FORWARD ACCEPT
              iptables-nft -P FORWARD ACCEPT
              set -e
              cat > /usr/local/sbin/ovs-vsctl <<'OVSWRAP'
              #!/usr/bin/env bash
              set -euo pipefail
              real=/usr/bin/ovs-vsctl
              timeout="\${SEED_OVS_VSCTL_TIMEOUT:-${ovnCniOvsVsctlTimeoutSeconds}}"
              args=()
              while [ "\$#" -gt 0 ]; do
                arg="\$1"
                case "\${arg}" in
                  --timeout=*)
                    value="\${arg#--timeout=}"
                    if [[ "\${value}" =~ ^[0-9]+$ ]] && [ "\${value}" -gt 0 ] && [ "\${value}" -lt "\${timeout}" ]; then
                      args+=("--timeout=\${timeout}")
                    else
                      args+=("\${arg}")
                    fi
                    ;;
                  --timeout)
                    args+=("\${arg}")
                    shift
                    if [ "\$#" -gt 0 ]; then
                      value="\$1"
                      if [[ "\${value}" =~ ^[0-9]+$ ]] && [ "\${value}" -gt 0 ] && [ "\${value}" -lt "\${timeout}" ]; then
                        args+=("\${timeout}")
                      else
                        args+=("\${value}")
                      fi
                    fi
                    ;;
                  *)
                    args+=("\${arg}")
                    ;;
                esac
                shift
              done
              exec "\${real}" "\${args[@]}"
              OVSWRAP
              sed -i 's/^[[:space:]]\\{14\\}//' /usr/local/sbin/ovs-vsctl
              chmod 0755 /usr/local/sbin/ovs-vsctl
              export SEED_OVS_VSCTL_TIMEOUT=${ovnCniOvsVsctlTimeoutSeconds}
              export SEED_OVS_INTERFACE_READY_TIMEOUT_SECONDS=${ovnInterfaceReadyTimeoutSeconds}
              echo "ovs-vsctl wrapper installed with minimum positive timeout \${SEED_OVS_VSCTL_TIMEOUT}s"
              echo "ovs interface ready timeout \${SEED_OVS_INTERFACE_READY_TIMEOUT_SECONDS}s"
              exec ./kube-ovn-daemon \\
                --ovs-socket="\${OVS_SOCK}" \\
                --bind-socket="\${CNI_SOCK}" \\
                --enable-mirror=false \\
                --mirror-iface=mirror0 \\
                --node-switch=join \\
                --encap-checksum=true \\
                --service-cluster-ip-range=${ovnServiceCidr} \\
                --iface=${ovnIface} \\
                --dpdk-tunnel-iface=br-phy \\
                --network-type=${ovnTunnelType} \\
                --default-interface-name= \\
                --logtostderr=false \\
                --alsologtostderr=true \\
                --log_file=/var/log/kube-ovn/kube-ovn-cni.log \\
                --log_file_max_size=200 \\
                --enable-metrics=true \\
                --kubelet-dir=/var/lib/kubelet \\
                --enable-tproxy=false \\
                --ovs-vsctl-concurrency=${ovnCniOvsVsctlConcurrency} \\
                --secure-serving=false \\
                --enable-ovn-ipsec=false \\
                --set-vxlan-tx-off=false \\
                --non-primary-cni-mode=true
          livenessProbe:
            failureThreshold: 18
            httpGet:
              path: /livez
              port: 10665
              scheme: HTTP
            initialDelaySeconds: 300
            periodSeconds: 10
            successThreshold: 1
            timeoutSeconds: 10
          readinessProbe:
            failureThreshold: 18
            httpGet:
              path: /readyz
              port: 10665
              scheme: HTTP
            periodSeconds: 10
            successThreshold: 1
            timeoutSeconds: 10
EOF
)"
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
      image: ${ovnImageRegistry}/${ovnImageRepository}:${ovnImageTag}
      imagePullPolicy: IfNotPresent
      command:
        - /bin/sh
        - -xec
        - |
          target=\$(readlink /host-cni/cni || true)
          if [ -z "\${target}" ]; then
            target=${ovnCniBinDir%/cni}/current/bin/cni
          fi
          rm -f /host-cni/loopback /host-cni/portmap
          ln -s "\${target}" /host-cni/loopback
          ln -s "\${target}" /host-cni/portmap
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
        echo "Run ApplyK3sCluster.py or K8sTools.py build before installing Kube-OVN." >&2
        exit 1
    fi

    local helm_bin
    local chart_ref
    helm_bin="$(ensureHelm)"
    chart_ref="$(ensureKubeOvnChart "${helm_bin}")"
    preloadKubeOvnImage
    prepareKubeOvnCniBinDir
    installKubeOvn "${helm_bin}" "${chart_ref}"
    patchKubeOvnCniStartupForScale
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
