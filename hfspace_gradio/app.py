"""GemmaForge — public-repo scanner on HuggingFace Spaces (Gradio + ZeroGPU).

Paste a public GitHub repo URL, get ranked vulnerability leads back. Runs the
shipped GemmaForge linear + per-CWE probes on Gemma 4 E2B activations,
sliding window over every supported source file.

The probe weights and vendored gemmaforge subset are shipped in this Space
(`probes/probe.npz`, `probes/probe_per_cwe.npz`, `gemmaforge_core/`). The
Gemma 4 LM is downloaded on first scan and cached for subsequent calls.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import gradio as gr

try:
    import spaces  # ZeroGPU runtime helper (no-op locally)
except Exception:  # pragma: no cover — local dev without the Spaces SDK
    class _SpacesShim:
        def GPU(self, *_args, **_kwargs):  # noqa: N802 — matches HF API
            def deco(fn):
                return fn
            return deco
    spaces = _SpacesShim()  # type: ignore[assignment]

# Vendored modules live next to this file
from gemmaforge_core.adapter import GemmaForgeFilter
from gemmaforge_core.events import MemoryEventSink
from gemmaforge_core.scan import lead_to_record, scan


# -------- limits & defaults --------------------------------------------- #

# Hard caps so a single scan fits inside one ZeroGPU window.
# ZeroGPU is H200-backed (the `zero-a10g` tier name is legacy from before
# the 2025 upgrade). Gemma 4 E2B runs ~50-100ms per 512-token forward pass
# on H200, so ~1000 chunks fits comfortably inside the 120s window with
# room for the cold model load.
MAX_REPO_BYTES = 100 * 1024 * 1024      # 100 MB after shallow clone
MAX_SOURCE_FILES = 400                  # source files we'll actually score
DEFAULT_MAX_CHUNKS = 800                # default global ceiling (user-tunable)
MAX_CHUNK_CEILING = 2000                # upper bound on the slider
TIME_BUDGET_SECONDS = 105               # bail before the 120s ZeroGPU wall
DEFAULT_LANGUAGES = "py,js"
DEFAULT_TOP_K = 25
DEFAULT_MIN_CONFIDENCE = 0.5

# Where the Space looks for probes / model
PROBE_BIN_PATH = str(Path(__file__).parent / "probes" / "probe.npz")
PROBE_CWE_PATH = str(Path(__file__).parent / "probes" / "probe_per_cwe.npz")
MODEL_ID = os.environ.get("GEMMAFORGE_MODEL_ID", "google/gemma-4-E2B-it")

# Eagerly loaded probe (tiny). Heavy model load deferred until first GPU call.
_FILTER: Optional[GemmaForgeFilter] = None


def _get_filter() -> GemmaForgeFilter:
    global _FILTER
    if _FILTER is None:
        _FILTER = GemmaForgeFilter(
            probe_path=PROBE_BIN_PATH,
            per_cwe_probe_path=PROBE_CWE_PATH,
            model_id=MODEL_ID,
            max_tokens=512,
            token_stride=256,
            scan_profile="weak-probe",
        )
    return _FILTER


# -------- URL parsing & safe clone -------------------------------------- #

_GITHUB_FULL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
_GITHUB_SHORT_RE = re.compile(r"^(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+)$")


def normalize_github_url(raw: str) -> str:
    """Accept `owner/repo`, full https URL, or git URL — return canonical https URL.

    Raises ``ValueError`` for anything else. We refuse SSH and arbitrary git
    hosts to prevent the Space from cloning out to surprising URLs.
    """
    s = raw.strip()
    if not s:
        raise ValueError("Please paste a public GitHub repo URL.")
    m = _GITHUB_FULL_RE.match(s)
    if m:
        owner, repo = m.group("owner"), m.group("repo")
    else:
        m = _GITHUB_SHORT_RE.match(s)
        if not m:
            raise ValueError(
                "URL must look like `owner/repo` or `https://github.com/owner/repo`."
            )
        owner, repo = m.group("owner"), m.group("repo")
    if owner.startswith(".") or repo.startswith("."):
        raise ValueError("Invalid owner/repo name.")
    return f"https://github.com/{owner}/{repo}.git"


def clone_shallow(url: str, dest: Path) -> None:
    """Shallow clone with no blob filter for speed and bounded size."""
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        "--quiet",
        url, str(dest),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},  # no interactive auth
    )
    if proc.returncode != 0:
        # Surface the first line of stderr — enough to tell "repo not found" from a network failure.
        msg = (proc.stderr or proc.stdout or "git clone failed").strip().splitlines()
        first = msg[0] if msg else "git clone failed"
        raise RuntimeError(f"Clone failed: {first}")


def dir_size_bytes(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


# -------- scan harness with hard caps ----------------------------------- #


class CappedFilter:
    """Wraps GemmaForgeFilter with a chunk cap and a wall-clock budget.

    When either limit is hit we stop calling the real probe and return a
    zero-confidence stub. ``scan()`` then drops these chunks via the
    ``min_confidence`` filter and finishes normally — so all leads collected
    before the cap survive, and the user gets partial results instead of an
    error.
    """

    def __init__(self, inner: GemmaForgeFilter, max_calls: int, deadline_at: float) -> None:
        self.inner = inner
        self.max_calls = max_calls
        self.deadline_at = deadline_at
        self.calls = 0
        self.skipped = 0
        self.stop_reason: Optional[str] = None
        # Expose the inner's identifying fields so scan.py can serialise leads.
        self.model_id = inner.model_id
        self._layer = inner._layer  # noqa: SLF001
        self.scan_profile = inner.scan_profile
        self.max_tokens = inner.max_tokens
        self.token_stride = inner.token_stride

    def _stub_score(self) -> dict:
        return {
            "gemmaforge_confidence": 0.0,
            "gemmaforge_confidence_robust": 0.0,
            "gemmaforge_top_cwe": None,
            "gemmaforge_top_cwe_score": None,
            "gemmaforge_cwe_ranking": [],
            "gemmaforge_layer": self._layer,
            "model_id": self.model_id,
            "scan_profile": self.scan_profile,
            "scoring_mode": "skipped",
            "token_count": 0,
            "windows_scored": 0,
            "max_tokens": self.max_tokens,
            "token_stride": self.token_stride,
        }

    def score_snippet(self, snippet: str) -> dict:
        if self.stop_reason is not None:
            self.skipped += 1
            return self._stub_score()
        if self.calls >= self.max_calls:
            self.stop_reason = "max_chunks"
            self.skipped += 1
            return self._stub_score()
        if time.time() >= self.deadline_at:
            self.stop_reason = "time_budget"
            self.skipped += 1
            return self._stub_score()
        self.calls += 1
        return self.inner.score_snippet(snippet)


def _trim_file_list(root: Path, languages: set[str], cap: int) -> list[Path]:
    """Walk the repo, pick up to `cap` source files matching the language set."""
    from gemmaforge_core.scan import LANG_BY_EXT, SKIP_DIRS

    picked: list[Path] = []
    for path in sorted(root.rglob("*")):
        if len(picked) >= cap:
            break
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        ext = path.suffix.lower()
        lang = LANG_BY_EXT.get(ext)
        if lang is None or lang not in languages:
            continue
        try:
            if path.stat().st_size > 256 * 1024:
                continue  # skip giant single files
        except OSError:
            continue
        picked.append(path)
    return picked


def _prune_to_files(root: Path, keep: list[Path]) -> None:
    """Delete every file in `root` that isn't in `keep`, so scan() only sees those."""
    keep_set = {p.resolve() for p in keep}
    for path in root.rglob("*"):
        if path.is_file() and path.resolve() not in keep_set:
            try:
                path.unlink()
            except OSError:
                pass


