"""Build a length-matched evaluation subset of `data/pairs.jsonl`.

Background (GitHub issue #22): in `data/pairs.jsonl` positives are truncated
AFTER the vulnerable line and negatives BEFORE it, so positives are
systematically longer (mean 396 vs 200 chars). A length-only baseline scores
AUC 0.883 on the Py->JS cross-language split versus the probe's 0.907, so we
need a length-controlled evaluation to know how much AUC survives once that
spurious cue is removed.

Strategy:
  1. Group rows by language.
  2. For each positive, pick a same-language negative whose character length
     is within +/-10% of the positive's. Match each negative at most once
     (greedy on the closest absolute length delta).
  3. Discard positives we cannot match. Print per-language pair counts and
     class-conditional length stats so we can confirm the mean/median lengths
     are approximately equal post-matching.
  4. Emit `data/pairs_length_matched.jsonl` containing the kept rows with an
     extra `_orig_idx` field so downstream scripts can filter the row-aligned
     activation matrix.

Constraints: sklearn / numpy / stdlib only. No transformers, no torch.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ROOT / "data" / "pairs.jsonl"
OUT = ROOT / "data" / "pairs_length_matched.jsonl"

LENGTH_TOL = 0.10  # +/- 10% character-length window
SEED = 7


def load_rows() -> list[dict]:
    rows = []
    for i, line in enumerate(PAIRS.read_text().splitlines()):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        r["_orig_idx"] = i
        r["_char_len"] = len(r["code"])
        rows.append(r)
    return rows


def match_per_language(rows: list[dict]) -> list[tuple[int, int]]:
    """Return list of (pos_orig_idx, neg_orig_idx) pairs, stratified by lang.

    Greedy matching: walk positives in deterministic order (sorted by orig_idx),
    and for each positive pick the unused negative with the smallest absolute
    character-length difference, provided it falls inside the +/- LENGTH_TOL
    window. A negative can only be reused if a positive cannot otherwise match.
    """
    pairs: list[tuple[int, int]] = []
    by_lang: dict[str, dict[int, list[dict]]] = defaultdict(lambda: {0: [], 1: []})
    for r in rows:
        by_lang[r["lang"]][r["label"]].append(r)

    for lang, by_label in by_lang.items():
        positives = sorted(by_label[1], key=lambda r: r["_orig_idx"])
        negatives = sorted(by_label[0], key=lambda r: r["_orig_idx"])
        # used_neg[orig_idx] = True once that negative has been claimed.
        used: set[int] = set()
        # Sort negatives once by length for fast windowed search.
        neg_sorted = sorted(negatives, key=lambda r: r["_char_len"])

        for pos in positives:
            target = pos["_char_len"]
            lo = target * (1.0 - LENGTH_TOL)
            hi = target * (1.0 + LENGTH_TOL)
            best = None
            best_delta = None
            for neg in neg_sorted:
                if neg["_orig_idx"] in used:
                    continue
                if neg["_char_len"] < lo:
                    continue
                if neg["_char_len"] > hi:
                    break  # sorted by length, no point continuing
                delta = abs(neg["_char_len"] - target)
                if best_delta is None or delta < best_delta:
                    best = neg
                    best_delta = delta
            if best is not None:
                used.add(best["_orig_idx"])
                pairs.append((pos["_orig_idx"], best["_orig_idx"]))
    return pairs


def main() -> None:
    rows = load_rows()
    by_idx = {r["_orig_idx"]: r for r in rows}
    print(f"loaded {len(rows)} rows from {PAIRS.relative_to(ROOT)}")

    # Pre-matching stats for reference.
    pre_stats: dict[tuple[str, int], list[int]] = defaultdict(list)
    for r in rows:
        pre_stats[(r["lang"], r["label"])].append(r["_char_len"])
    print("\nPRE-match length stats:")
    for (lang, label), lens in sorted(pre_stats.items()):
        print(
            f"  {lang:>10s} label={label}: n={len(lens):4d}  "
            f"mean={statistics.mean(lens):7.1f}  median={statistics.median(lens):6.1f}"
        )

    pairs = match_per_language(rows)
    kept_idx = sorted({i for pair in pairs for i in pair})
    print(f"\nmatched pairs: {len(pairs)}  (kept rows: {len(kept_idx)})")

    per_lang = Counter(by_idx[p[0]]["lang"] for p in pairs)
    print("per-language pair count:")
    for lang, n in sorted(per_lang.items()):
        print(f"  {lang:>10s}: {n} pairs ({2 * n} rows)")

    # Post-matching stats.
    post_stats: dict[tuple[str, int], list[int]] = defaultdict(list)
    for i in kept_idx:
        r = by_idx[i]
        post_stats[(r["lang"], r["label"])].append(r["_char_len"])
    print("\nPOST-match length stats:")
    for (lang, label), lens in sorted(post_stats.items()):
        print(
            f"  {lang:>10s} label={label}: n={len(lens):4d}  "
            f"mean={statistics.mean(lens):7.1f}  median={statistics.median(lens):6.1f}"
        )

    # Persist the kept rows in original order. Keep all original fields plus
    # `_orig_idx` (already injected) so downstream scripts can index back into
    # the row-aligned activation matrix without re-deriving anything.
    with OUT.open("w") as f:
        for i in kept_idx:
            r = {k: v for k, v in by_idx[i].items() if k != "_char_len"}
            f.write(json.dumps(r) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(kept_idx)} rows)")

    if len(pairs) < 150:
        print(
            f"WARNING: only {len(pairs)} matched pairs found, target was >=150."
            " Consider widening LENGTH_TOL."
        )


if __name__ == "__main__":
    main()
