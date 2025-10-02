#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法: cleanup_seed_env.sh [--full]

清理 29/57 实验生成的容器与网络，避免 docker-compose 网段冲突。
  --full   额外删除 seed_emulator 网络（默认仅删除 output_* 网络）
EOF
}

FULL_CLEAN=false
if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--full" ]]; then
  FULL_CLEAN=true
fi

bold() { printf '\033[1m%s\033[0m\n' "$1"; }

bold "[1/4] 停止并删除 mailserver / as*** 容器"
mapfile -t containers < <(docker ps -aq --filter "name=mailserver" --filter "name=as.*h-" || true)
if [[ ${#containers[@]} -gt 0 ]]; then
  docker rm -f "${containers[@]}"
else
  echo "无相关容器"
fi

bold "[2/4] 删除残留的 output_net_* 网络"
mapfile -t networks < <(docker network ls --format '{{.Name}}' | grep -E '^output_' || true)
if [[ ${#networks[@]} -gt 0 ]]; then
  docker network rm "${networks[@]}"
else
  echo "无 output_* 网络"
fi

if [[ "$FULL_CLEAN" == true ]]; then
  bold "[3/4] 删除 seed_emulator 网络"
  docker network rm seed_emulator 2>/dev/null || echo "seed_emulator 不存在"
else
  bold "[3/4] 保留 seed_emulator 网络 (增加 --full 可删除)"
fi

bold "[4/4] 清理悬挂镜像与构建缓存"
docker system prune -f >/dev/null

bold "完成：基础环境已清理，可重新运行实验。"
