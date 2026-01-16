# seedemu/core/ExternalEmulatorManager.py
from __future__ import annotations
from typing import List, Optional
from .ExternalEmulatorPlugin import ExternalEmulatorPlugin

class ExternalEmulatorManager:
    def __init__(self):
        self._plugins: List[ExternalEmulatorPlugin] = []

    def register(self, plugin: ExternalEmulatorPlugin):
        self._plugins.append(plugin)

    def get_plugin(self, external) -> Optional[ExternalEmulatorPlugin]:
        for p in self._plugins:
            if p.can_handle(external):
                return p
        return None

    def generate_all(self, externals: list, export_base_dir: str):
        results = []
        for ext in externals:
            plugin = self.get_plugin(ext)
            if plugin is None:
                raise RuntimeError(f"No plugin found for external: {ext}")
            export_dir = ext.getExportDir(export_base_dir)  # you likely already have this from Task 2
            meta = plugin.generate(ext, export_dir)
            results.append((ext, plugin.name, export_dir, meta))
        return results

