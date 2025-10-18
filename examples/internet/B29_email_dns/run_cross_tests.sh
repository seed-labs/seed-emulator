#!/usr/bin/env bash
set -uo pipefail

# Batch cross-domain email tests for B29 (DNS-first)
# Requires B29 stack up and accounts created via ./manage_roundcube.sh accounts

# Usage:
#   ./run_cross_tests.sh                 # use defaults
#   ./run_cross_tests.sh pairs.txt       # custom pairs file (one "from to" per line)
#   ./run_cross_tests.sh --pairs pairs.txt

PAIRS_INPUT=""
if [ $# -ge 1 ]; then
  if [ "$1" = "--pairs" ] && [ $# -ge 2 ]; then
    PAIRS_INPUT="$2"
  elif [ -f "$1" ]; then
    PAIRS_INPUT="$1"
  fi
fi

if [ -n "$PAIRS_INPUT" ] && [ -f "$PAIRS_INPUT" ]; then
  mapfile -t PAIRS < <(grep -E -v '^\s*(#|$)' "$PAIRS_INPUT")
else
  mapfile -t PAIRS < <(cat <<'EOF'
user@qq.com user@gmail.com
user@gmail.com user@qq.com
user@qq.com user@163.com
user@163.com user@outlook.com
admin@company.cn founder@startup.net
founder@startup.net admin@company.cn
user@163.com user@gmail.com
user@outlook.com user@qq.com
EOF
  )
fi

# Domain -> container map
function container_for_domain(){
  local dom="$1"
  case "$dom" in
    qq.com) echo "mail-qq-tencent" ;;
    gmail.com) echo "mail-gmail-google" ;;
    163.com) echo "mail-163-netease" ;;
    outlook.com) echo "mail-outlook-microsoft" ;;
    company.cn) echo "mail-company-aliyun" ;;
    startup.net) echo "mail-startup-selfhosted" ;;
    *) return 1 ;;
  esac
}

function domain_of(){ echo "${1##*@}"; }

function ensure_account(){
  local addr="$1"
  local dom; dom="$(domain_of "$addr")"
  local ctn; ctn="$(container_for_domain "$dom")"
  printf "password123\npassword123\n" | docker exec -i "$ctn" setup email add "$addr" >/dev/null 2>&1 || true
}

function send_and_check(){
  local from="$1" to="$2"
  local from_dom to_dom from_ctn to_ctn
  from_dom="$(domain_of "$from")"; to_dom="$(domain_of "$to")"
  from_ctn="$(container_for_domain "$from_dom")"
  to_ctn="$(container_for_domain "$to_dom")"
  ensure_account "$to" # recipient must exist
  ensure_account "$from" || true

  local now subj
  now="$(date +%s)"; subj="B29 ${from} -> ${to} ${now}"

  printf "Subject: %s\nFrom: %s\nTo: %s\n\nB29 batch test at %s\n" "$subj" "$from" "$to" "$now" |
    docker exec -i "$from_ctn" sendmail "$to" >/dev/null 2>&1 || true

  # Poll up to ~20s for delivery evidence
  local ok=1
  for i in {1..20}; do
    if docker logs --since 3m "$to_ctn" 2>/dev/null | grep -E "to=<${to}>.*Saved|stored mail into mailbox 'INBOX'" >/dev/null; then
      ok=0; break
    fi
    sleep 1
  done
  if [ $ok -eq 0 ]; then
    echo "PASS: ${from} -> ${to}"
    return 0
  else
    echo "FAIL: ${from} -> ${to} (no Saved/INBOX evidence)"
    docker logs --since 3m "$to_ctn" 2>/dev/null | egrep -i "${to}|lmtp|status=|cleanup|qmgr" | tail -n 20 || true
    return 1
  fi
}

passes=0; fails=0
for line in "${PAIRS[@]}"; do
  from="${line%% *}"; to="${line##* }"
  if send_and_check "$from" "$to"; then
    ((passes++))
  else
    ((fails++))
  fi
done

echo ""; echo "Summary: passes=${passes} fails=${fails} total=$((passes+fails))"
exit $([ "$fails" -eq 0 ] && echo 0 || echo 1)
