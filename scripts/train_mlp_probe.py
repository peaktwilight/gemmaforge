"""MLP-vs-linear probe ablation on Gemma 4 E2B layer-17 activations.

Closes the research thread in `RESULTS.md` §7.7 ("beyond linear"). The question:
how much of the missing 0.04 in the cross-language gap (Py->JS = 0.907 vs
random-stratified = 0.963) is "linear isn't expressive enough" vs "the
representation itself isn't language-portable"?

Pipeline:
  1. Load `data/activations_v2/activations_layer17.npz` (X: [1198, 1536],
     y: [1198] int8) and the row-aligned `data/pairs.jsonl` for the `lang`
     field.
  2. Train three probe variants on the SAME activations:
       - `LogisticRegression(C=1.0)` baseline (replicates the shipped probe).
       - Small MLP: `MLPClassifier(hidden_layer_sizes=(64,), alpha=1e-3,
         max_iter=300, random_state=7)`.
       - Wider 2-layer MLP: `MLPClassifier(hidden_layer_sizes=(128, 64),
         alpha=1e-3, max_iter=300, random_state=7)`.
  3. Evaluate each variant on two splits:
       - `random_stratified`: stratified 80/20 (seed=7), matches
         `src/train_probe.py:fit_layer` and the shipped headline (AUC 0.963).
       - `heldout_lang::test=javascript`: train on Python rows only, test on
         JavaScript rows only (Py->JS). Matches the `RESULTS.md` row that
         reports AUC 0.907 for the shipped logreg.
  4. Save the 3 x 2 comparison table to `data/probe_mlp_ablation.json` and
     print a Markdown table on stdout.

Constraints (per task brief):
  - sklearn only, no torch.
  - Read-only on `src/eval/*`, `data/probe.npz`, `WRITEUP.md`, `README.md`,
    `RESULTS.md`.
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
from sklearn.neural_network import MLPClassifier


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_activations(acts_path: Path) -> tuple[np.ndarray, np.ndarray]:
    npz = np.load(acts_path)
    X = npz["X"].astype(np.float32)
    y = npz["y"].astype(np.int64)
    return X, y


def load_langs(pairs_path: Path, n_expected: int) -> np.ndarray:
    """Read the `lang` field from pairs.jsonl in row order.

    The activations are saved row-aligned with `pairs.jsonl` (verified by
    `(npz['y'] == [row['label'] for row in pairs.jsonl]).all() == True`), so
    we can just zip them together.
    """
    langs: list[str] = []
    with pairs_path.open() as f:
        for line in f:
            rec = json.loads(line)
            langs.append(rec["lang"])
    if len(langs) != n_expected:
        raise ValueError(
            f"pairs.jsonl has {len(langs)} rows but activations have {n_expected}"
        )
    return np.array(langs)


# ---------------------------------------------------------------------------
# Variants + splits
# ---------------------------------------------------------------------------

def make_variants(seed: int) -> dict[str, object]:
    """Three classifiers compared on the same activations.

    - `logreg`: the shipped probe (replicates `src/train_probe.py:fit_layer`).
    - `mlp_64`: 1536 -> 64 -> 1, ReLU + L2.
    - `mlp_128_64`: 1536 -> 128 -> 64 -> 1, ReLU + L2. Wider / deeper to test
      whether more capacity helps the cross-language split.

    `alpha=1e-3` matches §7.7's "small MLP" sketch; `max_iter=300` is enough
    for both MLPs to converge on a 1k-row dataset.
    """
    return {
        "logreg":      LogisticRegression(max_iter=1000, C=1.0),
        "mlp_64":      MLPClassifier(hidden_layer_sizes=(64,),
                                     alpha=1e-3, max_iter=300, random_state=seed),
        "mlp_128_64": MLPClassifier(hidden_layer_sizes=(128, 64),
                                     alpha=1e-3, max_iter=300, random_state=seed),
    }


def split_random_stratified(
    X: np.ndarray, y: np.ndarray, seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )
    return Xtr, Xte, ytr, yte


def split_heldout_lang(
    X: np.ndarray, y: np.ndarray, langs: np.ndarray,
    train_lang: str, test_lang: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    tr = langs == train_lang
    te = langs == test_lang
    return X[tr], X[te], y[tr], y[te]


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------

def eval_one(clf, Xtr, Xte, ytr, yte) -> dict:
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)[:, 1]
    yhat = clf.predict(Xte)
    return {
        "auc": float(roc_auc_score(yte, proba)),
        "acc": float(accuracy_score(yte, yhat)),
        "n_train": int(len(ytr)),
        "n_test": int(len(yte)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--acts",
        default="data/activations_v2/activations_layer17.npz",
        help="Layer-17 activation .npz (X, y).",
    )
    ap.add_argument(
        "--pairs",
        default="data/pairs.jsonl",
        help="Row-aligned metadata (one JSON record per activation row).",
    )
    ap.add_argument(
        "--out",
        default="data/probe_mlp_ablation.json",
        help="Output JSON with the 6-row comparison table.",
    )
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    X, y = load_activations(Path(args.acts))
    langs = load_langs(Path(args.pairs), n_expected=len(y))
    print(
        f"[mlp-ablation] X={X.shape}  y_pos={int(y.sum())}/{len(y)}  "
        f"py={int((langs == 'python').sum())}  "
        f"js={int((langs == 'javascript').sum())}",
        file=sys.stderr,
    )

    # The two splits we report.
    splits = {
        "random_stratified": split_random_stratified(X, y, args.seed),
        "heldout_lang::test=javascript": split_heldout_lang(
            X, y, langs, train_lang="python", test_lang="javascript"
        ),
    }

    rows: list[dict] = []
    for variant_name, clf_factory_value in make_variants(args.seed).items():
        for split_name, (Xtr, Xte, ytr, yte) in splits.items():
            # Re-create the classifier per (variant, split) so MLPs don't see
            # leakage from a previous fit -- sklearn's `fit` is stateful.
            clf = make_variants(args.seed)[variant_name]
            m = eval_one(clf, Xtr, Xte, ytr, yte)
            rows.append({"variant": variant_name, "split": split_name, **m})
            print(
                f"[mlp-ablation] {variant_name:11s}  {split_name:33s}  "
                f"AUC={m['auc']:.3f}  ACC={m['acc']:.3f}  "
                f"n_train={m['n_train']}  n_test={m['n_test']}",
                file=sys.stderr,
            )

    Path(args.out).write_text(json.dumps({"rows": rows}, indent=2))
    print(f"[mlp-ablation] wrote {args.out}", file=sys.stderr)

    # Markdown table for the PR / report.
    print()
    print("| Variant | Split | AUC | ACC | n_train | n_test |")
    print("|---|---|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['variant']} | {r['split']} | {r['auc']:.3f} | "
            f"{r['acc']:.3f} | {r['n_train']} | {r['n_test']} |"
        )


if __name__ == "__main__":
    main()
