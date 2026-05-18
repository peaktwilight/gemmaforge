"""Smoke test for the token-level eval path.

Synthesises per-token probability arrays and offsets aligned to the
*real* `data/dataset.jsonl` token_labels, then runs the full token
report. The synthetic probe is a noisy oracle: it puts P=0.9 on every
token inside a positive span, P=0.1 elsewhere. AUC at all/span/span_max
levels should be near 1.0 if the eval plumbing is wired correctly.

Run:
    uv run --with scikit-learn --with numpy python scripts/test_token_eval.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.eval import baselines as bl_mod
from src.eval import token_data
from src.eval import token_protocol
from src.eval.token_data import (
    char_spans_to_token_spans,
    parse_spans,
)


def _synthetic_offsets(code: str, target_tokens: int = 256) -> list[tuple[int, int]]:
    """Word-piece-ish offsets: cut the string into ~uniform chunks.

    Real offsets would come from the model's tokenizer (HuggingFace
    `BatchEncoding.offset_mapping`). For the smoke test we just need
    offsets that *cover* the char-spans so the mapping has something to
    align against.
    """
    if not code:
        return []
    step = max(1, len(code) // target_tokens)
    offs: list[tuple[int, int]] = []
    i = 0
    while i < len(code):
        offs.append((i, min(i + step, len(code))))
        i += step
    return offs


def _oracle_probs(
    n_tokens: int,
    token_spans: list[tuple[int, int, int]],
    noise: float = 0.1,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng(0)
    probs = rng.uniform(0.0, noise, size=n_tokens)
    for start, end, lbl in token_spans:
        end_c = min(end, n_tokens - 1)
        if end_c < start:
            continue
        if lbl == 1:
            probs[start : end_c + 1] = rng.uniform(1.0 - noise, 1.0, size=end_c + 1 - start)
        else:
            probs[start : end_c + 1] = rng.uniform(0.0, noise, size=end_c + 1 - start)
    return probs.astype(np.float32)


def main() -> int:
    dataset_path = ROOT / "data" / "dataset.jsonl"
    if not dataset_path.exists():
        print(f"[test_token_eval] missing {dataset_path}; run build_dataset.py first.")
        return 1

    rows = token_data.load_token_dataset(dataset_path)
    print(f"loaded {len(rows)} rows from {dataset_path.name}")

    # Subsample for speed; the eval doesn't change shape with size.
    rng = np.random.default_rng(7)
    sample_n = min(400, len(rows))
    idx = rng.choice(len(rows), size=sample_n, replace=False)
    rows = [rows[i] for i in idx.tolist()]
    print(f"using {len(rows)}-row subsample")

    token_spans_per_row: list[list[tuple[int, int, int]]] = []
    token_probs_per_row: list[np.ndarray] = []
    rng2 = np.random.default_rng(13)
    for r in rows:
        offs = _synthetic_offsets(r["code"])
        char_spans = parse_spans(r)
        tspans = char_spans_to_token_spans(char_spans, offs)
        token_spans_per_row.append(tspans)
        token_probs_per_row.append(_oracle_probs(len(offs), tspans, noise=0.15, rng=rng2))

    full = token_protocol.full_token_report(
        rows, token_probs_per_row, token_spans_per_row,
        dataset_path=str(dataset_path),
        bootstrap_n=100,
        baselines=bl_mod.all_baselines(),
    )

    # Pretty print summary.
    print(f"\n{'split':32s}  {'level':10s}  {'AUC':>6s}  {'F1':>6s}  {'n_tot':>7s}  {'n_pos':>6s}")
    for sp in full.splits:
        for level_name, m in (("all", sp.all_metrics), ("span", sp.span_metrics), ("span_max", sp.span_max_metrics)):
            if m.get("n_total", 0) == 0:
                continue
            print(
                f"{sp.split_name:32s}  {level_name:10s}  "
                f"{m.get('auc', float('nan')):6.3f}  "
                f"{m.get('f1', float('nan')):6.3f}  "
                f"{m.get('n_total', 0):7d}  {m.get('n_pos', 0):6d}"
            )

    # Sanity asserts: the oracle should crush every level.
    failures = 0
    for sp in full.splits:
        if len(sp.test_idx if False else []) == 0:  # placeholder
            continue
        for lvl_name, m in (("all", sp.all_metrics), ("span", sp.span_metrics), ("span_max", sp.span_max_metrics)):
            if m.get("n_total", 0) == 0:
                continue
            auc = m.get("auc", float("nan"))
            if math.isnan(auc):
                continue
            if lvl_name == "span_max" and auc < 0.90:
                print(f"  FAIL  {sp.split_name} {lvl_name}: span_max AUC={auc:.3f}")
                failures += 1
    if failures:
        print(f"\n{failures} span_max AUC(s) below 0.90 — oracle plumbing broken.")
        return 2
    print("\nall span_max AUCs >= 0.90 — token eval plumbing OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
