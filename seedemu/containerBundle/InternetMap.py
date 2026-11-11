from .ContainerBundle import ContainerBundle

EMULATOR_API_SERVER = "emulator_api_server"
INTERNET_MAP_TOPLOGY = "internetmap_toplogy"
INTERNET_MAP_GEOGRAPHIC = "internetmap_geo"
TRAFFIC_OBSERVER = "traffic_observer"
EMULATOR_API_SERVER_IMAGE = "handsonsecurity/seedemu-emulator-service:1.0"
INTERNET_MAP_TOPLOGY_IMAGE = "handsonsecurity/seedemu-internet-toplogy:1.0"
INTERNET_MAP_GEOGRAPHIC_IMAGE = "handsonsecurity/seedemu-internet-map-geographic:1.0"
TRAFFIC_OBSERVER_IMAGE = "handsonsecurity/seedemu-traffic-observer-service:1.0"

DEFAULT_EXTERNAL_NETWORK = {
    "network_name": "internetMap_network",
    "prefix": "172.30.0.0/24",
    "ip_addresses": [f"172.30.0.{i}" for i in range(10, 14)],
    "default_route": "172.30.0.1",
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
EMULATOR_API_SERVER_INTERNAL_PORT = 7071
START_SCRIPT_NAME = "/entrypoint.sh"
TRAFFIC_OBSERVER_START_SCRIPT_NAME = "/usr/local/bin/traffic-observer-entrypoint"
INTERNET_MAP_TOPLOGY_NGINX_CONF = """
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
INTERNET_MAP_GEOGRAPHIC_NGINX_CONF = """
upstream seedemu_emulator_service_backend {{
    server {}:{};
}}

upstream traffic_observer {{
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
        proxy_pass http://traffic_observer/;
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
    @brief Bundle for topology, geographic map, and traffic views.

    Three containers share the first configured external network (or the default
    network); the traffic observer uses host networking. Host ports are read
    from indexes 0, 1, and 2 for observer control, topology HTTP, and geographic
    HTTP, respectively; the port list is not consumed. Only the API backend joins
    the first explicitly supplied internal network, using its first address;
    that attachment also adds the metadata labels used to display it on the map.
    Use unique suffixes, networks, and port pools for multiple instances.
    """

    def __init__(self, emulator, suffix=".map.seed"):
        """!
        @brief Create an Internet Map bundle.

        @param emulator emulator whose topology will be visualized.
        @param suffix suffix appended to generated container hostnames.
        """
        super().__init__(emulator=emulator, suffix=suffix)

        service_names = [
            EMULATOR_API_SERVER,
            INTERNET_MAP_TOPLOGY,
            INTERNET_MAP_GEOGRAPHIC,
            TRAFFIC_OBSERVER,
        ]
        for service_name in service_names:
            self._createContainer(service_name, suffix)
        self._required_port_count = 3
        self._required_internal_address_count = 1

    def configure(self) -> None:
        """!
        @brief Validate ports and configure all InternetMap services.

        @raises AssertionError when fewer than three host ports are configured.
        """
        super().configure()

        if not self._external_networks:
            self._external_networks.append(DEFAULT_EXTERNAL_NETWORK)
        external_network = self._external_networks[0]
        external_network_name = external_network["network_name"]
        ip_addresses = external_network["ip_addresses"]

        traffic_observer = self._containers[TRAFFIC_OBSERVER]
        traffic_observer_port = self._ports[0]
        traffic_observer.updateServiceConfig(
            {
                "image": TRAFFIC_OBSERVER_IMAGE,
                "privileged": True,
                "pid": "host",
                "network_mode": "host",
                "environment": {
                    "TRAFFIC_CONTROL_ADDR": f":{traffic_observer_port}",
                    "TRAFFIC_LOG_TIMEZONE": "Asia/Shanghai",
                },
                "volumes": [
                    "/sys/kernel/debug:/sys/kernel/debug",
                    "/sys/fs/bpf:/sys/fs/bpf",
                    "/var/run/docker.sock:/var/run/docker.sock:ro",
                    "./traffic-observer-service/pcap:/data/pcap",
                ],
            }
        )
        traffic_observer._service_ports = [traffic_observer_port]
        traffic_observer._start_script_name = TRAFFIC_OBSERVER_START_SCRIPT_NAME

        emulator_api_server = self._containers[EMULATOR_API_SERVER]
        emulator_api_server.joinExternalNetwork(network_name=external_network_name,hostname=emulator_api_server.getHostname(),ip_address=ip_addresses[0])
        self.addEtcHostsRecord(emulator_api_server.getName() + '-e' + self._suffix, ip_addresses[0])
        emulator_api_server.updateServiceConfig(
            {
                "privileged": True,
                "image": EMULATOR_API_SERVER_IMAGE,
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock:ro"],
                "environment": {"BACKEND_ENV": "production"},
            }
        )
        emulator_server_ip = emulator_api_server._service["networks"][
            external_network_name
        ]["ipv4_address"]

        internet_map_toplogy = self._containers[INTERNET_MAP_TOPLOGY]
        internet_map_toplogy.joinExternalNetwork(network_name=external_network_name,hostname=internet_map_toplogy.getHostname(),ip_address=ip_addresses[1])
        self.addEtcHostsRecord(internet_map_toplogy.getHostname(), ip_addresses[1])
        internet_map_toplogy.updateServiceConfig(
            {
                "privileged": True,
                "image": INTERNET_MAP_TOPLOGY_IMAGE,
                "depends_on": [emulator_api_server.getHostname()],
                "ports": [f"{self._ports[1]}:80"],
            }
        )
        internet_map_toplogy.setFile(
            NGINX_CONF_PATH,
            INTERNET_MAP_TOPLOGY_NGINX_CONF.format(
                emulator_server_ip,
                EMULATOR_API_SERVER_INTERNAL_PORT,
            ),
        )
        internet_map_toplogy._start_script_name = START_SCRIPT_NAME

        internet_map_geographic = self._containers[INTERNET_MAP_GEOGRAPHIC]
        internet_map_geographic.joinExternalNetwork(network_name=external_network_name,hostname=internet_map_geographic.getHostname(),ip_address=ip_addresses[2])
        self.addEtcHostsRecord(internet_map_geographic.getHostname(), ip_addresses[2])
        internet_map_geographic.updateServiceConfig(
            {
                "privileged": True,
                "image": INTERNET_MAP_GEOGRAPHIC_IMAGE,
                "depends_on": [emulator_api_server.getHostname()],
                "extra_hosts": {"host.docker.internal": "host-gateway"},
                "ports": [f"{self._ports[2]}:80"],
            }
        )
        internet_map_geographic.setFile(
            NGINX_CONF_PATH,
            INTERNET_MAP_GEOGRAPHIC_NGINX_CONF.format(
                emulator_server_ip,
                EMULATOR_API_SERVER_INTERNAL_PORT,
                traffic_observer._service.get("environment", {}).get(
                    "TRAFFIC_CONTROL_ADDR"
                )[1:],
            ),
        )
        internet_map_geographic._start_script_name = START_SCRIPT_NAME

        for index in range(len(self._internal_networks)):
            internal_network = self._internal_networks[index]
            ip_address = internal_network["ip_addresses"][0]
            emulator_api_server.joinInternalNetwork(
                asn=internal_network["asn"],
                network_name=internal_network["network_name"],
                hostname=emulator_api_server.getHostname(),
                ip_address=ip_address,
                default_route=internal_network["default_route"],
            )
            if index == 0:
                # index == 0, the emulator_api_server needs to be added to the emulator network (internal network). The frequency of using the corresponding IP will be higher. Therefore, the 'hostname' is set as the alias of this IP.
                self.addEtcHostsRecord(emulator_api_server.getHostname(), ip_address)
            else:
                self.addEtcHostsRecord(f"{emulator_api_server.getName()}-e{index}{self._suffix}", ip_address)
