"""Append-only JSON Lines trace for Adapter decisions and observations."""

import json
import threading
from pathlib import Path
from typing import Any


class TraceRecorder:
    """Record every candidate action and observation for later scoring."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._entries: list[dict[str, Any]] = []

    def append(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._entries.append(entry)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
                )

    def entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._entries)
