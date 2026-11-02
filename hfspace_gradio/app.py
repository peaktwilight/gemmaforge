"""GemmaForge — public-repo scanner on HuggingFace Spaces (Gradio + ZeroGPU).

Paste a public GitHub repo URL, get ranked vulnerability leads back. Runs the
spanmax-trained linear + per-CWE probes (layer 8) on Gemma 4 E2B activations,
sliding window over every supported source file. Sub-τ leads (below the F1-max
threshold calibrated on heldout) are kept in the table but greyed out in the
viewer — same calibration story as the local dashboard.

Two viewers ship in this Space:

- **Scan** tab: paste a URL, run a scan, see ranked leads. After the scan
  finishes, switch to **Last scan** to inspect the leads in the file-level
  visualizer.
- **Heldout benchmark** tab: the precomputed 136-repo SVEN heldout split,
  scored by the same probe. Browse by CWE/lang, click a repo, see truth
  spans + probe overlays.
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
from fastapi.staticfiles import StaticFiles

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
from viewer_routes import (
    LiveScan,
    LiveScanState,
    StaticBenchmark,
    build_scan_router,
    build_static_router,
    calibration_threshold,
    load_calibration,
)


# -------- limits & defaults --------------------------------------------- #

MAX_REPO_BYTES = 100 * 1024 * 1024
MAX_SOURCE_FILES = 400
DEFAULT_MAX_CHUNKS = 800
MAX_CHUNK_CEILING = 2000
TIME_BUDGET_SECONDS = 105
DEFAULT_LANGUAGES = "py,js"
DEFAULT_TOP_K = 25
DEFAULT_MIN_CONFIDENCE = 0.5

HERE = Path(__file__).parent
PROBE_BIN_PATH = str(HERE / "probes" / "probe_spanmax.npz")
PROBE_CWE_PATH = str(HERE / "probes" / "probe_per_cwe_sven.npz")
CALIBRATION_PATH = HERE / "probes" / "probe_spanmax_f1.json"
BENCHMARK_ROOT = HERE / "data" / "repo_benchmark_heldout"
REPORT_PATH = HERE / "data" / "eval" / "repo_scan_report_spanmax.json"
STATIC_DIR = HERE / "static"
MODEL_ID = os.environ.get("GEMMAFORGE_MODEL_ID", "google/gemma-4-E2B-it")

# Eagerly loaded probe (tiny). Heavy model load deferred until first GPU call.
_FILTER: Optional[GemmaForgeFilter] = None
_LIVE_SCAN = LiveScanState()
_STATIC_BENCH = StaticBenchmark(
    benchmark_root=BENCHMARK_ROOT,
    leads_dir_name="leads_spanmax",
    report_path=REPORT_PATH,
    calibration_path=CALIBRATION_PATH,
)
_CALIBRATION = load_calibration(CALIBRATION_PATH)
_TAU = calibration_threshold(_CALIBRATION)


def _get_filter() -> GemmaForgeFilter:
    global _FILTER
    if _FILTER is None:
        _FILTER = GemmaForgeFilter(
            probe_path=PROBE_BIN_PATH,
            per_cwe_probe_path=PROBE_CWE_PATH,
            model_id=MODEL_ID,
            max_tokens=512,
            token_stride=256,
            scan_profile="spanmax",
        )
    return _FILTER


# -------- URL parsing & safe clone -------------------------------------- #

_GITHUB_FULL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
_GITHUB_SHORT_RE = re.compile(r"^(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+)$")


def normalize_github_url(raw: str) -> str:
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


def _repo_id_from_url(url: str) -> str:
    m = _GITHUB_FULL_RE.match(url)
    if not m:
        return "scan"
    return f"{m.group('owner')}--{m.group('repo')}"


def clone_shallow(url: str, dest: Path) -> None:
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
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if proc.returncode != 0:
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
    """Wraps GemmaForgeFilter with a chunk cap and a wall-clock budget."""

    def __init__(self, inner: GemmaForgeFilter, max_calls: int, deadline_at: float) -> None:
        self.inner = inner
        self.max_calls = max_calls
        self.deadline_at = deadline_at
        self.calls = 0
        self.skipped = 0
        self.stop_reason: Optional[str] = None
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
    from gemmaforge_core.scan import LANG_BY_EXT, SKIP_DIRS

    picked: list[Path] = []
    for path in sorted(root.rglob("*")):
        if len(picked) >= cap:
            break
        if not path.is_file():
            continue
        try:
            path.resolve().relative_to(root.resolve())
        except (OSError, RuntimeError, ValueError):
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        ext = path.suffix.lower()
        lang = LANG_BY_EXT.get(ext)
        if lang is None or lang not in languages:
            continue
        try:
            if path.stat().st_size > 256 * 1024:
                continue
        except OSError:
            continue
        picked.append(path)
    return picked


def _prune_to_files(root: Path, keep: list[Path]) -> None:
    keep_set = {p.resolve() for p in keep}
    for path in root.rglob("*"):
        if path.is_file() and path.resolve() not in keep_set:
            try:
                path.unlink()
            except OSError:
                pass


def _retire_previous_scan() -> None:
    """Free the disk used by the previous scan's checkout (if any)."""
    prev = _LIVE_SCAN.get()
    if prev is None:
        return
    try:
        if prev.repo_dir.exists():
            shutil.rmtree(prev.repo_dir.parent, ignore_errors=True)
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

    # Persist the workdir across run_scan() so the viewer can serve files
    # from it. Cleared on the *next* scan via _retire_previous_scan().
    tmpdir = Path(tempfile.mkdtemp(prefix="gemmaforge-scan-"))
    repo_dir = tmpdir / "repo"
    clone_shallow(url, repo_dir)

    size = dir_size_bytes(repo_dir)
    if size > MAX_REPO_BYTES:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise RuntimeError(
            f"Repo is {size / (1024*1024):.1f} MB after shallow clone — "
            f"this Space caps at {MAX_REPO_BYTES // (1024*1024)} MB. "
            f"Try a smaller repo or scan locally."
        )

    files = _trim_file_list(repo_dir, lang_set, MAX_SOURCE_FILES)
    if not files:
        shutil.rmtree(tmpdir, ignore_errors=True)
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
        snippet_lines = (lead.chunk.text or "").strip().splitlines()
        preview = (snippet_lines[0][:120] + "…") if snippet_lines and len(snippet_lines[0]) > 120 else (snippet_lines[0] if snippet_lines else "")
        marker = "" if lead.confidence >= _TAU else "·"  # below-τ marker
        rows.append([
            f"{marker}{rank + 1}".strip(),
            f"{lead.chunk.file}:{lead.chunk.start_line}-{lead.chunk.end_line}",
            lead.top_cwe or "—",
            f"{lead.confidence:.3f}",
            "≥τ" if lead.confidence >= _TAU else "below τ",
            preview,
        ])

    jsonl_path = tmpdir / "leads.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fp:
        for rec in records:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")

    files_seen = sum(1 for e in events.events if e["kind"] == "scan.file")
    total_chunks = gf.calls + gf.skipped
    elapsed = time.time() - t0
    leads_above_tau = sum(1 for l in leads if l.confidence >= _TAU)

    status = (
        f"**Scanned `{url}`** — "
        f"{files_seen} file(s), {gf.calls}/{total_chunks} chunk(s) scored, "
        f"{len(leads)} lead(s) ({leads_above_tau} ≥τ={_TAU:.3f}) in {elapsed:.1f}s. "
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

    # Hand off to the viewer state. Clean up the *previous* scan workdir
    # first so we never carry more than one historical checkout.
    _retire_previous_scan()
    _LIVE_SCAN.set(LiveScan(
        repo_id=_repo_id_from_url(url),
        repo_url=url,
        repo_dir=repo_dir,
        files=[{"path": str(p.relative_to(repo_dir)), "role": ""} for p in files],
        leads=records,
        cwe=None,
        language=None,
    ))
    status += "\n\nOpen the **Last scan** tab to inspect the leads in the file viewer."

    return status, rows, str(jsonl_path)


# -------- Gradio UI ----------------------------------------------------- #

EXAMPLE_REPOS = [
    "expressjs/express",
    "psf/requests",
    "pallets/flask",
]


HEADER_MD = """
# GemmaForge — public-repo vulnerability scan

Paste any public GitHub repo. We shallow-clone it, sweep the source files with
the spanmax-trained linear + per-CWE probes on Gemma 4 E2B layer-8 activations,
and rank the regions that look most CVE-shaped.

**Calibrated thresholding.** Each lead has a confidence in [0, 1]; the *F1-max*
threshold τ on the heldout calibration set is **{tau:.3f}** (P={prec:.2f},
R={rec:.2f}, F1={f1:.2f}, AUC={auc:.2f}). Sub-τ leads are kept in the table for
inspection but are *not* painted on the file viewer — the probe didn't really
fire there.

Runs on ZeroGPU (H200-backed). Caps: **{files} files** / **{chunks} chunks**
default (max {ceiling}) / **{mb} MB** / **{secs}s wall**. Full sweep: clone
[the repo](https://github.com/peaktwilight/gemmaforge) and run `python -m src.scan`.
""".format(
    tau=_TAU,
    prec=(_CALIBRATION.get("f1_max") or {}).get("precision", 0.0),
    rec=(_CALIBRATION.get("f1_max") or {}).get("recall", 0.0),
    f1=(_CALIBRATION.get("f1_max") or {}).get("f1", 0.0),
    auc=_CALIBRATION.get("auc", 0.0),
    files=MAX_SOURCE_FILES,
    chunks=DEFAULT_MAX_CHUNKS,
    ceiling=MAX_CHUNK_CEILING,
    mb=MAX_REPO_BYTES // (1024 * 1024),
    secs=TIME_BUDGET_SECONDS,
)


IFRAME_TEMPLATE = """
<iframe src="{src}"
        style="width:100%; height:78vh; border:1px solid #1c232e; border-radius:6px; background:#07090c;"
        loading="lazy"></iframe>
"""


with gr.Blocks(title="GemmaForge — repo scan", theme=gr.themes.Soft()) as demo:
    gr.Markdown(HEADER_MD)

    with gr.Tabs():
        with gr.Tab("Scan"):
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
                headers=["#", "Location", "Top CWE", "Confidence", "vs τ", "Preview"],
                datatype=["str", "str", "str", "str", "str", "str"],
                wrap=True,
                label="Ranked leads (gemmaforge.leads/v1) — sub-τ rows marked '·'",
            )
            jsonl_file = gr.File(label="Download leads.jsonl", interactive=False)

            run_btn.click(
                fn=run_scan,
                inputs=[repo_url, languages, top_k, min_conf, max_chunks],
                outputs=[status_md, leads_table, jsonl_file],
            )

        with gr.Tab("Last scan"):
            gr.Markdown(
                "File-level viewer over the most recent scan. Click a file to "
                "see lead overlays. Below-τ leads are listed in the bottom "
                "table greyed out but not painted on the code."
            )
            gr.HTML(IFRAME_TEMPLATE.format(src="/gradio_api/viewer/scan.html"))

        with gr.Tab("Heldout benchmark"):
            gr.Markdown(
                "Pre-computed scan of 136 SVEN heldout microrepos. Each repo "
                "has one vulnerable file + a fixed counterpart + a few safe "
                "decoys with line-level ground truth. Same probe, same τ."
            )
            gr.HTML(IFRAME_TEMPLATE.format(src="/gradio_api/viewer/repos.html"))

    gr.Markdown(
        "Caveats: probes classify *representation*, not exploitability. "
        "Spanmax probe at F1-max τ: P=49%, R=35% on heldout — high-precision "
        "above τ, but expect FPs. Full eval suite: "
        "[`RESULTS.md`](https://github.com/peaktwilight/gemmaforge/blob/main/RESULTS.md)."
    )


