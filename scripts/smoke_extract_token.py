"""Smoke test for the fixed `src/extract_token_activations.py` char-range path.

The previous extractor only knew how to find a vuln span via the legacy
`_vuln_line_text` field; on the SVEN-derived dataset (which writes
`token_labels` char ranges instead) it silently fell back to "label the
last 5 tokens" -- defeating the diff-derived spans (issue #17).

This script:
  1. Loads the first 10 rows of `data/pairs_rich.jsonl`.
  2. Loads only the Gemma 4 tokenizer (no model weights -- cheap).
  3. Tokenizes each row the same way the extractor does (single call,
     `add_special_tokens=True`, `return_offsets_mapping=True`) and runs
     the new `positive_char_spans` + `char_spans_to_token_indices`
     mapping logic.
  4. Asserts that at least 6/10 positive rows produce a non-trivial token
     labelling -- i.e. the union of token-index ranges resolved from
     `token_labels` covers >=3 tokens (so we're definitively NOT just
     falling back to "label the last 5 tokens"). For SVEN rows the
     positive char ranges often collapse to 1-2 deduplicated entries
     (evidence == vulnerable_line, plus an optional sink), so we check
     token *coverage* rather than the number of distinct spans.

Usage:
    uv run scripts/smoke_extract_token.py
    uv run scripts/smoke_extract_token.py --pairs data/pairs_rich.jsonl --n 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.extract_token_activations import (  # noqa: E402
    _row_label,
    char_spans_to_token_indices,
    positive_char_spans,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pairs", type=Path, default=REPO_ROOT / "data" / "pairs_rich.jsonl")
    ap.add_argument("--model", default="google/gemma-4-E2B-it")
    ap.add_argument("--n", type=int, default=10, help="rows to sample from the head")
    ap.add_argument("--min-positives", type=int, default=6,
                    help="min positive rows that must produce non-trivial token labels")
    ap.add_argument("--min-tokens", type=int, default=3,
                    help="min total tokens covered by positive spans per row to count as 'success'")
    args = ap.parse_args()

    from transformers import AutoTokenizer  # type: ignore

    tok = AutoTokenizer.from_pretrained(args.model)

    rows: list[dict] = []
    with args.pairs.open() as f:
        for i, line in enumerate(f):
            if i >= args.n:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    print(f"[smoke] loaded {len(rows)} rows from {args.pairs}")

    n_positive = 0
    n_success = 0
    n_total_tokens_covered = 0
    n_legacy_lookup = 0

    for eid, row in enumerate(rows):
        label = _row_label(row)
        if label != 1:
            print(f"[smoke] row {eid}: label=0, skipping span check")
            continue
        n_positive += 1

        code = row["code"]
        char_spans = positive_char_spans(row)

        # Same tokenizer call shape as the fixed extractor.
        enc = tok(
            code,
            return_offsets_mapping=True,
            add_special_tokens=True,
            truncation=True,
            max_length=1024,
        )
        offsets = [(int(s), int(e)) for s, e in enc["offset_mapping"]]

        if not char_spans:
            n_legacy_lookup += 1
            print(f"[smoke] row {eid}: NO token_labels char spans (would fall back)")
            continue

        tok_spans = char_spans_to_token_indices(char_spans, offsets)
        # Count distinct token indices covered (union, so duplicates collapse).
        covered: set[int] = set()
        for s, e in tok_spans:
            for i in range(s, e + 1):
                covered.add(i)
        tokens_covered = len(covered)
        n_total_tokens_covered += tokens_covered
        ok = tokens_covered >= args.min_tokens
        n_success += 1 if ok else 0
        print(
            f"[smoke] row {eid}: char_spans={len(char_spans)} "
            f"tok_spans={tok_spans} tokens_covered={tokens_covered} "
            f"{'OK' if ok else 'WEAK'}"
        )

    print(
        f"\n[smoke] summary: positives={n_positive} "
        f"success_>={args.min_tokens}_tokens_covered={n_success} "
        f"legacy_lookup_fallback_rows={n_legacy_lookup} "
        f"total_tokens_covered={n_total_tokens_covered}"
    )

    if n_success < args.min_positives:
        print(
            f"[smoke] FAIL: only {n_success}/{n_positive} positive rows "
            f"covered >= {args.min_tokens} tokens (needed {args.min_positives})",
            file=sys.stderr,
        )
        return 1
    print(
        f"[smoke] PASS: {n_success}/{n_positive} positive rows covered "
        f">= {args.min_tokens} tokens (needed {args.min_positives})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
