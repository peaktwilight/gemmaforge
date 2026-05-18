"""Data efficiency curve for the GemmaForge layer-17 probe.

Question: how does held-out AUC degrade when we shrink the training set?
This is the kind of plot reviewers ask for when they want to know whether
the probe is sample-limited or representation-limited. CPU-only — replays
cached activations through scikit-learn, no model load.

Two evaluation regimes:
  * random — 80/20 stratified split of the full 1198-row dataset
             (mirrors the shipped probe's "AUC 0.963" headline number).
  * xlang  — train on Python rows, test on the full JavaScript set
             (mirrors the "AUC 0.907 Py->JS" cross-language number).

For each regime we subsample the *training* set at fixed fractions and
fit a fresh ``LogisticRegression(C=1.0)``. Test set never changes within
a regime so AUC comparisons are apples-to-apples. We run 5 seeds per
fraction and report mean + 95% CI (1.96 * SE).

Output: data/data_efficiency.json with one row per fraction, listing the
absolute training count and the random/xlang AUC stats. Pair with
``scripts/plot_data_efficiency.py`` for the rendered curve.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parent.parent
ACTIVATIONS = ROOT / "data" / "activations_v2" / "activations_layer17.npz"
PAIRS = ROOT / "data" / "pairs_v2.jsonl"
OUT_JSON = ROOT / "data" / "data_efficiency.json"

FRACTIONS = (0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00)
SEEDS = (7, 17, 23, 41, 101)
# Same split arithmetic the shipped probe uses (sklearn defaults).
TEST_SIZE = 0.20
# Standard probe knobs — match src/train_probe.py::fit_layer.
LR_C = 1.0
LR_MAX_ITER = 1000


def load_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (X, y, lang) all row-aligned to ``activations_layer17.npz``."""
    if not ACTIVATIONS.exists():
        sys.exit(f"[data-efficiency] missing activations file: {ACTIVATIONS}")
    if not PAIRS.exists():
        sys.exit(f"[data-efficiency] missing pairs file: {PAIRS}")
    npz = np.load(ACTIVATIONS)
    X = np.asarray(npz["X"], dtype=np.float32)
    y = np.asarray(npz["y"], dtype=np.int64)
    with PAIRS.open() as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    if len(rows) != X.shape[0]:
        sys.exit(
            f"[data-efficiency] pairs/activations mismatch: "
            f"pairs={len(rows)} acts={X.shape[0]}"
        )
    lang = np.array([r.get("lang") for r in rows])
    return X, y, lang