# -------- ZeroGPU entry point ------------------------------------------- #


@spaces.GPU(duration=120)
def run_scan(
    repo_url: str,
    languages: str,
    top_k: int,
    min_confidence: float,
    max_chunks: int,
) -> tuple[str, list[list[str]], Optional[str]]:
    """Clone + scan. Returns (status_md, leads_rows, jsonl_path)."""
    t0 = time.time()
    url = normalize_github_url(repo_url)
    lang_set = {tag.strip() for tag in (languages or DEFAULT_LANGUAGES).split(",") if tag.strip()}
    chunk_cap = max(50, min(int(max_chunks or DEFAULT_MAX_CHUNKS), MAX_CHUNK_CEILING))

    tmpdir = Path(tempfile.mkdtemp(prefix="gemmaforge-scan-"))
    repo_dir = tmpdir / "repo"
    try:
        clone_shallow(url, repo_dir)

        size = dir_size_bytes(repo_dir)
        if size > MAX_REPO_BYTES:
            raise RuntimeError(
                f"Repo is {size / (1024*1024):.1f} MB after shallow clone — "
                f"this Space caps at {MAX_REPO_BYTES // (1024*1024)} MB. "
                f"Try a smaller repo or scan locally."
            )

        files = _trim_file_list(repo_dir, lang_set, MAX_SOURCE_FILES)
        if not files:
            raise RuntimeError(
                f"No source files matching `{','.join(sorted(lang_set))}` found in the repo."
            )
        _prune_to_files(repo_dir, files)

        deadline_at = t0 + TIME_BUDGET_SECONDS
        gf = CappedFilter(_get_filter(), max_calls=chunk_cap, deadline_at=deadline_at)
        events = MemoryEventSink()

        leads = list(scan(
            repo_dir,
            gf=gf,  # type: ignore[arg-type]
            languages=lang_set,
            window=30,
            stride=20,
            min_confidence=float(min_confidence),
            top_k=int(top_k) or None,
            events=events,
        ))

        rows: list[list[str]] = []
        records: list[dict] = []
        for rank, lead in enumerate(leads):
            rec = lead_to_record(lead, rank)
            records.append(rec)
            snippet_preview = (lead.chunk.text or "").strip().splitlines()[0:1]
            preview = (snippet_preview[0][:120] + "…") if snippet_preview and len(snippet_preview[0]) > 120 else (snippet_preview[0] if snippet_preview else "")
            rows.append([
                str(rank + 1),
                f"{lead.chunk.file}:{lead.chunk.start_line}-{lead.chunk.end_line}",
                lead.top_cwe or "—",
                f"{lead.confidence:.3f}",
                preview,
            ])

        jsonl_path = tmpdir / "leads.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as fp:
            for rec in records:
                fp.write(json.dumps(rec, ensure_ascii=False) + "\n")

        files_seen = sum(1 for e in events.events if e["kind"] == "scan.file")
        total_chunks = gf.calls + gf.skipped
        elapsed = time.time() - t0

        status = (
            f"**Scanned `{url}`** — "
            f"{files_seen} file(s), {gf.calls}/{total_chunks} chunk(s) scored, "
            f"{len(leads)} lead(s) in {elapsed:.1f}s. "
            f"Probe layer {gf._layer}, model `{gf.model_id}`."
        )
        if gf.stop_reason == "max_chunks":
            status += (
                f"\n\n⚠️ Hit the {chunk_cap}-chunk cap — {gf.skipped} chunk(s) skipped. "
                f"Bump the slider (max {MAX_CHUNK_CEILING}) or scan locally for a full sweep."
            )
        elif gf.stop_reason == "time_budget":
            status += (
                f"\n\n⚠️ Hit the {TIME_BUDGET_SECONDS}s time budget — {gf.skipped} chunk(s) skipped. "
                f"Lower top-K / tighten languages, or scan locally."
            )
        return status, rows, str(jsonl_path)
    finally:
        # Keep the JSONL for download; just clear the repo checkout.
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)