# -------- Custom FastAPI routes mounted onto Gradio's own app ----------- #
#
# HF Spaces with SDK=gradio + ZeroGPU runs the script and expects
# ``demo.launch()`` to bind the port itself. Running our own uvicorn collides
# with the Spaces runtime (the port is already claimed by the time we try to
# bind). The portable workaround is to inject routes/mounts into the FastAPI
# instance Gradio builds during ``launch()`` via the ``App.create_app``
# constructor, so /api/* and /static/* live on the same server Gradio runs.


def _install_custom_routes() -> None:
    """Inject /api/* + /viewer/* into Gradio's own FastAPI app.

    Gradio defines a catch-all ``/{path:path}`` route to serve its SvelteKit
    frontend; FastAPI matches routes in declaration order, so any route we
    add *after* gradio is shadowed. The fix: prepend our routes/mount to
    ``app.router.routes`` so they match first.
    """
    from starlette.routing import Mount

    original_create_app = gr.routes.App.create_app

    def patched_create_app(*args, **kwargs):
        app = original_create_app(*args, **kwargs)

        static_router = build_static_router(_STATIC_BENCH)
        scan_router = build_scan_router(_LIVE_SCAN, CALIBRATION_PATH)

        @app.get("/gradio_api/healthz")
        def _healthz() -> dict:
            return {"ok": True, "probe": Path(PROBE_BIN_PATH).name, "tau": _TAU}

        added: list = []
        added.extend(static_router.routes)
        added.extend(scan_router.routes)
        healthz_route = app.router.routes.pop()
        added.append(healthz_route)
        if STATIC_DIR.is_dir():
            # Mount under /gradio_api/viewer so HF Spaces' edge proxy passes
            # asset requests straight through (anything outside that prefix
            # gets rewritten to the SvelteKit shell at /).
            added.insert(0, Mount("/gradio_api/viewer", app=StaticFiles(directory=STATIC_DIR), name="viewer"))

        app.router.routes = added + app.router.routes
        return app

    gr.routes.App.create_app = patched_create_app  # type: ignore[method-assign]


_install_custom_routes()


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
    )
