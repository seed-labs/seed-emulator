import sys
import os

# Add parent directory to path to import seedemu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from seedemu.core import Emulator
from seedemu.layers import Base

class EmulatorRuntime:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmulatorRuntime, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        self.emulator = Emulator()
        self.base = Base()
        self.emulator.addLayer(self.base)
        self.rendered = False
        
        # Docker deployment state
        self.output_dir = None
        self.docker_client = None
        
        # Name -> Object mapping for easy lookup by LLM
        self.registry = {}
        # Operation history for exporting script
        self.code_buffer = [
            "from seedemu.core import Emulator, Binding, Filter",
            "from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, Mpls",
            "from seedemu.services import WebService, DomainNameService",
            "from seedemu.compiler import Docker",
            "",
            "emulator = Emulator()",
            "base = Base()",
            "emulator.addLayer(base)",
        ]
    
    def get_docker_client(self):
        """Get or create Docker client"""
        if self.docker_client is None:
            import docker
            self.docker_client = docker.from_env()
        return self.docker_client

    def get_emulator(self) -> Emulator:
        return self.emulator

    def get_base(self) -> Base:
        return self.base

    def register_object(self, name: str, obj):
        """Register an object with a unique name"""
        self.registry[name] = obj

    def get_object(self, name: str):
        """Get an object by name"""
        return self.registry.get(name)

    def log_code(self, code: str):
        """Log Python code for export"""
        self.code_buffer.append(code)

    def get_script(self) -> str:
        """Get the full Python script"""
        return "\n".join(self.code_buffer)
        
    def find_node_by_name(self, node_name: str):
        """Helper to find a node object across all ASes in Base layer"""
        # First check local registry
        if node_name in self.registry:
            return self.registry[node_name]
            
        # Fallback: Search in Base layer
        for asn in self.base.getAsns():
            as_obj = self.base.getAutonomousSystem(asn)
            if node_name in as_obj.getRouters():
                return as_obj.getRouter(node_name)
            if node_name in as_obj.getHosts():
                return as_obj.getHost(node_name)
        return None

# Global singleton
runtime = EmulatorRuntime()
