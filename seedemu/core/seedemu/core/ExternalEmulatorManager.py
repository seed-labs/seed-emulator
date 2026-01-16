from typing import Dict
from seedemu.core.ExternalEmulation import ExternalEmuSpec


class ExternalEmulatorManager:
    """
    Manages external emulator integrations (Task 3).

    This class intentionally lives outside the Emulator core
    to avoid invasive changes.
    """

    def __init__(self):
        self._externals: Dict[str, ExternalEmuSpec] = {}

    def register(self, spec: ExternalEmuSpec):
        """Register an external emulator specification."""
        self._externals[spec.name] = spec

    def prepare(self, emulator):
        """
        Called after compile().
        Allows external emulators to export artifacts.
        """
        for spec in self._externals.values():
            spec.prepare(emulator)

    def start(self):
        """
        Optional runtime hook.
        """
        for spec in self._externals.values():
            if hasattr(spec, "start"):
                spec.start()
