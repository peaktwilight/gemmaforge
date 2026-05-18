#!/usr/bin/env python3
"""Build a vulnerability dataset from SVEN with diff-derived token labels.

One upstream SVEN row -> two output rows:

  VULN (label=1): the full `func_src_before` (the buggy function).
                  token_labels.vulnerable_line / .evidence cover every
                  character the human-authored patch removed or changed.
  SAFE (label=0): the full `func_src_after` (the patched function).
                  token_labels are all empty -- the bug is literally
                  diffed away in this version.

Both rows share `_func_name` + `_file_name`, so leakage-aware splits
can keep paired before/after together. All labels are
`label_confidence: "diff_oracle"` -- they come from a real commit,
not from regex.

Output schema (one JSON object per line)
----------------------------------------
{
  "code":  "<full function source>",
  "label": 1 | 0,
  "is_completion_vulnerable": true | false,
  "cwe":   "CWE-089" | null,
  "lang":  "python" | "c" | "cpp" | ...,
  "source": "SVEN-before" | "SVEN-after",
  "vuln_type": "cwe-089",
  "token_labels": {
    "sink":            [[start, end], ...],   # always empty for now
    "source":          [[start, end], ...],
    "sanitizer":       [[start, end], ...],
    "evidence":        [[start, end], ...],   # = vulnerable_line for SVEN
    "vulnerable_line": [[start, end], ...]    # char offsets into `code`
  },
  "label_confidence": "diff_oracle",
  "_func_name":   "<function>",
  "_file_name":   "<source path>"
}

Usage
-----
    uv run scripts/build_dataset.py                       # default out
    uv run scripts/build_dataset.py --out data/foo.jsonl
    uv run scripts/build_dataset.py --max-rows 100 --seed 7
    uv run scripts/build_dataset.py --lang python --cwe CWE-089
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "data" / "dataset.jsonl"

EMPTY_TOKEN_LABELS = {
    "sink": [],
    "source": [],
    "sanitizer": [],
    "evidence": [],
    "vulnerable_line": [],
}

EXT_TO_LANG = {
    "py": "python", "js": "javascript", "ts": "typescript",
    "c": "c", "cc": "cpp", "cpp": "cpp", "cxx": "cpp", "h": "c", "hpp": "cpp",
    "java": "java", "go": "go", "rb": "ruby", "php": "php", "rs": "rust",
}


def infer_lang(file_name: str | None) -> str:
    if not file_name or "." not in file_name:
        return "c"
    return EXT_TO_LANG.get(file_name.rsplit(".", 1)[-1].lower(), "c")


def normalize_cwe(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.upper() if raw.lower().startswith("cwe-") else raw


def merge_overlapping(spans: Iterable[list[int]]) -> list[list[int]]:
    out: list[list[int]] = []
    for s, e in sorted([list(x) for x in spans if x[0] < x[1]]):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def clip(s: int, e: int, lo: int, hi: int) -> tuple[int, int] | None:
    a, b = max(s, lo), min(e, hi)
    return (a, b) if a < b else None


def vuln_spans_in_before(src: str, char_changes: dict, line_changes: dict) -> list[list[int]]:
    """Char ranges within `func_src_before` that the patch removed.

    Prefers char-level diff. Falls back to line-level diff (converted to
    char offsets) when char info is missing. Returns merged non-overlapping
    spans, clipped to `len(src)`.
    """
    n = len(src)
    spans: list[list[int]] = []

    for entry in (char_changes or {}).get("deleted") or []:
        s, e = entry.get("char_start"), entry.get("char_end")
        if isinstance(s, int) and isinstance(e, int):
            c = clip(s, e, 0, n)
            if c:
                spans.append([c[0], c[1]])
    if spans:
        return merge_overlapping(spans)

    # No char-level diff -> fall back to line-level diff.
    line_offsets = [0]
    for i, ch in enumerate(src):
        if ch == "\n":
            line_offsets.append(i + 1)

    for entry in (line_changes or {}).get("deleted") or []:
        ln = entry.get("line_no")
        if not isinstance(ln, int) or ln < 1:
            continue
        if ln - 1 >= len(line_offsets):
            continue
        ls = line_offsets[ln - 1]
        le = line_offsets[ln] if ln < len(line_offsets) else n
        c = clip(ls, le, 0, n)
        if c:
            spans.append([c[0], c[1]])

    return merge_overlapping(spans)


def emit_pairs(max_rows: int | None) -> Iterable[dict]:
    """Yield (vuln_row, safe_row) for each usable SVEN upstream pair."""
    from datasets import load_dataset  # type: ignore

    emitted = 0
    for split in ("train", "val"):
        ds = load_dataset("bstee615/sven", split=split)
        for row in ds:
            before = row.get("func_src_before") or ""
            after = row.get("func_src_after") or ""
            if not before or not after:
                continue

            cwe_raw = row.get("vul_type") or ""
            cwe = normalize_cwe(cwe_raw) or None
            lang = infer_lang(row.get("file_name"))
            func_name = row.get("func_name") or None
            file_name = row.get("file_name") or None

            spans = vuln_spans_in_before(
                before,
                row.get("char_changes") or {},
                row.get("line_changes") or {},
            )
            if not spans:
                # No usable diff info -> can't supervise tokens, skip.
                continue

            yield {
                "code": before,
                "label": 1,
                "is_completion_vulnerable": True,
                "cwe": cwe,
                "lang": lang,
                "source": "SVEN-before",
                "vuln_type": cwe_raw or None,
                "token_labels": {
                    **EMPTY_TOKEN_LABELS,
                    "vulnerable_line": spans,
                    "evidence": spans,
                },
                "label_confidence": "diff_oracle",
                "_func_name": func_name,
                "_file_name": file_name,
            }
            yield {
                "code": after,
                "label": 0,
                "is_completion_vulnerable": False,
                "cwe": cwe,                # informative for stratified eval
                "lang": lang,
                "source": "SVEN-after",
                "vuln_type": cwe_raw or None,
                "token_labels": {k: [] for k in EMPTY_TOKEN_LABELS},
                "label_confidence": "diff_oracle",
                "_func_name": func_name,
                "_file_name": file_name,
            }
            emitted += 2
            if max_rows and emitted >= max_rows:
                return


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help="Output JSONL path (default: data/dataset.jsonl).",
    )
    ap.add_argument(
        "--max-rows", type=int, default=None,
        help="Cap total emitted rows (positives + negatives combined).",
    )
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument(
        "--lang", action="append", default=None,
        help="Restrict to these langs (repeatable).",
    )
    ap.add_argument(
        "--cwe", action="append", default=None,
        help="Restrict to these CWEs (repeatable).",
    )
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows: list[dict] = []
    for r in emit_pairs(args.max_rows):
        if args.lang and r["lang"] not in args.lang:
            continue
        if args.cwe and r["cwe"] not in args.cwe:
            continue
        rows.append(r)

    rng.shuffle(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    pos = sum(1 for r in rows if r["label"] == 1)
    neg = len(rows) - pos
    by_lang: dict[str, int] = {}
    by_cwe: dict[str, int] = {}
    for r in rows:
        by_lang[r["lang"]] = by_lang.get(r["lang"], 0) + 1
        by_cwe[r["cwe"] or "-"] = by_cwe.get(r["cwe"] or "-", 0) + 1
    print(f"[ds] wrote {args.out}: {len(rows)} rows ({pos} pos / {neg} neg)", file=sys.stderr)
    print(f"[ds] by lang: {by_lang}", file=sys.stderr)
    top_cwes = sorted(by_cwe.items(), key=lambda kv: -kv[1])[:8]
    print(f"[ds] top CWEs: {top_cwes}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
