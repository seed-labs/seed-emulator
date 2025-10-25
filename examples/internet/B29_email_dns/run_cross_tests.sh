#!/usr/bin/env bash
# Cross-domain test runner for B29 Email (DNS-first)
# Default: test primary providers only (qq, 163, gmail, outlook) to avoid known AS-204<->AS-205 routing issue
# Usage:
#   bash run_cross_tests.sh            # primary providers only
#   bash run_cross_tests.sh --all      # all six providers
#   bash run_cross_tests.sh --pairs file.txt   # custom pairs: each line "from_addr to_addr"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"

containers=(
  mail-qq-tencent
  mail-163-netease
  mail-gmail-google
  mail-outlook-microsoft
  mail-company-aliyun
  mail-startup-selfhosted
)
domains=(
  qq.com
  163.com
  gmail.com
  outlook.com
  company.cn
  startup.net
)
# default sender usernames by domain index
from_users=(
  user
  user
  user
  user
  admin
  founder
)

use_all=0
pairs_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) use_all=1; shift;;
    --pairs) pairs_file="${2:-}"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

# Ensure output is up
if [ ! -f "$OUTPUT_DIR/docker-compose.yml" ]; then
  echo "[run_cross_tests] output/docker-compose.yml not found; run 'bash b29ctl.sh start' first" >&2
  exit 1
fi

# Build test pairs
declare -a FROM_CONTAINERS
declare -a FROM_ADDRS
declare -a TO_CONTAINERS
declare -a TO_ADDRS

if [ -n "$pairs_file" ]; then
  # custom pairs
  while read -r a b; do
    [[ -z "${a:-}" || "${a:0:1}" == "#" ]] && continue
    from="${a}"; to="${b}"
    # infer recipient container by domain
    to_domain="${to##*@}"
    to_ci=-1
    for idx in {0..5}; do
      if [[ "${domains[$idx]}" == "$to_domain" ]]; then to_ci=$idx; break; fi
    done
    if [[ $to_ci -lt 0 ]]; then echo "Unknown recipient domain: $to"; continue; fi
    # infer sender container by domain
    from_domain="${from##*@}"
    from_ci=-1
    for idx in {0..5}; do
      if [[ "${domains[$idx]}" == "$from_domain" ]]; then from_ci=$idx; break; fi
    done
    if [[ $from_ci -lt 0 ]]; then echo "Unknown sender domain: $from"; continue; fi
    FROM_CONTAINERS+=("${containers[$from_ci]}")
    FROM_ADDRS+=("$from")
    TO_CONTAINERS+=("${containers[$to_ci]}")
    TO_ADDRS+=("$to")
  done < "$pairs_file"
else
  # matrix pairs (primary providers by default)
  if [[ $use_all -eq 1 ]]; then idxs=(0 1 2 3 4 5); else idxs=(0 1 2 3); fi
  for i in "${idxs[@]}"; do
    for j in "${idxs[@]}"; do
      if [[ $i -ne $j ]]; then
        from_c="${containers[$i]}"; from_d="${domains[$i]}"; from_user="${from_users[$i]}"; from_addr="${from_user}@${from_d}"
        to_c="${containers[$j]}"; to_d="${domains[$j]}"
        # default recipient user maps: user for first four, admin for company, founder for startup
        case "$to_d" in
          company.cn) to_user="admin";;
          startup.net) to_user="founder";;
          *) to_user="user";;
        esac
        to_addr="${to_user}@${to_d}"
        FROM_CONTAINERS+=("$from_c"); FROM_ADDRS+=("$from_addr"); TO_CONTAINERS+=("$to_c"); TO_ADDRS+=("$to_addr")
      fi
    done
  done
fi

ok=0; fail=0; total=0
for idx in "${!FROM_CONTAINERS[@]}"; do
  from_c="${FROM_CONTAINERS[$idx]}"; from_addr="${FROM_ADDRS[$idx]}"
  to_c="${TO_CONTAINERS[$idx]}"; to_addr="${TO_ADDRS[$idx]}"
  total=$((total+1))
  subject_token="$(date +%s)-$RANDOM"
  printf "Subject: %s\nTo: %s\nFrom: %s\n\nHi %s\n" "${from_addr##*@}->${to_addr##*@}" "$to_addr" "$from_addr" "$subject_token" \
    | docker exec -i "$from_c" sh -c "sendmail -t" || true
  delivered=0
  for k in {1..15}; do
    if docker exec "$to_c" sh -lc "grep -E \"(Saved|stored mail into mailbox .*INBOX|status=sent .* to=<$to_addr>)\" -n /var/log/mail/mail.log" >/dev/null 2>&1; then
      delivered=1; break; fi
    sleep 1
  done
  if [[ $delivered -eq 1 ]]; then echo "OK ${from_addr##*@} -> ${to_addr##*@}"; ok=$((ok+1)); else echo "FAIL ${from_addr##*@} -> ${to_addr##*@}"; fail=$((fail+1)); fi
done
printf "SUMMARY: OK=%d FAIL=%d TOTAL=%d\n" "$ok" "$fail" "$total"
