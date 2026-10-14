# D10 Eth Explorer Example

This example builds an Ethereum PoS private network and attaches the explorer implemented by [`EthExplorer`](../../../seedemu/containerBundle/EthExplorer.py). The explorer indexes execution-layer and consensus-layer data and provides a Web UI for blocks, transactions, epochs, slots, and validators.

The D10 entry point, [`ethereum_pos.py`](ethereum_pos.py), delegates network construction and bundle registration to [D01](../D01_ethereum_pos/ethereum_pos.py). D01 creates Geth/Beacon node pairs, validator clients, a Beacon setup node, and an Internet topology. It registers both `InternetMap` and `EthExplorer` with the Docker compiler.

## Run this example

From the project root:

```bash
cd examples/blockchain/D10_eth_explorer
python ethereum_pos.py --beacon-nodes 3 --validators-per-beacon 3 --platform amd
cd output
docker compose up --build
```

The legacy invocation `python ethereum_pos.py 3 amd` is also supported. `--platform arm` selects ARM64 output; the explorer images must also support the target architecture. `--output` changes the generated directory. `--dumpfile` saves the emulator and returns before rendering or compiling bundles.

With the current D01 port configuration, open the explorer at **http://127.0.0.1:8098**. D01 supplies `list(range(8090, 8099))`, and EthExplorer takes the last port, `8098`. The container listens on port `5000` internally. Startup and initial indexing can take time.

## Attach EthExplorer to an existing emulator

Import the bundle from `seedemu.containerBundle`. Create it after rendering the emulator, register it with the Docker compiler, and compile:

```python
from seedemu import Platform
from seedemu.compiler import Docker
from seedemu.containerBundle import EthExplorer

# emu is an existing emulator with a configured EthereumService PoS chain.
# Render first so host interfaces and Ethereum bootnode IPs are available.
emu.render()

docker = Docker(platform=Platform.AMD64)
explorer = EthExplorer(emu, ".eth.explorer.seed")
explorer.setPorts([8090])
docker.addContainerBundle(explorer)
emu.compile(docker, "./output", override=True)
```

Then run `docker compose up --build` inside `output` and open `http://127.0.0.1:8090`.

`Docker.addContainerBundle()` registers the bundle. During compilation, the compiler calls `configure()` and then `install()` to produce the Compose services, network definitions, build directories, startup scripts, and configuration files. Application code normally does not call these lifecycle methods directly. Configure and compile a fresh bundle for each build: configuration consumes ports and modifies startup scripts.

The current integration uses `addContainerBundle()`. The older `Docker(etherViewEnabled=True, etherViewPort=...)` examples do not describe this bundle API.

## Constructor and prerequisites

```python
explorer = EthExplorer(emulator=emu, suffix=".eth.explorer.seed")
```

| Argument | Meaning |
| --- | --- |
| `emulator` | The emulator containing the Ethereum service and reachable emulated hosts. |
| `suffix` | Appended to bundle hostnames and generated build directory names. The constructor default is `"eth.explorer"`; include a leading dot explicitly if desired. |

The emulator must contain an `EthereumService` with at least one blockchain. Automatic node selection requires that blockchain to expose Beacon and Geth bootnode IPs. Geth HTTP RPC and the Beacon API must be enabled and reachable from the explorer containers.

The constructor also finds the first registered host interface with an IP address and records its network and default router. The backend and Web containers later join this emulated network and route through that router to reach the chain nodes. Provide a rendered topology with a usable host interface and gateway; setting RPC host addresses alone does not create network connectivity.

The suffix changes generated hostnames/build directories. Compose service keys and `container_name` values remain fixed names such as `postgres` and `seedemu-ethexplorer-web`; a different suffix alone does not isolate multiple explorer bundles in one Compose project.

## Configure the bundle network

EthExplorer already provides a default bridge network, so `setDefaultNetwork()` is optional. The current default is:

