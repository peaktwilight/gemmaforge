"""Contract tests for `python -m src.scan`.

Mocks GemmaForgeFilter so the Gemma LM is never loaded. Tests focus on:
- repo walking + skip-dirs
- chunking (window/stride)
- ranking by confidence * (1 + 0.5 if top_cwe else 0)
- min_confidence threshold
- top_k truncation
- event stream + leads JSONL shape (schema ids, required fields)

Run::

    pytest tests/test_scan.py -q
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from src import scan as scan_mod
from src.scan import (
    Chunk,
    EventSink,
    Lead,
    SCHEMA_EVENTS,
    SCHEMA_LEADS,
    _chunk_lines,
    _iter_files,
    lead_to_record,
    scan,
)


class FakeGF:
    """Stand-in for GemmaForgeFilter that scores by a snippet-keyed table."""

    model_id = "google/gemma-4-E2B-it"
    _layer = 17

    def __init__(self, scores: dict[str, tuple[float, Optional[str]]]):
        self._scores = scores

    def score_snippet(self, snippet: str) -> dict:
        for key, (conf, cwe) in self._scores.items():
            if key in snippet:
                return {
                    "gemmaforge_confidence": conf,
                    "gemmaforge_top_cwe": cwe,
                    "gemmaforge_layer": self._layer,
                    "model_id": self.model_id,
                }
        return {
            "gemmaforge_confidence": 0.1,
            "gemmaforge_top_cwe": None,
            "gemmaforge_layer": self._layer,
            "model_id": self.model_id,
        }


# ---------------- chunking ---------------- #


def test_chunk_lines_window_and_stride():
    text = "\n".join(f"L{i}" for i in range(1, 11))  # 10 lines
    chunks = list(_chunk_lines(text, "x.py", window=4, stride=2))
    spans = [(c.start_line, c.end_line) for c in chunks]
    # window=4 stride=2 over 10 lines → (1,4), (3,6), (5,8), (7,10)
    assert spans == [(1, 4), (3, 6), (5, 8), (7, 10)]
    assert chunks[0].text == "L1\nL2\nL3\nL4"


def test_chunk_lines_skips_blank_only_windows():
    text = "code\n" + "\n" * 10 + "code2"
    chunks = list(_chunk_lines(text, "x.py", window=3, stride=3))
    # No chunk should be entirely whitespace.
    for c in chunks:
        assert c.text.strip()


def test_chunk_lines_empty_returns_nothing():
    assert list(_chunk_lines("", "x.py", window=4, stride=2)) == []


# ---------------- walking ---------------- #


def test_iter_files_respects_skip_dirs(tmp_path: Path):
    (tmp_path / "keep.py").write_text("a = 1\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("x;\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n")
    files = list(_iter_files(tmp_path, languages=None))
    rels = [p.relative_to(tmp_path).as_posix() for p in files]
    assert rels == ["keep.py"]


def test_iter_files_language_filter(tmp_path: Path):
    (tmp_path / "a.py").write_text("a = 1\n")
    (tmp_path / "b.js").write_text("var x;\n")
    (tmp_path / "c.go").write_text("package main\n")
    files = list(_iter_files(tmp_path, languages={"py", "js"}))
    rels = sorted(p.relative_to(tmp_path).as_posix() for p in files)
    assert rels == ["a.py", "b.js"]


# ---------------- ranking ---------------- #


def test_rank_score_prefers_cwe_match():
    a = Lead(Chunk("x.py", 1, 5, "x"), confidence=0.8, top_cwe="CWE-89", layer=17, model_id="m")
    b = Lead(Chunk("x.py", 6, 10, "x"), confidence=0.8, top_cwe=None, layer=17, model_id="m")
    assert a.rank_score() > b.rank_score()


# ---------------- end-to-end ---------------- #


def _write_repo(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "bad.py").write_text(
        "\n".join([
            "def lookup(uid):",
            "    return db.execute(VULN_SINK_MARKER + uid)",
            "def helper():",
            "    return 0",
            "def trivial():",
            "    return None",
        ]) + "\n"
    )
    (root / "src" / "fine.py").write_text(
        "\n".join([
            "def safe(uid):",
            "    return db.execute('SELECT 1', (uid,))",
            "def helper():",
            "    return 1",
        ]) + "\n"
    )


def test_scan_emits_schema_compliant_leads(tmp_path: Path):
    _write_repo(tmp_path)
    gf = FakeGF({"VULN_SINK_MARKER": (0.92, "CWE-89")})

    leads = scan(
        tmp_path,
        gf=gf,
        languages={"py"},
        window=2, stride=2,
        min_confidence=0.5,
        top_k=None,
        events=EventSink(None),
    )
    records = [lead_to_record(lead, rank) for rank, lead in enumerate(leads)]
    assert records, "expected at least one lead"
    top = records[0]
    # Required schema fields
    assert top["schema"] == SCHEMA_LEADS
    for field in ("file", "start_line", "end_line", "snippet",
                  "gemmaforge_confidence", "gemmaforge_layer", "model_id", "rank"):
        assert field in top, field
    assert top["gemmaforge_top_cwe"] == "CWE-89"
    assert top["rank"] == 0
    # All chunks below the marker should be filtered by min_confidence.
    assert all(r["gemmaforge_confidence"] >= 0.5 for r in records)


def test_scan_top_k_truncates(tmp_path: Path):
    _write_repo(tmp_path)
    # Both files have a hit if we accept anything > 0.5.
    gf = FakeGF({"def ": (0.7, None)})
    leads = scan(
        tmp_path, gf=gf, languages={"py"},
        window=1, stride=1, min_confidence=0.5, top_k=2,
        events=EventSink(None),
    )
    assert len(list(leads)) == 2


def test_scan_events_stream_schema(tmp_path: Path):
    _write_repo(tmp_path)
    events_path = tmp_path / "events.ndjson"
    gf = FakeGF({"VULN_SINK_MARKER": (0.92, "CWE-89")})

    scan(
        tmp_path, gf=gf, languages={"py"},
        window=2, stride=2, min_confidence=0.5, top_k=None,
        events=EventSink(str(events_path)),
    )
    lines = events_path.read_text().splitlines()
    kinds = []
    for line in lines:
        rec = json.loads(line)
        assert rec["schema"] == SCHEMA_EVENTS
        assert "ts" in rec and "kind" in rec
        kinds.append(rec["kind"])
    assert kinds[0] == "scan.start"
    assert kinds[-1] == "scan.end"
    assert "scan.lead" in kinds
    assert "probe.score" in kinds


def test_scan_min_confidence_drops_low(tmp_path: Path):
    _write_repo(tmp_path)
    gf = FakeGF({})  # everything scores 0.1
    leads = list(scan(
        tmp_path, gf=gf, languages={"py"},
        window=2, stride=2, min_confidence=0.5, top_k=None,
        events=EventSink(None),
    ))
    assert leads == []


def test_lead_to_record_omits_top_cwe_when_none():
    lead = Lead(Chunk("x.py", 1, 5, "code"), confidence=0.7, top_cwe=None, layer=17, model_id="m")
    rec = lead_to_record(lead, rank=3)
    assert "gemmaforge_top_cwe" not in rec
    assert rec["rank"] == 3
