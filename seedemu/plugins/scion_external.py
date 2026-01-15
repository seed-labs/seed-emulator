# seedemu/plugins/scion_external.py
from __future__ import annotations
import os, stat
from typing import Dict, Any
from seedemu.core.ExternalEmulatorPlugin import ExternalEmulatorPlugin

class ScionExternalPlugin(ExternalEmulatorPlugin):
    @property
    def name(self) -> str:
        return "scion"

    def can_handle(self, external) -> bool:
        # Example: external.emulator == "scion" or external.type == "scion"
        return getattr(external, "emulator", None) == "scion"

    def generate(self, external, export_dir: str) -> Dict[str, Any]:
        os.makedirs(export_dir, exist_ok=True)

        # Validate Task2 artifacts exist
        topo = os.path.join(export_dir, "topology.json")
        keys_dir = os.path.join(export_dir, "keys")
        if not os.path.isfile(topo):
            raise RuntimeError(f"Missing SCION artifact: {topo}")
        if not os.path.isdir(keys_dir):
            raise RuntimeError(f"Missing SCION artifact dir: {keys_dir}")

        # Minimal start/stop scripts (can be docker compose or direct command)
        start_sh = os.path.join(export_dir, "start_external.sh")
        stop_sh  = os.path.join(export_dir, "stop_external.sh")

        with open(start_sh, "w", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write("set -e\n")
            f.write('echo "[external:scion] starting..."\n')
            # Example placeholder:
            # f.write("docker compose up -d\n")
            f.write('echo "[external:scion] TODO: run external scion emulator here"\n')

        with open(stop_sh, "w", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write("set -e\n")
            f.write('echo "[external:scion] stopping..."\n')
            # Example placeholder:
            # f.write("docker compose down\n")
            f.write('echo "[external:scion] TODO: stop external scion emulator here"\n')

        # Make executable on Linux
        for p in (start_sh, stop_sh):
            try:
                st = os.stat(p)
                os.chmod(p, st.st_mode | stat.S_IEXEC)
            except Exception:
                pass

        return {
            "start_script": "start_external.sh",
            "stop_script": "stop_external.sh",
        }
