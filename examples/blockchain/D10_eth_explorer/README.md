# D10 Eth Explorer Example

This example builds an Ethereum PoS private network and attaches the explorer implemented by [`EthExplorer`](../../../seedemu/containerBundle/EthExplorer.py). The explorer indexes execution-layer and consensus-layer data and provides a Web UI for blocks, transactions, epochs, slots, and validators.

The D10 entry point, [`ethereum_pos.py`](ethereum_pos.py), contains the complete example. It creates the Geth/Beacon node pairs, validator clients, Beacon setup node, Internet topology, and both container bundles. D01 is not required to run this example.

## Run this example

From the project root:

```bash
cd examples/blockchain/D10_eth_explorer
python ethereum_pos.py --beacon-nodes 3 --validators-per-beacon 3 --platform amd
cd output
docker compose up --build
```

The legacy invocation `python ethereum_pos.py 3 amd` is also supported. `--platform arm` selects ARM64 output; the explorer images must also support the target architecture. `--output` changes the generated directory. `--dumpfile` saves the emulator and returns before rendering or compiling bundles.

The example supplies `list(range(8090, 8099))` to `EthExplorer`, which takes the last port, `8098`. Open the explorer at **http://127.0.0.1:8098**. The container listens on port `5000` internally. Startup and initial indexing can take time.

## Attach EthExplorer to an existing emulator

The example creates the emulator locally and then configures the bundle:

```python
from seedemu import *

emu = build_emulator(total_beacon_nodes=3, vc_per_beacon=3)
explorer = EthExplorer(emu, ".eth.explorer.seed")

explorer.setDefaultExternalNetwork(
    name="ethExplorer_network",
    prefix="172.20.0.0/24",
    ip_addresses=[
        "172.20.0.10", "172.20.0.11", "172.20.0.12",
        "172.20.0.13", "172.20.0.14", "172.20.0.15",
        "172.20.0.16",
    ],
    default_router="172.20.0.1",
)
explorer.setPorts([8090])

docker = Docker(platform=Platform.AMD64)
docker.addContainerBundle(explorer)
emu.compile(docker, "./output", override=True)
```

Then run `docker compose up --build` inside `output` and open `http://127.0.0.1:8090`.

`Docker.addContainerBundle()` registers the bundle. During compilation, the compiler calls `configure()` and then `install()` to produce the Compose services, network definitions, build directories, startup scripts, and configuration files. Application code normally does not call these lifecycle methods directly. Configure and compile a fresh bundle for each build: configuration consumes ports and modifies startup scripts.

The current integration uses `addContainerBundle()`. The `--ether-view` and `--no-ether-view` switches remain accepted for compatibility with existing scripts; this example always registers `EthExplorer` in its `run()` function.

## Constructor and prerequisites

```python
explorer = EthExplorer(emulator=emu, suffix=".eth.explorer.seed")
```

| Argument | Meaning |
| --- | --- |
| `emulator` | The emulator containing the Ethereum service and reachable emulated hosts. |
| `suffix` | Appended to bundle hostnames and generated build directory names. The constructor default is `"eth.explorer"`; include a leading dot explicitly if desired. |

The emulator must contain an `EthereumService` with at least one blockchain. Automatic node selection requires that blockchain to expose Beacon and Geth bootnode IPs. Geth HTTP RPC and the Beacon API must be enabled and reachable from the explorer containers.

The constructor records the requirement for two internal addresses; it does
not scan interfaces or allocate them. `configure()` later selects a rendered
host network unless a manual internal network is already set. The backend
and Web containers join that network and use its gateway to reach chain nodes.
Setting RPC host addresses alone does not create network connectivity.

The suffix applies to Compose service keys, `container_name` values, hostnames,
and build directories. D10 uses `.eth.explorer.seed`, producing names such as
`postgres.eth.explorer.seed`. Multiple explorer bundles also need distinct
external networks, subnets, and host ports.

For the differences between `EthExplorer` and `ContainerBundle`, detailed
`__init__()` and `configure()` behavior, the four Beacon/Geth host APIs, and
the backend/Web start-script changes and their reasons, see the
[EthExplorer design document](../../../docs/designs/eth_explorer.md).

## Configure the bundle network

EthExplorer already provides a default bridge network, so `setDefaultExternalNetwork()` is optional. The current default is:

```python
network = {
    "name": "ethExplorer_network",
    "prefix": "172.20.0.0/24",
    "ip_addresses": [
        "172.20.0.10",
        "172.20.0.11",
        "172.20.0.12",
        "172.20.0.13",
        "172.20.0.14",
        "172.20.0.15",
        "172.20.0.16",
    ],
    "default_router": "172.20.0.1",
}

# Optional: override the default before compilation.
explorer.setDefaultExternalNetwork(**network)
```

