#!/usr/bin/env python3
"""Run GemmaForge repo scanning over the generated repo benchmark.

This is the execution half of the repo-level benchmark:

1. Load `data/repo_benchmark/manifest.jsonl`.
2. Construct `GemmaForgeFilter` once.
3. Scan each benchmark repo with `src.scan.scan`.
4. Write `<leads-dir>/<repo_id>.jsonl`.
5. Write an aggregate repo-level eval report.

Example:
    uv run python scripts/run_repo_scan_benchmark.py --max-repos 10

Resume/shard examples:
    uv run python scripts/run_repo_scan_benchmark.py --resume
    uv run python scripts/run_repo_scan_benchmark.py --num-shards 4 --shard-index 0 --resume
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.pwnkit.adapter import GemmaForgeFilter
from src.events import EventSink
from src.eval.repo_protocol import full_repo_report, load_leads_jsonl, load_manifest_index
from src.scan import SCAN_PROFILES, lead_to_record, scan


def write_leads(path: Path, leads: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rank, lead in enumerate(leads):
            f.write(json.dumps(lead_to_record(lead, rank), ensure_ascii=False) + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--benchmark-root", type=Path, default=Path("data/repo_benchmark"))
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--leads-dir", type=Path, default=Path("data/repo_benchmark/leads"))
    ap.add_argument("--out-json", type=Path, default=Path("data/eval/repo_scan_report.json"))
    ap.add_argument("--max-repos", type=int, default=None)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Skip repos whose lead JSONL already exists in --leads-dir.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-scan even if --resume would skip an existing lead file.",
    )
    ap.add_argument("--probe-profile", choices=sorted(SCAN_PROFILES), default="weak-probe")
    ap.add_argument("--top-k", type=int, default=25)
    ap.add_argument("--min-confidence", type=float, default=0.5)
    ap.add_argument("--languages", type=str, default=None)
    ap.add_argument("--probe-path", type=str, default="data/probe.npz")
    ap.add_argument("--per-cwe-probe-path", type=str, default="data/probe_per_cwe.npz")
    ap.add_argument("--model-id", type=str, default="google/gemma-4-E2B-it")
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--token-stride", type=int, default=None)
    ap.add_argument("--event-dir", type=Path, default=None)
    ap.add_argument("--k", type=int, action="append", default=None)
    args = ap.parse_args(argv)

    manifest_path = args.manifest or (args.benchmark_root / "manifest.jsonl")
    if args.num_shards <= 0:
        raise SystemExit("--num-shards must be positive")
    if args.shard_index < 0 or args.shard_index >= args.num_shards:
        raise SystemExit("--shard-index must satisfy 0 <= shard-index < num-shards")

    manifests_all = load_manifest_index(manifest_path)
    manifests = manifests_all
    if args.max_repos is not None:
        manifests = manifests[args.start : args.start + args.max_repos]
    else:
        manifests = manifests[args.start :]
    if args.num_shards > 1:
        manifests = [
            m for i, m in enumerate(manifests)
            if i % args.num_shards == args.shard_index
        ]

    languages = None
    if args.languages:
        languages = {tag.strip() for tag in args.languages.split(",") if tag.strip()}

    profile = SCAN_PROFILES[args.probe_profile]
    max_tokens = args.max_tokens or int(profile["max_tokens"])
    token_stride = args.token_stride or int(profile["token_stride"])

    pending = [
        m for m in manifests
        if args.force
        or not args.resume
        or not (args.leads_dir / f"{m['repo_id']}.jsonl").exists()
    ]
    print(
        f"[repo-scan] setup: model={args.model_id} profile={args.probe_profile} "
        f"repos={len(manifests)} pending={len(pending)} "
        f"shard={args.shard_index}/{args.num_shards} resume={args.resume}",
        file=sys.stderr,
    )
    gf = None
    if pending:
        print("[repo-scan] loading probe/model once", file=sys.stderr)
        gf = GemmaForgeFilter(
            probe_path=args.probe_path,
            per_cwe_probe_path=args.per_cwe_probe_path,
            model_id=args.model_id,
            max_tokens=max_tokens,
            token_stride=token_stride,
            scan_profile=args.probe_profile,
        )

    started = time.time()
    scanned = 0
    skipped = 0
    for i, manifest in enumerate(manifests, start=1):
        repo_id = str(manifest["repo_id"])
        repo_path = args.benchmark_root / str(manifest["repo_path"])
        leads_path = args.leads_dir / f"{repo_id}.jsonl"
        if args.resume and not args.force and leads_path.exists():
            skipped += 1
            print(f"[repo-scan] {i}/{len(manifests)} {repo_id} skip existing", file=sys.stderr)
            continue
        if gf is None:
            raise RuntimeError("internal error: no GemmaForgeFilter for pending scan")
        event_path = None
        if args.event_dir is not None:
            event_path = str(args.event_dir / f"{repo_id}.events.jsonl")
        print(f"[repo-scan] {i}/{len(manifests)} {repo_id}", file=sys.stderr)
        leads = list(scan(
            repo_path,
            gf=gf,
            languages=languages,
            window=int(profile["window"]),
            stride=int(profile["stride"]),
            min_confidence=args.min_confidence,
            top_k=args.top_k,
            events=EventSink(event_path),
        ))
        write_leads(leads_path, leads)
        scanned += 1

    leads_by_repo = {
        str(m["repo_id"]): load_leads_jsonl(args.leads_dir / f"{m['repo_id']}.jsonl")
        for m in manifests
    }
    report = full_repo_report(manifests, leads_by_repo, k_values=args.k or [1, 5, 10, 25])
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    elapsed = time.time() - started
    print(f"[repo-scan] wrote leads to {args.leads_dir}", file=sys.stderr)
    print(f"[repo-scan] wrote report to {args.out_json}", file=sys.stderr)
    print(f"[repo-scan] scanned={scanned} skipped={skipped}", file=sys.stderr)
    print(f"[repo-scan] elapsed_seconds={elapsed:.1f}", file=sys.stderr)
    print(f"[repo-scan] repo_recall@K={report.repo_recall_at_k}", file=sys.stderr)
    print(f"[repo-scan] trace_recall@K={report.trace_recall_at_k}", file=sys.stderr)
    print(f"[repo-scan] precision@K={report.precision_at_k}", file=sys.stderr)
    print(f"[repo-scan] MRR={report.mean_reciprocal_rank:.4f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
