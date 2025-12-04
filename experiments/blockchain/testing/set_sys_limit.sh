#!/usr/bin/env bash
set -e
echo "kernel.pid_max = 4194303" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

echo "===== Applying system-wide file descriptor and process limits ====="

LIMITS_FILE="/etc/security/limits.conf"

append_if_missing() {
    local pattern="$1"
    local line="$2"

    if ! grep -qF "$pattern" "$LIMITS_FILE"; then
        echo "$line" | sudo tee -a "$LIMITS_FILE" >/dev/null
        echo "Added: $line"
    else
        echo "Exists: $line"
    fi
}

# Add limits (soft/hard nofile + nproc)
append_if_missing "* soft nofile"    "*               soft    nofile          1048576"
append_if_missing "* hard nofile"    "*               hard    nofile          1048576"
append_if_missing "* soft nproc"     "*               soft    nproc           1048576"
append_if_missing "* hard nproc"     "*               hard    nproc           1048576"

# Add root-specific limits
append_if_missing "root soft nofile" "root            soft    nofile          1048576"
append_if_missing "root hard nofile" "root            hard    nofile          1048576"

echo "===== Done. Reboot required for full effect ====="