The dictionary is expanded into keyword arguments. The equivalent call is `explorer.setDefaultExternalNetwork(name=..., prefix=..., ip_addresses=..., default_router=...)`.

| Field | Meaning |
| --- | --- |
| `name` | Compose network key used by all seven bundle services. |
| `prefix` | IPv4 subnet in CIDR notation. It is used as the Docker network subnet. |
| `ip_addresses` | Static IPv4 addresses assigned in container creation order. |
| `default_router` | IPv4 gateway address for the Docker network. |

`ip_addresses` must be nonempty and contain at least as many entries as
`explorer.getContainers()`. The bundle contains **seven containers**. Invalid
subnets, gateways, insufficient addresses, duplicate addresses, addresses
outside the subnet, or addresses equal to the gateway, network, or broadcast
address raise `ValueError`. Extra addresses are unused. Avoid overlap with
the emulated topology and other Docker networks.

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

All services join the bundle bridge network. The backend and Web service additionally join the selected emulated host network. The bundle derives the Compose network configuration from `prefix` and `default_router`.

During `configure()`, the bundle reserves two free internal addresses on one
rendered host network, starting at network-address offset 10. The backend uses
`ip_addresses[0]` and the Web service uses `ip_addresses[1]`. Allocation skips
occupied addresses, the gateway, and reservations shared with other bundles.
To choose the network manually, call
`explorer.setDefaultInternalNetwork(name, ip_addresses, default_route)` with
two free addresses before compilation. This setter does not reserve them.

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

`BACKEND_START_SH` and `FRONTEND_START_SH` are defined in `EthExplorer.py`.
During `configure()`, Python `.format()` replaces these five placeholders in
their `sed` commands with the corresponding service's static IP:

| Placeholder | Service |
| --- | --- |
| `{CLICKHOUSE_HOST}` | `clickhouse` |
| `{POSTGRES_HOST}` | `postgres` |
| `{REDIS_HOST}` | `redis` |
| `{LBT_HOST}` | `littlebigtable` |
| `{RBT_HOST}` | `rawbigtable` |

Runtime configuration is generated by the image's provisioning script. Python
formats only the host-replacement commands; it does not stage configuration
templates at `/tmp/config.yml`.

The backend uses `/app/local_deployment`; the Web service uses `/app/local-deployment`. Each startup script configures its route and runs `provision-explorer-config-custom.sh`, then replaces the database, cache, Bigtable, and ClickHouse host entries in the generated runtime `config.yml` with the static IPs assigned by `EthExplorer`. The backend starts `eth1indexer`, `rewards-exporter`, and `statistics`; the Web container starts `explorer`, `validator-tagger`, and `frontend-data-updater`.

Compose health checks gate startup on ClickHouse, Postgres, and Redis. The Bigtable services must be started. The Web service also waits for the backend health check, which checks for the Postgres `blocks` table; this does not guarantee that chain indexing has caught up.

The explorer image sources are in [`docker_images/seedemu-ethexplorer`](../../../docker_images/seedemu-ethexplorer). The bundle references `handsonsecurity/seedemu-ethexplorer-backend:1.0` and `handsonsecurity/seedemu-ethexplorer-web:1.0`, and generates build contexts that add its files and startup scripts.

## Inspect and troubleshoot

From the generated output directory:

```bash
docker compose config
docker compose ps
docker compose logs -f seedemu-ethexplorer-backend.eth.explorer.seed seedemu-ethexplorer-web.eth.explorer.seed
```

| Symptom | What to check |
| --- | --- |
| Address validation error during `setDefaultExternalNetwork()` | Supply at least seven unique usable addresses in the subnet, excluding the gateway. |
| Missing port error during compilation | Call `setPorts([host_port])` before compiling. |
| Missing blockchain or bootnode lookup failure | Render the emulator, configure the Ethereum service and bootnodes, or set explicit node hosts. |
| Network or route setup failure | Check the selected emulated host interface, its gateway, subnet overlap, and reachability of the chain nodes. |
| Cannot open the Web UI | Check the last supplied host port, port conflicts, Compose status, and backend health. D10 currently uses `8098`, not `5000`. |
| UI has no chain data | Wait for chain genesis and indexing, then inspect Geth RPC, Beacon API, database health, and explorer logs. |
| Invalid YAML values or host connection failures | Inspect the generated runtime configuration and verify the assigned bundle-network IPs. |

To inspect the effective runtime configuration:

```bash
docker compose exec seedemu-ethexplorer-backend.eth.explorer.seed cat /app/local_deployment/config.yml
docker compose exec seedemu-ethexplorer-web.eth.explorer.seed cat /app/local-deployment/config.yml
```

InternetMap complements the explorer by showing network topology and connectivity; EthExplorer shows chain state and indexing results. Register and configure each bundle separately, with nonoverlapping networks and host ports.
