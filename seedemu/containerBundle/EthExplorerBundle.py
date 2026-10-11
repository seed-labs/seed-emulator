from .ContainerBundle import ContainerBundle
from seedemu.core.enums import NetworkType

SEEDEMU_ETH_EXPLORER_BACKEND_IMAGE = "handsonsecurity/seedemu-ethexplorer-backend:1.0"
SEEDEMU_ETH_EXPLORER_WEB_IMAGE = "handsonsecurity/seedemu-ethexplorer-web:1.0"
CLICKHOUSE_IMAGE = "clickhouse/clickhouse-server:25.11"
POSTGRES_IMAGE = "postgres:15.2-alpine"
REDIS_IMAGE = "redis:7-alpine"
LITTLE_BIGTABLE_IMAGE = "gobitfly/little_bigtable:latest"

SEEDEMU_ETH_EXPLORER_WEB_INTERNAL_PORT = 5000


class EthExplorerBundle(ContainerBundle):
    def __init__(self, emulator, suffix="eth.explorer"):
        super().__init__(emulator=emulator, suffix=suffix)
        service_names = [
            "clickhouse",
            "postgres",
            "alloy",
            "redis",
            "littlebigtable",
            "rawbigtable",
            "seedemu-ethexplorer-backend",
            "seedemu-ethexplorer-web",
        ]
        for service_name in service_names:
            self._createContainer(service_name, suffix)

    def configure(self) -> None:
        self._required_port_number = 1
        super().configure()
        if self._default_network:
            for container in self._containers.values():
                container.joinExternalNetwork(self._default_network[0])

        clickhouse = self._containers["clickhouse"]
        clickhouse.setContentAttribute(
            {
                "image": CLICKHOUSE_IMAGE,
                "environment": {
                    "CLICKHOUSE_DB": "beaconchain",
                    "CLICKHOUSE_USER": "beacon",
                    "CLICKHOUSE_PASSWORD": "pass",
                },
                "healthcheck": {
                    "test": ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                },
            }
        )

        postgres = self._containers["postgres"]
        postgres.setContentAttribute(
            {
                "image": POSTGRES_IMAGE,
                "environment": {
                    "POSTGRES_DB": "db",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "pass",
                },
                "healthcheck": {
                    "test": ["CMD-SHELL", "pg_isready -U postgres"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 5,
                },
            }
        )

        alloy = self._containers["alloy"]
        alloy.setContentAttribute(
            {
                "image": POSTGRES_IMAGE,
                "environment": {
                    "POSTGRES_DB": "db",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "pass",
                },
                "healthcheck": {
                    "test": ["CMD-SHELL", "pg_isready -U postgres"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 5,
                },
            }
        )

        redis = self._containers["redis"]
        redis.setContentAttribute(
            {
                "image": REDIS_IMAGE,
                "command": "redis-server --appendonly yes",
                "healthcheck": {
                    "test": ["CMD", "redis-cli", "ping"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                },
            }
        )

        littlebigtable = self._containers["littlebigtable"]
        littlebigtable.setContentAttribute(
            {
                "image": LITTLE_BIGTABLE_IMAGE,
                "depends_on": [postgres.getName()],
            }
        )

        rawbigtable = self._containers["rawbigtable"]
        rawbigtable.setContentAttribute(
            {
                "image": LITTLE_BIGTABLE_IMAGE,
                "depends_on": [alloy.getName()],
            }
        )

        cl_host, beaconNetwork, el_host, gEthNetwork = self.getBeaconAndGethEndpoints()
        
        seedemu_ethexplorer_backend = self._containers["seedemu-ethexplorer-backend"]
        seedemu_ethexplorer_backend.setContentAttribute(
            {
                "image": SEEDEMU_ETH_EXPLORER_BACKEND_IMAGE,
                "privileged": True,
                "pid": "host",
                "cap_add": ["ALL"],
                "healthcheck": {
                    "test": [
                        "CMD-SHELL",
                        """PGPASSWORD=pass psql -h postgres -U postgres -d db -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='blocks';" | grep -q 1""",
                    ],
                    "interval": "5s",
                    "timeout": "3s",
                    "retries": 60,
                    "start_period": "10s",
                },
                "depends_on": {
                    "clickhouse": {"condition": "service_healthy"},
                    "postgres": {"condition": "service_healthy"},
                    "alloy": {"condition": "service_healthy"},
                    "redis": {"condition": "service_healthy"},
                    "littlebigtable": {"condition": "service_healthy"},
                    "rawbigtable": {"condition": "service_healthy"},
                },
                "environment": {"EL_HOST": el_host, "CL_HOST": cl_host},
            }
        )
        seedemu_ethexplorer_backend.joinInternalNetwork(network=beaconNetwork)
        seedemu_ethexplorer_backend.joinInternalNetwork(network=gEthNetwork)

        seedemu_ethexplorer_web = self._containers["seedemu-ethexplorer-web"]
        seedemu_ethexplorer_web.setContentAttribute(
            {
                "image": SEEDEMU_ETH_EXPLORER_WEB_IMAGE,
                "depends_on": [alloy.getName()],
                "privileged": True,
                "pid": "host",
                "cap_add": ["ALL"],
                "depends_on": {
                    "clickhouse": {"condition": "service_healthy"},
                    "postgres": {"condition": "service_healthy"},
                    "alloy": {"condition": "service_healthy"},
                    "redis": {"condition": "service_healthy"},
                    "littlebigtable": {"condition": "service_healthy"},
                    "rawbigtable": {"condition": "service_healthy"},
                    seedemu_ethexplorer_backend.getName(): {"condition": "service_healthy"},
                },
                "environment": {"EL_HOST": el_host, "CL_HOST": cl_host},
                "ports": [f"{self._ports.pop()}:{SEEDEMU_ETH_EXPLORER_WEB_INTERNAL_PORT}"],
            }
        )
        seedemu_ethexplorer_web.joinInternalNetwork(network=beaconNetwork)
        seedemu_ethexplorer_web.joinInternalNetwork(network=gEthNetwork)

    def getBeaconAndGethEndpoints(self) -> tuple[str, str, str, str]:
        registry = self._emulator.getRegistry()
        beacon_host = gEth_host = beaconNetwork = gEthNetwork = ""

        for (_, type, _), obj in registry.getAll().items():
            if type != "hnode":
                continue
            if beacon_host and gEth_host:
                break

            interfaces = obj.getInterfaces()
            if not interfaces:
                continue
            interface = interfaces[0]
            ip = str(interface.getAddress())
            net = interface.getNet()
            scope, _, _ = net.getRegistryInfo()
            # Match the network names emitted by the Docker compiler.
            network = net.getName() if net.getType() == NetworkType.Bridge else f"net_{scope}_{net.getName()}"
            display_name = obj.getDisplayName() or obj.getName()
            if "-Beacon-" in display_name and beacon_host == "":
                beacon_host = ip
                beaconNetwork = network
            elif "-Geth-" in display_name and gEth_host == "":
                gEth_host = ip
                gEthNetwork = network

        return (beacon_host, beaconNetwork, gEth_host, gEthNetwork)
