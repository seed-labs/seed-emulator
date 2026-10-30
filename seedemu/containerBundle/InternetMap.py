from .ContainerBundle import ContainerBundle

SEEDEMU_EMULATOR_SERVICE_IMAGE = "handsonsecurity/seedemu-emulator-service:1.0"
SEEDEMU_INTERNET_MAP_TOPLOGY_IMAGE = "handsonsecurity/seedemu-internet-toplogy:1.0"
SEEDEMU_INTERNET_MAP_GEOGRAPHIC_IMAGE = "handsonsecurity/seedemu-internet-map-geographic:1.0"
SEEDEMU_TRAFFIC_OBSERVER_SERVICE_IMAGE = "handsonsecurity/seedemu-traffic-observer-service:1.0"

DEFAULT_EXTERNAL_NETWORK = {
    "name": "internetMap_network",
    "prefix": "172.30.0.0/24",
    "ip_addresses": [f"172.30.0.{i}" for i in range(10, 14)],
    "default_router": "172.30.0.1",
    "type": "bridge",
    "network_config": {
        "driver": "bridge",
        "ipam": {
            "config": [
                {
                    "subnet": "172.30.0.0/24",
                    "gateway": "172.30.0.1",
                }
            ]
        },
    },
}

NGINX_CONF_PATH = "/etc/nginx/conf.d/default.conf"
SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT = 7071
START_SCRIPT_NAME = "/entrypoint.sh"
SEEDEMU_INTERNET_MAP_TOPLOGY_NGINX_CONF = """
upstream seedemu_emulator_service_backend {{
    server {}:{};
}}

server {{
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 100m;

    location ^~ /api/v1 {{
        proxy_pass http://seedemu_emulator_service_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }}

    location ^~ /emulator/ {{
        proxy_pass http://seedemu_emulator_service_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""
SEEDEMU_INTERNET_MAP_GEOGRAPHIC_NGINX_CONF = """
upstream seedemu_emulator_service_backend {{
    server {}:{};
}}

upstream seedemu_traffic_observer_service_backend {{
    server host.docker.internal:{};
}}

