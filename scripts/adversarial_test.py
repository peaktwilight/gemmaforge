"""Adversarial sanity test for the vulnerability probe.

Motivation: Bailey et al. (arXiv 2412.09565, ICLR 2026) and the SLODA
benchmark (Risse & Bohme, FSE 2025) both show that vulnerability detectors
often rely on superficial *identifier* shortcuts (sink names like `db.query`,
`cursor.execute`; source names like `req.params.id`) rather than the actual
taint flow. We probe the same failure mode here by applying two
semantic-preserving transformations to known-vulnerable test snippets and
measuring how much the probe score drops.

Transforms:
  T1 (identifier rename):
    db.query        → database.execute
    pool.query      → client.run
    cursor.execute  → db.run
    req.params.id   → userId
    request.args    → incomingArgs
  T3 (whitespace / comment insertion):
    Insert "// pre-validated by upstream middleware" two lines above the
    first line of the snippet (or above the first apparent vulnerable call),
    plus indent every original line by 2 extra spaces. Python files get
    a "#"-style comment instead of a "//" comment so they remain parsable
    in spirit.

For each transformed example we re-run Gemma 4 + probe and capture both
last-token and max-pool scores. We then report:
  * mean baseline score
  * mean score under T1, mean delta, flip-rate to score<0.5
  * mean score under T3, mean delta, flip-rate to score<0.5

Output: data/adversarial_eval.json
"""
from __future__ import annotations
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch


MODEL_ID_DEFAULT = "google/gemma-4-E2B-it"


# Regex-rename rules applied in order. We use word boundaries / exact regex
# so we don't accidentally rewrite substrings inside unrelated identifiers.
T1_RULES: list[tuple[str, str]] = [
    (r"\bdb\.query\b",       "database.execute"),
    (r"\bpool\.query\b",     "client.run"),
    (r"\bcursor\.execute\b", "db.run"),
    (r"\breq\.params\.id\b", "userId"),
    (r"\brequest\.args\b",   "incomingArgs"),
]


def apply_t1(code: str) -> tuple[str, int]:
    """Return (new_code, n_substitutions_applied)."""
    new = code
    n = 0
    for pat, repl in T1_RULES:
        new, k = re.subn(pat, repl, new)
        n += k
    return new, n


def apply_t3(code: str, lang: str | None) -> str:
    """Insert a benign comment + indent every line by 2 spaces."""
    comment = "// pre-validated by upstream middleware"
    if lang and lang.lower() in {"python", "py", "ruby", "rb", "yaml", "yml", "shell", "sh", "bash"}:
        comment = "# pre-validated by upstream middleware"

    lines = code.split("\n")
    # Insert blank line + comment near the top, two lines above the first
    # non-empty line (we want the comment to look like inline middleware doc).
    out_lines: list[str] = []
    inserted = False
    for ln in lines:
        if not inserted and ln.strip():
            out_lines.append(comment)
            out_lines.append("")
            inserted = True
        out_lines.append("  " + ln if ln else ln)
    if not inserted:
        out_lines = [comment, ""] + ["  " + ln if ln else ln for ln in lines]
    return "\n".join(out_lines)


def _sigmoid_arr(x: np.ndarray) -> np.ndarray:
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


