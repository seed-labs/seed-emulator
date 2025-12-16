from dataclasses import dataclass, field
from seedemu.core import Layer

@dataclass
class ExternalInterface:
    name: str
    network: str
    ip: str
    mac: str = None

@dataclass
class ExternalComponent:
    name: str
    role: str = "router"
    asn: int = None
    interfaces: list = field(default_factory=list)
    scion: dict = field(default_factory=dict)
    impl_type: str = "generic"

    def addInterface(self, name, network, ip, mac=None):
        iface = ExternalInterface(name, network, ip, mac)
        self.interfaces.append(iface)

class ExternalComponentLayer(Layer):
    def __init__(self):
        self.components = {}

    def addComponent(self, comp: ExternalComponent):
        self.components[comp.name] = comp

    def configure(self, emulator):
        """
        Register all external components in the emulator so that
        the builder and compilers can access them later.
        """
        for comp in self.components.values():
            emulator.registerExternalComponent(comp)

    def getName(self) -> str:
        return "ExternalComponent"

    def getTypeName(self) -> str:
        return "ExternalComponent"

    def getDependencies(self):
      	return {}

    def render(self, emulator):
        pass

