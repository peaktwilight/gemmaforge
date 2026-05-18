"""Evaluate the multi-head per-CWE probe on the cached activations.

Loads data/probe_per_cwe.npz, runs each head against the held-out 20% slice
of its own one-vs-rest task, prints a Markdown table of per-CWE AUC/ACC and
the macro-AUC, and renders a confusion matrix over positives of each
trained CWE: for every label==1 row whose CWE is one of the K heads, the
row is routed to whichever head fires highest (argmax over logits). The
diagonal tells you whether a CWE-89 example actually lands on head CWE-89
or smears across other heads.

CPU only: numpy + sklearn (split reproduction) + json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
ACT_PATH = ROOT / "data" / "activations_v2" / "activations_layer17.npz"
PAIRS_PATH = ROOT / "data" / "pairs.jsonl"
PROBE_PATH = ROOT / "data" / "probe_per_cwe.npz"

SEED = 0


def load_rows():
    npz = np.load(ACT_PATH)
    X = npz["X"].astype(np.float32)
    y = npz["y"].astype(np.int8)
    rows = [json.loads(l) for l in open(PAIRS_PATH)]
    cwes = [r.get("cwe") for r in rows]
    return X, y, cwes


def per_cwe_test_split(X, y, cwes, target_cwe):
    """Reproduce the stratified 80/20 split used at training time."""
    pos_mask = np.array(
        [lab == 1 and c == target_cwe for c, lab in zip(cwes, y)], dtype=bool
    )
    neg_mask = (y == 0)
    keep = pos_mask | neg_mask
    Xh = X[keep]
    yh = np.zeros(keep.sum(), dtype=np.int8)
    yh[pos_mask[keep]] = 1

    _, X_te, _, y_te = train_test_split(
        Xh, yh, test_size=0.2, stratify=yh, random_state=SEED
    )
    return X_te, y_te


def main():
    probe = np.load(PROBE_PATH, allow_pickle=False)
    cwes_arr = probe["cwes"]
    target_cwes = [str(c) for c in cwes_arr]
    W = probe["W"].astype(np.float32)
    b = probe["b"].astype(np.float32)
    layer = int(probe["layer"])
    K = len(target_cwes)

    X, y, cwes = load_rows()
    print(f"probe: layer={layer}  heads={K}  dim={W.shape[1]}")
    print(f"CWE heads: {target_cwes}\n")

    # 1. Per-head one-vs-rest metrics on its own held-out slice.
    print("| CWE | n_test_pos | AUC | ACC |")
    print("|---|---:|---:|---:|")
    aucs = []
    for i, cwe in enumerate(target_cwes):
        X_te, y_te = per_cwe_test_split(X, y, cwes, cwe)
        logits = X_te @ W[i] + b[i]
        proba = 1.0 / (1.0 + np.exp(-logits))
        pred = (proba >= 0.5).astype(np.int8)
        auc = float(roc_auc_score(y_te, proba))
        acc = float(accuracy_score(y_te, pred))
        aucs.append(auc)
        print(f"| {cwe} | {int(y_te.sum())} | {auc:.3f} | {acc:.3f} |")
    macro_auc = float(np.mean(aucs))
    print(f"\n**Macro-AUC across {K} heads: {macro_auc:.4f}**\n")

    # 2. Confusion matrix: for each positive whose CWE is one of the K heads,
    #    which head fires highest? Rows = true CWE, cols = argmax head.
    pos_idx = [
        i for i, (lab, c) in enumerate(zip(y, cwes))
        if lab == 1 and c in target_cwes
    ]
    X_pos = X[pos_idx]
    true_labels = [cwes[i] for i in pos_idx]

    all_logits = X_pos @ W.T + b  # (n_pos, K)
    argmax = np.argmax(all_logits, axis=1)
    pred_cwes = [target_cwes[k] for k in argmax]

    cwe_to_idx = {c: i for i, c in enumerate(target_cwes)}
    conf = np.zeros((K, K), dtype=np.int32)
    for tc, pc in zip(true_labels, pred_cwes):
        conf[cwe_to_idx[tc], cwe_to_idx[pc]] += 1

    print("Confusion matrix (rows = true CWE, cols = argmax head)")
    print("Counts over ALL positives of each trained CWE in the dataset.\n")
    header = "| true \\ pred | " + " | ".join(target_cwes) + " | row total | top1 acc |"
    sep = "|---|" + "|".join(["---:"] * (K + 2)) + "|"
    print(header)
    print(sep)
    for i, cwe in enumerate(target_cwes):
        row = conf[i]
        total = int(row.sum())
        top1 = float(row[i]) / total if total else float("nan")
        cells = " | ".join(str(int(x)) for x in row)
        print(f"| {cwe} | {cells} | {total} | {top1:.3f} |")

    diag = int(np.trace(conf))
    total = int(conf.sum())
    print(f"\nOverall top-1 routing accuracy: {diag}/{total} = {diag/total:.3f}")


if __name__ == "__main__":
    main()
