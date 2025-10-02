#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIL_DIR="${ROOT_DIR}/examples/.not_ready_examples/29-email-system/output"
INTEGRATED_DIR="${ROOT_DIR}/examples/.not_ready_examples/57-integrated-security-assessment"
TOOLS_DIR="${INTEGRATED_DIR}/external_tools"

usage() {
  cat <<'EOF'
用法: run_demo_57.sh <start|stop|status>

start  : 启动 29 邮件基座 + 57 号特色演练的外部工具（Gophish/PentestAgent/OpenBAS）
stop   : 停止上述所有 Compose 栈
status : 查看关键容器与端口状态

要求：
  1. 已在 29-email-system 目录执行过 email_system.py 生成 output/docker-compose.yml
  2. 已运行 ./scripts/prepare_external_tools.sh 拉取外部工具仓库
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

command_exists() { command -v "$1" >/dev/null 2>&1; }

detect_compose() {
  if command_exists docker && docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
    return
  fi
  if command_exists docker-compose; then
    COMPOSE_CMD=(docker-compose)
    return
  fi
  echo "错误: 未找到 docker compose 或 docker-compose" >&2
  exit 1
}

create_network_if_missing() {
  local net="$1"
  if ! docker network inspect "$net" >/dev/null 2>&1; then
    docker network create "$net" >/dev/null
  fi
}

connect_with_alias() {
  local net="$1" container="$2" alias="$3"
  if docker network inspect "$net" >/dev/null 2>&1; then
    if ! docker network inspect "$net" | grep -q "\"Name\": \"$container\""; then
      docker network connect --alias "$alias" "$net" "$container" 2>/dev/null || true
    fi
  fi
}

start_mail_stack() {
  echo "[Mail] 启动 29 邮件实验栈"
  if [[ ! -f "${MAIL_DIR}/docker-compose.yml" ]]; then
    echo "  ✖ 未找到 ${MAIL_DIR}/docker-compose.yml，请先运行 email_system.py" >&2
    exit 1
  fi
  pushd "$MAIL_DIR" >/dev/null
  "${COMPOSE_CMD[@]}" up -d
  popd >/dev/null
}

start_external_tools() {
  echo "[57] 启动外部工具"
  if [[ ! -d "${TOOLS_DIR}" ]]; then
    echo "  ✖ 未找到 external_tools，请先执行 prepare_external_tools.sh" >&2
    exit 1
  fi

  pushd "${TOOLS_DIR}/gophish/docker" >/dev/null
  "${COMPOSE_CMD[@]}" up -d
  popd >/dev/null

  pushd "${TOOLS_DIR}/pentest-agent/docker" >/dev/null
  "${COMPOSE_CMD[@]}" up -d
  popd >/dev/null

  pushd "${TOOLS_DIR}/openaev/deploy" >/dev/null
  "${COMPOSE_CMD[@]}" up -d
  popd >/dev/null

  create_network_if_missing seed_emulator
  connect_with_alias seed_emulator gophish gophish-admin
  connect_with_alias seed_emulator pentestagent-recon pentest-recon
  connect_with_alias seed_emulator pentestagent-planning pentest-plan
  connect_with_alias seed_emulator pentestagent-execution pentest-core
  connect_with_alias seed_emulator openbas openbas-c2
}

stop_mail_stack() {
  if [[ -f "${MAIL_DIR}/docker-compose.yml" ]]; then
    echo "[Mail] 停止邮件实验栈"
    pushd "$MAIL_DIR" >/dev/null
    "${COMPOSE_CMD[@]}" down
    popd >/dev/null
  fi
}

stop_external_tools() {
  if [[ -d "${TOOLS_DIR}/gophish/docker" ]]; then
    echo "[57] 停止 Gophish"
    pushd "${TOOLS_DIR}/gophish/docker" >/dev/null
    "${COMPOSE_CMD[@]}" down
    popd >/dev/null
  fi
  if [[ -d "${TOOLS_DIR}/pentest-agent/docker" ]]; then
    echo "[57] 停止 PentestAgent"
    pushd "${TOOLS_DIR}/pentest-agent/docker" >/dev/null
    "${COMPOSE_CMD[@]}" down
    popd >/dev/null
  fi
  if [[ -d "${TOOLS_DIR}/openaev/deploy" ]]; then
    echo "[57] 停止 OpenBAS"
    pushd "${TOOLS_DIR}/openaev/deploy" >/dev/null
    "${COMPOSE_CMD[@]}" down
    popd >/dev/null
  fi
}

show_status() {
  echo "容器状态："
  docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'mailserver|as[0-9]+h|gophish|pentestagent|openbas|seedemu' || echo "无相关容器"
  echo
  echo "端口检测："
  for port in 8000 2525 2526 2527 5870 5871 5872 1430 1431 1432 9930 9931 9932 3333 8080 8443 5080 4257; do
    if lsof -Pi :"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      printf "  %5s : LISTEN\n" "$port"
    fi
  done
}

ACTION=$1
detect_compose
case "$ACTION" in
  start)
    start_mail_stack
    start_external_tools
    echo "启动完成，可访问：http://localhost:8000、https://localhost:3333、https://localhost:8443、http://localhost:4257"
    ;;
  stop)
    stop_external_tools
    stop_mail_stack
    echo "所有服务已停止"
    ;;
  status)
    show_status
    ;;
  *)
    usage
    exit 1
    ;;
esac
