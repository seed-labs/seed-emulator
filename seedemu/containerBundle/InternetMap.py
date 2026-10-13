from .ContainerBundle import ContainerBundle

SEEDEMU_EMULATOR_SERVICE_IMAGE = "handsonsecurity/seedemu-emulator-service:1.0"
SEEDEMU_INTERNET_MAP_TOPLOGY_IMAGE = "handsonsecurity/seedemu-internet-toplogy:1.0"
SEEDEMU_INTERNET_MAP_GEOGRAPHIC_IMAGE = "handsonsecurity/seedemu-internet-map-geographic:1.0"
SEEDEMU_TRAFFIC_OBSERVER_SERVICE_IMAGE = "handsonsecurity/seedemu-traffic-observer-service:1.0"

NGINX_CONF_PATH = "/etc/nginx/conf.d/default.conf"
SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT = 7071
SEEDEMU_INTERNET_MAP_TOPLOGY_NGINX_CONF = """
upstream seedemu_emulator_service {{
    server {}:{};
}}

server {{
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 100m;

    location ^~ /api/v1 {{
        proxy_pass http://seedemu_emulator_service;
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
        proxy_pass http://seedemu_emulator_service/;
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
upstream seedemu_emulator_service {{
    server {}:{};
}}

upstream seedemu_traffic_observer_service {{
    server host.docker.internal:{};
}}

server {{
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 100m;

    location ^~ /api/v1 {{
        proxy_pass http://seedemu_emulator_service;
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
        proxy_pass http://seedemu_emulator_service/;
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
        proxy_pass http://seedemu_traffic_observer_service/;
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
    def __init__(self, emulator, suffix="map.seed"):
        super().__init__(emulator=emulator, suffix=suffix)
        service_names = [
            "seedemu_emulator_service",
            "seedemu_internet_map_toplogy",
            "seedemu_internet_map_geographic",
            "seedemu_traffic_observer_service",
        ]
        for service_name in service_names:
            self._createContainer(service_name, suffix)

    def configure(self) -> None:
        self._required_port_number = 3
        super().configure()
        
        seedemu_traffic_observer_service = self._containers["seedemu_traffic_observer_service"]
        seedemu_traffic_observer_service_port = self._ports.pop()
        seedemu_traffic_observer_service.setContentAttribute(
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
        seedemu_traffic_observer_service._service_ports = [seedemu_traffic_observer_service_port]

        seedemu_emulator_service = self._containers["seedemu_emulator_service"]
        seedemu_emulator_service.setContentAttribute(
            {
                "image": SEEDEMU_EMULATOR_SERVICE_IMAGE,
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock:ro"],
                "environment": {"BACKEND_ENV": "production"},
            }
        )

        seedemu_internet_map_toplogy = self._containers["seedemu_internet_map_toplogy"]
        seedemu_internet_map_toplogy.setContentAttribute(
            {
                "image": SEEDEMU_INTERNET_MAP_TOPLOGY_IMAGE,
                "depends_on": [seedemu_emulator_service.getName()],
                "ports": [f"{self._ports.pop()}:80"],
                "build": f"./{seedemu_internet_map_toplogy.getHostname()}",
            }
        )
        seedemu_internet_map_toplogy.setFile(
            NGINX_CONF_PATH,
            SEEDEMU_INTERNET_MAP_TOPLOGY_NGINX_CONF.format(
                seedemu_emulator_service.getName(), SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT
            ),
        )

        seedemu_internet_map_geographic = self._containers["seedemu_internet_map_geographic"]
        seedemu_internet_map_geographic.setContentAttribute(
            {
                "image": SEEDEMU_INTERNET_MAP_GEOGRAPHIC_IMAGE,
                "depends_on": [seedemu_emulator_service.getName()],
                "extra_hosts": {"host.docker.internal": "host-gateway"},
                "ports": [f"{self._ports.pop()}:80"],
                "build": f"./{seedemu_internet_map_geographic.getHostname()}",
            }
        )
        seedemu_internet_map_geographic.setFile(
            NGINX_CONF_PATH,
            SEEDEMU_INTERNET_MAP_GEOGRAPHIC_NGINX_CONF.format(
                seedemu_emulator_service.getName(),
                SEEDEMU_EMULATOR_SERVICE_INTERNAL_PORT,
                seedemu_traffic_observer_service.service.get("environment", {}).get(
                    "TRAFFIC_CONTROL_ADDR"
                )[1:],
            ),
        )

        if self._default_network:
            default_network_name = self._default_network[0]
            for container in self._containers.values():
                if container is seedemu_traffic_observer_service:
                    continue
                container.joinExternalNetwork(default_network_name)