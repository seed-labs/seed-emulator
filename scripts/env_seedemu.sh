#!/usr/bin/env bash
# Shared environment guardrails for SEED emulator scripts.
# Source this file from any working directory.

_seedemu_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Derive REPO_ROOT from this script location, not from caller cwd.
export REPO_ROOT="${REPO_ROOT:-$(cd "${_seedemu_script_dir}/.." && pwd)}"

if [[ -n "${PYTHONPATH:-}" ]]; then
    case ":${PYTHONPATH}:" in
        *":${REPO_ROOT}:"*) ;;
        *) export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH}" ;;
    esac
else
    export PYTHONPATH="${REPO_ROOT}"
fi

export SEED_CLUSTER_NAME="${SEED_CLUSTER_NAME:-seedemu-kvtest}"
export SEED_NAMESPACE="${SEED_NAMESPACE:-seedemu-kvtest}"
export SEED_REGISTRY="${SEED_REGISTRY:-localhost:5001}"
export SEED_CNI_TYPE="${SEED_CNI_TYPE:-bridge}"
export SEED_CNI_MASTER_INTERFACE="${SEED_CNI_MASTER_INTERFACE:-eth0}"
export SEED_SCHEDULING_STRATEGY="${SEED_SCHEDULING_STRATEGY:-custom}"
