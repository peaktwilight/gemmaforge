"""Cross-language ensemble evaluation: does the per-layer LogReg ensemble
that won the random split also lift the Python<->JavaScript transfer?

Context:
  - We already showed that a uniform-mean ensemble of layers {8,17,26,34}
    LogReg probes hits AUC=0.9764 under the random stratified split, beating
    single-layer 17 (AUC=0.9633). See `scripts/train_probe_ensemble.py` and
    `data/probe_ensemble.json`.
  - The baseline `scripts/eval_splits.py` already showed that the
    *single-layer-17* probe gets AUC=0.907 when trained on Python rows and
    tested on JavaScript rows (heldout_lang test=javascript). The mirror
    direction (train JS, test Py) is also reported there.
  - Open question: does the same ensemble lift hold under language transfer,
    or is it specific to in-distribution variance reduction?

Pipeline:
  1) Load activations for layers 8, 17, 26, 34 (rows aligned with
     data/pairs.jsonl).
  2) Read pairs.jsonl, grab the `lang` field per row.
  3) For each direction (train_lang -> test_lang):
       - Train one LogisticRegression(C=1.0, max_iter=1000) per layer on
         train_lang rows only.
       - Score per-layer test AUC on test_lang rows.
       - Build the uniform-mean ensemble over the 4 per-layer test
         probabilities and score its AUC.
       - Record `lift = ensemble_auc - max(per_layer_auc)` (the honest
         "did the ensemble beat the best single layer in *this* setting?"
         delta, which is what matters when we don't get to pick the single-
         best layer with test labels).
  4) Write data/probe_ensemble_cross_lang.json with both directions.

Constraints:
  - sklearn + numpy only.
  - Does NOT touch data/probe.npz, data/probe_ensemble.npz, src/eval/*,
    WRITEUP.md, README.md, or RESULTS.md.
  - Does NOT spawn subagents.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
ACT_DIR = ROOT / "data" / "activations_v2"
PAIRS = ROOT / "data" / "pairs.jsonl"
OUT_JSON = ROOT / "data" / "probe_ensemble_cross_lang.json"

LAYERS = [8, 17, 26, 34]


def _load_layer(layer: int) -> tuple[np.ndarray, np.ndarray]:
    npz = np.load(ACT_DIR / f"activations_layer{layer:02d}.npz")
    return npz["X"].astype(np.float32), npz["y"].astype(np.int8)


def _load_langs(n_rows: int) -> np.ndarray:
    rows = [json.loads(line) for line in PAIRS.read_text().splitlines() if line.strip()]
    if len(rows) != n_rows:
        raise SystemExit(
            f"row count mismatch: pairs.jsonl={len(rows)} activations={n_rows}"
        )
    return np.array([r["lang"] for r in rows], dtype=object)


def _eval_direction(
    layer_data: dict[int, np.ndarray],
    y: np.ndarray,
    lang: np.ndarray,
    train_lang: str,
    test_lang: str,
) -> dict:
    tr_idx = np.where(lang == train_lang)[0]
    te_idx = np.where(lang == test_lang)[0]
    y_tr, y_te = y[tr_idx], y[te_idx]

    if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
        raise SystemExit(
            f"single-class partition for {train_lang}->{test_lang}; "
            "cannot compute AUC"
        )

    per_layer_auc: dict[str, float] = {}
    per_layer_acc: dict[str, float] = {}
    test_probas: list[np.ndarray] = []

    print(
        f"\n[{train_lang} -> {test_lang}] n_train={len(tr_idx)} "
        f"n_test={len(te_idx)} pos_train={int(y_tr.sum())} "
        f"pos_test={int(y_te.sum())}"
    )
    print(f"{'layer':>5s}  {'auc':>7s}  {'acc':>7s}")
    print("-" * 24)
    for L in LAYERS:
        X = layer_data[L]
        clf = LogisticRegression(max_iter=1000, C=1.0)
        clf.fit(X[tr_idx], y_tr)
        p_te = clf.predict_proba(X[te_idx])[:, 1]
        auc = float(roc_auc_score(y_te, p_te))
        acc = float(accuracy_score(y_te, (p_te >= 0.5).astype(np.int8)))
        per_layer_auc[str(L)] = auc
        per_layer_acc[str(L)] = acc
        test_probas.append(p_te)
        print(f"{L:>5d}  {auc:7.4f}  {acc:7.4f}")

    P = np.stack(test_probas, axis=0)  # (K, n_test)
    p_uniform = P.mean(axis=0)
    ens_auc = float(roc_auc_score(y_te, p_uniform))
    ens_acc = float(accuracy_score(y_te, (p_uniform >= 0.5).astype(np.int8)))

    best_layer = max(per_layer_auc, key=per_layer_auc.get)
    best_auc = per_layer_auc[best_layer]
    lift = ens_auc - best_auc

    print(f"  ens  {ens_auc:7.4f}  {ens_acc:7.4f}   "
          f"(best single = L{best_layer} @ {best_auc:.4f}, lift = {lift:+.4f})")

    return {
        "train_lang": train_lang,
        "test_lang": test_lang,
        "n_train": int(len(tr_idx)),
        "n_test": int(len(te_idx)),
        "n_train_pos": int(y_tr.sum()),
        "n_test_pos": int(y_te.sum()),
        "per_layer_auc": per_layer_auc,
        "per_layer_acc": per_layer_acc,
        "ensemble_auc": ens_auc,
        "ensemble_acc": ens_acc,
        "best_single_layer": int(best_layer),
        "best_single_auc": best_auc,
        "lift": lift,
    }


def main() -> None:
    layer_data: dict[int, np.ndarray] = {}
    y_ref: np.ndarray | None = None
    for L in LAYERS:
        X, y = _load_layer(L)
        if y_ref is None:
            y_ref = y
        else:
            if not np.array_equal(y, y_ref):
                raise SystemExit(
                    f"label vector mismatch at layer {L}; cross-lang split "
                    "assumes rows align across layer files."
                )
        layer_data[L] = X
    assert y_ref is not None

    lang = _load_langs(y_ref.shape[0])
    uniq = sorted({str(l) for l in lang.tolist()})
    print(f"loaded n_rows={y_ref.shape[0]}  langs={uniq}")

    if not {"python", "javascript"}.issubset(uniq):
        raise SystemExit(f"need both python and javascript in lang field; got {uniq}")

    directions = [("python", "javascript"), ("javascript", "python")]
    out = []
    for train_lang, test_lang in directions:
        out.append(
            _eval_direction(layer_data, y_ref, lang, train_lang, test_lang)
        )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "layers": LAYERS,
        "model": "LogisticRegression(max_iter=1000, C=1.0)",
        "ensemble": "uniform_mean of per-layer predicted probabilities",
        "dataset": "pairs_v2 / activations_v2",
        "baseline_single_layer_py_to_js_auc": 0.907,
        "baseline_random_split_single_l17_auc": 0.9633,
        "baseline_random_split_ensemble_auc": 0.9764,
        "directions": out,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    print(f"\nsaved {OUT_JSON}")


if __name__ == "__main__":
    main()
