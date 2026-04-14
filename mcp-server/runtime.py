import os
import sys
from enum import Enum
from typing import Any

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


class LifecycleAction(Enum):
    """Canonical lifecycle actions for build and attached-runtime flows."""

    RENDER = "render_simulation"
    COMPILE = "compile_simulation"
    BUILD = "build_images"
    START = "start_simulation"
    STOP = "stop_simulation"
    ATTACH = "attach_to_simulation"


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
        self.topology_version = 0
        self.rendered_version = -1
        self.compiled_version = -1
        self.built_version = -1
        self.attached_output_dir = None
        self.last_transition_reason = "reset"

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

    def note_topology_change(self, reason: str = "") -> None:
        """Invalidate rendered/compiled runtime state after topology mutations."""
        self.topology_version += 1
        self.rendered = False
        self.rendered_version = -1
        self.compiled_version = -1
        self.built_version = -1
        self.output_dir = None
        self.attached_output_dir = None
        self.last_transition_reason = reason or "topology_changed"
        if self.phase in {
            AgentPhase.CONFIRMED,
            AgentPhase.COMPILING,
            AgentPhase.RUNNING,
            AgentPhase.OPERATING,
            AgentPhase.DEBUGGING,
        }:
            self.phase = AgentPhase.DESIGNING

    def mark_rendered(self) -> None:
        self.rendered = True
        self.rendered_version = self.topology_version
        self.compiled_version = -1
        self.built_version = -1
        self.output_dir = None
        self.attached_output_dir = None
        self.phase = AgentPhase.CONFIRMED
        self.last_transition_reason = LifecycleAction.RENDER.value

    def mark_compiled(self, output_dir: str) -> None:
        self.output_dir = os.path.abspath(output_dir)
        self.attached_output_dir = None
        self.compiled_version = self.topology_version
        self.built_version = -1
        self.phase = AgentPhase.COMPILING
        self.last_transition_reason = LifecycleAction.COMPILE.value

    def mark_built(self) -> None:
        self.built_version = self.compiled_version
        self.phase = AgentPhase.COMPILING
        self.last_transition_reason = LifecycleAction.BUILD.value

    def mark_started(self) -> None:
        self.phase = AgentPhase.RUNNING
        self.last_transition_reason = LifecycleAction.START.value

    def mark_stopped(self) -> None:
        self.phase = AgentPhase.CONFIRMED if self.rendered_version == self.topology_version else AgentPhase.IDLE
        self.last_transition_reason = LifecycleAction.STOP.value

    def mark_attached(self, output_dir: str) -> None:
        resolved = os.path.abspath(output_dir)
        self.output_dir = resolved
        self.attached_output_dir = resolved
        self.phase = AgentPhase.OPERATING
        self.last_transition_reason = LifecycleAction.ATTACH.value

    def is_render_current(self) -> bool:
        return self.rendered and self.rendered_version == self.topology_version

    def is_compile_current(self) -> bool:
        return bool(self.output_dir) and self.compiled_version == self.topology_version

    def is_build_current(self) -> bool:
        return self.is_compile_current() and self.built_version == self.compiled_version

    def lifecycle_contract(self) -> dict[str, Any]:
        """Return explicit lifecycle state and valid next actions."""
        next_actions: list[str] = []
        if not self.is_render_current():
            next_actions.append(LifecycleAction.RENDER.value)
        if self.is_render_current() and not self.is_compile_current():
            next_actions.append(LifecycleAction.COMPILE.value)
        if self.is_compile_current() and not self.is_build_current():
            next_actions.append(LifecycleAction.BUILD.value)
        if self.is_build_current():
            next_actions.extend([LifecycleAction.START.value, LifecycleAction.STOP.value])
        if self.attached_output_dir:
            next_actions.extend(["workspace_attach_compose", "workspace_refresh", "operate_runtime"])
        if self.phase == AgentPhase.RUNNING:
            next_actions.extend(["list_containers", "discover_running_simulation"])

        return {
            "phase": self.phase.value,
            "topology_version": self.topology_version,
            "rendered": self.is_render_current(),
            "compiled": self.is_compile_current(),
            "images_built": self.is_build_current(),
            "running": self.phase == AgentPhase.RUNNING,
            "attached": bool(self.attached_output_dir),
            "output_dir": self.output_dir,
            "attached_output_dir": self.attached_output_dir,
            "last_transition_reason": self.last_transition_reason,
            "next_actions": next_actions,
            "preconditions": {
                LifecycleAction.COMPILE.value: "requires rendered topology current with latest mutations",
                LifecycleAction.BUILD.value: "requires compiled output current with latest render",
                LifecycleAction.START.value: "requires built images current with latest compile",
                LifecycleAction.ATTACH.value: "requires an existing output directory with docker-compose.yml",
            },
        }
    
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