# -------- Gradio UI ----------------------------------------------------- #


EXAMPLE_REPOS = [
    "expressjs/express",
    "psf/requests",
    "pallets/flask",
]


HEADER_MD = """
# GemmaForge — public-repo vulnerability scan

Paste any public GitHub repo. We shallow-clone it, sweep the source files with the
shipped GemmaForge linear + per-CWE probes on Gemma 4 E2B activations, and rank
the regions that look most CVE-shaped.

**Two-tier pipeline.** Tier 1 (this Space) is the activation-probe triage —
laptop-class, fast, high-recall. Tier 2 ([`pwnkit`](https://github.com/0sec-labs/pwnkit)
on a workstation) drives Gemma 4 27B as an agent that reads files and corroborates
each lead. Output here is the same `gemmaforge.leads/v1` schema pwnkit consumes
via `--seed-findings`.

Runs on ZeroGPU (H200-backed). Each scan caps at **{files} files** /
**{chunks} chunks** by default (slider goes up to {ceiling}) / **{mb} MB** /
**{secs}s wall** — fits the 120s ZeroGPU window. For unbounded scans clone
[the repo](https://github.com/peaktwilight/gemmaforge) and run `python -m src.scan`.
""".format(
    files=MAX_SOURCE_FILES,
    chunks=DEFAULT_MAX_CHUNKS,
    ceiling=MAX_CHUNK_CEILING,
    mb=MAX_REPO_BYTES // (1024 * 1024),
    secs=TIME_BUDGET_SECONDS,
)


