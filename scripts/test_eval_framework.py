"""Smoke test for src/eval/. Self-contained: invents a synthetic dataset,
fits a probe, runs every split, and asserts the output shape.

Run:
    uv run python scripts/test_eval_framework.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import math

import numpy as np

from src.eval import baselines as bl_mod
from src.eval import probe_io
from src.eval.metrics import (
    bootstrap_auc_ci,
    calibration_metrics,
    compute_clf_metrics,
    reliability_curve,
)
from src.eval.protocol import evaluate_split, full_report
from src.eval.splits import make_splits


def _make_synthetic(n: int = 200, dim: int = 32, seed: int = 7):
    rng = np.random.default_rng(seed)
    y = np.tile([0, 1], n // 2).astype(np.int8)
    # Make positives separable from negatives via a planted direction.
    direction = rng.normal(size=dim).astype(np.float32)
    X = rng.normal(size=(n, dim)).astype(np.float32)
    X[y == 1] += 1.5 * direction
    # Pair each positive with a negative in the same fake repo + lang + source.
    rows: list[dict] = []
    for i in range(n):
        repo = f"repo_{i // 2}"
        lang = ["python", "javascript", "c"][i % 3]
        cwe = ["CWE-78", "CWE-89", "CWE-22"][(i // 2) % 3]
        rows.append({
            "label": int(y[i]),
            "code": ("eval(x)" if y[i] == 1 else "x = parse(input)") + " " + "x" * (50 + (i % 30)),
            "cwe": cwe if y[i] == 1 else None,
            "lang": lang,
            "source": "synthetic-pos" if y[i] == 1 else "synthetic-neg",
            "_origin_repo": repo,
        })
    return X, y, rows


def test_metrics() -> None:
    rng = np.random.default_rng(0)
    n = 200
    y = (rng.random(n) > 0.5).astype(int)
    probs = np.clip(y + rng.normal(0, 0.4, size=n), 0, 1)
    preds = (probs >= 0.5).astype(int)
    m = compute_clf_metrics(preds, y, probs)
    assert 0 <= m.accuracy <= 1
    assert 0 <= m.f1 <= 1
    assert 0 <= m.auc <= 1
    assert "recall_at_fpr_0.10" in m.recall_at_fpr
    pt, lo, hi = bootstrap_auc_ci(y, probs, n_iter=200)
    assert lo <= pt <= hi
    cal = calibration_metrics(y, probs)
    assert 0 <= cal["brier"] <= 1
    assert 0 <= cal["ece"] <= 1
    centers, acc, count = reliability_curve(y, probs, n_bins=10)
    assert len(centers) == len(acc) == len(count) == 10
    print("  metrics OK")


def test_splits() -> None:
    X, y, rows = _make_synthetic(n=120)
    sp_list = make_splits(rows, y)
    names = [s.name for s in sp_list]
    assert "random_stratified" in names
    assert "group_repo" in names
    assert any(n.startswith("heldout_cwe::") for n in names)
    assert any(n.startswith("heldout_lang::") for n in names)
    # Group split: no repo appears in both train and test.
    gs = next(s for s in sp_list if s.name == "group_repo")
    tr_repos = {rows[i]["_origin_repo"] for i in gs.train_idx.tolist()}
    te_repos = {rows[i]["_origin_repo"] for i in gs.test_idx.tolist()}
    assert tr_repos.isdisjoint(te_repos), "group_repo leaked a repo"
    print("  splits OK")


def test_baselines() -> None:
    _, _, rows = _make_synthetic(n=60)
    for bl in bl_mod.all_baselines():
        scores = bl.score(rows)
        assert scores.shape == (60,)
        assert (scores >= 0).all() and (scores <= 1).all(), f"{bl.name} out-of-range"
    print("  baselines OK")


def test_protocol_smoke() -> None:
    X, y, rows = _make_synthetic(n=200)
    rep = full_report(
        X, y, rows,
        activations_path="<synthetic>",
        pairs_path="<synthetic>",
        layer=0,
        refit=True,
        baselines=bl_mod.all_baselines(),
    )
    assert rep.n_examples == 200
    # Random split AUC on the planted-direction setup should be well above 0.5.
    rs = next(s for s in rep.splits if s.split_name == "random_stratified")
    assert not math.isnan(rs.auc)
    assert rs.auc > 0.7, f"sanity AUC too low: {rs.auc:.3f}"
    # Baselines populated.
    assert "random" in rs.baseline_aucs
    assert "regex" in rs.baseline_aucs
    print(f"  protocol OK (random_stratified AUC={rs.auc:.3f})")


def main() -> int:
    print("eval framework smoke tests:")
    test_metrics()
    test_splits()
    test_baselines()
    test_protocol_smoke()
    print("all passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
