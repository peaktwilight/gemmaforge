"""Repo scanner that emits ranked vulnerability leads as ND-JSON.

Walks a directory tree, chunks each source file into overlapping line windows,
runs the GemmaForge linear + per-CWE probes on each chunk, and writes ranked
leads to stdout in the ``gemmaforge.leads/v1`` schema (see
``docs/leads-schema.md``).

Usage::

    python -m src.scan path/to/repo --top-k 25 --min-confidence 0.5 \
        --languages py,js > leads.jsonl

Pairs with pwnkit's ``--seed-findings`` flag (see
https://github.com/0sec-labs/pwnkit/issues/368) so a smaller GemmaForge probe
can pick leads for a larger agentic hunter to chase.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Iterable, Iterator, Optional

from integrations.pwnkit.adapter import GemmaForgeFilter


SCHEMA_LEADS = "gemmaforge.leads/v1"
SCHEMA_EVENTS = "gemmaforge.events/v1"

# Extension → language family. Used by the --languages filter and for
# selecting reasonable chunking defaults. Conservative on purpose: probe
# was trained on Python / JS / C / C++; languages outside that get scored
# but the consumer should treat them as out-of-distribution.
LANG_BY_EXT = {
    ".py": "py",
    ".js": "js",
    ".jsx": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".ts": "ts",
    ".tsx": "ts",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".java": "java",
    ".go": "go",
    ".rb": "rb",
    ".php": "php",
}

# Directories we never want to descend into. Conservative: only the ones
# that are essentially always machine-generated or vendored.
SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "vendor", "dist", "build", "out", "target",
    ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".next", ".nuxt", ".cache", ".tox",
}


@dataclass
class Chunk:
    file: str           # repo-relative POSIX path
    start_line: int     # 1-indexed, inclusive
    end_line: int       # 1-indexed, inclusive
    text: str


@dataclass
class Lead:
    chunk: Chunk
    confidence: float
    top_cwe: Optional[str]
    layer: int
    model_id: str

    def rank_score(self) -> float:
        bonus = 0.5 if self.top_cwe else 0.0
        return self.confidence * (1.0 + bonus)


# ---------------- walking + chunking ---------------- #


def _iter_files(root: Path, languages: Optional[set[str]]) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        ext = path.suffix.lower()
        lang = LANG_BY_EXT.get(ext)
        if languages is not None and lang not in languages:
            continue
        if lang is None:
            continue  # unknown extension — skip silently
        yield path


def _chunk_lines(
    text: str,
    file_rel: str,
    window: int,
    stride: int,
) -> Iterator[Chunk]:
    """Sliding line-window chunks. Language-agnostic v1."""
    lines = text.splitlines()
    if not lines:
        return
    n = len(lines)
    i = 0
    while i < n:
        end = min(i + window, n)
        body = "\n".join(lines[i:end])
        if body.strip():
            yield Chunk(
                file=file_rel,
                start_line=i + 1,
                end_line=end,
                text=body,
            )
        if end == n:
            return
        i += stride


# ---------------- event emission ---------------- #


class EventSink:
    """Writes ND-JSON events. ``-`` routes to stderr; path opens append."""

    def __init__(self, target: Optional[str]) -> None:
        self._fp: Optional[IO[str]]
        self._owns: bool
        if target is None:
            self._fp = None
            self._owns = False
        elif target == "-":
            self._fp = sys.stderr
            self._owns = False
        else:
            self._fp = open(target, "a", encoding="utf-8")
            self._owns = True

    def emit(self, kind: str, **fields: object) -> None:
        if self._fp is None:
            return
        rec = {"schema": SCHEMA_EVENTS, "ts": time.time(), "kind": kind, **fields}
        self._fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fp.flush()

    def close(self) -> None:
        if self._owns and self._fp is not None:
            self._fp.close()


# ---------------- scan loop ---------------- #


def scan(
    root: Path,
    *,
    gf: GemmaForgeFilter,
    languages: Optional[set[str]],
    window: int,
    stride: int,
    min_confidence: float,
    top_k: Optional[int],
    events: EventSink,
) -> Iterable[Lead]:
    started = time.time()
    files_seen = 0
    chunks_scored = 0
    leads: list[Lead] = []

    events.emit(
        "scan.start",
        repo=str(root),
        model_id=gf.model_id,
        layer=int(gf._layer),
        chunker=f"sliding-window:{window}/{stride}",
    )

    for path in _iter_files(root, languages):
        files_seen += 1
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        file_chunks = list(_chunk_lines(text, rel, window=window, stride=stride))
        events.emit("scan.file", file=rel, chunks=len(file_chunks))

        for ch in file_chunks:
            chunks_scored += 1
            scored = gf.score_snippet(ch.text)
            conf = float(scored["gemmaforge_confidence"])
            top_cwe = scored.get("gemmaforge_top_cwe")
            events.emit(
                "probe.score",
                file=ch.file, start_line=ch.start_line, end_line=ch.end_line,
                confidence=conf, top_cwe=top_cwe,
            )
            if conf < min_confidence:
                continue
            leads.append(Lead(
                chunk=ch,
                confidence=conf,
                top_cwe=top_cwe,
                layer=int(scored["gemmaforge_layer"]),
                model_id=str(scored["model_id"]),
            ))

    leads.sort(key=lambda lead: lead.rank_score(), reverse=True)
    if top_k is not None:
        leads = leads[:top_k]

    for rank, lead in enumerate(leads):
        events.emit(
            "scan.lead",
            file=lead.chunk.file, start_line=lead.chunk.start_line,
            end_line=lead.chunk.end_line, confidence=lead.confidence,
            top_cwe=lead.top_cwe, rank=rank,
        )

    events.emit(
        "scan.end",
        files_seen=files_seen, chunks_scored=chunks_scored,
        leads_emitted=len(leads), elapsed_seconds=round(time.time() - started, 3),
    )
    return leads


def lead_to_record(lead: Lead, rank: int) -> dict:
    rec: dict = {
        "schema": SCHEMA_LEADS,
        "file": lead.chunk.file,
        "start_line": lead.chunk.start_line,
        "end_line": lead.chunk.end_line,
        "snippet": lead.chunk.text,
        "gemmaforge_confidence": round(lead.confidence, 6),
        "gemmaforge_layer": lead.layer,
        "model_id": lead.model_id,
        "rank": rank,
    }
    if lead.top_cwe is not None:
        rec["gemmaforge_top_cwe"] = lead.top_cwe
    return rec


# ---------------- CLI ---------------- #


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="gemmaforge scan",
        description="Walk a repo, score chunks with the GemmaForge probe, emit ranked leads.",
    )
    ap.add_argument("repo", type=Path, help="Path to the repo to scan.")
    ap.add_argument(
        "--top-k", type=int, default=25,
        help="Keep only the top-K leads after ranking. 0 means keep all.",
    )
    ap.add_argument(
        "--min-confidence", type=float, default=0.5,
        help="Drop chunks below this probe confidence before ranking.",
    )
    ap.add_argument(
        "--languages", type=str, default=None,
        help="Comma-separated language tags to keep (py,js,ts,c,cpp,...). Default: all known.",
    )
    ap.add_argument(
        "--window", type=int, default=30,
        help="Chunk window size in lines.",
    )
    ap.add_argument(
        "--stride", type=int, default=20,
        help="Chunk stride in lines (overlap = window - stride).",
    )
    ap.add_argument(
        "--probe-path", type=str, default="data/probe.npz",
        help="Path to the binary probe .npz.",
    )
    ap.add_argument(
        "--per-cwe-probe-path", type=str, default="data/probe_per_cwe.npz",
        help="Path to the per-CWE probe .npz.",
    )
    ap.add_argument(
        "--model-id", type=str, default="google/gemma-4-E2B-it",
        help="HuggingFace model id for the LM used to extract activations.",
    )
    ap.add_argument(
        "--events", type=str, default=None,
        help='Where to write the ND-JSON event stream. "-" for stderr; otherwise a file path (append mode).',
    )
    ap.add_argument(
        "--output", type=str, default="-",
        help='Where to write the ranked leads JSONL. "-" for stdout.',
    )
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    root = args.repo.resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    languages: Optional[set[str]] = None
    if args.languages:
        languages = {tag.strip() for tag in args.languages.split(",") if tag.strip()}

    top_k: Optional[int] = None if args.top_k == 0 else args.top_k

    gf = GemmaForgeFilter(
        probe_path=args.probe_path,
        per_cwe_probe_path=args.per_cwe_probe_path,
        model_id=args.model_id,
    )

    events = EventSink(args.events)
    out_fp: IO[str] = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    try:
        leads = scan(
            root,
            gf=gf,
            languages=languages,
            window=args.window,
            stride=args.stride,
            min_confidence=args.min_confidence,
            top_k=top_k,
            events=events,
        )
        for rank, lead in enumerate(leads):
            out_fp.write(json.dumps(lead_to_record(lead, rank), ensure_ascii=False) + "\n")
    finally:
        events.close()
        if out_fp is not sys.stdout:
            out_fp.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
