import types
from .ContainerBundle import ContainerBundle

SEEDEMU_ETH_EXPLORER_BACKEND_IMAGE = "handsonsecurity/seedemu-ethexplorer-backend:1.0"
SEEDEMU_ETH_EXPLORER_WEB_IMAGE = "handsonsecurity/seedemu-ethexplorer-web:1.0"
CLICKHOUSE_IMAGE = "clickhouse/clickhouse-server:25.11"
POSTGRES_IMAGE = "postgres:15.2-alpine"
REDIS_IMAGE = "redis:7-alpine"
LITTLE_BIGTABLE_IMAGE = "gobitfly/little_bigtable:latest"

SEEDEMU_ETH_EXPLORER_WEB_INTERNAL_PORT = 5000
DOCKER_LOGGOING_SET = {
    "driver": "json-file",
    "options": {"max-size": "200m", "max-file": 1},
}

DEFAULT_NETWORK = {
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
        "ipam": {"config": [{"subnet": "172.20.0.0/24", "gateway": "172.20.0.1"}]},
    },
}

BACKEND_CONFIG_YML = """
justV2: false
# Database credentials
readerDatabase:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
writerDatabase:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
alloyReader:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
alloyWriter:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
bigtable:
  project: explorer
  instance: explorer
  emulator: true
  emulatorPort: $LBT_PORT
  emulatorHost: {LBT_HOST}
rawBigtable:
  project: rawExplorer
  instance: rawExplorer
  emulator: true
  emulatorPort: $RBT_PORT
  emulatorHost: {RBT_HOST}
eth1ErigonEndpoint: 'http://$EL_HOST:$EL_PORT'
eth1GethEndpoint: 'http://$EL_HOST:$EL_PORT'
redisCacheEndpoint: '{REDIS_HOST}:$REDIS_PORT'
redisSessionStoreEndpoint: '{REDIS_HOST}:$REDIS_SESSIONS_PORT'
tieredCacheProvider: 'redis'

clickHouseEnabled: true
validatorTagger:
  enabled: true
  schedulerEnabled: true

# Chain network configuration (example will work for the prysm testnet)
chain:
  name: "mainnet"

  genesisTimestamp: $GENESIS_TIMESTAMP
  genesisValidatorsRoot: $GENESIS_VALIDATORSROOT
  clConfigPath: ./local_deployment/mainnet.chain.yml
  pectraWithdrawalRequestContractAddress: "0x0000000000000000000000000000000000000000"
  pectraConsolidationRequestContractAddress: "0x0000000000000000000000000000000000000000"

clickhouse:
  readerDatabase:
    user: beacon
    password: "pass"
    name: beaconchain
    host: {CLICKHOUSE_HOST}
    port: $CLICKHOUSE_PORT
    ssl: false

  writerDatabase:
    user: beacon
    password: "pass"
    name: beaconchain
    host: {CLICKHOUSE_HOST}
    port: $CLICKHOUSE_PORT
    ssl: false

# Note: It is possible to run either the frontend or the indexer or both at the same time
# Frontend config
frontend:
  sessionSameSiteNone: false
  siteDomain: "localhost:$SERVER_PORT"
  siteName: 'Open Source Ethereum (ETH) Testnet Explorer' # Name of the site, displayed in the title tag
  siteSubtitle: "Showing a local testnet."
  csrfAuthKey: '0123456789abcdef000000000000000000000000000000000000000000000000'
  jwtSigningSecret: "0123456789abcdef000000000000000000000000000000000000000000000000"
  jwtIssuer: "beaconcha.in"
  jwtValidityInMinutes: 30
  server:
    host: "0.0.0.0" # Address to listen on
    port: $SERVER_PORT # Port to listen on
  readerDatabase:
    name: $POSTGRES_DB
    host: {POSTGRES_HOST}
    port: $POSTGRES_PORT
    user: $POSTGRES_USER
    password: $POSTGRES_PASSWORD
  writerDatabase:
    name: $POSTGRES_DB
    host: {POSTGRES_HOST}
    port: $POSTGRES_PORT
    user: $POSTGRES_USER
    password: $POSTGRES_PASSWORD
  sessionSecret: "11111111111111111111111111111111"

# Indexer config
indexer:
  enabled: true # Enable or disable the indexing service
  fullIndexOnStartup: false # Perform a one time full db index on startup
  indexMissingEpochsOnStartup: false # Check for missing epochs and export them after startup
  node:
    host: $CL_HOST
    port: $CL_PORT
    type: lighthouse
"""
BACKEND_START_SH = [
    "#!/bin/sh",
    'DEFAULT_ROUTE="{default_route}"',
    'IFACE=$(ip route get "$DEFAULT_ROUTE" | awk \'{for (i=1;i<=NF;i++) if ($i=="dev") print $(i+1); exit}\')',
    'echo "gateway=$DEFAULT_ROUTE interface=$IFACE"',
    "ip route del default 2>/dev/null || true",
    'ip route add default via "$DEFAULT_ROUTE" dev "$IFACE"',
    "stopit() {",
    '  echo "trapped SIGINT"',
    "  exit 0",
    "}",
    "trap stopit SIGINT",
    'echo "run provision-explorer-config-custom.sh ..."',
    "cd /app/local_deployment",
    "chmod +x provision-explorer-config-custom.sh",
    "./provision-explorer-config-custom.sh",
    "if [ $? -eq 0 ]; then",
    '  echo "SUCCESS: script executed normally"',
    "else",
    '  echo "ERROR: script failed"',
    "  exit 1",
    "fi",
    "cat /tmp/config.yml > /app/local_deployment/config.yml",
    "cd /app",
    'echo "start ..."',
    'echo "run eth1indexer"',
    "bc eth1indexer -config /app/local_deployment/config.yml -concurrency 1 -blocks.tracemode 'geth' &",
    'echo "run rewards-exporter"',
    "bc rewards-exporter -config /app/local_deployment/config.yml &",
    'echo "run statistics"',
    "bc statistics -config /app/local_deployment/config.yml --charts.enabled --graffiti.enabled -validators.enabled -deposits.enabled &",
    'echo "end."',
    "while true; do",
    "  date",
    "  sleep 1",
    "done",
]
FRONTEND_CONFIG_YML = """
justV2: false
# Database credentials
readerDatabase:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
writerDatabase:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
alloyReader:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
alloyWriter:
  name: $POSTGRES_DB
  host: {POSTGRES_HOST}
  port: $POSTGRES_PORT
  user: $POSTGRES_USER
  password: $POSTGRES_PASSWORD
bigtable:
  project: explorer
  instance: explorer
  emulator: true
  emulatorPort: $LBT_PORT
  emulatorHost: {LBT_HOST}
rawBigtable:
  project: rawExplorer
  instance: rawExplorer
  emulator: true
  emulatorPort: $RBT_PORT
  emulatorHost: {RBT_HOST}
eth1ErigonEndpoint: 'http://$EL_HOST:$EL_PORT'
eth1GethEndpoint: 'http://$EL_HOST:$EL_PORT'
redisCacheEndpoint: '{REDIS_HOST}:$REDIS_PORT'
redisSessionStoreEndpoint: '{REDIS_HOST}:$REDIS_SESSIONS_PORT'
tieredCacheProvider: 'redis'

clickHouseEnabled: true
validatorTagger:
  enabled: true
  schedulerEnabled: true

# Chain network configuration (example will work for the prysm testnet)
chain:
  name: "mainnet"

  genesisTimestamp: $GENESIS_TIMESTAMP
  genesisValidatorsRoot: $GENESIS_VALIDATORSROOT
  clConfigPath: ./local-deployment/mainnet.chain.yml
  pectraWithdrawalRequestContractAddress: "0x0000000000000000000000000000000000000000"
  pectraConsolidationRequestContractAddress: "0x0000000000000000000000000000000000000000"

clickhouse:
  readerDatabase:
    user: beacon
    password: "pass"
    name: beaconchain
    host: {CLICKHOUSE_HOST}
    port: $CLICKHOUSE_PORT
    ssl: false

  writerDatabase:
    user: beacon
    password: "pass"
    name: beaconchain
    host: {CLICKHOUSE_HOST}
    port: $CLICKHOUSE_PORT
    ssl: false

# Note: It is possible to run either the frontend or the indexer or both at the same time
# Frontend config
frontend:
  enabled: true
  sessionSameSiteNone: false
  siteDomain: "localhost:$SERVER_PORT"
  siteName: 'Open Source Ethereum (ETH) Testnet Explorer' # Name of the site, displayed in the title tag
  siteSubtitle: "Showing a local testnet."
  csrfAuthKey: '0123456789abcdef000000000000000000000000000000000000000000000000'
  jwtSigningSecret: "0123456789abcdef000000000000000000000000000000000000000000000000"
  jwtIssuer: "beaconcha.in"
  jwtValidityInMinutes: 30
  server:
    host: "0.0.0.0" # Address to listen on
    port: $SERVER_PORT # Port to listen on
  readerDatabase:
    name: $POSTGRES_DB
    host: {POSTGRES_HOST}
    port: $POSTGRES_PORT
    user: $POSTGRES_USER
    password: $POSTGRES_PASSWORD
  writerDatabase:
    name: $POSTGRES_DB
    host: {POSTGRES_HOST}
    port: $POSTGRES_PORT
    user: $POSTGRES_USER
    password: $POSTGRES_PASSWORD
  sessionSecret: "11111111111111111111111111111111"

# Indexer config
indexer:
  enabled: true # Enable or disable the indexing service
  fullIndexOnStartup: false # Perform a one time full db index on startup
  indexMissingEpochsOnStartup: false # Check for missing epochs and export them after startup
  node:
    host: $CL_HOST
    port: $CL_PORT
    type: lighthouse
"""
FRONTEND_START_SH = [
    "#!/bin/bash",
    'DEFAULT_ROUTE="{default_route}"',
    'IFACE=$(ip route get "$DEFAULT_ROUTE" | awk \'{for (i=1;i<=NF;i++) if ($i=="dev") print $(i+1); exit}\')',
    'echo "gateway=$DEFAULT_ROUTE interface=$IFACE"',
    "ip route del default 2>/dev/null || true",
    'ip route add default via "$DEFAULT_ROUTE" dev "$IFACE"',
    "stopit() {",
    '  echo "trapped SIGINT"',
    "  exit 0",
    "}",
    "trap stopit SIGINT",
    'echo "run provision-explorer-config-custom.sh ..."',
    "cd /app/local-deployment",
    "chmod +x provision-explorer-config-custom.sh",
    "./provision-explorer-config-custom.sh",
    "if [ $? -eq 0 ]; then",
    '  echo "SUCCESS: script executed normally"',
    "else",
    '  echo "ERROR: script failed"',
    "  exit 1",
    "fi",
    "cat /tmp/config.yml > /app/local_deployment/config.yml",
    "cd /app",
    'echo "start ..."',
    'echo "run explorer"',
    "/app/explorer -config /app/local-deployment/config.yml &",
    'echo "run validator-tagger"',
    "/app/validator-tagger -config /app/local-deployment/config.yml -schedule true &",
    'echo "run frontend-data-updater"',
    "/app/frontend-data-updater -config /app/local-deployment/config.yml &",
    'echo "end."',
    "while true; do",
    "  date",
    "  sleep 1",
    "done",
]


