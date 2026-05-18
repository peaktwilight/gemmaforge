"""Train a multi-head per-CWE linear probe on layer 17 activations.

For the top-K (default 5) most-frequent CWEs in the positive set, fit an
independent one-vs-rest LogisticRegression head:

  - positives = rows with label==1 AND cwe==<this_cwe>
  - negatives = rows with label==0 (the "safe" lead-up positions only)

Other-CWE positives are dropped from each head's training set so the head
learns this specific vuln signal vs the safe-code baseline (classes stay
disjoint per head). Per-head AUC + ACC and the macro-averaged AUC are
reported. Stacked weights are saved to data/probe_per_cwe.npz alongside a
card with the metrics.

CPU only: sklearn + numpy + json. Does not touch torch / transformers.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

# Lazy + guarded wandb import.
try:
    import wandb  # type: ignore
    _HAS_WANDB = True
except Exception:
    wandb = None  # type: ignore
    _HAS_WANDB = False

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACT_PATH = ROOT / "data" / "activations_v2" / "activations_layer17.npz"
PAIRS_PATH = ROOT / "data" / "pairs.jsonl"
DEFAULT_OUT_NPZ = ROOT / "data" / "probe_per_cwe.npz"
DEFAULT_OUT_CARD = ROOT / "data" / "probe_per_cwe_card.json"

DEFAULT_LAYER = 17
TOP_K = 5
SEED = 0


def load_data(act_path: Path):
    npz = np.load(act_path)
    X = npz["X"].astype(np.float32)
    y = npz["y"].astype(np.int8)

    rows = []
    with open(PAIRS_PATH) as f:
        for line in f:
            rows.append(json.loads(line))

    assert len(rows) == X.shape[0], f"row mismatch: {len(rows)} vs {X.shape[0]}"
    labels = np.array([r["label"] for r in rows], dtype=np.int8)
    assert np.array_equal(labels, y), "label column in JSONL does not match activations y"

    cwes = [r.get("cwe") for r in rows]
    return X, y, cwes


def top_cwes(cwes, y, k):
    pos_cwes = [c for c, lab in zip(cwes, y) if lab == 1 and c is not None]
    counter = Counter(pos_cwes)
    return [c for c, _ in counter.most_common(k)]


def train_head(X, y, cwes, target_cwe, seed=SEED):
    """Build a binary task: target-CWE positives vs all label==0 negatives."""
    pos_mask = np.array(
        [lab == 1 and c == target_cwe for c, lab in zip(cwes, y)], dtype=bool
    )
    neg_mask = (y == 0)

    keep = pos_mask | neg_mask
    Xh = X[keep]
    yh = np.zeros(keep.sum(), dtype=np.int8)
    yh[pos_mask[keep]] = 1

    X_tr, X_te, y_tr, y_te = train_test_split(
        Xh, yh, test_size=0.2, stratify=yh, random_state=seed
    )

    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(X_tr, y_tr)

    proba = clf.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(np.int8)
    auc = float(roc_auc_score(y_te, proba))
    acc = float(accuracy_score(y_te, pred))
    cm = confusion_matrix(y_te, pred, labels=[0, 1])  # 2x2: tn, fp / fn, tp

    return {
        "clf": clf,
        "auc": auc,
        "acc": acc,
        "n_pos": int(pos_mask.sum()),
        "n_neg": int(neg_mask.sum()),
        "n_train": int(len(y_tr)),
        "n_test": int(len(y_te)),
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    }


def _wandb_init(args, layer: int):
    """Init wandb if --wandb-project was passed; gracefully no-op otherwise."""
    if not args.wandb_project:
        return None
    if not _HAS_WANDB:
        print("[train_per_cwe] wandb not installed, skipping logging", file=sys.stderr)
        return None
    try:
        mode = "online" if os.environ.get("WANDB_API_KEY") else "offline"
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_name = f"probe-per-cwe-L{layer}-k{TOP_K}-{ts}"
        run = wandb.init(
            project=args.wandb_project,
            name=run_name,
            mode=mode,
            config={**vars(args), "layer": layer, "top_k": TOP_K, "seed": SEED},
            job_type="per-cwe-probe",
        )
        print(f"[train_per_cwe] wandb run: {run_name} (mode={mode})", file=sys.stderr)
        return run
    except Exception as e:
        print(f"[train_per_cwe] wandb init failed: {e}", file=sys.stderr)
        return None


def _wandb_log(run, payload, step=None):
    if run is None:
        return
    try:
        if step is not None:
            wandb.log(payload, step=step)
        else:
            wandb.log(payload)
    except Exception as e:
        print(f"[train_per_cwe] wandb.log failed: {e}", file=sys.stderr)


def _wandb_artifact(run, path: Path, name: str, art_type: str, metadata: dict):
    if run is None or not path.exists():
        return
    try:
        art = wandb.Artifact(name=name, type=art_type, metadata=metadata)
        art.add_file(str(path))
        run.log_artifact(art)
    except Exception as e:
        print(f"[train_per_cwe] wandb artifact failed: {e}", file=sys.stderr)


def _wandb_finish(run):
    if run is None:
        return
    try:
        wandb.finish()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--activations",
        default=str(DEFAULT_ACT_PATH),
        help="Path to activations .npz (must contain X, y).",
    )
    ap.add_argument(
        "--layer",
        type=int,
        default=DEFAULT_LAYER,
        help="Layer index recorded in the metric card / weights file.",
    )
    ap.add_argument(
        "--out",
        default=str(DEFAULT_OUT_NPZ),
        help="Output path for stacked per-CWE weights (.npz).",
    )
    ap.add_argument(
        "--card",
        default=str(DEFAULT_OUT_CARD),
        help="Output path for the metric card (.json).",
    )
    ap.add_argument(
        "--wandb-project",
        default=None,
        help="W&B project name; omit to disable wandb logging",
    )
    args = ap.parse_args()

    act_path = Path(args.activations)
    out_npz = Path(args.out)
    out_card = Path(args.card)
    layer = int(args.layer)

    X, y, cwes = load_data(act_path)
    print(f"loaded activations: X={X.shape}  y={y.shape}  layer={layer}")

    targets = top_cwes(cwes, y, TOP_K)
    print(f"top-{TOP_K} CWEs (by positive count): {targets}")

    run = _wandb_init(args, layer)

    W = np.zeros((len(targets), X.shape[1]), dtype=np.float32)
    b = np.zeros((len(targets),), dtype=np.float32)
    per_cwe = []

    print(f"\n{'CWE':12s}  {'n_pos':>6s}  {'n_neg':>6s}  {'AUC':>6s}  {'ACC':>6s}")
    print("-" * 48)
    aucs = []
    for i, cwe in enumerate(targets):
        r = train_head(X, y, cwes, cwe)
        W[i] = r["clf"].coef_.astype(np.float32).ravel()
        b[i] = float(r["clf"].intercept_[0])
        aucs.append(r["auc"])
        per_cwe.append(
            {
                "cwe": cwe,
                "auc": r["auc"],
                "acc": r["acc"],
                "n_pos": r["n_pos"],
                "n_neg": r["n_neg"],
                "n_train": r["n_train"],
                "n_test": r["n_test"],
                "tn": r["tn"],
                "fp": r["fp"],
                "fn": r["fn"],
                "tp": r["tp"],
            }
        )
        print(f"{cwe:12s}  {r['n_pos']:6d}  {r['n_neg']:6d}  {r['auc']:6.3f}  {r['acc']:6.3f}")
        # Per-head log row, keyed by head index for a stable x-axis.
        _wandb_log(
            run,
            {
                "head/cwe": cwe,
                "head/auc": r["auc"],
                "head/acc": r["acc"],
                "head/n_pos": r["n_pos"],
                "head/n_neg": r["n_neg"],
                "head/tp": r["tp"],
                "head/fp": r["fp"],
                "head/tn": r["tn"],
                "head/fn": r["fn"],
                "head_idx": i,
            },
            step=i,
        )

    macro_auc = float(np.mean(aucs))
    print("-" * 48)
    print(f"macro-AUC across {len(targets)} heads: {macro_auc:.4f}")

    out_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_npz,
        cwes=np.array(targets),
        W=W,
        b=b,
        layer=np.int32(layer),
    )
    print(f"saved weights: {out_npz}")

    card = {
        "layer": layer,
        "top_k": TOP_K,
        "cwes": targets,
        "per_cwe": per_cwe,
        "macro_auc": macro_auc,
        "model": "LogisticRegression(max_iter=1000, C=1.0)",
        "split": "stratified 80/20, seed=0",
        "negative_set": "all label==0 rows (safe lead-up positions)",
        "activations": str(act_path),
    }
    out_card.write_text(json.dumps(card, indent=2))
    print(f"saved card:    {out_card}")

    # Final summary: macro-AUC + a per-CWE table + a confusion-matrix table.
    if run is not None:
        try:
            per_cwe_tbl = wandb.Table(
                columns=["cwe", "auc", "acc", "n_pos", "n_neg", "n_train", "n_test"]
            )
            for row in per_cwe:
                per_cwe_tbl.add_data(
                    row["cwe"], row["auc"], row["acc"],
                    row["n_pos"], row["n_neg"], row["n_train"], row["n_test"],
                )
            cm_tbl = wandb.Table(columns=["cwe", "tn", "fp", "fn", "tp"])
            for row in per_cwe:
                cm_tbl.add_data(row["cwe"], row["tn"], row["fp"], row["fn"], row["tp"])
            wandb.log({"per_cwe_table": per_cwe_tbl, "confusion_matrix": cm_tbl})
            wandb.summary["macro_auc"] = macro_auc
            wandb.summary["n_heads"] = len(targets)
        except Exception as e:
            print(f"[train_per_cwe] wandb summary failed: {e}", file=sys.stderr)

    _wandb_artifact(
        run,
        out_npz,
        name="probe-per-cwe-weights",
        art_type="model",
        metadata={"layer": layer, "top_k": TOP_K, "macro_auc": macro_auc, "cwes": targets},
    )
    _wandb_finish(run)


if __name__ == "__main__":
    main()
