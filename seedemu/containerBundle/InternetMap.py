from .ContainerBundle import ContainerBundle

SEEDEMU_EMULATOR_SERVICE_IMAGE = "handsonsecurity/seedemu-emulator-service:1.0"
SEEDEMU_INTERNET_MAP_TOPLOGY_IMAGE = "handsonsecurity/seedemu-internet-toplogy:1.0"
SEEDEMU_INTERNET_MAP_GEOGRAPHIC_IMAGE = "handsonsecurity/seedemu-internet-map-geographic:1.0"
SEEDEMU_TRAFFIC_OBSERVER_SERVICE_IMAGE = "handsonsecurity/seedemu-traffic-observer-service:1.0"

DEFAULT_NETWORK = {
    "name": "internetMap_network",
    "prefix": "172.30.0.0/24",
    "ip_addresses": [
        "172.30.0.10",
        "172.30.0.11",
        "172.30.0.12",
        "172.30.0.13",
    ],
    "default_router": "172.30.0.1",
}

NGINX_CONF_PATH = "/etc/nginx/conf.d/default.conf"
SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT = 7071
START_SH = [
    "#!/bin/sh",
    "set -eu",
    "nginx -g 'daemon off;' &",
    "nginx_pid=$!",
    "trap 'kill \"$nginx_pid\" 2> /dev/null || true' INT TERM",
    "while true; do",
    '    if ! kill -0 "$nginx_pid" 2> /dev/null; then',
    '        wait "$nginx_pid"',
    "        exit $?",
    "    fi",
    "    sleep 2",
    "done",
]
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
    """Container bundle for the topology, geographic map, and traffic views."""

    def __init__(self, emulator, suffix="map.seed"):
        """Create an Internet Map bundle.

        Args:
            emulator: Emulator whose topology will be visualized.
            suffix: Suffix appended to generated container hostnames.
        """
        super().__init__(emulator=emulator, suffix=suffix)
        self._default_network = DEFAULT_NETWORK
        service_names = [
            "seedemu_emulator_service_backend",
            "seedemu_internet_map_toplogy",
            "seedemu_internet_map_geographic",
            "seedemu_traffic_observer_service_backend",
        ]
        for service_name in service_names:
            self._createContainer(service_name, suffix)
        self._emu_internal_network = self.getEmuHostNetworkInfo()

    def enableEmulatorNetwork(self):
        """
        Enable access to an emulator internal network.
        """
        seedemu_emulator_service_backend = self._containers["seedemu_emulator_service_backend"]
        seedemu_emulator_service_backend.joinInternalNetwork(**self._emu_internal_network)
        
        return self

    def configure(self) -> None:
        """Validate ports and configure the map, API, and observer services."""
        self._required_port_number = 3
        super().configure()

        seedemu_traffic_observer_service_backend = self._containers[
            "seedemu_traffic_observer_service_backend"
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

        default_network_name = self._default_network["name"]
        ip_addresses = self._default_network["ip_addresses"]
        for index, container in enumerate(self._containers.values()):
            if container is seedemu_traffic_observer_service_backend:
                continue
            container.joinExternalNetwork(
                default_network_name, container.getHostname(), ip_addresses[index]
            )

        seedemu_emulator_service_backend = self._containers["seedemu_emulator_service_backend"]
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

        seedemu_internet_map_toplogy = self._containers["seedemu_internet_map_toplogy"]
        seedemu_internet_map_toplogy.setContentAttribute(
            {
                "privileged": True,
                "image": SEEDEMU_INTERNET_MAP_TOPLOGY_IMAGE,
                "depends_on": [seedemu_emulator_service_backend.getName()],
                "ports": [f"{self._ports.pop()}:80"],
                "build": f"./{seedemu_internet_map_toplogy.getHostname()}",
            }
        )
        seedemu_internet_map_toplogy.setFile(
            NGINX_CONF_PATH,
            SEEDEMU_INTERNET_MAP_TOPLOGY_NGINX_CONF.format(
                seedemu_emulator_service_backend.getHostname(),
                SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT,
            ),
        )
        # seedemu_internet_map_toplogy._start_commands = START_SH
        seedemu_internet_map_toplogy._start_script_name = START_SCRIPT_NAME
        seedemu_internet_map_toplogy.setEtcHosts(
            "\n".join(
                [f"{seedemu_emulator_service_ip} {seedemu_emulator_service_backend.getHostname()}"]
            )
        )

        seedemu_internet_map_geographic = self._containers["seedemu_internet_map_geographic"]
        seedemu_internet_map_geographic.setContentAttribute(
            {
                "privileged": True,
                "image": SEEDEMU_INTERNET_MAP_GEOGRAPHIC_IMAGE,
                "depends_on": [seedemu_emulator_service_backend.getName()],
                "extra_hosts": {"host.docker.internal": "host-gateway"},
                "ports": [f"{self._ports.pop()}:80"],
                "build": f"./{seedemu_internet_map_geographic.getHostname()}",
            }
        )
        seedemu_internet_map_geographic.setFile(
            NGINX_CONF_PATH,
            SEEDEMU_INTERNET_MAP_GEOGRAPHIC_NGINX_CONF.format(
                seedemu_emulator_service_backend.getHostname(),
                SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT,
                seedemu_traffic_observer_service_backend.service.get("environment", {}).get(
                    "TRAFFIC_CONTROL_ADDR"
                )[1:],
            ),
        )
        # seedemu_internet_map_geographic._start_commands = START_SH
        seedemu_internet_map_geographic._start_script_name = START_SCRIPT_NAME
        seedemu_internet_map_geographic.setEtcHosts(
            "\n".join(
                [f"{seedemu_emulator_service_ip} {seedemu_emulator_service_backend.getHostname()}"]
            )
        )
