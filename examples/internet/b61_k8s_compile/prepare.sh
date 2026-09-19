#!/usr/bin/env bash
# Prepare an Ubuntu host for the B61 native KVM/K3s workflow.
#
# Default role:
#   control     The machine runs k8sTools.py and also acts as a KVM hypervisor.
#               It needs kubectl, ansible-playbook, Docker, and KVM/libvirt.
#
# Optional role:
#   hypervisor  A remote KVM hypervisor controlled over SSH. It does not need
#               kubectl or ansible-playbook, but the current multi-host scripts
#               do require Python/PyYAML, Docker, SSH, rsync, KVM, and libvirt.
#
# kubectl version:
#   All B61 macvlan+VLAN configs and the current B62/B63 configs use K3s
#   v1.29.15+k3s1, so this script installs kubectl v1.29.15 by default.
#
# Common invocations:
#
#   ./prepare.sh
#   ./prepare.sh --role hypervisor
#   ./prepare.sh --verify-only
#
# Run this script as the normal account that will run the SeedEMU workflow.
# The script calls sudo for system changes. Do not run the whole script with
# sudo, because it must configure groups, SSH keys, and Docker access for the
# normal account.
#
# Multi-host requirements outside package installation:
#   - Run the default control role on the control/local-hypervisor machine.
#   - Run --role hypervisor on every remote KVM hypervisor.
#   - Copy the control machine's SSH public key to each remote hypervisor.
#   - Confirm key-based SSH and `sudo -n true` work on every hypervisor.
#   - Every hypervisor needs hardware virtualization (/dev/kvm), enough
#     CPU/RAM/disk, and network/firewall access for the configured K3s/VXLAN
#     traffic.
set -euo pipefail

ROLE="control"
KUBECTL_VERSION="${KUBECTL_VERSION:-v1.29.15}"
VERIFY_ONLY="false"
CONFIGURE_PASSWORDLESS_SUDO="${SEED_CONFIGURE_PASSWORDLESS_SUDO:-true}"

usage() {
    cat <<'EOF'
Usage: ./prepare.sh [options]

Options:
  --role control|hypervisor   Host role. Default: control.
  --kubectl-version VERSION   Exact kubectl version for the control role.
                              Default: v1.29.15.
  --verify-only               Do not install or modify; only verify.
  -h, --help                  Show this help.

Environment:
  KUBECTL_VERSION                    Alternative exact kubectl version.
  SEED_CONFIGURE_PASSWORDLESS_SUDO   true (default) or false.
EOF
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --role)
            [ "$#" -ge 2 ] || die "--role requires a value"
            ROLE="$2"
            shift 2
            ;;
        --kubectl-version)
            [ "$#" -ge 2 ] || die "--kubectl-version requires a value"
            KUBECTL_VERSION="$2"
            shift 2
            ;;
        --verify-only)
            VERIFY_ONLY="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown argument: $1"
            ;;
    esac
done

case "${ROLE}" in
    control|hypervisor) ;;
    *) die "--role must be control or hypervisor" ;;
esac

[[ "${KUBECTL_VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
    die "kubectl version must look like v1.29.15: ${KUBECTL_VERSION}"

if [ "${EUID}" -eq 0 ]; then
    die "run this script as the normal SeedEMU user, without sudo"
fi

TARGET_USER="$(id -un)"
TARGET_HOME="$(getent passwd "${TARGET_USER}" | cut -d: -f6)"
[ -n "${TARGET_HOME}" ] || die "cannot determine home directory for ${TARGET_USER}"

requireCommand() {
    command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

installPackages() {
    command -v apt-get >/dev/null 2>&1 || die "this script currently supports apt-based Ubuntu/Debian hosts"
    command -v docker >/dev/null 2>&1 || die "Docker is not installed; install Docker before running this script"

    echo ">> Installing KVM/libvirt, SSH, rsync, networking, and Python YAML support"
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3-yaml \
        qemu-kvm \
        qemu-utils \
        libvirt-daemon-system \
        libvirt-clients \
        virtinst \
        openssh-client \
        openssh-server \
        rsync \
        curl \
        ca-certificates \
        iproute2

    if [ "${ROLE}" = "control" ]; then
        echo ">> Installing Ansible on the control host"
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ansible-core
    fi
}

ensureDockerBuildx() {
    if docker buildx version >/dev/null 2>&1; then
        return
    fi

    echo ">> Docker Buildx is missing; installing the package available from the configured APT sources"
    if apt-cache show docker-buildx-plugin >/dev/null 2>&1; then
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-buildx-plugin
    elif apt-cache show docker-buildx >/dev/null 2>&1; then
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-buildx
    else
        die "neither docker-buildx-plugin nor docker-buildx is available from the configured APT sources"
    fi
}

kubectlArchitecture() {
    case "$(uname -m)" in
        x86_64|amd64) printf '%s\n' amd64 ;;
        aarch64|arm64) printf '%s\n' arm64 ;;
        *) die "unsupported kubectl architecture: $(uname -m)" ;;
    esac
}

installKubectl() (
    local architecture temporary_dir checksum
    architecture="$(kubectlArchitecture)"
    temporary_dir="$(mktemp -d)"
    trap 'rm -rf "${temporary_dir:-}"' EXIT

    echo ">> Installing exact kubectl version ${KUBECTL_VERSION} (${architecture})"
    curl -fL --retry 5 --retry-delay 3 \
        -o "${temporary_dir}/kubectl" \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${architecture}/kubectl"
    curl -fL --retry 5 --retry-delay 3 \
        -o "${temporary_dir}/kubectl.sha256" \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${architecture}/kubectl.sha256"

    checksum="$(cat "${temporary_dir}/kubectl.sha256")"
    printf '%s  %s\n' "${checksum}" "${temporary_dir}/kubectl" | sha256sum --check
    sudo install -o root -g root -m 0755 "${temporary_dir}/kubectl" /usr/local/bin/kubectl
)

