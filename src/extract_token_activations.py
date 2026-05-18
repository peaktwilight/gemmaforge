"""Capture per-token hidden states from Gemma 4, with per-token vulnerability labels.

This is the proper "span-aware" extraction. For each labelled example row:
  1. Tokenize the full code **once** (with offsets + special tokens) so the
     model input and the offset mapping are perfectly aligned.
  2. Resolve per-token labels from the row's `token_labels` char ranges
     (the SVEN/diff-oracle builder writes these). Positive spans:
     evidence / vulnerable_line / sink / source. Sanitizer spans are
     negative (label-0) and are NOT used to mark tokens as vulnerable.
  3. If a row predates the new builder and lacks `token_labels`, fall
     back to the legacy `_vuln_line_text` line-locator (graceful
     degradation for older datasets).
  4. Forward-pass once through Gemma 4 with `output_hidden_states=True`.
  5. For each captured layer, store hidden states at **every token
     position** along with a per-token binary label (1 if token is inside
     a positive vulnerability span, 0 otherwise).

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


# Keys in `token_labels` that mark tokens as vulnerable (positive).
POSITIVE_LABEL_KEYS: tuple[str, ...] = ("evidence", "vulnerable_line", "sink", "source")
# Keys in `token_labels` that mark tokens as mitigated (negative / label-0).
# We deliberately do NOT mark these as vulnerable.
NEGATIVE_LABEL_KEYS: tuple[str, ...] = ("sanitizer",)


def _device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _row_label(row: dict) -> int:
    """Return 0/1 label, tolerant to rows that omit `label` (use is_completion_vulnerable)."""
    lbl = row.get("label")
    if lbl is not None:
        try:
            return int(lbl)
        except (TypeError, ValueError):
            pass
    return 1 if row.get("is_completion_vulnerable") else 0


def positive_char_spans(row: dict) -> list[tuple[int, int]]:
    """Collect deduplicated positive char ranges from `row['token_labels']`.

    Returns a list of (start_char, end_char) half-open ranges. Sanitizer
    spans are intentionally excluded — they're negative evidence.
    """
    tl = row.get("token_labels") or {}
    seen: set[tuple[int, int]] = set()
    spans: list[tuple[int, int]] = []
    for key in POSITIVE_LABEL_KEYS:
        for entry in tl.get(key, []) or []:
            try:
                s, e = int(entry[0]), int(entry[1])
            except (TypeError, ValueError, IndexError):
                continue
            if e <= s:
                continue
            k = (s, e)
            if k in seen:
                continue
            seen.add(k)
            spans.append(k)
    return spans


def char_spans_to_token_indices(
    char_spans: list[tuple[int, int]],
    offsets: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Map char ranges → (start_tok, end_tok) inclusive token-index ranges.

    `offsets[i] == (s, e)` is the char span for token i. Special tokens
    (e.g. BOS) get (0, 0) from HuggingFace tokenizers — those are skipped
    because their range is empty.

    A char-range maps to every token whose char span overlaps it. Empty
    overlaps (e.g. a sanitizer span that only touches whitespace tokens)
    are dropped by the caller.
    """
    out: list[tuple[int, int]] = []
    for c_s, c_e in char_spans:
        first = last = -1
        for i, (t_s, t_e) in enumerate(offsets):
            if t_s == t_e:
                # Special / empty token. Skip; do not let it anchor a span.
                continue
            if t_e <= c_s:
                continue
            if t_s >= c_e:
                break
            if first < 0:
                first = i
            last = i
        if first >= 0 and last >= first:
            out.append((first, last))
    return out


def find_vuln_span(text: str, line_text: str, offsets: list[tuple[int, int]]) -> tuple[int, int] | None:
    """Legacy fallback: locate vulnerable line via `_vuln_line_text` lookup.

    Used only for rows that predate the SVEN builder and don't have
    `token_labels`. `offsets` must already come from the same tokenizer
    call as the model input (i.e. include special-token (0,0) entries).
    """
    if not line_text:
        return None
    target = line_text.rstrip("\n")
    char_start = text.find(target)
    if char_start < 0:
        ls = target.lstrip()
        char_start = text.find(ls)
        if char_start < 0:
            return None
        target = ls
    char_end = char_start + len(target)
    spans = char_spans_to_token_indices([(char_start, char_end)], offsets)
    return spans[0] if spans else None


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
    fallback_legacy = 0
    fallback_last5 = 0
    t_loop = time.time()
    with torch.inference_mode():
        for eid, row in enumerate(rows):
            code = row["code"]
            label = _row_label(row)

            # Single tokenize call: produces both the model input ids AND the
            # offset mapping under the SAME `add_special_tokens` setting, so
            # there is no off-by-one between hidden states and char spans.
            enc = tokenizer(
                code,
                return_offsets_mapping=True,
                add_special_tokens=True,
                truncation=True,
                max_length=1024,
                return_tensors="pt",
            )
            ids = enc["input_ids"].to(device)
            # `offset_mapping` from return_tensors="pt" is a tensor; convert to
            # a plain list of (int, int) for our mapper.
            om = enc["offset_mapping"][0].tolist()
            offsets: list[tuple[int, int]] = [(int(s), int(e)) for s, e in om]
            out = model(ids, output_hidden_states=True, use_cache=False)
            n_pos = ids.shape[1]
            hs = out.hidden_states

            # --- Resolve token spans ---------------------------------------
            # Preferred: char ranges from the diff-oracle builder.
            char_spans = positive_char_spans(row) if label == 1 else []
            tok_spans: list[tuple[int, int]] = []
            if char_spans:
                tok_spans = char_spans_to_token_indices(char_spans, offsets)
            elif label == 1:
                # Legacy fallback for older datasets without `token_labels`.
                line_text = row.get("_vuln_line_text") or row.get("vuln_line_text") or ""
                if line_text:
                    span = find_vuln_span(code, line_text, offsets)
                    if span is not None:
                        tok_spans = [span]
                        fallback_legacy += 1

            # Label tokens inside any positive span as 1, else 0.
            tok_labels = np.zeros(n_pos, dtype=np.int8)
            if tok_spans:
                for s, e in tok_spans:
                    s = max(0, min(s, n_pos - 1))
                    e = max(s, min(e, n_pos - 1))
                    tok_labels[s : e + 1] = 1
                    spans.append((eid, s, e))
            elif label == 1:
                # Positive example with no usable span — last-5 fallback.
                # Logged so the caller can see how often we degrade.
                fallback_span_start = max(0, n_pos - 5)
                tok_labels[fallback_span_start:] = 1
                spans.append((eid, fallback_span_start, n_pos - 1))
                fallback_last5 += 1

            for li in layer_indices:
                h = hs[li + 1][0, :, :].detach().to("cpu").float().numpy()  # (n_pos, dim)
                per_layer[li].append(h)
            labels.extend(tok_labels.tolist())
            example_ids.extend([eid] * n_pos)

            if (eid + 1) % 50 == 0:
                rate = (eid + 1) / (time.time() - t_loop)
                print(f"[token-extract] {eid+1}/{len(rows)}  {rate:.2f} ex/s", file=sys.stderr)

    print(
        f"[token-extract] skipped {skipped} rows | "
        f"legacy-line fallback: {fallback_legacy} | last-5 fallback: {fallback_last5}",
        file=sys.stderr,
    )
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
