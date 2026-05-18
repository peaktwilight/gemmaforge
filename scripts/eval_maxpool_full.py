"""Evaluate max-pool aggregation on the FULL held-out split (no subsetting).

This is the unsubsetted companion to scripts/eval_maxpool.py. The original
script caps the re-forward at 60 examples to fit a tight time budget; this
one walks every example in the 20% stratified held-out split (n=240 for the
shipped pairs.jsonl), so the reported max-pool AUC is the real held-out
number, not a stratified subset estimate.

Mechanics are otherwise identical to scripts/eval_maxpool.py:
  1. Load shipped probe (data/probe.npz, layer 17).
  2. Reproduce the 20% stratified held-out split (random_state=7, matches
     src/train_probe.py).
  3. Baseline last-token AUC from cached activations.
  4. Re-forward EVERY held-out example through Gemma, capture per-token
     activations at the probe layer, apply probe at every position, take
     max → max-pool AUC.
  5. Write report to data/eval_maxpool_full.json with the same schema as
     data/eval_maxpool.json (n_subset_reforwarded == n_heldout_full here).
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split


MODEL_ID_DEFAULT = "google/gemma-4-E2B-it"


def _sigmoid(x: np.ndarray) -> np.ndarray:
    out = np.empty_like(x, dtype=np.float64)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    e = np.exp(x[~pos])
    out[~pos] = e / (1.0 + e)
    return out


def _device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_probe(probe_path: Path):
    npz = np.load(probe_path)
    return npz["w"].astype(np.float32), float(npz["b"]), int(npz["layer"])


def load_rows(jsonl_path: Path) -> list[dict]:
    rows = []
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def run_probe_pertoken(model, tokenizer, device, w, b, layer, code: str, max_length: int = 512) -> tuple[float, float]:
    """Return (last_token_score, max_pool_score) for a single snippet."""
    ids = tokenizer.encode(code, return_tensors="pt", truncation=True, max_length=max_length).to(device)
    with torch.inference_mode():
        out = model(ids, output_hidden_states=True, use_cache=False)
    H = out.hidden_states[layer + 1][0].detach().to("cpu").float().numpy()  # (T, dim)
    logits = H @ w + b  # (T,)
    risks = _sigmoid(logits)
    return float(risks[-1]), float(risks.max())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_ID_DEFAULT)
    ap.add_argument("--probe", default="data/probe.npz")
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument("--acts", default="data/activations_v2/activations_layer17.npz")
    ap.add_argument("--out", default="data/eval_maxpool_full.json")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on number of held-out examples to re-forward (0 = full split). "
        "Default 0 evaluates the FULL held-out split (n≈240).",
    )
    args = ap.parse_args()

    w, b, layer = load_probe(Path(args.probe))
    print(f"[eval_maxpool_full] probe layer={layer} dim={len(w)} b={b:.3f}", file=sys.stderr)

    acts = np.load(args.acts)
    X_all, y_all = acts["X"].astype(np.float32), acts["y"].astype(np.int64)
    rows = load_rows(Path(args.pairs))
    assert len(rows) == len(y_all), f"row mismatch: {len(rows)} vs {len(y_all)}"

    idx = np.arange(len(rows))
    _, test_idx = train_test_split(
        idx, test_size=0.2, random_state=args.seed, stratify=y_all,
    )
    print(
        f"[eval_maxpool_full] held-out split: n={len(test_idx)} pos_rate={float(y_all[test_idx].mean()):.3f}",
        file=sys.stderr,
    )

    # --- Baseline last-token AUC on the full held-out (cached, fast). ---
    X_test = X_all[test_idx]
    y_test = y_all[test_idx]
    logits_full = X_test @ w + b
    scores_full = _sigmoid(logits_full)
    auc_last_full = float(roc_auc_score(y_test, scores_full))
    print(
        f"[eval_maxpool_full] baseline last-token AUC (n={len(test_idx)}): {auc_last_full:.4f}",
        file=sys.stderr,
    )

    # --- Full-split re-forward (or capped if --limit > 0). ---
    if args.limit and args.limit > 0 and args.limit < len(test_idx):
        rng = np.random.default_rng(args.seed)
        pos = test_idx[y_all[test_idx] == 1]
        neg = test_idx[y_all[test_idx] == 0]
        n_each = args.limit // 2
        sub_pos = rng.choice(pos, size=min(n_each, len(pos)), replace=False)
        sub_neg = rng.choice(neg, size=min(args.limit - len(sub_pos), len(neg)), replace=False)
        eval_idx = np.concatenate([sub_pos, sub_neg])
        rng.shuffle(eval_idx)
    else:
        eval_idx = test_idx
    print(
        f"[eval_maxpool_full] re-forwarding n={len(eval_idx)} examples through Gemma…",
        file=sys.stderr,
    )

    from transformers import AutoTokenizer, AutoModelForCausalLM

    device = _device()
    print(f"[eval_maxpool_full] device={device} model={args.model}", file=sys.stderr)
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    dtype = torch.float16 if device != "cpu" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=dtype, attn_implementation="eager")
    model.to(device)
    model.eval()
    print(f"[eval_maxpool_full] model loaded in {time.time()-t0:.1f}s", file=sys.stderr)

    last_scores: list[float] = []
    max_scores: list[float] = []
    sub_labels: list[int] = []
    t_loop = time.time()
    for k, gi in enumerate(eval_idx):
        code = rows[int(gi)]["code"]
        last_s, max_s = run_probe_pertoken(model, tokenizer, device, w, b, layer, code, args.max_length)
        last_scores.append(last_s)
        max_scores.append(max_s)
        sub_labels.append(int(y_all[int(gi)]))
        if (k + 1) % 10 == 0:
            rate = (k + 1) / (time.time() - t_loop)
            eta = (len(eval_idx) - (k + 1)) / max(rate, 0.01)
            print(
                f"[eval_maxpool_full] {k+1}/{len(eval_idx)}  {rate:.2f} ex/s  eta {eta:.0f}s",
                file=sys.stderr,
            )

    sub_labels_arr = np.array(sub_labels)
    auc_last_eval = float(roc_auc_score(sub_labels_arr, np.array(last_scores)))
    auc_max_eval = float(roc_auc_score(sub_labels_arr, np.array(max_scores)))

    report = {
        "probe_layer": layer,
        "seed": args.seed,
        "n_heldout_full": int(len(test_idx)),
        "n_subset_reforwarded": int(len(eval_idx)),
        "baseline_last_token_auc_full_heldout": auc_last_full,
        "subset_last_token_auc": auc_last_eval,
        "subset_max_pool_auc": auc_max_eval,
        "delta_auc_subset": auc_max_eval - auc_last_eval,
        "model": args.model,
        "max_length": args.max_length,
        "note": (
            "FULL held-out re-forward: every example in the 20% stratified held-out split "
            "(random_state=7, matches src/train_probe.py) is re-forwarded through Gemma to "
            "capture per-token activations. subset_* AUCs are therefore on the FULL split — "
            "they are no longer a subset estimate. Use --limit N to fall back to a capped "
            "stratified sub-sample (matches scripts/eval_maxpool.py)."
        ),
    }

    print(f"\n[eval_maxpool_full] RESULTS")
    print(f"  last-token AUC (full held-out n={len(test_idx)}): {auc_last_full:.4f}")
    print(f"  last-token AUC (re-forwarded n={len(eval_idx)}):  {auc_last_eval:.4f}")
    print(f"  max-pool   AUC (re-forwarded n={len(eval_idx)}):  {auc_max_eval:.4f}")
    print(f"  Δ (max - last):                                  {auc_max_eval - auc_last_eval:+.4f}")

    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"[eval_maxpool_full] wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
