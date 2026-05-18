"""Capture per-token hidden states from Gemma 4, with per-token vulnerability labels.

This is the proper "span-aware" extraction. For each labelled example row:
  1. Tokenize the full code.
  2. Locate the vulnerable line via the row's `_vuln_line_text` field (carried
     from the dataset builder) — find which tokens fall inside that line.
  3. Forward-pass once through Gemma 4 with `output_hidden_states=True`.
  4. For each captured layer, store hidden states at **every token position**
     along with a per-token binary label (1 if token is inside the vulnerable
     line span, 0 otherwise).

Output: `data/token_activations_layer{NN}.npz` containing
  - X: float32 array  (N_total_positions, hidden_dim)
  - y: int8 array     (N_total_positions,)
  - example_ids: int32 array  (N_total_positions,)  — groups positions
  - spans: list of (example_id, start, end) — for the span-max loss

This format lets the span-max trainer compute Σ_{s∈S} BCE(y_s, max_{i∈s} p_i)
by grouping positions by example_id.

Memory note: for 1k examples × ~200 avg tokens × 1536 dims × 4 bytes × 4 layers
≈ 5 GB float32 → kept on disk per-layer to avoid blowing through 32 GB.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch


def _device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def find_vuln_span(text: str, line_text: str, tokenizer) -> tuple[int, int] | None:
    """Return (start_tok, end_tok) of the vulnerable line in token space.

    `text` is the full code. `line_text` is the literal vulnerable line content
    (with original whitespace, as provided by CyberSecEval).

    We use the tokenizer's offset_mapping to map character offsets to token
    indices, then locate `line_text` in the source via plain str.find.
    """
    if not line_text:
        return None
    target = line_text.rstrip("\n")
    char_start = text.find(target)
    if char_start < 0:
        # try stripped match
        ls = target.lstrip()
        char_start = text.find(ls)
        if char_start < 0:
            return None
        target = ls
    char_end = char_start + len(target)

    enc = tokenizer(text, return_offsets_mapping=True, add_special_tokens=False, truncation=True, max_length=1024)
    offsets = enc["offset_mapping"]
    if not offsets:
        return None

    start_tok = end_tok = -1
    for i, (s, e) in enumerate(offsets):
        if s == e:
            continue  # special tokens get (0,0)
        if start_tok < 0 and e > char_start:
            start_tok = i
        if s < char_end:
            end_tok = i
    if start_tok < 0 or end_tok < start_tok:
        return None
    return start_tok, end_tok


def extract(model_id: str, jsonl_path: Path, out_dir: Path, layer_indices: list[int] | None = None) -> None:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = _device()
    print(f"[token-extract] device={device}  model={model_id}", file=sys.stderr)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    dtype = torch.float16 if device != "cpu" else torch.float32
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype, attn_implementation="eager")
    model.to(device).eval()
    print(f"[token-extract] loaded in {time.time()-t0:.1f}s", file=sys.stderr)

    inner = model
    for attr in ("model", "transformer", "language_model"):
        if hasattr(inner, attr):
            inner = getattr(inner, attr)
    layers = getattr(inner, "layers", None) or getattr(getattr(inner, "model", None), "layers", None)
    n_layers = len(layers) if layers is not None else model.config.num_hidden_layers
    if layer_indices is None:
        layer_indices = sorted({n_layers // 4, n_layers // 2, (3 * n_layers) // 4, n_layers - 1})
    print(f"[token-extract] capturing layers {layer_indices} of {n_layers}", file=sys.stderr)

    rows: list[dict] = []
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print(f"[token-extract] processing {len(rows)} rows…", file=sys.stderr)

    # One growing list per layer, plus per-token labels + example ids.
    per_layer: dict[int, list[np.ndarray]] = {i: [] for i in layer_indices}
    labels: list[int] = []
    example_ids: list[int] = []
    spans: list[tuple[int, int, int]] = []  # (example_id, tok_start_inclusive, tok_end_inclusive)

    skipped = 0
    t_loop = time.time()
    with torch.inference_mode():
        for eid, row in enumerate(rows):
            code = row["code"]
            label = int(row["label"])
            vuln_line_text = row.get("_vuln_line_text") or row.get("vuln_line_text") or ""

            ids = tokenizer.encode(code, return_tensors="pt", truncation=True, max_length=1024).to(device)
            out = model(ids, output_hidden_states=True, use_cache=False)
            n_pos = ids.shape[1]
            hs = out.hidden_states

            # span: positive examples have the vulnerable line; negative do not.
            span = None
            if label == 1 and vuln_line_text:
                span = find_vuln_span(code, vuln_line_text, tokenizer)

            # If we have a span, label tokens INSIDE the span as 1, outside as 0.
            # If no span (e.g. negative example), all tokens labeled 0.
            tok_labels = np.zeros(n_pos, dtype=np.int8)
            if span is not None:
                s, e = span
                s = max(0, min(s, n_pos - 1))
                e = max(s, min(e, n_pos - 1))
                tok_labels[s : e + 1] = 1
                spans.append((eid, s, e))
            elif label == 1:
                # Positive example but couldn't locate span — fall back to
                # labeling just the last few tokens (this is our previous
                # "snippet-level" behavior, retained as a fallback).
                fallback_span_start = max(0, n_pos - 5)
                tok_labels[fallback_span_start:] = 1
                spans.append((eid, fallback_span_start, n_pos - 1))

            for li in layer_indices:
                h = hs[li + 1][0, :, :].detach().to("cpu").float().numpy()  # (n_pos, dim)
                per_layer[li].append(h)
            labels.extend(tok_labels.tolist())
            example_ids.extend([eid] * n_pos)

            if (eid + 1) % 50 == 0:
                rate = (eid + 1) / (time.time() - t_loop)
                print(f"[token-extract] {eid+1}/{len(rows)}  {rate:.2f} ex/s", file=sys.stderr)

    print(f"[token-extract] skipped {skipped} rows", file=sys.stderr)
    y = np.array(labels, dtype=np.int8)
    eid_arr = np.array(example_ids, dtype=np.int32)

    out_dir.mkdir(parents=True, exist_ok=True)
    for li in layer_indices:
        mat = np.vstack(per_layer[li]).astype(np.float32)
        p = out_dir / f"token_activations_layer{li:02d}.npz"
        np.savez_compressed(p, X=mat, y=y, example_ids=eid_arr)
        print(f"[token-extract] saved {p}  X={mat.shape}", file=sys.stderr)
    # Save spans as JSON since they're metadata not bulk arrays.
    (out_dir / "spans.json").write_text(json.dumps(spans))
    print(f"[token-extract] saved spans.json with {len(spans)} positive spans", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-4-E2B-it")
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument("--out", default="data/token_activations")
    args = ap.parse_args()
    extract(args.model, Path(args.pairs), Path(args.out))


if __name__ == "__main__":
    main()
