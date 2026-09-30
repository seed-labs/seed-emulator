from sys import stderr
from enum import Enum
from dataclasses import dataclass, field
from textwrap import indent
from typing import Any, Dict, List, Optional
from yaml import safe_dump


class VisualizationType(str, Enum):
    INTERNET_MAP_TOPOLOGY = "internet_map_topology"
    INTERNET_MAP_GEOGRAPHIC = "internet_map_geographic"
    INTERNET_MAP_SATELLITE = "internet_map_satellite"
    TRAFFIC_OBSERVER = "traffic_observer"


@dataclass
class VisualizationContainer:
    """
    Represents one visualization-related Docker service.
    """

    name: str
    image: str

    enabled: bool = True

    container_name: Optional[str] = None

    ports: List[str] = field(default_factory=list)

    environment: Dict[str, Any] = field(default_factory=dict)

    volumes: List[str] = field(default_factory=list)

    networks: List[str] = field(default_factory=lambda: ["seed-visualization"])

    depends_on: List[str] = field(default_factory=list)

    command: Optional[str] = None

    privileged: bool = True

    extra: Dict[str, Any] = field(default_factory=dict)

    pid: Optional[str] = None

    network_mode: Optional[str] = None

    # Fixed listening port inside the container; independent of the host port.
    container_port: Optional[int] = None

    def toCompose(self) -> Dict[str, Any]:

        service: Dict[str, Any] = {
            "image": self.image,
            "container_name": self.container_name or self.name,
        }

        if self.ports:
            service["ports"] = self.ports

        if self.environment:
            service["environment"] = self.environment

        if self.volumes:
            service["volumes"] = self.volumes

        if self.networks:
            service["networks"] = self.networks

        if self.depends_on:
            service["depends_on"] = self.depends_on

        if self.command:
            service["command"] = self.command

        if self.privileged:
            service["privileged"] = True

        service.update(self.extra)

        if self.pid:
            service["pid"] = self.pid
        if self.network_mode:
            service["network_mode"] = self.network_mode
        if service.get("network_mode"):
            service.pop("networks", None)
        if service.get("network_mode") == "host":
            service.pop("ports", None)

        return service


@dataclass
class EmulatorServiceContainer(VisualizationContainer):
    container_port: Optional[int] = 7071
    image: str = "handsonsecurity/seedemu-emulator-service:1.0"
    name: str = "seedemu_emulator_service"
    container_name: str = "seedemu_emulator_service"
    volumes: List[str] = field(
        default_factory=lambda: [
            "/var/run/docker.sock:/var/run/docker.sock:ro",
        ]
    )
    environment: Dict[str, Any] = field(default_factory=lambda: {"BACKEND_ENV": "production"})


@dataclass
class InternetMapToplogyContainer(VisualizationContainer):
    container_port: Optional[int] = 80
    image: str = "handsonsecurity/seedemu-internet-toplogy:1.0"
    name: str = "seedemu_internet_map_toplogy"
    container_name: str = "seedemu_internet_map_toplogy"
    depends_on: List[str] = field(default_factory=lambda: ["seedemu_emulator_service"])


@dataclass
class InternetMapGeographicContainer(VisualizationContainer):
    container_port: Optional[int] = 80
    image: str = "handsonsecurity/seedemu-internet-map-geographic:1.0"
    extra: Dict[str, Any] = field(
        default_factory=lambda: {"extra_hosts": {"host.docker.internal": "host-gateway"}}
    )
    name: str = "seedemu_internet_map_geographic"
    container_name: str = "seedemu_internet_map_geographic"
    depends_on: List[str] = field(
        default_factory=lambda: ["seedemu_emulator_service", "seedemu_traffic_observer_service"]
    )


@dataclass
class InternetMapSatelliteContainer(VisualizationContainer):
    # Set this to the listening port of the satellite map image.
    container_port: Optional[int] = 80
    image: str = "handsonsecurity/seedemu-internet-map-satellite:1.0"
    extra: Dict[str, Any] = field(
        default_factory=lambda: {"extra_hosts": {"host.docker.internal": "host-gateway"}}
    )
    name: str = "seedemu_internet_map_satellite"
    container_name: str = "seedemu_internet_map_satellite"
    depends_on: List[str] = field(
        default_factory=lambda: ["seedemu_emulator_service", "seedemu_satellite_emulator_service"]
    )