enableServicesAndPermissions() {
    echo ">> Enabling libvirt, SSH, and Docker"
    sudo systemctl enable --now libvirtd
    sudo systemctl enable --now ssh
    sudo systemctl enable --now docker

    echo ">> Adding ${TARGET_USER} to libvirt, kvm, and docker groups"
    local group
    for group in libvirt kvm docker; do
        getent group "${group}" >/dev/null 2>&1 || die "required group does not exist: ${group}"
        sudo usermod -aG "${group}" "${TARGET_USER}"
    done
}

configurePasswordlessSudo() {
    if [ "${CONFIGURE_PASSWORDLESS_SUDO}" != "true" ]; then
        echo ">> Skipping passwordless sudo configuration"
        return
    fi

    local safe_user sudoers_path
    safe_user="${TARGET_USER//[^A-Za-z0-9_.-]/_}"
    sudoers_path="/etc/sudoers.d/90-seedemu-k8s-${safe_user}"
    echo ">> Configuring passwordless sudo required by the multi-host scripts"
    printf '%s ALL=(ALL) NOPASSWD:ALL\n' "${TARGET_USER}" | sudo tee "${sudoers_path}" >/dev/null
    sudo chmod 0440 "${sudoers_path}"
    sudo visudo -cf "${sudoers_path}"
}

ensureSshKey() {
    local ssh_dir ssh_key
    ssh_dir="${TARGET_HOME}/.ssh"
    ssh_key="${ssh_dir}/id_ed25519"

    if [ -f "${ssh_key}" ]; then
        echo ">> Reusing SSH key ${ssh_key}"
        if [ ! -f "${ssh_key}.pub" ]; then
            ssh-keygen -y -f "${ssh_key}" > "${ssh_key}.pub"
            chmod 0644 "${ssh_key}.pub"
        fi
        return
    fi

    echo ">> Creating SSH key ${ssh_key}"
    install -d -m 0700 "${ssh_dir}"
    ssh-keygen -t ed25519 -f "${ssh_key}" -N "" -C "seedemu-k8s"
    chmod 0600 "${ssh_key}"
    chmod 0644 "${ssh_key}.pub"
}

verifyKubectlVersion() {
    kubectl version --client --output=json | python3 -c '
import json
import sys

expected = sys.argv[1]
actual = json.load(sys.stdin)["clientVersion"]["gitVersion"]
if actual != expected:
    raise SystemExit(f"kubectl version mismatch: actual={actual}, expected={expected}")
print(f"kubectl version: OK ({actual})")
' "${KUBECTL_VERSION}"
}

verifyHost() {
    echo ">> Verifying role=${ROLE}"

    local command_name
    for command_name in \
        python3 curl docker ssh scp ssh-keygen rsync ip bridge \
        virsh virt-install qemu-img systemctl; do
        requireCommand "${command_name}"
    done

    python3 -c 'import yaml; print("PyYAML: OK")'
    test -c /dev/kvm || die "/dev/kvm is missing; enable hardware virtualization or KVM passthrough"

    systemctl is-active --quiet libvirtd || die "libvirtd is not active"
    systemctl is-active --quiet ssh || die "SSH service is not active"
    systemctl is-active --quiet docker || die "Docker service is not active"

    qemu-img --version
    virt-install --version
    ip -Version
    bridge -Version

    if [ "${CONFIGURE_PASSWORDLESS_SUDO}" = "true" ] && ! sudo -n true >/dev/null 2>&1; then
        die "passwordless sudo was requested, but sudo -n still fails"
    fi

    if [ "${ROLE}" = "control" ]; then
        requireCommand ansible-playbook
        requireCommand kubectl
        ansible-playbook --version
        verifyKubectlVersion
    fi

    # sudo verifies the daemons immediately. The unprivileged checks below
    # require a new login when group membership was added by this run.
    sudo virsh -c qemu:///system list --all >/dev/null
    sudo docker info >/dev/null
    docker buildx version

    local active_groups missing_groups=""
    active_groups=" $(id -nG) "
    for command_name in libvirt kvm docker; do
        case "${active_groups}" in
            *" ${command_name} "*) ;;
            *) missing_groups="${missing_groups} ${command_name}" ;;
        esac
    done

    if [ -n "${missing_groups}" ]; then
        echo
        echo "Installation completed, but this login session does not yet have these groups:${missing_groups}"
        echo "Log out and log in again, then run:"
        echo "  ./prepare.sh --role ${ROLE} --kubectl-version ${KUBECTL_VERSION} --verify-only"
        return
    fi

    virsh -c qemu:///system list --all >/dev/null
    docker info >/dev/null
    test -r /dev/kvm && test -w /dev/kvm || die "${TARGET_USER} cannot read/write /dev/kvm"

    echo
    echo "SeedEMU B61 ${ROLE} host verification: PASS"
}

main() {
    if [ "${VERIFY_ONLY}" = "false" ]; then
        sudo -v
        installPackages
        ensureDockerBuildx
        if [ "${ROLE}" = "control" ]; then
            installKubectl
        fi
        enableServicesAndPermissions
        configurePasswordlessSudo
        if [ "${ROLE}" = "control" ]; then
            ensureSshKey
        fi
    fi

    verifyHost
}

main "$@"
