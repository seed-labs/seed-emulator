#!/usr/bin/env bash
set -e

echo "===== Configure Docker systemd limits (High Concurrency) ====="

# Create override directory
sudo mkdir -p /etc/systemd/system/docker.service.d

# Write override config
cat <<EOF | sudo tee /etc/systemd/system/docker.service.d/override.conf >/dev/null
[Service]
LimitNOFILE=1048576
LimitNPROC=4194304
TasksMax=4194304
EOF

echo "? override.conf created with high limits"

# Reload systemd
sudo systemctl daemon-reload
echo "? systemd daemon reloaded"

# Restart Docker
sudo systemctl restart docker
echo "? Docker restarted"

echo "===== Done: High concurrency limits applied ====="