class EthExplorer(ContainerBundle):
    def __init__(self, emulator, suffix="eth.explorer"):
        super().__init__(emulator=emulator, suffix=suffix)
        self._default_network = DEFAULT_NETWORK
        service_names = [
            "clickhouse",
            "postgres",
            "redis",
            "littlebigtable",
            "rawbigtable",
            "seedemu-ethexplorer-backend",
            "seedemu-ethexplorer-web",
        ]
        for service_name in service_names:
            self._createContainer(service_name, suffix)
        self.__beacon_host = self.__geth_host = ""
        self._emu_internal_network = self.getEmuHostNetworkInfo()

    def configure(self) -> None:
        self._required_port_number = 1
        super().configure()

        eth = self._emulator.getLayer("EthereumService")
        blockchain = eth.getBlockchainByName(eth.getBlockchainNames()[0])
        if not self.__beacon_host:
            self.__beacon_host = blockchain.getBeaconBootNodeIP()[0]
        if not self.__geth_host:
            self.__geth_host = blockchain.getGethBootNodeIP()[0]

        default_network_name = self._default_network["name"]
        ip_addresses = self._default_network["ip_addresses"]
        for index, container in enumerate(self._containers.values()):
            container.joinExternalNetwork(
                default_network_name, container.getHostname(), ip_addresses[index]
            )

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
                "depends_on": [postgres.getName()],
            }
        )

        clickhouse_ip = clickhouse.service["networks"][default_network_name]["ipv4_address"]
        postgres_ip = postgres.service["networks"][default_network_name]["ipv4_address"]
        redis_ip = redis.service["networks"][default_network_name]["ipv4_address"]
        littlebigtable_ip = littlebigtable.service["networks"][default_network_name][
            "ipv4_address"
        ]
        rawbigtable_ip = rawbigtable.service["networks"][default_network_name]["ipv4_address"]

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
                    "redis": {"condition": "service_healthy"},
                    "littlebigtable": {"condition": "service_started"},
                    "rawbigtable": {"condition": "service_started"},
                },
                "environment": {"CL_HOST": self.__beacon_host, "EL_HOST": self.__geth_host},
                "build": f"./{seedemu_ethexplorer_backend.getHostname()}",
                "logging": DOCKER_LOGGOING_SET,
            }
        )
        seedemu_ethexplorer_backend.joinInternalNetwork(*self._emu_internal_network)
        BACKEND_START_SH[1] = BACKEND_START_SH[1].format(
            default_route=self._emu_internal_network[3]
        )
        seedemu_ethexplorer_backend._start_commands = BACKEND_START_SH
        seedemu_ethexplorer_backend.setFile(
            "/tmp/config.yml",
            BACKEND_CONFIG_YML.format(
                POSTGRES_HOST=postgres_ip,
                CLICKHOUSE_HOST=clickhouse_ip,
                LBT_HOST=littlebigtable_ip,
                RBT_HOST=rawbigtable_ip,
                REDIS_HOST=redis_ip,
            ),
        )

        seedemu_ethexplorer_web = self._containers["seedemu-ethexplorer-web"]
        seedemu_ethexplorer_web.setContentAttribute(
            {
                "image": SEEDEMU_ETH_EXPLORER_WEB_IMAGE,
                "privileged": True,
                "pid": "host",
                "cap_add": ["ALL"],
                "depends_on": {
                    "clickhouse": {"condition": "service_healthy"},
                    "postgres": {"condition": "service_healthy"},
                    "redis": {"condition": "service_healthy"},
                    "littlebigtable": {"condition": "service_started"},
                    "rawbigtable": {"condition": "service_started"},
                    seedemu_ethexplorer_backend.getName(): {"condition": "service_healthy"},
                },
                "environment": {"CL_HOST": self.__beacon_host, "EL_HOST": self.__geth_host},
                "ports": [f"{self._ports.pop()}:{SEEDEMU_ETH_EXPLORER_WEB_INTERNAL_PORT}"],
                "build": f"./{seedemu_ethexplorer_web.getHostname()}",
                "logging": DOCKER_LOGGOING_SET,
            }
        )
        seedemu_ethexplorer_web.joinInternalNetwork(*self._emu_internal_network)
        FRONTEND_START_SH[1] = FRONTEND_START_SH[1].format(
            default_route=self._emu_internal_network[3]
        )
        seedemu_ethexplorer_web._start_commands = FRONTEND_START_SH
        seedemu_ethexplorer_web.setFile(
            "/tmp/config.yml",
            FRONTEND_CONFIG_YML.format(
                POSTGRES_HOST=postgres_ip,
                CLICKHOUSE_HOST=clickhouse_ip,
                LBT_HOST=littlebigtable_ip,
                RBT_HOST=rawbigtable_ip,
                REDIS_HOST=redis_ip,
            ),
        )

    def getBeaconHost(self) -> str:
        return self.__beacon_host

    def getGethHost(self) -> str:
        return self.__geth_host

    def setBeaconHost(self, beacon_host) -> None:
        self.__beacon_host = beacon_host

    def setGethHost(self, geth_host) -> None:
        self.__geth_host = geth_host
