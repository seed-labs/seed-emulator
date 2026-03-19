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

_seedemu_shortcuts_dir="${REPO_ROOT}/scripts/shortcuts"
if [ -d "${_seedemu_shortcuts_dir}" ]; then
    case ":${PATH}:" in
        *":${_seedemu_shortcuts_dir}:"*) ;;
        *) export PATH="${_seedemu_shortcuts_dir}:${PATH}" ;;
    esac
fi

export SEED_EXPERIMENT_PROFILE="${SEED_EXPERIMENT_PROFILE:-mini_internet}"
export SEED_AGENT_PROACTIVE_MODE="${SEED_AGENT_PROACTIVE_MODE:-guided}"
export SEED_FAILURE_ACTION_MAP="${SEED_FAILURE_ACTION_MAP:-${REPO_ROOT}/configs/seed_failure_action_map.yaml}"

# Kind-specific: prevent masq-agent from SNATing SEED Multus secondary networks.
# (Only takes effect if a script uses this variable, e.g. scripts/kind_masq_exempt.sh
# or scripts/validate_kubevirt_hybrid.sh.)
# Include:
# - 10.0.0.0/8: typical SEED subnets
# - 224.0.0.0/4: OSPF multicast (otherwise OSPF hellos can get SNATed to kind node IPs)
export SEED_KIND_MASQ_EXEMPT_CIDRS="${SEED_KIND_MASQ_EXEMPT_CIDRS:-10.0.0.0/8,224.0.0.0/4}"
