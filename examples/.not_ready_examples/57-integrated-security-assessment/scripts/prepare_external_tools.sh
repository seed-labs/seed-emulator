#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
TOOLS_DIR="${ROOT_DIR}/external_tools"

clone_or_update() {
  local repo_url="$1";
  local target_dir="$2";
  if [ -d "${target_dir}/.git" ]; then
    echo "[+] Updating $(basename "${target_dir}")"
    git -C "${target_dir}" pull --ff-only
  else
    echo "[+] Cloning $(basename "${target_dir}")"
    git clone --depth=1 "${repo_url}" "${target_dir}"
  fi
}

mkdir -p "${TOOLS_DIR}"

# 1. Gophish
clone_or_update "https://github.com/gophish/gophish.git" "${TOOLS_DIR}/gophish"
mkdir -p "${TOOLS_DIR}/gophish" "${TOOLS_DIR}/gophish/docker"
cat > "${TOOLS_DIR}/gophish/docker/docker-compose.yml" <<'EOF'
version: "3.9"
services:
  gophish:
    image: gophish/gophish:latest
    container_name: gophish
    restart: unless-stopped
    environment:
      - GOPHISH_ADMIN_LISTEN=0.0.0.0:3333
      - GOPHISH_ADMIN_USE_TLS=true
      - GOPHISH_CONFIG=/config/config.json
    ports:
      - "3333:3333"   # Admin UI (HTTPS)
      - "8080:80"     # Phishing landing pages (HTTP)
    volumes:
      - ./config:/config
    networks:
      - seed_emulator
networks:
  seed_emulator:
    external: true
EOF

cat > "${TOOLS_DIR}/gophish/docker/README.md" <<'EOF'
# Gophish Deployment Notes

1. 确保 Seed-Emulator 已创建外部网络 `seed_emulator`：

   ```bash
   docker network create seed_emulator || true
   ```

2. 启动 Gophish：

   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

3. 首次启动会在容器日志中输出管理员密码：

   ```bash
   docker logs gophish | grep "Please login"
   ```

4. 管理员 UI 默认监听 https://localhost:3333，钓鱼落地页监听 http://localhost:8080。

5. 如需使用 SEED 邮件系统发信，请在 Gophish UI 中配置 SMTP（推荐指向 29 或 29-1 邮件服务）。
EOF

# 2. PentestAgent
clone_or_update "https://github.com/nbshenxm/pentest-agent.git" "${TOOLS_DIR}/pentest-agent"
mkdir -p "${TOOLS_DIR}/pentest-agent/docker"
cat > "${TOOLS_DIR}/pentest-agent/.env.example" <<'EOF'
# PentestAgent 环境变量示例
OPENAI_API_KEY=sk-xxx
HUGGING_FACE_TOKEN=hf_xxx
PROJECTDISCOVERY_KEY=pdcp_xxx
GITHUB_KEY=ghp_xxx
GITLAB_TOKEN=glpat-xxx
INDEX_STORAGE_DIR=/data/indexes
PLANNING_OUTPUT_DIR=/data/planning
LOG_DIR=/data/logs
EOF

cat > "${TOOLS_DIR}/pentest-agent/docker/docker-compose.local.yml" <<'EOF'
version: "3.9"
services:
  recon:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: ["python", "pentest_agent/agents/recon_agent.py"]
    env_file:
      - ../.env
    volumes:
      - ../data:/data
    networks:
      - seed_emulator
    container_name: pentestagent-recon
  planning:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: ["python", "pentest_agent/agents/planning_agent.py"]
    env_file:
      - ../.env
    volumes:
      - ../data:/data
    networks:
      - seed_emulator
    container_name: pentestagent-planning
  execution:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: ["python", "pentest_agent/agents/execution_agent.py"]
    env_file:
      - ../.env
    volumes:
      - ../data:/data
    networks:
      - seed_emulator
    container_name: pentestagent-execution
networks:
  seed_emulator:
    external: true
EOF

cat > "${TOOLS_DIR}/pentest-agent/docker/README.md" <<'EOF'
# PentestAgent Deployment Notes

1. 复制 `.env.example` 为 `.env` 并填写真实的 API key / token。
2. 建议创建数据目录：

   ```bash
   mkdir -p ../data/indexes ../data/planning ../data/logs
   ```

3. 构建并启动容器：

   ```bash
   docker compose -f docker/docker-compose.local.yml up -d
   ```

4. 需要时可一次启动某个 agent，例如：

   ```bash
   docker compose -f docker/docker-compose.local.yml up recon
   ```

5. 在 `configs/config.yaml` 中设置 Seed-Emulator 目标主机的 IP/端口。
EOF

# 3. OpenBAS
clone_or_update "https://github.com/OpenAEV-Platform/openaev.git" "${TOOLS_DIR}/openaev"
mkdir -p "${TOOLS_DIR}/openaev/deploy"
cat > "${TOOLS_DIR}/openaev/deploy/docker-compose.local.yml" <<'EOF'
version: "3.9"
services:
  openbas:
    image: openbas/openbas:latest
    container_name: openbas
    restart: unless-stopped
    environment:
      - OPENBAS_ADMIN_EMAIL=admin@openaev.local
      - OPENBAS_ADMIN_PASSWORD=ChangeMe!123
      - OPENBAS_BASE_URL=https://openbas.local
    ports:
      - "8443:443"
    volumes:
      - openbas-data:/data
    networks:
      - seed_emulator
volumes:
  openbas-data:
networks:
  seed_emulator:
    external: true
EOF

cat > "${TOOLS_DIR}/openaev/deploy/README.md" <<'EOF'
# OpenBAS Deployment Notes

1. 确保已经配置 Docker 外部网络 `seed_emulator`：

   ```bash
   docker network create seed_emulator || true
   ```

2. 启动服务：

   ```bash
   docker compose -f deploy/docker-compose.local.yml up -d
   ```

3. 首次登陆：https://localhost:8443 ，账号 `admin@openaev.local`，密码 `ChangeMe!123`。

4. 建议登陆后立即修改密码，并根据需要配置 SMTP、Webhook、Integration 等组件。
EOF

echo "[+] External security tools prepared under ${TOOLS_DIR}"