def score_snippet(model, tokenizer, device, w, b, layer, code: str, max_length: int = 512) -> tuple[float, float]:
    """Return (last_token_score, max_pool_score)."""
    ids = tokenizer.encode(code, return_tensors="pt", truncation=True, max_length=max_length).to(device)
    with torch.inference_mode():
        out = model(ids, output_hidden_states=True, use_cache=False)
    H = out.hidden_states[layer + 1][0].detach().to("cpu").float().numpy()
    logits = H @ w + b
    risks = _sigmoid_arr(logits)
    return float(risks[-1]), float(risks.max())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_ID_DEFAULT)
    ap.add_argument("--probe", default="data/probe.npz")
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument("--out", default="data/adversarial_eval.json")
    ap.add_argument("--n", type=int, default=20, help="number of vulnerable rows to sample")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--max-length", type=int, default=512)
    args = ap.parse_args()

    w, b, layer = load_probe(Path(args.probe))
    print(f"[adversarial] probe layer={layer} dim={len(w)} b={b:.3f}", file=sys.stderr)

    rows = load_rows(Path(args.pairs))
    positives = [(i, r) for i, r in enumerate(rows) if int(r.get("label", 0)) == 1]
    print(f"[adversarial] {len(positives)} positives total", file=sys.stderr)

    rng = random.Random(args.seed)
    sample = rng.sample(positives, k=min(args.n, len(positives)))

    # Pre-compute transforms (cheap, no GPU needed).
    examples = []
    for gi, row in sample:
        code = row["code"]
        lang = row.get("lang")
        t1_code, t1_hits = apply_t1(code)
        t3_code = apply_t3(code, lang)
        examples.append({
            "row_idx": int(gi),
            "lang": lang,
            "cwe": row.get("cwe"),
            "baseline_code": code,
            "t1_code": t1_code,
            "t1_hits": int(t1_hits),
            "t3_code": t3_code,
        })

    # Load Gemma.
    from transformers import AutoTokenizer, AutoModelForCausalLM

    device = _device()
    print(f"[adversarial] device={device} model={args.model}", file=sys.stderr)
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    dtype = torch.float16 if device != "cpu" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=dtype, attn_implementation="eager")
    model.to(device)
    model.eval()
    print(f"[adversarial] model loaded in {time.time()-t0:.1f}s", file=sys.stderr)

    per_example_results = []
    t_loop = time.time()
    for k, ex in enumerate(examples):
        b_last, b_max = score_snippet(model, tokenizer, device, w, b, layer, ex["baseline_code"], args.max_length)
        t1_last, t1_max = score_snippet(model, tokenizer, device, w, b, layer, ex["t1_code"], args.max_length)
        t3_last, t3_max = score_snippet(model, tokenizer, device, w, b, layer, ex["t3_code"], args.max_length)
        per_example_results.append({
            "row_idx": ex["row_idx"],
            "lang": ex["lang"],
            "cwe": ex["cwe"],
            "t1_hits": ex["t1_hits"],
            "baseline_last": b_last, "baseline_max": b_max,
            "t1_last": t1_last,       "t1_max": t1_max,
            "t3_last": t3_last,       "t3_max": t3_max,
        })
        if (k + 1) % 5 == 0:
            rate = (k + 1) / (time.time() - t_loop)
            eta = (len(examples) - (k + 1)) / max(rate, 0.01)
            print(f"[adversarial] {k+1}/{len(examples)}  {rate:.2f} ex/s  eta {eta:.0f}s",
                  file=sys.stderr)

    # Aggregate.
    def _mean(xs):
        return float(np.mean(xs)) if xs else 0.0

    def _flip_rate(scores_after):
        # fraction whose post-transform score drops below 0.5
        if not scores_after:
            return 0.0
        return float(np.mean([s < 0.5 for s in scores_after]))

    baseline_last = [e["baseline_last"] for e in per_example_results]
    baseline_max = [e["baseline_max"] for e in per_example_results]
    t1_last = [e["t1_last"] for e in per_example_results]
    t1_max = [e["t1_max"] for e in per_example_results]
    t3_last = [e["t3_last"] for e in per_example_results]
    t3_max = [e["t3_max"] for e in per_example_results]

    # Subset of examples where T1 actually fired (at least one rename hit).
    t1_subset = [e for e in per_example_results if e["t1_hits"] > 0]
    t1_subset_baseline = [e["baseline_last"] for e in t1_subset]
    t1_subset_after = [e["t1_last"] for e in t1_subset]

    report = {
        "n_examples": len(per_example_results),
        "seed": args.seed,
        "model": args.model,
        "probe_layer": layer,
        "baseline_mean_score": _mean(baseline_last),
        "baseline_mean_score_maxpool": _mean(baseline_max),
        "t1_rename": {
            "mean_score": _mean(t1_last),
            "flip_rate": _flip_rate(t1_last),
            "delta": _mean(t1_last) - _mean(baseline_last),
            "mean_score_maxpool": _mean(t1_max),
            "flip_rate_maxpool": _flip_rate(t1_max),
            "delta_maxpool": _mean(t1_max) - _mean(baseline_max),
            "n_examples_with_at_least_one_rename": len(t1_subset),
            "subset_baseline_mean": _mean(t1_subset_baseline),
            "subset_after_mean": _mean(t1_subset_after),
            "subset_delta": _mean(t1_subset_after) - _mean(t1_subset_baseline) if t1_subset else 0.0,
        },
        "t3_comment": {
            "mean_score": _mean(t3_last),
            "flip_rate": _flip_rate(t3_last),
            "delta": _mean(t3_last) - _mean(baseline_last),
            "mean_score_maxpool": _mean(t3_max),
            "flip_rate_maxpool": _flip_rate(t3_max),
            "delta_maxpool": _mean(t3_max) - _mean(baseline_max),
        },
        "per_example": per_example_results,
    }

    print("\n[adversarial] RESULTS (last-token)")
    print(f"  baseline   mean={_mean(baseline_last):.3f}")
    print(f"  T1 rename  mean={_mean(t1_last):.3f}  Δ={_mean(t1_last)-_mean(baseline_last):+.3f}  flip={_flip_rate(t1_last):.2f}  (hits-only Δ={report['t1_rename']['subset_delta']:+.3f} on n={len(t1_subset)})")
    print(f"  T3 comment mean={_mean(t3_last):.3f}  Δ={_mean(t3_last)-_mean(baseline_last):+.3f}  flip={_flip_rate(t3_last):.2f}")
    print("[adversarial] RESULTS (max-pool)")
    print(f"  baseline   mean={_mean(baseline_max):.3f}")
    print(f"  T1 rename  mean={_mean(t1_max):.3f}  Δ={_mean(t1_max)-_mean(baseline_max):+.3f}  flip={_flip_rate(t1_max):.2f}")
    print(f"  T3 comment mean={_mean(t3_max):.3f}  Δ={_mean(t3_max)-_mean(baseline_max):+.3f}  flip={_flip_rate(t3_max):.2f}")

    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"[adversarial] wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
