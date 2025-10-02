#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"

if ! command -v python >/dev/null 2>&1; then
  echo "[!] 未找到 python，请先配置 Python 环境" >&2
  exit 1
fi

if [ -f "${ROOT_DIR}/requirements.txt" ]; then
  echo "[+] 如果尚未安装依赖，可执行："
  echo "    python -m pip install -r requirements.txt"
fi

echo "[+] 启动 57 号实验集成控制台 (http://localhost:4257)"
cd "${ROOT_DIR}"
exec python web_interface.py
