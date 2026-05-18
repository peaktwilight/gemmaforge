"""MLP-per-layer ensemble probe with cross-language evaluation.

Stacks two known-good improvements at once:
  - MLPClassifier(128, 64) per layer instead of LogisticRegression.
  - Uniform-mean ensemble across layers {8, 17, 26, 34}.

Each improvement helps alone (RESULTS.md): MLP(128,64) on layer 17 lifts
Py->JS from 0.907 to 0.919, and a linear ensemble on a random-stratified
split goes from 0.963 to 0.9764. This script asks whether stacking the two
compounds, trades off, or plateaus.

We report three splits:
  - random_stratified: 80/20 stratified by label, mixes both languages
    (sanity check that matches the linear ensemble methodology).
  - py->js: train on Python rows only, evaluate on all JavaScript rows.
  - js->py: train on JavaScript rows only, evaluate on all Python rows.

For each split we report:
  - per-layer MLP AUC/ACC,
  - uniform-mean ensemble AUC/ACC.

Output: data/probe_mlp_ensemble_xlang.json

Constraints (per task brief):
  - sklearn only, no torch.
  - Read-only on data/probe.npz, src/eval/*, WRITEUP.md, README.md,
    RESULTS.md.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

ROOT = Path(__file__).resolve().parents[1]
ACT_DIR = ROOT / "data" / "activations_v2"
PAIRS = ROOT / "data" / "pairs.jsonl"
OUT_JSON = ROOT / "data" / "probe_mlp_ensemble_xlang.json"

LAYERS = [8, 17, 26, 34]
SEED = 7

# MLP hyperparams fixed by the task brief.
MLP_KWARGS = dict(
    hidden_layer_sizes=(128, 64),
    alpha=1e-3,
    max_iter=300,
    random_state=SEED,
)


def _load_layer(layer: int) -> tuple[np.ndarray, np.ndarray]:
    npz = np.load(ACT_DIR / f"activations_layer{layer:02d}.npz")
    return npz["X"].astype(np.float32), npz["y"].astype(np.int64)


def _load_langs(n_expected: int) -> np.ndarray:
    langs: list[str] = []
    with PAIRS.open() as f:
        for line in f:
            langs.append(json.loads(line)["lang"])
    if len(langs) != n_expected:
        raise ValueError(
            f"pairs.jsonl has {len(langs)} rows but activations have {n_expected}"
        )
    return np.array(langs)


def _score(y_true: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    auc = float(roc_auc_score(y_true, p))
    acc = float(accuracy_score(y_true, (p >= 0.5).astype(np.int8)))
    return auc, acc


def _run_split(
    layer_X: dict[int, np.ndarray],
    y: np.ndarray,
    tr_idx: np.ndarray,
    te_idx: np.ndarray,
    split_name: str,
) -> dict:
    """Train one MLP per layer on tr_idx, evaluate on te_idx, ensemble."""
    y_tr, y_te = y[tr_idx], y[te_idx]
    per_layer: dict[str, dict] = {}
    probas: list[np.ndarray] = []

    print(
        f"\n[{split_name}] n_train={len(tr_idx)}  n_test={len(te_idx)}  "
        f"pos_train={int(y_tr.sum())}  pos_test={int(y_te.sum())}",
        file=sys.stderr,
    )
    print(f"{'layer':>5s}  {'AUC':>6s}  {'ACC':>6s}  {'fit_s':>6s}", file=sys.stderr)

    for L in LAYERS:
        X = layer_X[L]
        X_tr, X_te = X[tr_idx], X[te_idx]
        clf = MLPClassifier(**MLP_KWARGS)
        t0 = time.time()
        clf.fit(X_tr, y_tr)
        dt = time.time() - t0
        p_te = clf.predict_proba(X_te)[:, 1]
        auc, acc = _score(y_te, p_te)
        per_layer[str(L)] = {"auc": auc, "acc": acc, "fit_sec": dt}
        probas.append(p_te)
        print(f"{L:>5d}  {auc:6.4f}  {acc:6.4f}  {dt:6.1f}", file=sys.stderr)

    # Uniform-mean ensemble.
    P = np.stack(probas, axis=0)  # (K, n_test)
    p_mean = P.mean(axis=0)
    ens_auc, ens_acc = _score(y_te, p_mean)
    print(
        f"  ENS  {ens_auc:6.4f}  {ens_acc:6.4f}   (uniform mean)",
        file=sys.stderr,
    )

    return {
        "split": split_name,
        "n_train": int(len(tr_idx)),
        "n_test": int(len(te_idx)),
        "pos_train": int(y_tr.sum()),
        "pos_test": int(y_te.sum()),
        "per_layer": per_layer,
        "ensemble_uniform_mean": {"auc": ens_auc, "acc": ens_acc},
    }


def main() -> None:
    # ---- load activations, sanity-check row alignment ----
    layer_X: dict[int, np.ndarray] = {}
    y_ref: np.ndarray | None = None
    for L in LAYERS:
        X, y = _load_layer(L)
        if y_ref is None:
            y_ref = y
        else:
            assert np.array_equal(y, y_ref), (
                f"label vector mismatch at layer {L}; activations not row-aligned."
            )
        layer_X[L] = X
    assert y_ref is not None
    n = y_ref.shape[0]
    langs = _load_langs(n)
    print(
        f"[mlp-ensemble] layers={LAYERS}  n_rows={n}  "
        f"py={int((langs == 'python').sum())}  "
        f"js={int((langs == 'javascript').sum())}",
        file=sys.stderr,
    )

    # ---- build three splits (as row-index arrays) ----
    all_idx = np.arange(n)

    # random stratified 80/20 by label
    tr_rand, te_rand = train_test_split(
        all_idx, test_size=0.2, stratify=y_ref, random_state=SEED
    )

    py_mask = langs == "python"
    js_mask = langs == "javascript"
    py_idx = all_idx[py_mask]
    js_idx = all_idx[js_mask]

    splits = {
        "random_stratified": (tr_rand, te_rand),
        "py_to_js": (py_idx, js_idx),
        "js_to_py": (js_idx, py_idx),
    }

    # ---- run each split ----
    split_results: list[dict] = []
    for name, (tr, te) in splits.items():
        split_results.append(_run_split(layer_X, y_ref, tr, te, name))

    # ---- payload ----
    payload = {
        "model": "MLPClassifier(hidden_layer_sizes=(128,64), alpha=1e-3, max_iter=300, random_state=7)",
        "ensemble": "uniform_mean over layers {8, 17, 26, 34}",
        "layers": LAYERS,
        "seed": SEED,
        "dataset": "pairs_v2 / activations_v2",
        "n_rows": int(n),
        "n_python": int(py_mask.sum()),
        "n_javascript": int(js_mask.sum()),
        "splits": split_results,
        "baselines_from_results_md": {
            "linear_single_L17_py_to_js_auc": 0.907,
            "linear_ensemble_random_stratified_auc": 0.9764,
            "mlp_128_64_single_L17_py_to_js_auc": 0.919,
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    print(f"\n[mlp-ensemble] wrote {OUT_JSON}", file=sys.stderr)

    # ---- markdown summary ----
    print()
    print("| Split | Per-layer best AUC | Ensemble AUC |")
    print("|---|---:|---:|")
    for sr in split_results:
        best_layer_auc = max(v["auc"] for v in sr["per_layer"].values())
        ens_auc = sr["ensemble_uniform_mean"]["auc"]
        print(f"| {sr['split']} | {best_layer_auc:.4f} | {ens_auc:.4f} |")


if __name__ == "__main__":
    main()