@dataclass
class SatelliteEmulatorServiceContainer(VisualizationContainer):
    container_port: Optional[int] = 9091
    image: str = "handsonsecurity/seedemu-satellite-emulator-service:1.0"
    name: str = "seedemu_satellite_emulator_service"
    container_name: str = "seedemu_satellite_emulator_service"


@dataclass
class TrafficObserverServiceContainer(VisualizationContainer):
    image: str = "handsonsecurity/seedemu-traffic-observer-service:1.0"
    pid: Optional[str] = "host"
    network_mode: Optional[str] = "host"
    volumes: List[str] = field(
        default_factory=lambda: [
            "/sys/kernel/debug:/sys/kernel/debug",
            "/sys/fs/bpf:/sys/fs/bpf",
            "/sys/kernel/btf:/sys/kernel/btf:ro",
            "/lib/modules:/lib/modules:ro",
            "/var/run/docker.sock:/var/run/docker.sock:ro",
            "./traffic-observer-service/pcap:/data/pcap",
        ]
    )
    name: str = "seedemu_traffic_observer_service"
    container_name: str = "seedemu_traffic_observer_service"


class VisualizationManager:

    def __init__(self):
        self.__services: Dict[str, VisualizationContainer] = {}

    def add_emulator_service(self, **kwargs):
        self.add(EmulatorServiceContainer(**kwargs))

    def add_internet_map_toplogy(self, **kwargs):
        self.add(InternetMapToplogyContainer(**kwargs))

    def add_internet_map_geographic(self, **kwargs):
        self.add(InternetMapGeographicContainer(**kwargs))

    def add_satellite_emulator_service(self, **kwargs):
        self.add(SatelliteEmulatorServiceContainer(**kwargs))

    def add_internet_map_satellite(self, **kwargs):
        self.add(InternetMapSatelliteContainer(**kwargs))

    def add_traffic_observer_service(self, **kwargs):
        self.add(TrafficObserverServiceContainer(**kwargs))

    def add(self, visualization: VisualizationContainer) -> "VisualizationManager":

        if visualization.name in self.__services:
            raise ValueError(f"visualization service already exists: " f"{visualization.name}")

        self.__services[visualization.name] = visualization

        return self

    def remove(self, name: str) -> "VisualizationManager":

        self.__services.pop(name, None)

        return self

    def get(self, name: str) -> Optional[VisualizationContainer]:

        return self.__services.get(name)

    def enable(self, name: str) -> "VisualizationManager":

        self.__services[name].enabled = True

        return self

    def disable(self, name: str) -> "VisualizationManager":

        self.__services[name].enabled = False

        return self

    def getAll(self) -> List[VisualizationContainer]:

        return list(self.__services.values())

    def getEnabled(self) -> List[VisualizationContainer]:

        return [
            visualization for visualization in self.__services.values() if visualization.enabled
        ]

    def toComposeServices(self) -> Dict[str, Dict[str, Any]]:

        services = {}

        for visualization in self.getEnabled():

            services[visualization.name] = visualization.toCompose()

        return services

    def toComposeTxt(self) -> tuple[str, str]:
        """Return indented YAML entries without services/networks headers.

        Entries use four-space indentation for the Docker Compose template.
        Each service ends with a blank line. Empty sections return empty strings.
        """
        services = self.toComposeServices()
        if not services:
            return "", ""

        networks = {
            network: {} for service in services.values() for network in service.get("networks", [])
        }
        compose_services_txt = "\n" + "".join(
            indent(
                safe_dump(
                    {name: service}, sort_keys=False, default_flow_style=False, indent=4
                ),
                "    ",
            ) + "\n"
            for name, service in services.items()
        )
        compose_networks_txt = (
            "\n" + indent(
                safe_dump(networks, sort_keys=False, default_flow_style=False, indent=4),
                "    ",
            )
            if networks else ""
        )
        return compose_services_txt, compose_networks_txt

visualization_manager = VisualizationManager()
