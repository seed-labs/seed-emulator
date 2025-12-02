from web3 import Web3
from datetime import datetime
import json

# Connect to the Ethereum node
w3 = Web3(Web3.HTTPProvider("http://10.152.0.71:8545"))

# Request the list of peers (requires admin API enabled on Geth)
peers = w3.provider.make_request("admin_peers", [])

# Pretty-print the raw JSON response
print(json.dumps(peers, indent=4))

print("\n===== Extracted Addresses =====")

# Extract localAddress and remoteAddress from each peer
for p in peers.get("result", []):
    network = p.get("network", {})
    local_addr = network.get("localAddress")
    remote_addr = network.get("remoteAddress")

    print(f"local: {local_addr},   remote: {remote_addr}")