```python
network = {
    "name": "ethExplorer_network",
    "prefix": ".eth",
    "ip_addresses": [
        "172.20.0.10",
        "172.20.0.11",
        "172.20.0.12",
        "172.20.0.13",
        "172.20.0.14",
        "172.20.0.15",
        "172.20.0.16",
    ],
    "network_config": {
        "driver": "bridge",
        "ipam": {
            "config": [{"subnet": "172.20.0.0/24", "gateway": "172.20.0.1"}]
        },
    },
}

# Optional: override the default before compilation.
explorer.setDefaultNetwork(**network)
```

The dictionary is expanded into keyword arguments. The equivalent call is `explorer.setDefaultNetwork(name=..., prefix=..., ip_addresses=..., network_config=...)`.

| Field | Meaning |
| --- | --- |
| `name` | Compose network key used by all seven bundle services. |
| `prefix` | Stored network metadata; the current EthExplorer implementation does not use it to generate hostnames or allocate addresses. It is separate from the constructor's `suffix`. |
| `ip_addresses` | Static IPv4 addresses assigned in container creation order. |
| `network_config` | Compose network configuration, including bridge driver, subnet, and gateway. Pass a dictionary; the setter calls `.copy()` on it. |

`ip_addresses` must be nonempty and contain at least as many entries as `explorer.getContainers()`. The current bundle contains **seven containers**, so fewer than seven addresses trigger an assertion in `setDefaultNetwork()`. Extra addresses are unused. Supply unique addresses within the configured subnet, exclude the gateway, and avoid overlap with the emulated topology or other Docker networks. The assertions check presence and count; they do not validate subnet membership or uniqueness.

Default address assignment:

| Order | Service | Default IP | Role |
| --- | --- | --- | --- |
| 1 | `clickhouse` | `172.20.0.10` | Analytical chain storage |
| 2 | `postgres` | `172.20.0.11` | Relational explorer data |
| 3 | `redis` | `172.20.0.12` | Cache and session storage |
| 4 | `littlebigtable` | `172.20.0.13` | Bigtable emulator |
| 5 | `rawbigtable` | `172.20.0.14` | Raw-data Bigtable emulator |
| 6 | `seedemu-ethexplorer-backend` | `172.20.0.15` | Indexing, rewards, and statistics |
| 7 | `seedemu-ethexplorer-web` | `172.20.0.16` | Explorer UI and frontend update tasks |

All services join the bundle bridge network. The backend and Web service additionally join the selected emulated host network. When serializing Compose, the bundle uses `network_config` for its network and avoids redeclaring emulator-owned networks.

## Select Beacon and Geth nodes

By default, `configure()` selects the first blockchain returned by `EthereumService.getBlockchainNames()`, then uses:

```python
blockchain.getBeaconBootNodeIP()[0]  # CL_HOST
blockchain.getGethBootNodeIP()[0]    # EL_HOST
```

Selection uses the Ethereum service API, rather than matching container display names. Override either address before compilation:

```python
explorer.setBeaconHost("10.150.0.71")  # Replace with a reachable Beacon node IP.
explorer.setGethHost("10.150.0.72")    # Replace with a reachable Geth node IP.
```

These setters accept host addresses, not complete URLs or `host:port` strings. The YAML templates build the execution-layer URL as `http://$EL_HOST:$EL_PORT`; API ports come from the image's runtime configuration. Both containers receive `CL_HOST` and `EL_HOST` environment variables.

For an emulator with multiple blockchains, set both hosts to nodes on the intended chain. Even with both overrides, the current implementation still looks up the first blockchain during configuration, so an Ethereum service and at least one blockchain remain required.

`getBeaconHost()` and `getGethHost()` return the selected values. They are initially empty unless explicitly set; automatically selected values are populated during compilation.

## Set the Web port

```python
explorer.setPorts([8090])  # Host 8090 -> container 5000.
```

At least one port is required; otherwise compilation raises `ValueError`. The setter copies the supplied list. The Web service consumes its last element using `.pop()`:

```python
explorer.setPorts(list(range(8090, 8099)))  # Publishes host port 8098.
```

Only one port is used by EthExplorer. Additional ports in the list do not publish additional explorer endpoints. Use a single-element list when you want an explicit URL. This port setting is separate from `InternetMap.setPorts()`.

## Configuration templates and startup

`BACKEND_CONFIG_YML` and `FRONTEND_CONFIG_YML` are defined in `EthExplorer.py`. During `configure()`, Python `.format()` replaces these five placeholders with the corresponding service's static IP:

| Placeholder | Service |
| --- | --- |
| `{CLICKHOUSE_HOST}` | `clickhouse` |
| `{POSTGRES_HOST}` | `postgres` |
| `{REDIS_HOST}` | `redis` |
| `{LBT_HOST}` | `littlebigtable` |
| `{RBT_HOST}` | `rawbigtable` |

Other placeholders, such as `$EL_HOST`, `$CL_HOST`, `$POSTGRES_DB`, `$GENESIS_TIMESTAMP`, and `$SERVER_PORT`, remain in shell-style form after Python formatting. The formatted templates are written into each container at `/tmp/config.yml`.

The backend uses `/app/local_deployment`; the Web service uses `/app/local-deployment`. Each startup script configures its route and runs `provision-explorer-config-custom.sh`, then copies `/tmp/config.yml` over the runtime `config.yml` in its deployment directory. The backend starts `eth1indexer`, `rewards-exporter`, and `statistics`; the Web container starts `explorer`, `validator-tagger`, and `frontend-data-updater`.

**Current implementation detail:** the copy of `/tmp/config.yml` is a plain `cat`, with no explicit shell substitution at that step. Therefore, the remaining `$...` placeholders are preserved in the copied file. If startup reports invalid configuration values, inspect the generated file and the image's configuration-loading behavior rather than assuming that Python formatting or the copy expanded those variables.

Compose health checks gate startup on ClickHouse, Postgres, and Redis. The Bigtable services must be started. The Web service also waits for the backend health check, which checks for the Postgres `blocks` table; this does not guarantee that chain indexing has caught up.

The explorer image sources are in [`docker_images/seedemu-ethexplorer`](../../../docker_images/seedemu-ethexplorer). The bundle references `handsonsecurity/seedemu-ethexplorer-backend:1.0` and `handsonsecurity/seedemu-ethexplorer-web:1.0`, and generates build contexts that add its files and startup scripts.

## Inspect and troubleshoot

From the generated output directory:

```bash
docker compose config
docker compose ps
docker compose logs -f seedemu-ethexplorer-backend seedemu-ethexplorer-web
```

| Symptom | What to check |
| --- | --- |
| IP assertion during `setDefaultNetwork()` | Supply a nonempty list with at least seven IP addresses. |
| Missing port error during compilation | Call `setPorts([host_port])` before compiling. |
| Missing blockchain or bootnode lookup failure | Render the emulator, configure the Ethereum service and bootnodes, or set explicit node hosts. |
| Network or route setup failure | Check the selected emulated host interface, its gateway, subnet overlap, and reachability of the chain nodes. |
| Cannot open the Web UI | Check the last supplied host port, port conflicts, Compose status, and backend health. D10 currently uses `8098`, not `5000`. |
| UI has no chain data | Wait for chain genesis and indexing, then inspect Geth RPC, Beacon API, database health, and explorer logs. |
| Invalid YAML values or literal `$...` in configuration | Inspect `/tmp/config.yml` and the copied runtime config; confirm how the image resolves the remaining placeholders. |

To inspect the effective runtime configuration:

```bash
docker compose exec seedemu-ethexplorer-backend cat /app/local_deployment/config.yml
docker compose exec seedemu-ethexplorer-web cat /app/local-deployment/config.yml
```

InternetMap complements the explorer by showing network topology and connectivity; EthExplorer shows chain state and indexing results. Register and configure each bundle separately, with nonoverlapping networks and host ports.
