"""Repo scanner that emits ranked vulnerability leads as ND-JSON.

Walks a directory tree, chunks each source file into overlapping line windows,
runs the GemmaForge linear + per-CWE probes on each chunk, and writes ranked
leads to stdout in the ``gemmaforge.leads/v1`` schema (see
``docs/leads-schema.md``).

Usage::

    python -m src.scan path/to/repo --top-k 25 --min-confidence 0.5 \
        --languages py,js > leads.jsonl

Pairs with pwnkit's ``--seed-findings`` flag (see
https://0sec.ai/pwnkit) so a smaller GemmaForge probe
can pick leads for a larger agentic hunter to chase.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Iterable, Iterator, Optional

from gemmaforge_core.adapter import GemmaForgeFilter
from gemmaforge_core.events import SCHEMA_EVENTS, MemoryEventSink as EventSink


SCHEMA_LEADS = "gemmaforge.leads/v1"

SCAN_PROFILES = {
    # Default mode: span-max-trained binary probe at layer 8 (paired with
    # data/probe_per_cwe_sven.npz). Same 30/20 chunker as ``weak-probe``.
    "spanmax": {
        "window": 30,
        "stride": 20,
        "max_tokens": 512,
        "token_stride": 256,
    },
    # Legacy laptop/default mode: layer-17 sklearn LR probe (data/probe.npz).
    "weak-probe": {
        "window": 30,
        "stride": 20,
        "max_tokens": 512,
        "token_stride": 256,
    },
    # Larger initial probe mode: wider code regions and token windows. Use with
    # a matching larger-model probe via --model-id/--probe-path when available.
    "strong-probe": {
        "window": 120,
        "stride": 80,
        "max_tokens": 2048,
        "token_stride": 1024,
    },
}

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

IMPORT_CONTEXT_LANGS = {"py", "js", "ts"}
MAX_IMPORT_CONTEXT_LINES = 80

_JS_REQUIRE_RE = re.compile(
    r"^\s*(?:const|let|var)\s+[\w${}\s,*]+\s*=\s*require\s*\("
)


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
    scan_profile: str = "weak-probe"
    confidence_robust: Optional[float] = None
    top_cwe_score: Optional[float] = None
    scoring_mode: str = "last-token"
    token_count: Optional[int] = None
    windows_scored: Optional[int] = None
    max_tokens: Optional[int] = None

    def rank_score(self) -> float:
        bonus = 0.5 if self.top_cwe else 0.0
        return self.confidence * (1.0 + bonus)


# ---------------- walking + chunking ---------------- #


def _iter_files(root: Path, languages: Optional[set[str]]) -> Iterator[Path]:
    root_resolved = root.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            path.resolve().relative_to(root_resolved)
        except (OSError, RuntimeError, ValueError):
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
    context_blocks: Optional[list[tuple[int, int, str]]] = None,
    max_context_lines: int = MAX_IMPORT_CONTEXT_LINES,
) -> Iterator[Chunk]:
    """Sliding line-window chunks, optionally prefixed with import context."""
    lines = text.splitlines()
    if not lines:
        return
    n = len(lines)
    i = 0
    while i < n:
        end = min(i + window, n)
        body = "\n".join(lines[i:end])
        if body.strip():
            prefix = _context_before_line(
                context_blocks or [],
                before_line=i + 1,
                max_lines=max_context_lines,
            )
            chunk_text = f"{prefix}\n\n{body}" if prefix else body
            yield Chunk(
                file=file_rel,
                start_line=i + 1,
                end_line=end,
                text=chunk_text,
            )
        if end == n:
            return
        i += stride


def _chunk_file(
    text: str,
    file_rel: str,
    lang: Optional[str],
    window: int,
    stride: int,
) -> Iterator[Chunk]:
    """Chunk a file and prepend easy import context for supported languages.

    Python and JS/TS have simple, high-value import forms that are cheap to
    extract without adding heavy parser dependencies. Other languages fall
    back to standard line-window chunks.
    """
    context_blocks = _import_context_blocks(text, lang)
    yield from _chunk_lines(
        text,
        file_rel,
        window=window,
        stride=stride,
        context_blocks=context_blocks,
    )


def _import_context_blocks(text: str, lang: Optional[str]) -> list[tuple[int, int, str]]:
    if lang not in IMPORT_CONTEXT_LANGS:
        return []
    if lang == "py":
        return _python_import_blocks(text)
    if lang in {"js", "ts"}:
        return _javascript_import_blocks(text)
    return []


def _context_before_line(
    blocks: list[tuple[int, int, str]],
    before_line: int,
    max_lines: int,
) -> str:
    """Return import blocks ending before `before_line`, capped from the tail."""
    selected: list[str] = []
    used = 0
    for _start, end, block in reversed(blocks):
        if end >= before_line:
            continue
        block_lines = block.splitlines()
        if used + len(block_lines) > max_lines:
            continue
        selected.append(block)
        used += len(block_lines)
    return "\n".join(reversed(selected))


def _python_import_blocks(text: str) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _regex_python_import_blocks(lines)

    blocks: list[tuple[int, int, str]] = []
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if getattr(node, "col_offset", 0) != 0:
            continue
        start = int(getattr(node, "lineno", 0))
        end = int(getattr(node, "end_lineno", start))
        if start <= 0 or end < start or start > len(lines):
            continue
        block = "\n".join(lines[start - 1:min(end, len(lines))]).strip()
        if block:
            blocks.append((start, min(end, len(lines)), block))
    return blocks


def _regex_python_import_blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            blocks.append((idx, idx, line))
    return blocks


def _javascript_import_blocks(text: str) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    blocks: list[tuple[int, int, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        is_import = (
            stripped.startswith("import ")
            or stripped.startswith("export ") and " from " in stripped
        )
        is_require = bool(_JS_REQUIRE_RE.match(line))
        if not (is_import or is_require):
            i += 1
            continue

        start = i
        end = i
        while end + 1 < len(lines) and ";" not in lines[end] and not lines[end].rstrip().endswith(")"):
            end += 1
        block = "\n".join(lines[start:end + 1]).strip()
        if block:
            blocks.append((start + 1, end + 1, block))
        i = end + 1
    return blocks


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
        scan_profile=getattr(gf, "scan_profile", "weak-probe"),
        chunker=f"line-window:{window}/{stride}",
        scorer=f"token-window:{getattr(gf, 'max_tokens', None)}/{getattr(gf, 'token_stride', None)}",
    )

    for path in _iter_files(root, languages):
        files_seen += 1
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lang = LANG_BY_EXT.get(path.suffix.lower())
        file_chunks = list(_chunk_file(text, rel, lang=lang, window=window, stride=stride))
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
                confidence_robust=scored.get("gemmaforge_confidence_robust"),
                token_count=scored.get("token_count"),
                windows_scored=scored.get("windows_scored"),
            )
            if conf < min_confidence:
                continue
            leads.append(Lead(
                chunk=ch,
                confidence=conf,
                top_cwe=top_cwe,
                layer=int(scored["gemmaforge_layer"]),
                model_id=str(scored["model_id"]),
                scan_profile=str(scored.get("scan_profile") or getattr(gf, "scan_profile", "weak-probe")),
                confidence_robust=(
                    float(scored["gemmaforge_confidence_robust"])
                    if scored.get("gemmaforge_confidence_robust") is not None else None
                ),
                top_cwe_score=(
                    float(scored["gemmaforge_top_cwe_score"])
                    if scored.get("gemmaforge_top_cwe_score") is not None else None
                ),
                scoring_mode=str(scored.get("scoring_mode") or "last-token"),
                token_count=(
                    int(scored["token_count"])
                    if scored.get("token_count") is not None else None
                ),
                windows_scored=(
                    int(scored["windows_scored"])
                    if scored.get("windows_scored") is not None else None
                ),
                max_tokens=(
                    int(scored["max_tokens"])
                    if scored.get("max_tokens") is not None else None
                ),
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
        "scan_profile": lead.scan_profile,
        "scoring_mode": lead.scoring_mode,
    }
    if lead.top_cwe is not None:
        rec["gemmaforge_top_cwe"] = lead.top_cwe
    if lead.confidence_robust is not None:
        rec["gemmaforge_confidence_robust"] = round(lead.confidence_robust, 6)
    if lead.top_cwe_score is not None:
        rec["gemmaforge_top_cwe_score"] = round(lead.top_cwe_score, 6)
    if lead.token_count is not None:
        rec["token_count"] = lead.token_count
    if lead.windows_scored is not None:
        rec["windows_scored"] = lead.windows_scored
    if lead.max_tokens is not None:
        rec["max_tokens"] = lead.max_tokens
    return rec


# ---------------- CLI ---------------- #


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="gemmaforge scan",
        description="Walk a repo, score chunks with the GemmaForge probe, emit ranked leads.",
    )
    ap.add_argument("repo", type=Path, help="Path to the repo to scan.")
    ap.add_argument(
        "--probe-profile",
        choices=sorted(SCAN_PROFILES),
        default="spanmax",
        help=(
            "Initial probe-scan profile. weak-probe uses small overlapping ranges; "
            "strong-probe uses larger ranges and token windows. For strong-probe "
            "with a larger model, pass a matching --model-id and --probe-path."
        ),
    )
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
        "--window", type=int, default=None,
        help="Chunk window size in lines. Defaults come from --probe-profile.",
    )
    ap.add_argument(
        "--stride", type=int, default=None,
        help="Chunk stride in lines (overlap = window - stride). Defaults come from --probe-profile.",
    )
    ap.add_argument(
        "--probe-path", type=str, default="data/probe_spanmax.npz",
        help="Path to the binary probe .npz.",
    )
    ap.add_argument(
        "--per-cwe-probe-path", type=str, default="data/probe_per_cwe_sven.npz",
        help="Path to the per-CWE probe .npz (layer-8, pairs with probe_spanmax).",
    )
    ap.add_argument(
        "--model-id", type=str, default="google/gemma-4-E2B-it",
        help="HuggingFace model id for the LM used to extract activations.",
    )
    ap.add_argument(
        "--max-tokens", type=int, default=None,
        help="Token budget per probe forward pass. Defaults come from --probe-profile.",
    )
    ap.add_argument(
        "--token-stride", type=int, default=None,
        help="Stride for long-snippet token windows. Defaults come from --probe-profile.",
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
    profile = SCAN_PROFILES[args.probe_profile]
    window = args.window or int(profile["window"])
    stride = args.stride or int(profile["stride"])
    max_tokens = args.max_tokens or int(profile["max_tokens"])
    token_stride = args.token_stride or int(profile["token_stride"])

    gf = GemmaForgeFilter(
        probe_path=args.probe_path,
        per_cwe_probe_path=args.per_cwe_probe_path,
        model_id=args.model_id,
        max_tokens=max_tokens,
        token_stride=token_stride,
        scan_profile=args.probe_profile,
    )

    events = EventSink(args.events)
    out_fp: IO[str] = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    try:
        leads = scan(
            root,
            gf=gf,
            languages=languages,
            window=window,
            stride=stride,
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
