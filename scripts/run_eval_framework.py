"""Top-level CLI for the GemmaForge probe evaluation framework.

Single entry point that:
  1. Loads activations + pairs for a given layer.
  2. Runs every leakage-aware split.
  3. Adds regex / length / random baselines on each split.
  4. Writes Markdown + JSON reports to `data/eval/`.

Reproduces (and extends) `scripts/eval_splits.py`:
  - keeps the random / group_repo / heldout_cwe / heldout_lang / heldout_source splits
  - adds AUC bootstrap CIs, F1, recall@FPR, calibration (Brier, ECE)
  - adds baselines (random / regex / length)
  - emits machine-readable JSON alongside the Markdown

Usage:
  uv run python scripts/run_eval_framework.py \
    --activations data/activations_v2/activations_layer17.npz \
    --pairs data/pairs.jsonl \
    --out-md data/eval/report.md \
    --out-json data/eval/report.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.eval import baselines as bl_mod  # noqa: E402
from src.eval import probe_io  # noqa: E402
from src.eval import protocol  # noqa: E402
from src.eval import report as report_mod  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--activations", default="data/activations_v2/activations_layer17.npz")
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument("--layer", type=int, default=17)
    ap.add_argument("--out-md", default="data/eval/report.md")
    ap.add_argument("--out-json", default="data/eval/report.json")
    ap.add_argument("--bootstrap-n", type=int, default=1000)
    ap.add_argument("--no-baselines", action="store_true")
    ap.add_argument(
        "--include",
        nargs="*",
        default=["random", "group_repo", "heldout_cwe", "heldout_lang", "heldout_source"],
        help="Which split families to run.",
    )
    args = ap.parse_args()

    X, y = probe_io.load_activations(args.activations)
    rows = probe_io.load_pairs(args.pairs)
    if len(rows) != len(y):
        print(
            f"[run_eval] row count mismatch: pairs={len(rows)} activations={len(y)}",
            file=sys.stderr,
        )
        return 1
    print(
        f"[run_eval] X={X.shape}  y_pos={int(y.sum())}  layer={args.layer}",
        file=sys.stderr,
    )

    baselines = None if args.no_baselines else bl_mod.all_baselines()
    full = protocol.full_report(
        X, y, rows,
        activations_path=args.activations,
        pairs_path=args.pairs,
        layer=args.layer,
        refit=True,
        baselines=baselines,
        include=tuple(args.include),
    )

    report_mod.write_report(full, args.out_md, args.out_json)
    print(f"[run_eval] wrote {args.out_md}", file=sys.stderr)
    print(f"[run_eval] wrote {args.out_json}", file=sys.stderr)
    # Echo top headline to stdout for CI-style consumption.
    print(report_mod.render_markdown(full))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
