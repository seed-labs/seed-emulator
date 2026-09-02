"""Tests for the append-only lifecycle journal."""

import json
import tempfile
import unittest
from pathlib import Path

from benchmark_agent.journal import Journal


class JournalTests(unittest.TestCase):
    def test_append_summary_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            journal = Journal(path)
            journal.append({"kind": "baseline", "n": 1})
            journal.append({"kind": "inject", "n": 2})
            self.assertEqual(len(Journal.load(path)), 2)
            summary = Path(directory) / "events.json"
            journal.write_summary(summary)
            self.assertEqual(len(json.loads(summary.read_text())), 2)

    def test_load_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(Journal.load(Path(directory) / "absent.jsonl"), [])


if __name__ == "__main__":
    unittest.main()
