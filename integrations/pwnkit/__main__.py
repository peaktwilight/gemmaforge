"""Tiny CLI over the pwnkit adapter, for demoing the GemmaForge -> pwnkit
pipeline end-to-end.

Run modes:

    # 1. Re-score an existing leads.jsonl through the adapter (no LM, just
    #    pretty-prints and validates the schema).
    python -m integrations.pwnkit leads.jsonl

    # 2. Score the example findings using the live probe (loads Gemma 4 — slow,
    #    requires weights).
    python -m integrations.pwnkit --score integrations/pwnkit/example_findings.json

The first mode is what ``scripts/demo_pipeline.sh`` uses — it lets the demo
flow run without Gemma weights present.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCHEMA_LEADS = "gemmaforge.leads/v1"
REQUIRED = ("schema", "file", "start_line", "end_line", "snippet",
            "gemmaforge_confidence", "model_id")


def _validate_record(rec: dict, lineno: int) -> list[str]:
    errs: list[str] = []
    for key in REQUIRED:
        if key not in rec:
            errs.append(f"line {lineno}: missing required field {key!r}")
    if rec.get("schema") not in (None, SCHEMA_LEADS):
        errs.append(f"line {lineno}: unexpected schema {rec.get('schema')!r}")
    conf = rec.get("gemmaforge_confidence")
    if isinstance(conf, (int, float)) and not (0.0 <= float(conf) <= 1.0):
        errs.append(f"line {lineno}: confidence out of [0,1]: {conf}")
    return errs


def cmd_inspect(jsonl_path: Path) -> int:
    """Read a leads.jsonl, validate against the schema, print a summary table."""
    if not jsonl_path.is_file():
        print(f"error: {jsonl_path} not found", file=sys.stderr)
        return 2
    rows: list[dict] = []
    errs: list[str] = []
    with jsonl_path.open() as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errs.append(f"line {i}: invalid JSON: {e}")
                continue
            errs.extend(_validate_record(rec, i))
            rows.append(rec)

    if errs:
        print("schema errors:", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"# {jsonl_path}: {len(rows)} valid lead(s) (schema={SCHEMA_LEADS})")
    print(f"# {'rank':>4}  {'conf':>5}  {'cwe':<8}  file:lines")
    for rec in rows:
        rank = rec.get("rank", "?")
        conf = rec.get("gemmaforge_confidence", 0.0)
        cwe = rec.get("gemmaforge_top_cwe") or "-"
        loc = f"{rec.get('file')}:{rec.get('start_line')}-{rec.get('end_line')}"
        print(f"  {str(rank):>4}  {conf:>5.2f}  {cwe:<8}  {loc}")
    return 0


def cmd_score(findings_path: Path) -> int:
    """Run the live GemmaForgeFilter over a pwnkit-style findings file."""
    from integrations.pwnkit.adapter import GemmaForgeFilter  # lazy: heavy

    findings = json.loads(findings_path.read_text())
    gf = GemmaForgeFilter()
    for f in findings:
        scored = gf.score_finding(f)
        print(json.dumps(scored))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m integrations.pwnkit")
    ap.add_argument(
        "path",
        type=Path,
        help="leads.jsonl to inspect, or a findings JSON when --score is set.",
    )
    ap.add_argument(
        "--score",
        action="store_true",
        help="Run the live probe over a pwnkit findings file (loads Gemma 4).",
    )
    args = ap.parse_args(argv)
    return cmd_score(args.path) if args.score else cmd_inspect(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
