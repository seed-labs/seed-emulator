#!/usr/bin/env bash
set -euo pipefail

CLI="./resources/cardano-static/bin/cardano-cli"
NODE="as150h-Cardano-Node-1-10.150.0.71"
MAGIC=4242

FROM=1
TO=""
AMOUNT=2000000
MSG="Hello World!"
EXECUTE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f)
            FROM="$2"; shift 2 ;;
        -t)
            TO="$2"; shift 2 ;;
        -a)
            AMOUNT="$2"; shift 2 ;;
        -m)
            MSG="$2"; shift 2 ;;
        --execute)
            EXECUTE=true; shift ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1 ;;
    esac
done

[[ "$FROM" =~ ^[123]$ ]] || {
    echo "Sender must be delegator 1, 2, or 3" >&2
    exit 1
}

[[ "$AMOUNT" =~ ^[0-9]+$ ]] || {
    echo "Amount must be an integer in lovelace" >&2
    exit 1
}

KEYROOT="config/generated/testnet-02/stake-delegators"
KEY="$KEYROOT/delegator${FROM}/payment.skey"
ADDR_FILE="data/transaction-test/delegator${FROM}-base.addr"

[[ -f "$KEY" && -f "$ADDR_FILE" && -x "$CLI" ]] || {
    echo "Missing signing key, address file, or cardano-cli" >&2
    exit 1
}

ADDR=$(tr -d '\r\n' < "$ADDR_FILE")

# Create private temporary workspace on the VM.
umask 077
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# Generate CIP-20 metadata with valid JSON escaping.
python3 - "$MSG" "$WORK/meta.json" <<'PY'
import json
import sys

msg = sys.argv[1]
chunks = []
current = ""

for char in msg:
    candidate = current + char
    if len(candidate.encode("utf-8")) > 64:
        if current:
            chunks.append(current)
        current = char
    else:
        current = candidate

if current:
    chunks.append(current)

with open(sys.argv[2], "w") as f:
    json.dump({"674": {"msg": chunks}}, f)
PY

echo "Sender: $ADDR"
echo "Metadata:"
cat "$WORK/meta.json"
echo

# Query UTxOs from the Cardano container.
docker exec "$NODE" \
    cardano-cli query utxo \
    --address "$ADDR" \
    --testnet-magic "$MAGIC" \
    --socket-path /cardano/node.socket \
    > "$WORK/utxos.json"

# Select the largest pure-ADA UTxO.
UTXO=$(python3 - "$WORK/utxos.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    entries = json.load(f)

candidates = []

for ref, entry in entries.items():
    value = entry.get("value", {})
    if (
        isinstance(value, dict)
        and set(value) == {"lovelace"}
        and int(value["lovelace"]) > 0
    ):
        candidates.append((int(value["lovelace"]), ref))

if candidates:
    print(max(candidates)[1])
PY
)

[[ -n "$UTXO" ]] || {
    echo "No suitable funded UTxO found" >&2
    exit 1
}

echo "Selected UTxO: $UTXO"

# Build using the running node.
# Only public metadata and unsigned transaction files enter Docker.
docker cp "$WORK/meta.json" "$NODE:/tmp/meta-$$.json"

REMOTE_META="/tmp/meta-$$.json"
REMOTE_TX="/tmp/tx-$$.raw"

cleanup_remote() {
    docker exec "$NODE" rm -f "$REMOTE_META" "$REMOTE_TX" \
        >/dev/null 2>&1 || true
}

trap 'cleanup_remote; rm -rf "$WORK"' EXIT

OUT_ARGS=()

if [[ -n "$TO" ]]; then
    [[ "$TO" == addr_test1* ]] || {
        echo "Invalid receiver address" >&2
        exit 1
    }
    (( AMOUNT > 0 )) || {
        echo "Transfer amount must be positive" >&2
        exit 1
    }
    OUT_ARGS=(--tx-out "${TO}+${AMOUNT}")
fi

docker exec "$NODE" \
    cardano-cli conway transaction build \
    --testnet-magic "$MAGIC" \
    --socket-path /cardano/node.socket \
    --tx-in "$UTXO" \
    "${OUT_ARGS[@]}" \
    --change-address "$ADDR" \
    --metadata-json-file "$REMOTE_META" \
    --out-file "$REMOTE_TX"

docker cp "$NODE:$REMOTE_TX" "$WORK/tx.raw"

echo "Transaction built successfully."

if [[ "$EXECUTE" != true ]]; then
    echo "DRY RUN: Transaction was not signed or submitted."
    exit 0
fi

# Sign locally, keeping the signing key outside Docker.
"$CLI" conway transaction sign \
    --tx-body-file "$WORK/tx.raw" \
    --signing-key-file "$KEY" \
    --out-file "$WORK/tx.signed"

docker cp "$WORK/tx.signed" "$NODE:/tmp/tx-$$.signed"

docker exec "$NODE" \
    cardano-cli conway transaction submit \
    --tx-file "/tmp/tx-$$.signed" \
    --testnet-magic "$MAGIC" \
    --socket-path /cardano/node.socket

TXID=$("$CLI" conway transaction txid \
    --tx-file "$WORK/tx.signed")

# Handle Cardano CLI versions that return JSON.
TXID=$(printf '%s\n' "$TXID" | python3 -c '
import json, sys
value = sys.stdin.read().strip()
try:
    value = json.loads(value)
    if isinstance(value, dict):
        value = value["txhash"]
except json.JSONDecodeError:
    pass
print(value)
')

# Preserve the signed transaction for verification.
mkdir -p data/metadata-test

cp "$WORK/tx.signed" \
   "data/metadata-test/${TXID}.signed"

cp "$WORK/meta.json" \
   "data/metadata-test/${TXID}.metadata.json"

echo "Submitted transaction ID: $TXID"
echo "Signed transaction saved to: data/metadata-test/${TXID}.signed"

docker exec "$NODE" rm -f "/tmp/tx-$$.signed"