with gr.Blocks(title="GemmaForge — repo scan", theme=gr.themes.Soft()) as demo:
    gr.Markdown(HEADER_MD)

    with gr.Row():
        with gr.Column(scale=3):
            repo_url = gr.Textbox(
                label="Public GitHub repo",
                placeholder="owner/repo  —  or  https://github.com/owner/repo",
                value="expressjs/express",
            )
        with gr.Column(scale=1):
            languages = gr.Textbox(
                label="Languages (comma-sep)",
                value=DEFAULT_LANGUAGES,
                info="Subset of: py, js, ts, c, cpp",
            )

    with gr.Row():
        top_k = gr.Slider(1, 50, value=DEFAULT_TOP_K, step=1, label="Top-K leads")
        min_conf = gr.Slider(0.0, 0.95, value=DEFAULT_MIN_CONFIDENCE, step=0.05, label="Min probe confidence")
        max_chunks = gr.Slider(
            50, MAX_CHUNK_CEILING, value=DEFAULT_MAX_CHUNKS, step=50,
            label="Max chunks",
            info="Probe forward-pass budget. Higher → deeper coverage, longer scan.",
        )
        run_btn = gr.Button("Scan repo", variant="primary")

    gr.Examples(
        examples=[[repo] for repo in EXAMPLE_REPOS],
        inputs=[repo_url],
        label="Try a small open-source repo",
    )

    status_md = gr.Markdown()
    leads_table = gr.Dataframe(
        headers=["#", "Location", "Top CWE", "Confidence", "Preview"],
        datatype=["str", "str", "str", "str", "str"],
        wrap=True,
        label="Ranked leads (gemmaforge.leads/v1)",
    )
    jsonl_file = gr.File(label="Download leads.jsonl", interactive=False)

    run_btn.click(
        fn=run_scan,
        inputs=[repo_url, languages, top_k, min_conf, max_chunks],
        outputs=[status_md, leads_table, jsonl_file],
    )

    gr.Markdown(
        "Caveats: probes classify *representation*, not exploitability. "
        "AUC 0.907 cross-language (Py→JS, in-distribution = 0.963). "
        "Full eval suite: [`RESULTS.md`](https://github.com/peaktwilight/gemmaforge/blob/main/RESULTS.md)."
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch()
