"""Probe ensemble experiment: combine per-layer LogReg probes via four
ensembling strategies and report whether any beats the single-best layer.

We already know from data/probe_card.json (pairs_v2 / activations_v2) that
layer 17 is the strongest single layer (AUC 0.963). A prior attempt to
concatenate layer activations into one giant feature vector lost to solo
layer 17. This script tries the orthogonal idea: keep four *separate*
probes and combine their *probabilities* on the held-out test set.

Pipeline:
  1) Load activations for layers 8, 17, 26, 34.
  2) Stratified 80/20 split with random_state=7 (the SAME indices for every
     layer — they share the same y, so the same shuffle aligns rows).
  3) Train LogisticRegression(C=1.0, max_iter=1000) per layer.
  4) On the test set, gather per-layer predicted probabilities p_i.
  5) Compute four ensembles:
       - uniform_mean : mean(p_i)
       - auc_weighted : sum(w_i * p_i) with w_i = train-AUC_i / sum(train-AUCs)
       - max          : max(p_i)
       - soft_vote    : sum_i [p_i >= 0.5] / 4   (vote count, normalized)
  6) Report AUC + ACC for each ensemble and for the single-best layer.
  7) Write data/probe_ensemble.json with one row per method.
  8) If any ensemble beats single-best by >= 0.005 AUC, save the four
     LogReg weights + the ensemble weight vector to data/probe_ensemble.npz.

sklearn + numpy only. Does not touch data/probe.npz, src/eval/*, WRITEUP.md,
README.md, or RESULTS.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
ACT_DIR = ROOT / "data" / "activations_v2"
OUT_JSON = ROOT / "data" / "probe_ensemble.json"
OUT_NPZ = ROOT / "data" / "probe_ensemble.npz"

LAYERS = [8, 17, 26, 34]
SEED = 7
SINGLE_BEST_LAYER = 17
BEAT_THRESHOLD = 0.005  # required AUC delta to "win"


def _load_layer(layer: int):
    npz = np.load(ACT_DIR / f"activations_layer{layer:02d}.npz")
    return npz["X"].astype(np.float32), npz["y"].astype(np.int8)


def _split_indices(n: int, y: np.ndarray, seed: int):
    """Stratified 80/20 split returning the train/test index arrays."""
    idx = np.arange(n)
    tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=seed)
    return tr, te


def main():
    # ----------- load + sanity-check that y is identical across layers -----------
    layer_data = {}
    y_ref = None
    for L in LAYERS:
        X, y = _load_layer(L)
        if y_ref is None:
            y_ref = y
        else:
            assert np.array_equal(y, y_ref), (
                f"label vector mismatch at layer {L}; "
                "ensemble assumes rows are aligned across all layer files."
            )
        layer_data[L] = X
    n = y_ref.shape[0]
    print(f"loaded {len(LAYERS)} layers; n_rows={n}  n_pos={int(y_ref.sum())}")

    # ----------- shared split -----------
    tr_idx, te_idx = _split_indices(n, y_ref, SEED)
    y_tr, y_te = y_ref[tr_idx], y_ref[te_idx]
    print(f"split: n_train={len(tr_idx)}  n_test={len(te_idx)}  seed={SEED}")

    # ----------- train one LogReg per layer; collect train + test probas -----------
    clfs = {}
    train_aucs = {}
    test_probas = {}
    test_aucs = {}
    test_accs = {}

    print(f"\n{'layer':>5s}  {'train_auc':>9s}  {'test_auc':>8s}  {'test_acc':>8s}")
    print("-" * 40)
    for L in LAYERS:
        X = layer_data[L]
        X_tr, X_te = X[tr_idx], X[te_idx]

        clf = LogisticRegression(max_iter=1000, C=1.0)
        clf.fit(X_tr, y_tr)

        p_tr = clf.predict_proba(X_tr)[:, 1]
        p_te = clf.predict_proba(X_te)[:, 1]

        a_tr = float(roc_auc_score(y_tr, p_tr))
        a_te = float(roc_auc_score(y_te, p_te))
        acc_te = float(accuracy_score(y_te, (p_te >= 0.5).astype(np.int8)))

        clfs[L] = clf
        train_aucs[L] = a_tr
        test_probas[L] = p_te
        test_aucs[L] = a_te
        test_accs[L] = acc_te
        print(f"{L:>5d}  {a_tr:9.4f}  {a_te:8.4f}  {acc_te:8.4f}")

    # ----------- single-best baseline (layer 17 on THIS split) -----------
    single_auc = test_aucs[SINGLE_BEST_LAYER]
    single_acc = test_accs[SINGLE_BEST_LAYER]

    # ----------- build the four ensembles -----------
    P = np.stack([test_probas[L] for L in LAYERS], axis=0)  # (K, n_test)

    # uniform mean
    p_uniform = P.mean(axis=0)
    w_uniform = np.full(len(LAYERS), 1.0 / len(LAYERS), dtype=np.float64)

    # AUC-weighted (use TRAIN auc to avoid leaking test labels into weights)
    raw_w = np.array([train_aucs[L] for L in LAYERS], dtype=np.float64)
    w_auc = raw_w / raw_w.sum()
    p_auc = (w_auc[:, None] * P).sum(axis=0)

    # max
    p_max = P.max(axis=0)

    # soft vote: count how many probes vote "1" at threshold 0.5, normalize to [0,1]
    votes = (P >= 0.5).astype(np.float64).sum(axis=0)
    p_vote = votes / len(LAYERS)

    def _score(p):
        auc = float(roc_auc_score(y_te, p))
        acc = float(accuracy_score(y_te, (p >= 0.5).astype(np.int8)))
        return auc, acc

    ens_results = [
        ("uniform_mean", *_score(p_uniform)),
        ("auc_weighted", *_score(p_auc)),
        ("max", *_score(p_max)),
        ("soft_vote", *_score(p_vote)),
    ]

    # ----------- report -----------
    print(f"\n{'method':>14s}  {'AUC':>6s}  {'ACC':>6s}  {'dAUC vs L17':>11s}")
    print("-" * 48)
    print(f"{'single_best_L17':>14s}  {single_auc:6.4f}  {single_acc:6.4f}  {'(baseline)':>11s}")
    rows = [
        {"method": "single_best_L17", "auc": single_auc, "acc": single_acc}
    ]
    best = ("single_best_L17", single_auc, single_acc)
    best_ens_name = None
    for name, auc, acc in ens_results:
        d = auc - single_auc
        flag = "*" if d >= BEAT_THRESHOLD else " "
        print(f"{name:>14s}  {auc:6.4f}  {acc:6.4f}  {d:+11.4f} {flag}")
        rows.append({"method": name, "auc": auc, "acc": acc})
        if auc > best[1]:
            best = (name, auc, acc)
            if name != "single_best_L17":
                best_ens_name = name

    # ----------- persist results -----------
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "layers": LAYERS,
        "split": "stratified 80/20",
        "random_state": SEED,
        "single_best_layer": SINGLE_BEST_LAYER,
        "per_layer_train_auc": {str(L): train_aucs[L] for L in LAYERS},
        "per_layer_test_auc": {str(L): test_aucs[L] for L in LAYERS},
        "per_layer_test_acc": {str(L): test_accs[L] for L in LAYERS},
        "ensemble_weights": {
            "uniform_mean": w_uniform.tolist(),
            "auc_weighted": w_auc.tolist(),
            # max and soft_vote are non-linear, no per-layer weight vector.
        },
        "results": rows,
        "best_method": best[0],
        "beat_threshold": BEAT_THRESHOLD,
        "ensemble_beats_single": any(
            r["method"] != "single_best_L17" and (r["auc"] - single_auc) >= BEAT_THRESHOLD
            for r in rows
        ),
        "model": "LogisticRegression(max_iter=1000, C=1.0)",
        "dataset": "pairs_v2 / activations_v2",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    print(f"\nsaved card: {OUT_JSON}")

    # ----------- save weights only if an ensemble wins -----------
    winning_methods = [
        r["method"] for r in rows
        if r["method"] != "single_best_L17"
        and (r["auc"] - single_auc) >= BEAT_THRESHOLD
    ]
    if winning_methods:
        # Stack each per-layer LogReg's coef + intercept into matrices we can
        # reload without sklearn: y_hat = sigmoid(W[i] @ x + b[i]).
        dims = layer_data[LAYERS[0]].shape[1]
        W = np.zeros((len(LAYERS), dims), dtype=np.float32)
        bvec = np.zeros((len(LAYERS),), dtype=np.float32)
        for i, L in enumerate(LAYERS):
            W[i] = clfs[L].coef_.astype(np.float32).ravel()
            bvec[i] = float(clfs[L].intercept_[0])
        np.savez(
            OUT_NPZ,
            layers=np.array(LAYERS, dtype=np.int32),
            W=W,
            b=bvec,
            w_uniform=w_uniform.astype(np.float32),
            w_auc=w_auc.astype(np.float32),
            winning_methods=np.array(winning_methods),
        )
        print(f"saved weights: {OUT_NPZ}  (winning methods: {winning_methods})")
    else:
        print(
            "no ensemble beat single-best layer 17 by >= "
            f"{BEAT_THRESHOLD} AUC — not saving weights."
        )


if __name__ == "__main__":
    main()
