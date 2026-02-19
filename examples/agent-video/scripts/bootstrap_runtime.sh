#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIDEO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${VIDEO_ROOT}/.runtime"

NODE_VERSION="${SEED_VIDEO_NODE_VERSION:-v20.12.2}"

arch="$(uname -m)"
case "${arch}" in
  aarch64|arm64) node_arch="arm64" ;;
  x86_64|amd64) node_arch="x64" ;;
  *)
    echo "[seed-video] ERROR: unsupported arch: ${arch}" >&2
    exit 2
    ;;
esac

node_dist="node-${NODE_VERSION}-linux-${node_arch}"
tarball="${RUNTIME_DIR}/downloads/${node_dist}.tar.xz"
node_home="${RUNTIME_DIR}/node"

mkdir -p "${RUNTIME_DIR}/downloads"

if [[ ! -x "${node_home}/bin/node" ]]; then
  if [[ ! -f "${tarball}" ]]; then
    url="https://nodejs.org/dist/${NODE_VERSION}/${node_dist}.tar.xz"
    echo "[seed-video] Downloading Node: ${url}"
    curl -fsSL "${url}" -o "${tarball}"
  fi

  tmp="${RUNTIME_DIR}/tmp_extract"
  rm -rf "${tmp}"
  mkdir -p "${tmp}"
  tar -xJf "${tarball}" -C "${tmp}"
  extracted="$(find "${tmp}" -maxdepth 1 -type d -name 'node-v*-linux-*' | head -n 1 || true)"
  if [[ -z "${extracted}" ]]; then
    echo "[seed-video] ERROR: failed to extract node tarball: ${tarball}" >&2
    exit 2
  fi

  rm -rf "${node_home}"
  mv "${extracted}" "${node_home}"
  rm -rf "${tmp}"
fi

echo "[seed-video] node=$("${node_home}/bin/node" --version)"
