CARDANO CONWAY TRANSACTION AUTOMATION + OPTIONAL SENSOR METADATA
================================================================
Environment: your B12-cardano project, Python >=3.8, existing cardano-cli,
Docker Cardano nodes, network magic 4242.

INSTALL
-------
1. Save cardano_transaction.py in the B12-cardano directory, next to blockchain.py.
2. Keep your existing config/, data/, and keys; do not regenerate them.
3. In B12-cardano, run: python3 cardano_transaction.py --help

METADATA EXAMPLE: CIP-20 LABEL 674
---------------------------------
Create the file from the B12-cardano directory:

mkdir -p data/metadata-test
cat > data/metadata-test/sensor_metadata.json <<'JSON'
{
  "674": {
    "msg": [
      "Sensor: AGRI_001",
      "Temperature: 24.5 C",
      "Humidity: 62 percent",
      "Location: Greenhouse_01"
    ]
  }
}
JSON

DRY RUN (builds but does not sign/submit/spend)
-----------------------------------------------
python3 cardano_transaction.py \
  --node 150 --from 1 --to 2 --amount 2 \
  --metadata data/metadata-test/sensor_metadata.json

LIVE EXECUTION (spends test ADA)
--------------------------------
python3 cardano_transaction.py \
  --node 150 --from 1 --to 2 --amount 2 \
  --metadata data/metadata-test/sensor_metadata.json \
  --verify-nodes 150 151 152 153 --timeout 300 --execute

ORDINARY TRANSFERS STILL WORK (no --metadata)
---------------------------------------------
python3 cardano_transaction.py --node 151 --from 2 --to 3 --amount 1

NODE SELECTION
--------------
--node 150 / 151 / 152 / 153 chooses a Docker node.
Alternatively, pass a complete Docker container name.
--from and --to choose delegator indexes, .addr files, or Bech32 addresses.
For custom senders, specify --signing-key /path/to/payment.skey.
The submitting Docker node is NOT necessarily the owner of the sender address.

AUTOMATED WORKFLOW
------------------
1. Validate address, amount, optional metadata JSON.
2. Query sender's unspent pure-ADA outputs; select enough for amount plus reserve.
3. Copy metadata to Docker /tmp if supplied.
4. Build Conway transaction with --metadata-json-file and automatic fee/change.
5. Copy unsigned transaction to host. In dry run, stop here.
6. Locally sign with sender's payment signing key (never copied into Docker).
7. Copy signed transaction to chosen Docker node and submit.
8. Query each selected node for a recipient UTxO with this transaction hash.
9. Write CSV and JSON experiment records.

RECORDS
-------
data/transaction-test/transaction_history.csv
  Historical rows are preserved if the script upgrades the CSV header to
  include 'metadata_file' and 'metadata_sha256' columns.
data/transaction-test/runs/<timestamp>_<id>/
  tx.body, tx.signed (only for live transactions),
  metadata.json (only when metadata supplied),
  result.json, submission.txt (only for successfully submitted transactions).

READING METADATA FROM THE SIGNED TRANSACTION
--------------------------------------------
./resources/cardano-static/bin/cardano-cli debug transaction view \
  --tx-file data/transaction-test/runs/<RUN_ID>/tx.signed | jq '.metadata'

The above reads the LOCAL signed transaction. Confirmation is independently
checked from live node UTxO state. Independent historical on-chain retrieval
of metadata requires chain data access/indexing (not query utxo alone).

CAUTIONS
--------
* Metadata is visible to participants in the blockchain. Use dummy readings.
* JSON metadata uses numeric top-level labels; strings <= 64 UTF-8 bytes;
  do not directly supply floats, booleans, or nulls. Example uses CIP-20 674.
* The transaction fee is network-config dependent, and increases with size.
* Polling measurements represent detection of confirmation, not exact P2P
  propagation time or block-forging time.
* Do not run simultaneous transactions spending the same sender's UTxOs.
* Do not share payment.skey contents.
* Only plain ADA transfers are handled here; Plutus transactions need extra logic.
* The script was syntax/logic-checked locally, but not run against your VM.
