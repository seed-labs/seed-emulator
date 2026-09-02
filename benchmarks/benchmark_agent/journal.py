"""Append-only session journal for the benchmark lifecycle."""

import json
from pathlib import Path
from typing import Any


class Journal:
    """Write lifecycle events incrementally as append-only JSON Lines.

    Events are written one line at a time so a crashed run still leaves a
    replayable journal; ``events.json`` remains a summary written at the end.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []

    def append(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def write_summary(self, path: Path) -> None:
        path.write_text(
            json.dumps(self._events, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def load(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events
