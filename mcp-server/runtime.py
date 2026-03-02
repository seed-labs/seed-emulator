import sys
import os
from enum import Enum

# Ensure local repository root has highest import priority for `seedemu`.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
while _REPO_ROOT in sys.path:
    sys.path.remove(_REPO_ROOT)
sys.path.insert(0, _REPO_ROOT)

from seedemu.core import Emulator
from seedemu.layers import Base


class AgentPhase(Enum):
    """Agent state machine phases."""
    IDLE = "idle"                    # No active work
    DESIGNING = "designing"          # Creating design, awaiting confirmation
    CONFIRMED = "confirmed"          # Design approved, ready to execute
    COMPILING = "compiling"          # Generating Docker files
    RUNNING = "running"              # Simulation containers are up
    OPERATING = "operating"          # Performing dynamic operations
    DEBUGGING = "debugging"          # Analyzing/fixing issues


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
        
        # Agent state machine
        self.phase = AgentPhase.IDLE
        self.current_example = None     # Path to loaded example
        self.examples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples'))
        
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
    
    def set_phase(self, phase: AgentPhase):
        """Update agent phase."""
        self.phase = phase
    
    def get_phase(self) -> AgentPhase:
        """Get current agent phase."""
        return self.phase
    
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

    def get_code_log(self) -> list:
        """Get the logged code lines"""
        return self.code_buffer

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
