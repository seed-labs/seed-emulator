#!/bin/bash
# Send a transaction carrying a text message as metadata (label 674).
# Run on the VM (not inside a container), from the cardano/ folder.
#
#   ./send-metadata.sh                                     utxo1 -> itself, "Hello World!"
#   ./send-metadata.sh -m "temp-01: 21.4"                  custom message
#   ./send-metadata.sh -f utxo2 -t addr_test1... -a 5000000 -m "hi"
#
#   -f  sender: utxo1 / utxo2, or a key path prefix like /cardano/payment
#       (then <prefix>.vkey and <prefix>.skey are used)     default: utxo1
#   -t  receiver address; if omitted, no ADA is sent and everything
#       except the fee goes back to the sender               default: none
#   -a  lovelace sent to the receiver (1 ADA = 1000000)      default: 2000000
#   -m  message                                              default: "Hello World!"
#
# Wait ~10 s between two sends from the same wallet.
set -e
FROM=utxo1; TO=""; AMOUNT=2000000; MSG="Hello World!"
while getopts "f:t:a:m:" opt; do
  case $opt in
    f) FROM=$OPTARG ;;
    t) TO=$OPTARG ;;
    a) AMOUNT=$OPTARG ;;
    m) MSG=$OPTARG ;;
    *) awk 'NR>1 && /^#/ {print; next} NR>1 {exit}' "$0"; exit 1 ;;
  esac
done

# sender's key files (inside the container)
if [[ $FROM == */* ]]; then KEY=$FROM; else KEY=/cardano/utxo-keys/$FROM/utxo; fi

# message -> metadata JSON, split into 64-byte strings (Cardano's limit per string)
CHUNKS=$(printf '%s' "$MSG" | fold -b -w 64 | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/.*/"&"/' | paste -sd, -)
META="{\"674\": {\"msg\": [$CHUNKS]}}"

# pool 1's container, found by its SEED display name
C="as150h-Cardano-Node-1-10.150.0.71"
[ -n "$C" ] || { echo "pool 1 container not found"; exit 1; }

# everything below runs inside the container
docker exec -i -e CARDANO_NODE_SOCKET_PATH=/cardano/node.socket -w /tmp "$C" \
  bash -s -- "$KEY" "$TO" "$AMOUNT" "$META" <<'EOF'
set -e
KEY=$1; TO=$2; AMOUNT=$3; META=$4
ADDR=$(cardano-cli conway address build --payment-verification-key-file "$KEY.vkey" --testnet-magic 4242)

# spend all of the sender's unspent outputs (TxHash#TxIx)
INS=()
for t in $(cardano-cli conway query utxo --address "$ADDR" --testnet-magic 4242 | grep -o '[0-9a-f]\{64\}#[0-9]*'); do
  INS+=(--tx-in "$t")
done
if [ ${#INS[@]} -eq 0 ]; then echo "sender $ADDR has no funds"; exit 1; fi

# receiver output, only if -t was given
OUT=()
if [ -n "$TO" ]; then OUT=(--tx-out "$TO+$AMOUNT"); fi

echo "$META" > meta.json
cardano-cli conway transaction build --testnet-magic 4242 "${INS[@]}" "${OUT[@]}" \
  --change-address "$ADDR" --metadata-json-file meta.json --out-file tx.raw
cardano-cli conway transaction sign --tx-body-file tx.raw --signing-key-file "$KEY.skey" --out-file tx.signed
cardano-cli conway transaction submit --tx-file tx.signed --testnet-magic 4242

echo "from: $ADDR"
echo "to:   ${TO:-(back to sender)}"
echo "meta: $META"
echo "txid: $(cardano-cli conway transaction txid --tx-file tx.signed)"
EOF
