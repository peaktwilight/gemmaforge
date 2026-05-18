"""Re-evaluate the layer-17 LogReg probe on the length-matched subset.

Goal (GitHub issue #22): tell us how much of the probe's headline AUC (0.907
on the Py->JS cross-language split) survives once positives and negatives
have matched character lengths. Reads:

  - data/activations_v2/activations_layer17.npz  (row-aligned to pairs.jsonl)
  - data/pairs_length_matched.jsonl              (subset emitted by
                                                  build_length_matched_eval.py)

Reports four AUC numbers:

  1. Probe AUC on the full length-matched subset
     (LogReg trained on the full set, evaluated on the matched rows -- mirrors
      the shipped probe usage; we use the same 80/20 stratified split as
      `src/train_probe.py` so the test fold is paired and we never train on
      a row we score).
  2. Length-baseline AUC on the same matched subset
     (raw character length used as the only feature -- by construction this
      should be approximately 0.50 if matching worked).
  3. Probe AUC on the Py->JS slice within the matched set
     (train on the matched Python rows, evaluate on matched JS rows).
  4. Length baseline on the same Py->JS slice.

Constraints: sklearn + numpy only. No transformers, no torch (we never
re-forward Gemma; cached activations are sufficient).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
ACTS = ROOT / "data" / "activations_v2" / "activations_layer17.npz"
PAIRS = ROOT / "data" / "pairs.jsonl"
MATCHED = ROOT / "data" / "pairs_length_matched.jsonl"
OUT = ROOT / "data" / "eval_length_matched.json"
LAYER = 17
SEED = 7


def load_full() -> tuple[np.ndarray, np.ndarray, list[dict]]:
    npz = np.load(ACTS)
    X, y = npz["X"], npz["y"].astype(int)
    rows = [json.loads(line) for line in PAIRS.read_text().splitlines() if line.strip()]
    if len(rows) != len(X):
        raise SystemExit(f"row count mismatch: jsonl={len(rows)} npz={len(X)}")
    return X, y, rows


def load_matched_indices() -> list[int]:
    idx = []
    for line in MATCHED.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        idx.append(int(r["_orig_idx"]))
    return sorted(idx)


def char_lens(rows: list[dict], idx: np.ndarray) -> np.ndarray:
    return np.array([len(rows[i]["code"]) for i in idx], dtype=np.float64)


def fit_probe_and_eval(
    X: np.ndarray, y: np.ndarray, tr_idx: np.ndarray, te_idx: np.ndarray
) -> tuple[float, np.ndarray]:
    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(X[tr_idx], y[tr_idx])
    prob = clf.predict_proba(X[te_idx])[:, 1]
    return float(roc_auc_score(y[te_idx], prob)), prob


def length_auc(rows: list[dict], idx: np.ndarray, y_full: np.ndarray) -> float:
    if len(np.unique(y_full[idx])) < 2:
        return float("nan")
    lens = char_lens(rows, idx)
    # raw length as a score for the positive class
    return float(roc_auc_score(y_full[idx], lens))


def main() -> None:
    X, y, rows = load_full()
    print(f"loaded X={X.shape}  y_pos={int(y.sum())}  rows={len(rows)}")

    matched_idx = np.array(load_matched_indices(), dtype=int)
    print(f"length-matched rows: {len(matched_idx)}")

    lang_arr = np.array([r["lang"] for r in rows])
    per_lang = {
        lang: int((lang_arr[matched_idx] == lang).sum() // 2)
        for lang in sorted(set(lang_arr[matched_idx].tolist()))
    }
    print(f"per-language pair counts: {per_lang}")

    # ---- (1) probe AUC on the length-matched subset --------------------
    # Stratified 80/20 train/test split *within* the matched subset, fit the
    # probe on the train fold, score the held-out fold. This mirrors the
    # within-language eval methodology used elsewhere in the repo while
    # keeping every scored row inside the length-controlled subset.
    y_m = y[matched_idx]
    tr_local, te_local = train_test_split(
        np.arange(len(matched_idx)), test_size=0.2, stratify=y_m, random_state=SEED
    )
    tr_idx = matched_idx[tr_local]
    te_idx = matched_idx[te_local]
    probe_auc, _ = fit_probe_and_eval(X, y, tr_idx, te_idx)
    length_baseline_auc = length_auc(rows, te_idx, y)
    delta = probe_auc - length_baseline_auc
    print(
        f"\nLength-matched subset: probe AUC = {probe_auc:.3f}  "
        f"length-only AUC = {length_baseline_auc:.3f}  "
        f"delta = {delta:+.3f}"
    )

    # ---- (2) Py -> JS within the matched set ---------------------------
    py_idx = matched_idx[lang_arr[matched_idx] == "python"]
    js_idx = matched_idx[lang_arr[matched_idx] == "javascript"]
    print(f"Py rows: {len(py_idx)}  JS rows: {len(js_idx)}")

    py_to_js_probe_auc, _ = fit_probe_and_eval(X, y, py_idx, js_idx)
    py_to_js_length_auc = length_auc(rows, js_idx, y)
    py_to_js_delta = py_to_js_probe_auc - py_to_js_length_auc
    print(
        f"Py->JS (matched): probe AUC = {py_to_js_probe_auc:.3f}  "
        f"length-only AUC = {py_to_js_length_auc:.3f}  "
        f"delta = {py_to_js_delta:+.3f}"
    )

    out = {
        "n_pairs_kept": int(len(matched_idx) // 2),
        "n_per_lang": per_lang,
        "probe_auc": probe_auc,
        "length_baseline_auc": length_baseline_auc,
        "delta": delta,
        "py_to_js_probe_auc": py_to_js_probe_auc,
        "py_to_js_length_auc": py_to_js_length_auc,
        "py_to_js_delta": py_to_js_delta,
        "layer": LAYER,
        "n_train_within_matched": int(len(tr_idx)),
        "n_test_within_matched": int(len(te_idx)),
        "source_activations": str(ACTS.relative_to(ROOT)),
        "source_matched_pairs": str(MATCHED.relative_to(ROOT)),
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
