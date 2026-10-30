#!/usr/bin/env python3
"""Python entrypoint for buildRegistryImages with its shell body embedded."""
from __future__ import annotations

import sys
from pathlib import Path

from _embeddedShell import runEmbeddedShell


SHELL_BODY = r'''#!/usr/bin/env bash
# Build SeedEMU workload images with BuildKit/buildx and push them to the
# registry selected by command-line arguments or configRunning.yaml.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${SEED_K8S_ENTRYPOINT}")" && pwd)"
CONFIG_PATH="${SCRIPT_DIR}/configRunning.yaml"
OUTPUT_DIR=""
REGISTRY_PREFIX=""
IMAGE_REGISTRY_PREFIX=""
HELPER="${SCRIPT_DIR}/manageK8sManifest.py"

usage() {
    cat <<EOF
Usage: $0 [--config configRunning.yaml] [--output-dir output] [--registry-prefix host:port] [--image-registry-prefix seedemu]

Build images listed in images.yaml and push them to the configured registry.
The remote large-scale build path passes explicit --output-dir and
--registry-prefix so it does not depend on host-local config paths.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --registry-prefix)
            REGISTRY_PREFIX="$2"
            shift 2
            ;;
        --image-registry-prefix)
            IMAGE_REGISTRY_PREFIX="$2"
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

if [ -z "${OUTPUT_DIR}" ]; then
    OUTPUT_DIR="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key outputDir)"
fi
if [ -z "${REGISTRY_PREFIX}" ]; then
    REGISTRY_PREFIX="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key registryPrefix)"
fi
if [ -z "${IMAGE_REGISTRY_PREFIX}" ]; then
    IMAGE_REGISTRY_PREFIX="$(python3 "${HELPER}" config-value --config "${CONFIG_PATH}" --key imageRegistryPrefix)"
fi

IMAGES_YAML="${OUTPUT_DIR}/images.yaml"
[ -s "${IMAGES_YAML}" ] || IMAGES_YAML="${OUTPUT_DIR}/images.txt"
OUTPUT_DIR="$(cd "${OUTPUT_DIR}" && pwd)"
cd "${OUTPUT_DIR}"

buildImageWithBuildx() {
    # Args:
    #   $1: full destination image reference
    #   $2: Docker build context directory
    local image="$1"
    local context="$2"
    local log_file
    log_file="$(mktemp)"
    echo "+ DOCKER_BUILDKIT=1 docker buildx build --load --provenance=false -t ${image} ${context}"
    if DOCKER_BUILDKIT=1 docker buildx build --load --provenance=false -t "${image}" "${context}" 2>&1 | tee "${log_file}"; then
        rm -f "${log_file}"
        return 0
    fi

    if grep -Eq 'parent snapshot .* does not exist|failed to prepare extraction snapshot' "${log_file}"; then
        echo "[k8s_build] buildx export/cache failure while building ${image}; pruning buildx cache and retrying once" >&2
        docker buildx prune -af >/dev/null 2>&1 || true
        rm -f "${log_file}"
        DOCKER_BUILDKIT=1 docker buildx build --load --provenance=false -t "${image}" "${context}"
        return $?
    fi

    rm -f "${log_file}"
    return 1
}

firstFromImage() {
    # Args:
    #   $1: Dockerfile path.
    # Prints the first FROM image reference, handling optional --platform.
    awk '
        toupper($1) == "FROM" {
            if ($2 ~ /^--platform=/) {
                print $3
            } else {
                print $2
            }
            exit
        }
    ' "$1"
}

isCompilerBaseTag() {
    # Args:
    #   $1: image reference to check.
    # Returns true for Docker compiler hash tags used in generated FROM lines.
    [[ "$1" =~ ^[0-9a-f]{32}(:latest)?$ ]]
}

ensureCompilerBaseImages() {
    # Build every hash-tagged base image required by generated node Dockerfiles.
    # A missing base_images/<hash>/Dockerfile means the compiler output is
    # incomplete; without this check Docker would try pulling library/<hash>.
    local tmpfile
    local dockerfile
    local from_image
    local base_tag
    local context
    local missing=0

    tmpfile="$(mktemp)"
    while IFS= read -r dockerfile; do
        from_image="$(firstFromImage "${dockerfile}")"
        if isCompilerBaseTag "${from_image}"; then
            printf '%s\n' "${from_image%:latest}" >> "${tmpfile}"
        fi
    done < <(find . -path './base_images/*' -prune -o -name Dockerfile -print | sort)

    while IFS= read -r base_tag; do
        [ -n "${base_tag}" ] || continue
        context="base_images/${base_tag}"
        if [ -f "${context}/Dockerfile" ]; then
            buildImageWithBuildx "${base_tag}" "${context}"
        elif docker image inspect "${base_tag}" >/dev/null 2>&1; then
            continue
        else
            echo "Missing compiler base image context: ${context}/Dockerfile" >&2
            echo "Re-run compile with the current KubernetesCompiler so base_images/ is generated." >&2
            missing=1
        fi
    done < <(sort -u "${tmpfile}")

    rm -f "${tmpfile}"
    return "${missing}"
}

ensureCompilerBaseImages

python3 "${HELPER}" mapped-images \
    --images-yaml "${IMAGES_YAML}" \
    --image-registry-prefix "${IMAGE_REGISTRY_PREFIX}" \
    --registry-prefix "${REGISTRY_PREFIX}" |
while IFS=$'\t' read -r image context; do
    [ -n "${image}" ] || continue
    [ -n "${context}" ] || { echo "Missing context for ${image}" >&2; exit 1; }
    buildImageWithBuildx "${image}" "${context}"
    echo "+ docker push ${image}"
    docker push "${image}"
done
'''


def main(argv: list[str] | None = None) -> int:
    """Run this entrypoint with optional argv override for tests."""
    return runEmbeddedShell(Path(__file__), list(sys.argv[1:] if argv is None else argv), SHELL_BODY)


if __name__ == "__main__":
    raise SystemExit(main())
