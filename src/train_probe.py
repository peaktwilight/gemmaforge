"""Train a linear probe on Gemma 4 hidden-state activations.

Reads data/activations/activations_layer*.npz, trains a LogisticRegression
per layer, reports AUC + accuracy, saves the best probe as data/probe.npz
plus a small `probe_card.json` with metrics.

The "probe" is just (w, b) for w @ activation + b → vulnerability logit.
Apply sigmoid to get a 0..1 risk score.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.model_selection import train_test_split


def fit_layer(X: np.ndarray, y: np.ndarray, seed: int = 7) -> dict:
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)
    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(Xtr, ytr)
    yhat_prob = clf.predict_proba(Xte)[:, 1]
    yhat_cls = clf.predict(Xte)
    auc = roc_auc_score(yte, yhat_prob)
    acc = accuracy_score(yte, yhat_cls)
    return {
        "auc": float(auc),
        "acc": float(acc),
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "pos_rate": float(y.mean()),
        "w": clf.coef_[0].astype(np.float32),
        "b": float(clf.intercept_[0]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acts-dir", default="data/activations")
    ap.add_argument("--out", default="data/probe.npz")
    ap.add_argument("--card", default="data/probe_card.json")
    args = ap.parse_args()

    acts_dir = Path(args.acts_dir)
    files = sorted(acts_dir.glob("activations_layer*.npz"))
    if not files:
        print(f"[train_probe] no activation files in {acts_dir}", file=sys.stderr)
        sys.exit(1)

    results: list[dict] = []
    for f in files:
        layer = int(f.stem.split("layer")[-1])
        npz = np.load(f)
        X, y = npz["X"], npz["y"]
        print(f"[train_probe] layer {layer:02d}  X={X.shape}  y_pos={int(y.sum())}", file=sys.stderr)
        r = fit_layer(X, y)
        r["layer"] = layer
        results.append(r)
        print(f"[train_probe] layer {layer:02d}  AUC={r['auc']:.3f}  ACC={r['acc']:.3f}", file=sys.stderr)

    best = max(results, key=lambda r: r["auc"])
    print(f"[train_probe] best layer = {best['layer']}  AUC={best['auc']:.3f}", file=sys.stderr)

    np.savez_compressed(
        args.out,
        w=best["w"],
        b=np.float32(best["b"]),
        layer=np.int32(best["layer"]),
    )
    card = {
        "best_layer": best["layer"],
        "best_auc": best["auc"],
        "best_acc": best["acc"],
        "all_layers": [
            {"layer": r["layer"], "auc": r["auc"], "acc": r["acc"], "n_train": r["n_train"], "n_test": r["n_test"]}
            for r in results
        ],
        "pos_rate": best["pos_rate"],
    }
    Path(args.card).write_text(json.dumps(card, indent=2))
    print(f"[train_probe] saved {args.out} + {args.card}", file=sys.stderr)


if __name__ == "__main__":
    main()