server {{
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 100m;

    location ^~ /api/v1 {{
        proxy_pass http://seedemu_emulator_service_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }}

    location ^~ /emulator/ {{
        proxy_pass http://seedemu_emulator_service_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }}

    location ^~ /traffic-observer/ {{
        proxy_pass http://seedemu_traffic_observer_service_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""


class InternetMap(ContainerBundle):
    """!
    @brief Bundle for topology, geographic map, and traffic views."""

    def __init__(self, emulator, suffix="map.seed"):
        """!
        @brief Create an Internet Map bundle.

        @param emulator emulator whose topology will be visualized.
        @param suffix suffix appended to generated container hostnames.
        """
        super().__init__(emulator=emulator, suffix=suffix)
        self._default_external_network = DEFAULT_EXTERNAL_NETWORK
        service_names = [
            "seedemu_emulator_service_backend",
            "seedemu_internet_map_toplogy",
            "seedemu_internet_map_geographic",
            "seedemu_traffic_observer_service_backend",
        ]
        for service_name in service_names:
            self._createContainer(service_name, suffix)
        self._required_port_number = 3
        self._required_emu_network_address_number = 1
        self._enableInternalNetwork = False

    def enableInternalNetwork(self):
        """!
        @brief Attach the API backend to the emulator network.

        @returns this bundle for fluent configuration.
        """
        self._enableInternalNetwork = True

        return self

    def configure(self) -> None:
        """!
        @brief Validate ports and configure all InternetMap services.

        @raises ValueError when fewer than three host ports are configured.
        """
        super().configure()

        seedemu_traffic_observer_service_backend = self._containers[
            "seedemu_traffic_observer_service_backend" + self._suffix
        ]
        seedemu_traffic_observer_service_port = self._ports.pop()
        seedemu_traffic_observer_service_backend.setContentAttribute(
            {
                "image": SEEDEMU_TRAFFIC_OBSERVER_SERVICE_IMAGE,
                "privileged": True,
                "pid": "host",
                "network_mode": "host",
                "environment": {
                    "TRAFFIC_CONTROL_ADDR": f":{seedemu_traffic_observer_service_port}",
                    "TRAFFIC_LOG_TIMEZONE": "Asia/Shanghai",
                },
                "volumes": [
                    "/sys/kernel/debug:/sys/kernel/debug",
                    "/sys/fs/bpf:/sys/fs/bpf",
                    "/sys/kernel/btf:/sys/kernel/btf:ro",
                    "/lib/modules:/lib/modules:ro",
                    "/var/run/docker.sock:/var/run/docker.sock:ro",
                    "./traffic-observer-service/pcap:/data/pcap",
                ],
            }
        )
        seedemu_traffic_observer_service_backend._service_ports = [
            seedemu_traffic_observer_service_port
        ]

        default_network_name = self._default_external_network["name"]
        ip_addresses = self._default_external_network["ip_addresses"]
        for index, container in enumerate(self._containers.values()):
            if container is seedemu_traffic_observer_service_backend:
                continue
            container.joinExternalNetwork(
                default_network_name, container.getHostname(), ip_addresses[index]
            )

        seedemu_emulator_service_backend = self._containers[
            "seedemu_emulator_service_backend" + self._suffix
        ]
        seedemu_emulator_service_backend.setContentAttribute(
            {
                "privileged": True,
                "image": SEEDEMU_EMULATOR_SERVICE_IMAGE,
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock:ro"],
                "environment": {"BACKEND_ENV": "production"},
            }
        )
        seedemu_emulator_service_ip = seedemu_emulator_service_backend.service["networks"][
            default_network_name
        ]["ipv4_address"]

        if self._enableInternalNetwork:
            if not self._default_internal_network:
                self.allocateEmuNetworkAddress()
            seedemu_emulator_service_backend.joinInternalNetwork(
                hostname=seedemu_emulator_service_backend.getHostname(),
                network=self._default_internal_network["network"],
                ip_address=self._default_internal_network["ip_addresses"][0],
                default_route=self._default_internal_network["default_route"],
            )
            seedemu_emulator_service_backend.setContentAttribute(
                {
                    "build": f"./{seedemu_emulator_service_backend.getHostname()}",
                }
            )

        seedemu_internet_map_toplogy = self._containers[
            "seedemu_internet_map_toplogy" + self._suffix
        ]
        seedemu_internet_map_toplogy.setContentAttribute(
            {
                "privileged": True,
                "image": SEEDEMU_INTERNET_MAP_TOPLOGY_IMAGE,
                "depends_on": [seedemu_emulator_service_backend.getHostname()],
                "ports": [f"{self._ports.pop()}:80"],
                "build": f"./{seedemu_internet_map_toplogy.getHostname()}",
            }
        )
        seedemu_internet_map_toplogy.setFile(
            NGINX_CONF_PATH,
            SEEDEMU_INTERNET_MAP_TOPLOGY_NGINX_CONF.format(
                seedemu_emulator_service_ip,
                SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT,
            ),
        )
        seedemu_internet_map_toplogy._start_script_name = START_SCRIPT_NAME
        seedemu_internet_map_toplogy.setEtcHosts(
            "\n".join(
                [f"{seedemu_emulator_service_ip} {seedemu_emulator_service_backend.getHostname()}"]
            )
        )

        seedemu_internet_map_geographic = self._containers[
            "seedemu_internet_map_geographic" + self._suffix
        ]
        seedemu_internet_map_geographic.setContentAttribute(
            {
                "privileged": True,
                "image": SEEDEMU_INTERNET_MAP_GEOGRAPHIC_IMAGE,
                "depends_on": [seedemu_emulator_service_backend.getHostname()],
                "extra_hosts": {"host.docker.internal": "host-gateway"},
                "ports": [f"{self._ports.pop()}:80"],
                "build": f"./{seedemu_internet_map_geographic.getHostname()}",
            }
        )
        seedemu_internet_map_geographic.setFile(
            NGINX_CONF_PATH,
            SEEDEMU_INTERNET_MAP_GEOGRAPHIC_NGINX_CONF.format(
                seedemu_emulator_service_ip,
                SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT,
                seedemu_traffic_observer_service_backend.service.get("environment", {}).get(
                    "TRAFFIC_CONTROL_ADDR"
                )[1:],
            ),
        )
        seedemu_internet_map_geographic._start_script_name = START_SCRIPT_NAME
        seedemu_internet_map_geographic.setEtcHosts(
            "\n".join(
                [f"{seedemu_emulator_service_ip} {seedemu_emulator_service_backend.getHostname()}"]
            )
        )
