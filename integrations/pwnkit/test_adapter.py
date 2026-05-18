"""Contract tests for GemmaForgeFilter.

These mock both the binary probe + per-CWE probe (no real .npz files) and
stub out _hidden_state so the Gemma LM is never loaded. Run with:

    pytest integrations/pwnkit/test_adapter.py -q
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from integrations.pwnkit.adapter import GemmaForgeFilter


DIM = 8  # tiny stand-in for the real ~2560-dim Gemma hidden state


@pytest.fixture
def probe_files(tmp_path: Path) -> tuple[Path, Path]:
    bin_path = tmp_path / "probe.npz"
    np.savez_compressed(
        bin_path, w=np.ones(DIM, dtype=np.float32), b=np.float32(0.0),
        layer=np.int32(17),
    )

    per_path = tmp_path / "probe_per_cwe.npz"
    # 5 heads, head 0 (CWE-78) gets all-ones → fires highest on positive h.
    W = np.zeros((5, DIM), dtype=np.float32)
    W[0] = 1.0
    W[1] = 0.5
    np.savez(
        per_path,
        cwes=np.array(["CWE-78", "CWE-338", "CWE-95", "CWE-94", "CWE-328"]),
        W=W, b=np.zeros(5, dtype=np.float32), layer=np.int32(17),
    )
    return bin_path, per_path


def _build(monkeypatch, probe_files, h_value: float = 2.0) -> GemmaForgeFilter:
    bin_path, per_path = probe_files
    gf = GemmaForgeFilter(probe_path=str(bin_path), per_cwe_probe_path=str(per_path))
    monkeypatch.setattr(
        gf, "_hidden_state", lambda snippet: np.full(DIM, h_value, dtype=np.float32)
    )
    return gf


def test_returns_required_fields(monkeypatch, probe_files):
    gf = _build(monkeypatch, probe_files)
    out = gf.score_finding({"snippet": "exec(req.query.cmd)", "cwe": "CWE-78"})
    assert set(out) >= {
        "snippet", "cwe", "gemmaforge_confidence",
        "gemmaforge_cwe_match", "gemmaforge_top_cwe", "gemmaforge_layer",
    }
    assert 0.0 <= out["gemmaforge_confidence"] <= 1.0
    assert out["gemmaforge_layer"] == 17


def test_cwe_match_argmax(monkeypatch, probe_files):
    gf = _build(monkeypatch, probe_files)
    out = gf.score_finding({"snippet": "x", "cwe": "CWE-78"})
    assert out["gemmaforge_cwe_match"] == 1.0
    assert out["gemmaforge_top_cwe"] == "CWE-78"


def test_cwe_match_top2(monkeypatch, probe_files):
    gf = _build(monkeypatch, probe_files)
    out = gf.score_finding({"snippet": "x", "cwe": "CWE-338"})
    assert out["gemmaforge_cwe_match"] == 0.5


def test_cwe_match_miss(monkeypatch, probe_files):
    gf = _build(monkeypatch, probe_files)
    out = gf.score_finding({"snippet": "x", "cwe": "CWE-94"})
    assert out["gemmaforge_cwe_match"] == 0.0


def test_cwe_outside_trained_heads_returns_none(monkeypatch, probe_files):
    gf = _build(monkeypatch, probe_files)
    out = gf.score_finding({"snippet": "x", "cwe": "CWE-601"})
    assert out["gemmaforge_cwe_match"] is None
    assert out["gemmaforge_top_cwe"] is None


def test_no_cwe_field_skips_match(monkeypatch, probe_files):
    gf = _build(monkeypatch, probe_files)
    out = gf.score_finding({"snippet": "x"})
    assert out["gemmaforge_cwe_match"] is None
    assert "gemmaforge_confidence" in out


def test_empty_snippet_raises(monkeypatch, probe_files):
    gf = _build(monkeypatch, probe_files)
    with pytest.raises(ValueError):
        gf.score_finding({"snippet": "   ", "cwe": "CWE-78"})


def test_lm_not_loaded_at_construction(probe_files, monkeypatch):
    # If torch were imported eagerly, constructing the filter would do so.
    # We can't easily assert "torch is not imported" globally, but we CAN
    # assert that _ensure_model has not been called by checking the cache.
    bin_path, per_path = probe_files
    gf = GemmaForgeFilter(probe_path=str(bin_path), per_cwe_probe_path=str(per_path))
    assert gf._model is None and gf._tokenizer is None


def _make_per_cwe_npz(path: Path, layer: int = 17) -> None:
    np.savez(
        path,
        cwes=np.array(["CWE-78", "CWE-338", "CWE-95", "CWE-94", "CWE-328"]),
        W=np.zeros((5, DIM), dtype=np.float32),
        b=np.zeros(5, dtype=np.float32),
        layer=np.int32(layer),
    )


def test_scan_profile_auto_routes_per_cwe_probe(tmp_path, monkeypatch):
    """When no per_cwe_probe_path is given the constructor must pick the file
    that matches scan_profile so weak/strong probes never cross-contaminate."""
    # Build a binary probe used by both branches.
    bin_path = tmp_path / "probe.npz"
    np.savez_compressed(
        bin_path, w=np.ones(DIM, dtype=np.float32), b=np.float32(0.0),
        layer=np.int32(17),
    )

    # Create both candidate per-CWE files under a fake "data/" sibling.
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    weak = data_dir / "probe_per_cwe.npz"
    strong = data_dir / "probe_strong_per_cwe.npz"
    _make_per_cwe_npz(weak)
    _make_per_cwe_npz(strong)

    # Run the constructor from inside tmp_path so the default relative paths
    # resolve to the fixture files (no real model touched).
    monkeypatch.chdir(tmp_path)

    gf_weak = GemmaForgeFilter(probe_path=str(bin_path), scan_profile="weak-probe")
    assert gf_weak.per_cwe_probe_path.name == "probe_per_cwe.npz"
    assert gf_weak._W_cwe is not None  # was loaded

    gf_strong = GemmaForgeFilter(probe_path=str(bin_path), scan_profile="strong-probe")
    assert gf_strong.per_cwe_probe_path.name == "probe_strong_per_cwe.npz"
    assert gf_strong._W_cwe is not None

    # Explicit path beats scan_profile.
    gf_override = GemmaForgeFilter(
        probe_path=str(bin_path),
        per_cwe_probe_path=str(weak),
        scan_profile="strong-probe",
    )
    assert gf_override.per_cwe_probe_path == weak
