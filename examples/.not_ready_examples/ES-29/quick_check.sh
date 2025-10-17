#!/usr/bin/env bash
set -euo pipefail

# Quick health check for 29-email-system
# Usage:
#   ./quick_check.sh           # status only
#   ./quick_check.sh --send    # also send a test email seedemail -> corporate

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/output" || { echo "output/ not found, run email_simple.py first"; exit 1; }

echo "== docker-compose ps"
docker-compose ps || true

echo
echo "== RS (IX-100) peers"
docker exec as100brd-ix100-10.100.0.100 birdc show protocols | grep BGP || true

echo
echo "== AS150 route to 10.151.0.0/24"
docker exec as150brd-router0-10.150.0.254 birdc show route for 10.151.0.0/24 || true

echo
echo "== corporate transport map (should NOT include corporate.local)"
docker exec mail-151-corporate sh -lc "sed -n '1,80p' /etc/postfix/transport || true"

if [[ "${1:-}" == "--send" ]]; then
  echo
  echo "== send seedemail -> corporate"
  printf "Subject: XDomain\nFrom: alice@seedemail.net\nTo: admin@corporate.local\n\nBody\n" \
    | docker exec -i mail-150-seedemail sendmail admin@corporate.local || true
  sleep 2
  echo
  echo "== sender log tail (mail-150-seedemail)"
  docker logs --tail 50 mail-150-seedemail || true
  echo
  echo "== receiver log tail (mail-151-corporate)"
  docker logs --tail 50 mail-151-corporate || true
fi
