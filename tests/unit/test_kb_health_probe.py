"""KB health probe report writer."""

from __future__ import annotations

import json

from evaluation.kb_health_probe import write_kb_health_report


def test_write_kb_health_report(tmp_path):
    path = write_kb_health_report({"ok": True, "probes": 3, "retrieve_hit_rate": 0.8}, path=tmp_path / "r.json")
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["probes"] == 3
