# seedemu/core/ExternalEmulatorPlugin.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ExternalEmulatorPlugin(ABC):
    """
    Plugin API for external emulators.
    A plugin is responsible for:
      - generating runnable artifacts (configs + start commands)
      - optionally starting/stopping the external emulator
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name, e.g., 'scion'."""
        raise NotImplementedError

    @abstractmethod
    def can_handle(self, external) -> bool:
        """Return True if this plugin can handle the given external component."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, external, export_dir: str) -> Dict[str, Any]:
        """
        Generate config + start commands inside export_dir.
        Must be deterministic, idempotent if possible.
        Return metadata (e.g., start_cmd, compose_file, etc.).
        """
        raise NotImplementedError

    def start(self, external, export_dir: str) -> int:
        """
        Optional: start external emulator from export_dir (default: rely on generated scripts).
        Return exit code.
        """
        return 0

    def stop(self, external, export_dir: str) -> int:
        """Optional: stop external emulator."""
        return 0
