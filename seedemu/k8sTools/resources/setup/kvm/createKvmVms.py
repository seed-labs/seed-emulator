#!/usr/bin/env python3
"""Python entrypoint for createKvmVms with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Create or start KVM VMs from kvm.yaml. The script resolves non-conflicting
# VM names/IPs/MACs, writes user-facing configK3s.yaml plus internal
# kvmState.yaml, and waits for SSH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
SETUP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${1:-${SETUP_DIR}/kvm.yaml}"
HELPER="${SCRIPT_DIR}/manageKvmConfig.py"
kvmBaseImageSearchDirs="${HOME}/k8s/output"
kvmBaseImageReuseMode="copy"
baseImageLowSpeedSeconds=60
baseImageLowSpeedLimit=1024

eval "$(python3 "${HELPER}" "${CONFIG_PATH}" kvm-vars)"

SSH_PUB_KEY=""
EXISTING_VMS_TSV=""
PLANNED_NODES_TSV=""
REUSING_KVM_STATE_PLAN="false"

usage() {
    cat <<EOF
Usage: $0 [kvm.yaml]

Create/start KVM guests described by the YAML config.
This script does not install K3s. It writes configK3s.yaml for the K3s stage.
EOF
}

requireCommand() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required command: $1" >&2
        exit 1
    }
}

cleanupTmp() {
    [ -n "${EXISTING_VMS_TSV}" ] && rm -f "${EXISTING_VMS_TSV}" || true
    [ -n "${PLANNED_NODES_TSV}" ] && rm -f "${PLANNED_NODES_TSV}" || true
}

domainExists() {
    virsh dominfo "$1" >/dev/null 2>&1
}

domainRunning() {
    virsh domstate "$1" 2>/dev/null | grep -qi "running"
}

prepareDirs() {
    mkdir -p "${kvmStorageDir}/base"
    mkdir -p "${kvmDiskDir}"
    mkdir -p "${kvmCloudInitDir}"
    mkdir -p "$(dirname "${kvmBaseImagePath}")"
}

validBaseImage() {
    # Args:
    #   $1: qcow2 image path to validate.
    local image_path="$1"
    [ -s "${image_path}" ] && qemu-img info "${image_path}" >/dev/null 2>&1
}

downloadBaseImageFile() {
    # Args:
    #   $1: URL, $2: destination path.
    local image_url="$1"
    local image_path="$2"
    local partial_path="${image_path}.part"
    mkdir -p "$(dirname "${image_path}")"
    curl -fL \
        --retry 5 \
        --retry-delay 5 \
        --retry-all-errors \
        --connect-timeout 20 \
        --speed-time "${baseImageLowSpeedSeconds}" \
        --speed-limit "${baseImageLowSpeedLimit}" \
        -C - \
        -o "${partial_path}" \
        "${image_url}"
    validBaseImage "${partial_path}" || {
        echo "Downloaded base image is not a valid qcow2 file: ${partial_path}" >&2
        return 1
    }
    mv -f "${partial_path}" "${image_path}"
}

ensureNetwork() {
    if ! virsh net-info "${kvmNetwork}" >/dev/null 2>&1; then
        echo "Libvirt network not found: ${kvmNetwork}" >&2
        exit 1
    fi
    virsh net-start "${kvmNetwork}" >/dev/null 2>&1 || true
    virsh net-autostart "${kvmNetwork}" >/dev/null 2>&1 || true
}

collectExistingVms() {
    EXISTING_VMS_TSV="$(mktemp "${kvmStorageDir}/existing-vms.XXXXXX.tsv")"
    PLANNED_NODES_TSV="$(mktemp "${kvmStorageDir}/planned-vms.XXXXXX.tsv")"

    if [ -f "${outputKvmState}" ]; then
        if ! python3 "${HELPER}" "${CONFIG_PATH}" validate-kvm-state --state "${outputKvmState}"; then
            echo "Refusing to reuse stale KVM state: ${outputKvmState}" >&2
            echo "Remove it only if you intentionally want this setup directory to generate a new VM plan." >&2
            exit 1
        fi
        REUSING_KVM_STATE_PLAN="true"
        python3 "${HELPER}" "${CONFIG_PATH}" state-nodes-tsv --state "${outputKvmState}" > "${PLANNED_NODES_TSV}"
        echo "Using existing KVM state: ${outputKvmState}"
        awk -F '\t' '{printf "  %-24s role=%-6s ip=%-15s mac=%s vcpus=%s memory_mb=%s disk_gb=%s\n", $1, $2, $3, $4, $5, $6, $7}' "${PLANNED_NODES_TSV}"
        return
    fi

    virsh list --all --name 2>/dev/null | awk 'NF {print $1 "\t\t"}' >> "${EXISTING_VMS_TSV}"

    virsh net-dumpxml "${kvmNetwork}" 2>/dev/null | python3 -c '
import sys
import xml.etree.ElementTree as ET

root = ET.fromstring(sys.stdin.read())
for host in root.findall(".//host"):
    print("\t".join([
        host.get("name") or "",
        host.get("ip") or "",
        (host.get("mac") or "").lower(),
    ]))
' >> "${EXISTING_VMS_TSV}"

    virsh net-dhcp-leases "${kvmNetwork}" 2>/dev/null | awk '
        NR <= 2 {next}
        NF >= 5 {
          name=$6
          if (name == "-" || name == "") name=""
          ip=$5
          sub("/.*", "", ip)
          print name "\t" ip "\t" tolower($3)
        }
    ' >> "${EXISTING_VMS_TSV}" || true

    python3 "${HELPER}" "${CONFIG_PATH}" nodes-tsv --existing-tsv "${EXISTING_VMS_TSV}" > "${PLANNED_NODES_TSV}"
    echo "Planned KVM nodes:"
    awk -F '\t' '{printf "  %-24s role=%-6s ip=%-15s mac=%s vcpus=%s memory_mb=%s disk_gb=%s\n", $1, $2, $3, $4, $5, $6, $7}' "${PLANNED_NODES_TSV}"
}

downloadBaseImage() {
    if [ -f "${kvmBaseImagePath}" ]; then
        if validBaseImage "${kvmBaseImagePath}"; then
            return
        fi
        echo "Removing incomplete or invalid base image: ${kvmBaseImagePath}"
        rm -f "${kvmBaseImagePath}"
    fi
    if [ -n "${kvmLegacyBaseImagePath:-}" ] && [ -f "${kvmLegacyBaseImagePath}" ]; then
        echo "Using existing base image from ${kvmLegacyBaseImagePath}"
        if [ "${kvmBaseImageReuseMode}" = "symlink" ]; then
            ln -s "${kvmLegacyBaseImagePath}" "${kvmBaseImagePath}"
        else
            cp --reflink=auto "${kvmLegacyBaseImagePath}" "${kvmBaseImagePath}"
        fi
        return
    fi
    local output_image=""
    local search_dir=""
    for search_dir in ${kvmBaseImageSearchDirs}; do
        [ -d "${search_dir}" ] || continue
        output_image="$(find "${search_dir}" -type f -name "$(basename "${kvmBaseImagePath}")" -print -quit 2>/dev/null || true)"
        if [ -n "${output_image}" ]; then
            echo "Using existing base image from ${output_image}"
            if [ "${kvmBaseImageReuseMode}" = "symlink" ]; then
                ln -s "${output_image}" "${kvmBaseImagePath}"
            else
                cp --reflink=auto "${output_image}" "${kvmBaseImagePath}"
            fi
            return
        fi
    done
    echo "Downloading Ubuntu cloud image to ${kvmBaseImagePath}"
    downloadBaseImageFile "${kvmBaseImageUrl}" "${kvmBaseImagePath}"
}

loadSshPubkey() {
    if [ -f "${sshKey}.pub" ]; then
        SSH_PUB_KEY="$(tr -d '\n' < "${sshKey}.pub")"
        return
    fi
    if [ -f "${sshKey}" ]; then
        SSH_PUB_KEY="$(ssh-keygen -y -f "${sshKey}" 2>/dev/null | tr -d '\n')"
        [ -n "${SSH_PUB_KEY}" ] && return
    fi
    echo "Cannot read SSH key. Set ssh.key in ${CONFIG_PATH} to a valid private key." >&2
    exit 1
}

updateDhcpHost() {
    local vm_name="$1"
    local vm_ip="$2"
    local vm_mac="$3"
    local host_xml="<host mac='${vm_mac}' name='${vm_name}' ip='${vm_ip}'/>"
    virsh net-update "${kvmNetwork}" delete ip-dhcp-host "${host_xml}" --live --config >/dev/null 2>&1 || true
    virsh net-update "${kvmNetwork}" add ip-dhcp-host "${host_xml}" --live --config >/dev/null
}

createVmCloudInit() {
    local vm_name="$1"
    local vm_dir="${kvmCloudInitDir}/${vm_name}"
    mkdir -p "${vm_dir}"

    cat > "${vm_dir}/user-data.yaml" <<EOF
#cloud-config
users:
  - default
  - name: ${sshUser}
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: [sudo]
    ssh_authorized_keys:
      - ${SSH_PUB_KEY}
package_update: true
packages:
  - qemu-guest-agent
runcmd:
  - [ systemctl, enable, --now, qemu-guest-agent ]
EOF

    cat > "${vm_dir}/meta-data.yaml" <<EOF
instance-id: ${vm_name}
local-hostname: ${vm_name}
EOF
}

createVmDisk() {
    local vm_name="$1"
    local disk_gb="$2"
    local vm_disk="${kvmDiskDir}/${vm_name}.qcow2"
    if [ -f "${vm_disk}" ]; then
        return
    fi
    qemu-img create -f qcow2 -F qcow2 -b "${kvmBaseImagePath}" "${vm_disk}" "${disk_gb}G" >/dev/null
}

createOrStartVm() {
    local vm_name="$1"
    local vm_ip="$2"
    local vm_mac="$3"
    local vcpus="$4"
    local memory_mb="$5"
    local disk_gb="$6"
    local vm_disk="${kvmDiskDir}/${vm_name}.qcow2"
    local vm_cloud_dir="${kvmCloudInitDir}/${vm_name}"

    if domainExists "${vm_name}"; then
        validateExistingDomainBelongsToSetup "${vm_name}"
        if [ "${kvmAllowExisting}" != "true" ] && [ "${REUSING_KVM_STATE_PLAN}" != "true" ]; then
            echo "Refusing to reuse existing VM '${vm_name}'. Set kvm.allowExisting: true only if this is intentional." >&2
            exit 1
        fi
        echo "VM exists: ${vm_name}"
        if ! domainRunning "${vm_name}"; then
            virsh start "${vm_name}" >/dev/null
        fi
        return
    fi

    echo "Creating VM: ${vm_name} ip=${vm_ip} vcpus=${vcpus} memory_mb=${memory_mb} disk_gb=${disk_gb}"
    virt-install \
        --name "${vm_name}" \
        --memory "${memory_mb}" \
        --vcpus "${vcpus}" \
        --cpu host-passthrough \
        --import \
        --os-variant generic \
        --network "network=${kvmNetwork},model=virtio,mac=${vm_mac}" \
        --disk "path=${vm_disk},format=qcow2,bus=virtio" \
        --graphics none \
        --noautoconsole \
        --cloud-init "user-data=${vm_cloud_dir}/user-data.yaml,meta-data=${vm_cloud_dir}/meta-data.yaml" >/dev/null
}

validateExistingDomainBelongsToSetup() {
    # Args:
    #   $1: VM domain name that already exists.
    # Uses kvmDiskDir from kvm.yaml to make stale kvmState.yaml files fail safe.
    local vm_name="$1"
    local disk_path=""
    disk_path="$(
        virsh domblklist "${vm_name}" --details 2>/dev/null \
        | awk '$2 == "disk" && $4 != "-" {print $4; exit}'
    )"
    if [ -z "${disk_path}" ]; then
        echo "Cannot determine disk path for existing VM ${vm_name}; refusing to reuse it." >&2
        exit 1
    fi
    case "${disk_path}" in
        "${kvmDiskDir}"/*) ;;
        *)
            echo "Refusing to reuse existing VM ${vm_name}: disk is outside this setup diskDir." >&2
            echo "  vm_disk=${disk_path}" >&2
            echo "  setup_disk_dir=${kvmDiskDir}" >&2
            echo "This usually means kvmState.yaml is stale or points to an existing cluster." >&2
            exit 1
            ;;
    esac
}

checkNetworkConflict() {
    local vm_name="$1"
    local vm_ip="$2"
    local vm_mac="$3"

    virsh net-dumpxml "${kvmNetwork}" | python3 -c '
import sys
import xml.etree.ElementTree as ET

name, ip, mac = sys.argv[1], sys.argv[2], sys.argv[3].lower()
root = ET.fromstring(sys.stdin.read())
for host in root.findall(".//host"):
    h_name = host.get("name") or ""
    h_ip = host.get("ip") or ""
    h_mac = (host.get("mac") or "").lower()
    same_host = h_name == name and h_ip == ip and h_mac == mac
    if h_ip == ip and not same_host:
        raise SystemExit(f"IP {ip} is already reserved by host name={h_name} mac={h_mac}")
    if h_mac == mac and not same_host:
        raise SystemExit(f"MAC {mac} is already reserved by host name={h_name} ip={h_ip}")
' "${vm_name}" "${vm_ip}" "${vm_mac}"

    if virsh net-dhcp-leases "${kvmNetwork}" 2>/dev/null | awk -v ip="${vm_ip}" -v mac="${vm_mac,,}" -v name="${vm_name}" '
        NR <= 2 {next}
        {
          lease_mac=tolower($3); lease_ip=$5; sub("/.*", "", lease_ip); lease_name=$6
          if ((lease_ip == ip || lease_mac == mac) && !(lease_ip == ip && lease_mac == mac && lease_name == name)) {
            print "DHCP lease conflict: name=" lease_name " mac=" lease_mac " ip=" lease_ip > "/dev/stderr"
            exit 1
          }
        }
    '; then
        return
    fi
    exit 1
}

checkCreateConflicts() {
    local vm_name="$1"
    local vm_ip="$2"
    local vm_mac="$3"
    local vm_disk="${kvmDiskDir}/${vm_name}.qcow2"

    if domainExists "${vm_name}" && [ "${kvmAllowExisting}" != "true" ] && [ "${REUSING_KVM_STATE_PLAN}" != "true" ]; then
        echo "VM name conflict: ${vm_name} already exists. Choose a new name or set kvm.allowExisting: true intentionally." >&2
        exit 1
    fi
    if [ -e "${vm_disk}" ] && ! domainExists "${vm_name}" ]; then
        echo "Disk conflict: ${vm_disk} already exists but VM ${vm_name} is not defined." >&2
        exit 1
    fi
    checkNetworkConflict "${vm_name}" "${vm_ip}" "${vm_mac}"
}

waitForSsh() {
    local vm_name="$1"
    local vm_ip="$2"
    local elapsed=0
    while [ "${elapsed}" -lt "${kvmBootTimeoutSeconds}" ]; do
        if ssh -o StrictHostKeyChecking=no \
               -n \
               -o UserKnownHostsFile=/dev/null \
               -o LogLevel=ERROR \
               -o BatchMode=yes \
               -o IdentitiesOnly=yes \
               -o IdentityAgent=none \
               -o ConnectTimeout=5 \
               -i "${sshKey}" \
               "${sshUser}@${vm_ip}" "echo ok" >/dev/null 2>&1; then
            echo "SSH ready: ${vm_name} (${vm_ip})"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    echo "Timeout waiting for SSH on ${vm_name} (${vm_ip})" >&2
    return 1
}

writeK3sConfig() {
    # Args: none.
    # Writes the user-facing configK3s.yaml from the transient planned node
    # list. It intentionally omits KVM resource details and output paths.
    python3 "${HELPER}" "${CONFIG_PATH}" write-k3s-config \
        --nodes-tsv "${PLANNED_NODES_TSV}" \
        --output "${outputK3sConfig}"
    echo "K3s config: ${outputK3sConfig}"
}

writeKvmState() {
    # Args: none.
    # Writes internal kvmState.yaml with VM MAC/resource/disk metadata. Cleanup
    # uses this file instead of overloading the user-facing configK3s.yaml.
    python3 "${HELPER}" "${CONFIG_PATH}" write-kvm-state \
        --nodes-tsv "${PLANNED_NODES_TSV}" \
        --output "${outputKvmState}"
    echo "KVM state: ${outputKvmState}"
}

main() {
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        usage
        exit 0
    fi
    requireCommand python3
    requireCommand virsh
    requireCommand virt-install
    requireCommand qemu-img
    requireCommand curl
    requireCommand ssh
    requireCommand ssh-keygen
    requireCommand awk

    [ -f "${sshKey}" ] || {
        echo "SSH key not found: ${sshKey}" >&2
        exit 1
    }
    trap cleanupTmp EXIT

    prepareDirs
    ensureNetwork
    collectExistingVms
    downloadBaseImage
    loadSshPubkey

    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        checkCreateConflicts "${name}" "${ip}" "${mac}"
    done < "${PLANNED_NODES_TSV}"

    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        updateDhcpHost "${name}" "${ip}" "${mac}"
        createVmCloudInit "${name}"
        createVmDisk "${name}" "${disk_gb}"
        createOrStartVm "${name}" "${ip}" "${mac}" "${vcpus}" "${memory_mb}" "${disk_gb}"
    done < "${PLANNED_NODES_TSV}"

    while IFS=$'\t' read -r name role ip mac vcpus memory_mb disk_gb; do
        waitForSsh "${name}" "${ip}"
    done < "${PLANNED_NODES_TSV}"

    if [ "${kvmSkipK3sConfig}" = "true" ]; then
        echo "Skipping host-local configK3s.yaml generation because kvm.skipK3sConfig=true."
    else
        writeK3sConfig
    fi
    writeKvmState
    echo "KVM VMs are ready."
    echo "Next step: ${SCRIPT_DIR}/tuneVmLimits.py ${outputK3sConfig}"
}

main "$@"
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