def subsample_indices(
    train_idx: np.ndarray,
    y_train: np.ndarray,
    fraction: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Stratified subsample of training indices at the given fraction.

    Keeps the positive-rate roughly constant; tiny fractions can lose a
    class entirely otherwise, which makes LogReg unfittable.
    """
    if fraction >= 1.0:
        return train_idx.copy()
    n_total = len(train_idx)
    n_target = max(2, int(round(n_total * fraction)))
    pos_idx = train_idx[y_train == 1]
    neg_idx = train_idx[y_train == 0]
    pos_frac = len(pos_idx) / n_total
    n_pos = max(1, int(round(n_target * pos_frac)))
    n_neg = max(1, n_target - n_pos)
    n_pos = min(n_pos, len(pos_idx))
    n_neg = min(n_neg, len(neg_idx))
    pick_pos = rng.choice(pos_idx, size=n_pos, replace=False)
    pick_neg = rng.choice(neg_idx, size=n_neg, replace=False)
    return np.concatenate([pick_pos, pick_neg])


def fit_eval(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> tuple[float, float]:
    """Fit C=1.0 LogReg, return (AUC, ACC) on the fixed held-out set."""
    clf = LogisticRegression(C=LR_C, max_iter=LR_MAX_ITER)
    clf.fit(X_train, y_train)
    prob = clf.predict_proba(X_test)[:, 1]
    pred = clf.predict(X_test)
    return float(roc_auc_score(y_test, prob)), float(accuracy_score(y_test, pred))


def ci95(values: list[float]) -> float:
    """95% confidence interval half-width using normal approximation."""
    if len(values) < 2:
        return 0.0
    arr = np.asarray(values, dtype=np.float64)
    se = arr.std(ddof=1) / np.sqrt(len(arr))
    return float(1.96 * se)


def sweep_random(X: np.ndarray, y: np.ndarray) -> list[dict]:
    """Random 80/20 stratified split, subsample TRAIN at each fraction."""
    idx_all = np.arange(len(y))
    # Fix the held-out set once so every fraction shares the same test rows.
    tr_idx, te_idx = train_test_split(
        idx_all, test_size=TEST_SIZE, stratify=y, random_state=7
    )
    X_test, y_test = X[te_idx], y[te_idx]
    y_train_full = y[tr_idx]
    out = []
    for frac in FRACTIONS:
        aucs, accs, ns = [], [], []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            sub = subsample_indices(tr_idx, y_train_full, frac, rng)
            if len(np.unique(y[sub])) < 2:
                # Degenerate (all-one-class) sample — skip; AUC undefined.
                continue
            auc, acc = fit_eval(X[sub], y[sub], X_test, y_test)
            aucs.append(auc)
            accs.append(acc)
            ns.append(len(sub))
        out.append(
            {
                "fraction": frac,
                "n_train": int(round(float(np.mean(ns)))) if ns else 0,
                "auc_mean": float(np.mean(aucs)) if aucs else float("nan"),
                "auc_ci": ci95(aucs),
                "auc_values": aucs,
                "acc_mean": float(np.mean(accs)) if accs else float("nan"),
                "acc_ci": ci95(accs),
                "n_seeds": len(aucs),
            }
        )
        print(
            f"[random] frac={frac:.2f}  n_train={out[-1]['n_train']:4d}  "
            f"AUC={out[-1]['auc_mean']:.3f} +/- {out[-1]['auc_ci']:.3f}",
            file=sys.stderr,
        )
    return out


def sweep_xlang(X: np.ndarray, y: np.ndarray, lang: np.ndarray) -> list[dict]:
    """Cross-language: subsample the Python train set, test on full JS set."""
    py_mask = lang == "python"
    js_mask = lang == "javascript"
    if py_mask.sum() == 0 or js_mask.sum() == 0:
        sys.exit("[data-efficiency] expected python+javascript rows in pairs_v2")
    train_idx = np.where(py_mask)[0]
    test_idx = np.where(js_mask)[0]
    X_test, y_test = X[test_idx], y[test_idx]
    y_train_full = y[train_idx]
    out = []
    for frac in FRACTIONS:
        aucs, accs, ns = [], [], []
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            sub = subsample_indices(train_idx, y_train_full, frac, rng)
            if len(np.unique(y[sub])) < 2:
                continue
            auc, acc = fit_eval(X[sub], y[sub], X_test, y_test)
            aucs.append(auc)
            accs.append(acc)
            ns.append(len(sub))
        out.append(
            {
                "fraction": frac,
                "n_train": int(round(float(np.mean(ns)))) if ns else 0,
                "auc_mean": float(np.mean(aucs)) if aucs else float("nan"),
                "auc_ci": ci95(aucs),
                "auc_values": aucs,
                "acc_mean": float(np.mean(accs)) if accs else float("nan"),
                "acc_ci": ci95(accs),
                "n_seeds": len(aucs),
            }
        )
        print(
            f"[xlang ] frac={frac:.2f}  n_train={out[-1]['n_train']:4d}  "
            f"AUC={out[-1]['auc_mean']:.3f} +/- {out[-1]['auc_ci']:.3f}",
            file=sys.stderr,
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_JSON), help="output json path")
    args = ap.parse_args()

    X, y, lang = load_data()
    print(
        f"[data-efficiency] activations: X={X.shape} y_pos={int(y.sum())}/{len(y)}  "
        f"py={(lang == 'python').sum()} js={(lang == 'javascript').sum()}",
        file=sys.stderr,
    )

    random_rows = sweep_random(X, y)
    xlang_rows = sweep_xlang(X, y, lang)

    # Merge by fraction so consumers get one row per data point.
    by_frac: dict[float, dict] = {}
    for r in random_rows:
        by_frac.setdefault(r["fraction"], {"fraction": r["fraction"]})
        by_frac[r["fraction"]].update(
            {
                "random_n_train": r["n_train"],
                "random_auc_mean": r["auc_mean"],
                "random_auc_ci": r["auc_ci"],
                "random_auc_values": r["auc_values"],
                "random_acc_mean": r["acc_mean"],
                "random_acc_ci": r["acc_ci"],
                "random_n_seeds": r["n_seeds"],
            }
        )
    for r in xlang_rows:
        by_frac.setdefault(r["fraction"], {"fraction": r["fraction"]})
        by_frac[r["fraction"]].update(
            {
                "xlang_n_train": r["n_train"],
                "xlang_auc_mean": r["auc_mean"],
                "xlang_auc_ci": r["auc_ci"],
                "xlang_auc_values": r["auc_values"],
                "xlang_acc_mean": r["acc_mean"],
                "xlang_acc_ci": r["acc_ci"],
                "xlang_n_seeds": r["n_seeds"],
            }
        )

    points = [by_frac[f] for f in sorted(by_frac)]
    payload = {
        "schema_version": 1,
        "model_layer": 17,
        "estimator": "LogisticRegression(C=1.0, max_iter=1000)",
        "test_size": TEST_SIZE,
        "fractions": list(FRACTIONS),
        "seeds": list(SEEDS),
        "random_test_size": int(round(len(y) * TEST_SIZE)),
        "xlang_test_lang": "javascript",
        "xlang_train_lang": "python",
        "points": points,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"[data-efficiency] wrote {out_path.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
