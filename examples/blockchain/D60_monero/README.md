### D60_monero: Monero Blockchain Service Examples

This folder provides three Seed-Emulator examples for the Monero blockchain service:

- **ver1 (detailed configuration)**: Shows the full API surface with fine-grained options.
- **ver2 (default configuration)**: Minimal configuration to spin up a ready-to-use blockchain.
- **ver3 (custom binaries)**: Demonstrates how to run with your own Monero executables.

### ver1: Detailed configuration (monero_ver1_detailed_config.py)

- Create the blockchain with `MoneroService.createBlockchain("base-monero", net_type=...)`
- Configure blockchain-level options:
  - `setSeedConnectionMode()`: seed connectivity policy (e.g., EXCLUSIVE)
  - `setFixedDifficulty()`: fixed mining difficulty (reduce for demos/teaching)
  - `setDefaultWalletTemplate()`: default wallet template
- Define nodes and roles:
  - `createNode()` with `setSeedRole()`/`setClientRole()`
  - Control mining, threads, and triggers (e.g., AFTER_SEED_REACHABLE)
  - Enable Wallet RPC for light/full nodes as needed

Topology layout:
- AS150-154: two hosts per AS; `host_0` is seed, `host_1` is client (only AS150 client mines)
- AS160-161: one client per AS
- AS162-163: one light wallet per AS
- AS164: one pruned node

Run:
```bash
python3 monero_ver1_detailed_config.py [amd|arm]
cd output && docker compose build && docker compose up
```


### ver2: Default configuration (monero_ver2_default_config.py)

- Create a blockchain with minimal configuration: `MoneroService.createBlockchain("base-monero")`
- Use convenience node APIs:
  - `createSeedNode()` / `createClientNode()` / `createLightWallet()` / `createPrunedNode()`
- Demonstrate a mining trigger that starts only after seeds are reachable

Run:
```bash
python3 monero_ver2_default_config.py [amd|arm]
cd output && docker compose build && docker compose up
```


### ver3: Custom binaries (monero_ver3_custom_binary.py)

When you modify Monero (research/experiments), place your binaries under `custom/`:

- Required files:
  - `custom/monerod`
  - `custom/monero-wallet-cli`
  - `custom/monero-wallet-rpc`
- The script validates these files before proceeding
- Configure each node to use custom binaries:
  ```python
  server.options.binary_source = MoneroBinarySource.CUSTOM
  server.options.custom_binary_imports = {
      "/usr/local/bin/monerod": "<path>/custom/monerod",
      "/usr/local/bin/monero-wallet-cli": "<path>/custom/monero-wallet-cli",
      "/usr/local/bin/monero-wallet-rpc": "<path>/custom/monero-wallet-rpc",
  }
  ```

Run:
```bash
python3 monero_ver3_custom_binary.py [amd|arm]
cd output && docker compose build && docker compose up
```


### Interacting and verifying

- Seed and full nodes expose P2P/RPC/ZMQ ports (determined by blockchain defaults and auto assignment)
- Light wallet nodes enable Wallet RPC by default; check `enableWalletRpc()` in scripts for exposure settings

Enter a container:
```bash
docker ps | grep monero
docker exec -it <container_id_or_name> bash
```

### FAQ

- Port conflicts: Ports are auto-assigned across nodes; if you override ports manually, ensure no conflicts (P2P/RPC/ZMQ/Wallet-RPC).
- Slow mining: Reduce difficulty for demos (e.g., `setFixedDifficulty(2000)`).
- Missing custom binaries: Ensure all three files under `custom/` exist and are executable.


### Testing

The following commands help you validate the deployment. By default:
- Wallet RPC (digest auth) listens on 18088 inside containers (username/password are typically `seed:seed` in examples).
- Daemon RPC (no auth) listens on 28081 inside containers.

Replace `<container>` with an actual container name (e.g., `as150h-Monero-Client-150-10.150.0.72`).


#### Wallet RPC (port 18088, digest auth)

```bash
# Get wallet height
docker exec <container> curl -s --digest -u <user>:<pass> \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"height","method":"get_height"}' \
  http://127.0.0.1:18088/json_rpc

# Get wallet balance for account 0
docker exec <container> curl -s --digest -u <user>:<pass> \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"balance","method":"get_balance","params":{"account_index":0}}' \
  http://127.0.0.1:18088/json_rpc

# Get primary address (account 0)
docker exec <container> curl -s --digest -u <user>:<pass> \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"addr","method":"get_address","params":{"account_index":0}}' \
  http://127.0.0.1:18088/json_rpc

# Refresh wallet (rescan)
docker exec <container> curl -s --digest -u <user>:<pass> \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"refresh","method":"refresh"}' \
  http://127.0.0.1:18088/json_rpc

# List transfers (in/out/pending/failed)
docker exec <container> curl -s --digest -u <user>:<pass> \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"txs","method":"get_transfers","params":{"in":true,"out":true,"pending":true,"failed":true}}' \
  http://127.0.0.1:18088/json_rpc
```

Example transfer request (may return “not enough unlocked money” until coinbase rewards unlock; retry after sufficient blocks):

```bash
docker exec <container> curl -s --digest -u <user>:<pass> \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"tx","method":"transfer","params":{"destinations":[{"address":"<recipient-address>","amount":1000000000000}],"account_index":0,"ring_size":12,"priority":0,"get_tx_key":true,"do_not_relay":false}}' \
  http://127.0.0.1:18088/json_rpc
```


#### Daemon RPC (port 28081, no auth)

```bash
# Get block count
docker exec <container> curl -s \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"count","method":"get_block_count"}' \
  http://127.0.0.1:28081/json_rpc

# Get node info
docker exec <container> curl -s \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"info","method":"get_info"}' \
  http://127.0.0.1:28081/json_rpc

# Get peer connections
docker exec <container> curl -s \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"conn","method":"get_connections"}' \
  http://127.0.0.1:28081/json_rpc

# Get block hash at height 123
docker exec <container> curl -s \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"hash","method":"get_block_hash","params":[123]}' \
  http://127.0.0.1:28081/json_rpc
```

#### Logs and troubleshooting

```bash
# Recent logs of a container
docker logs <container_name> | tail -n 120

# Check daemon logs for ERROR/WARNING
docker exec <container_name> grep -i "error" /var/log/monero/<log_dir>/monerod.log | tail
docker exec <container_name> grep -i "warning" /var/log/monero/<log_dir>/monerod.log | tail

# Inspect wallet CLI / RPC logs
docker exec <container_name> tail -n 40 /var/log/monero/<log_dir>/wallet-cli.log
docker exec <container_name> tail -n 40 /var/log/monero/<log_dir>/wallet-rpc.log

# Ensure wallet-rpc process exists (light/RPC nodes)
docker exec <container_name> ps aux | grep monero-wallet-rpc
```

#### Notes on ports

- Full/pruned nodes expose P2P/RPC/ZMQ on incrementing testnet-style ports (P2P ≈ 28080+N, RPC ≈ 28081+N, ZMQ ≈ 28082+N).
- Wallet RPC defaults to `0.0.0.0:18088` inside containers with digest auth (examples use `seed:seed`).
- Light nodes run only `monero-wallet-rpc` (port 18088); they do not start `monerod`.

