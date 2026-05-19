"""FastAPI routes for the GemmaForge viewer pages.

Two viewers share the same JS/CSS frontend; only the route prefix and the
data source differ:

- ``/api/repos/*`` serves the pre-computed heldout benchmark (manifest +
  leads_spanmax/*.jsonl + repo_scan_report_spanmax.json bundled into the
  Space at ``data/repo_benchmark_heldout/``).
- ``/api/scan/*`` serves the most recent live scan submitted via the Gradio
  "Scan" tab. The handler resolves files from the on-disk clone the scan
  job leaves behind (the scan harness no longer deletes the repo dir at
  the end of ``run_scan``).

Both endpoints emit the same ``{repos, calibration, ...}`` shape so the
shared ``static/repos.js`` works against either one with just a
``BASE`` prefix change.
"""
from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query


# --------------------------- Calibration sidecar ------------------------- #


def load_calibration(path: Path) -> dict:
    """Read ``probe_spanmax_f1.json``. Returns an empty dict if absent so the
    viewer degrades to "no threshold applied" rather than 500-ing."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def calibration_threshold(cal: dict) -> float:
    if not cal:
        return 0.0
    try:
        return float((cal.get("f1_max") or {}).get("threshold") or 0.0)
    except (TypeError, ValueError):
        return 0.0


# --------------------------- JSON sanitiser ------------------------------ #


def clean_nan(obj):
    """Replace NaN/Inf floats with None so the payload is RFC-8259 valid JSON.

    The repo-scan reports come from Python's default json dumper, which emits
    literal NaN tokens that browsers' ``JSON.parse`` rejects.
    """
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    if isinstance(obj, tuple):
        return [clean_nan(v) for v in obj]
    return obj


# --------------------------- Static benchmark ---------------------------- #


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


class StaticBenchmark:
    """Lazy-loaded cache of the heldout manifest + leads + report."""

    def __init__(
        self,
        benchmark_root: Path,
        leads_dir_name: str,
        report_path: Path,
        calibration_path: Path,
    ) -> None:
        self.benchmark_root = benchmark_root
        self.leads_dir = benchmark_root / leads_dir_name
        self.report_path = report_path
        self.calibration_path = calibration_path
        self._index: Optional[dict] = None
        self._index_key: Optional[tuple] = None
        self._lock = threading.Lock()

    def _cache_key(self, tau: float) -> tuple:
        return (
            str(self.benchmark_root),
            str(self.leads_dir),
            self.leads_dir.stat().st_mtime if self.leads_dir.exists() else 0,
            str(self.report_path),
            self.report_path.stat().st_mtime if self.report_path.exists() else 0,
            float(tau),
        )

    def index(self) -> dict:
        cal = load_calibration(self.calibration_path)
        tau = calibration_threshold(cal)
        key = self._cache_key(tau)
        with self._lock:
            if self._index is not None and self._index_key == key:
                return self._index

            manifests = read_jsonl(self.benchmark_root / "manifest.jsonl")
            manifest_by_id = {m["repo_id"]: m for m in manifests if "repo_id" in m}

            report_entries: dict = {}
            if self.report_path.exists():
                try:
                    report = json.loads(self.report_path.read_text(encoding="utf-8"))
                    for entry in report.get("repos", []):
                        rid = entry.get("repo_id")
                        if rid:
                            report_entries[rid] = entry
                except json.JSONDecodeError:
                    pass

            leads_files: dict[str, Path] = {}
            if self.leads_dir.is_dir():
                for path in self.leads_dir.glob("*.jsonl"):
                    leads_files[path.stem] = path

            rows: list[dict] = []
            for repo_id, manifest in manifest_by_id.items():
                lead_path = leads_files.get(repo_id)
                n_leads = 0
                n_leads_above_tau = 0
                top_conf = None
                if lead_path is not None:
                    leads = read_jsonl(lead_path)
                    n_leads = len(leads)
                    if leads:
                        top_conf = max(
                            (float(l.get("gemmaforge_confidence", 0.0)) for l in leads),
                            default=None,
                        )
                    n_leads_above_tau = (
                        sum(
                            1 for l in leads
                            if float(l.get("gemmaforge_confidence", 0.0)) >= tau
                        ) if tau > 0 else n_leads
                    )
                entry = report_entries.get(repo_id, {})
                rows.append({
                    "repo_id": repo_id,
                    "cwe": manifest.get("cwe"),
                    "language": manifest.get("language"),
                    "n_traces": len(manifest.get("vulnerability_traces") or []),
                    "n_files": len(manifest.get("files") or []),
                    "n_leads": n_leads,
                    "n_leads_above_tau": n_leads_above_tau,
                    "top_confidence": top_conf,
                    "first_hit_rank": entry.get("first_hit_rank"),
                    "reciprocal_rank": entry.get("reciprocal_rank"),
                    "has_leads": lead_path is not None,
                })

            def sort_key(r: dict) -> tuple:
                fhr = r["first_hit_rank"]
                return (
                    0 if r["has_leads"] else 1,
                    0 if fhr is not None else 1,
                    fhr if fhr is not None else 0,
                    r["repo_id"],
                )
            rows.sort(key=sort_key)

            self._index = {
                "benchmark_root": str(self.benchmark_root),
                "leads_dir": str(self.leads_dir) if self.leads_dir.exists() else None,
                "report_path": str(self.report_path) if self.report_path.exists() else None,
                "n_repos": len(rows),
                "n_with_leads": sum(1 for r in rows if r["has_leads"]),
                "repos": rows,
                "_manifest_by_id": manifest_by_id,
                "_leads_files": leads_files,
                "_report_entries": report_entries,
                "_calibration": cal,
            }
            self._index_key = key
            return self._index


def build_static_router(bench: StaticBenchmark) -> APIRouter:
    # All custom routes live under ``/gradio_api/*`` because HuggingFace
    # Spaces' edge proxy serves the Gradio SPA shell for any path outside
    # that namespace (including plain ``/api/*``), regardless of what the
    # backend returns. Putting our handlers behind the recognized prefix
    # lets the proxy pass requests through unchanged.
    router = APIRouter(prefix="/gradio_api")

    @router.get("/repos/index")
    def repos_index() -> dict:
        idx = bench.index()
        payload = {
            "benchmark_root": idx["benchmark_root"],
            "leads_dir": idx["leads_dir"],
            "report_path": idx["report_path"],
            "n_repos": idx["n_repos"],
            "n_with_leads": idx["n_with_leads"],
            "repos": idx["repos"],
        }
        cal = idx.get("_calibration") or {}
        if cal:
            payload["calibration"] = {
                "path": str(bench.calibration_path),
                "f1_max": cal.get("f1_max"),
                "auc": cal.get("auc"),
                "n_leads": cal.get("n_leads"),
                "n_pos": cal.get("n_pos"),
                "n_neg": cal.get("n_neg"),
            }
        return clean_nan(payload)

    @router.get("/repos/file")
    def repos_file(repo: str = Query(...), path: str = Query(...)) -> dict:
        idx = bench.index()
        manifest = idx["_manifest_by_id"].get(repo)
        if manifest is None:
            raise HTTPException(404, f"unknown repo_id {repo}")
        allowed = {f.get("path") for f in (manifest.get("files") or [])}
        if path not in allowed:
            raise HTTPException(403, f"path not in manifest: {path}")
        repo_path = bench.benchmark_root / str(manifest.get("repo_path") or "")
        target = (repo_path / path).resolve()
        try:
            target.relative_to(repo_path.resolve())
        except ValueError:
            raise HTTPException(403, "path traversal blocked")
        if not target.is_file():
            raise HTTPException(404, "file missing on disk")
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = target.read_bytes().decode("utf-8", errors="replace")
        return clean_nan({
            "repo_id": repo,
            "path": path,
            "text": text,
            "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        })

    @router.get("/repos/{repo_id}")
    def repos_detail(repo_id: str) -> dict:
        if "/" in repo_id or not repo_id:
            raise HTTPException(404, "invalid repo_id")
        idx = bench.index()
        manifest = idx["_manifest_by_id"].get(repo_id)
        if manifest is None:
            raise HTTPException(404, f"unknown repo_id {repo_id}")
        lead_path = idx["_leads_files"].get(repo_id)
        leads = read_jsonl(lead_path) if lead_path is not None else []
        return clean_nan({
            "repo_id": repo_id,
            "manifest": manifest,
            "leads": leads,
            "report_entry": idx["_report_entries"].get(repo_id),
            "leads_path": str(lead_path) if lead_path else None,
        })

    return router


# --------------------------- Live scan state ----------------------------- #


@dataclass
class LiveScan:
    """Result of the most recent ``run_scan`` invocation."""

    repo_id: str
    repo_url: str
    repo_dir: Path
    files: list[dict] = field(default_factory=list)   # [{path, role}]
    leads: list[dict] = field(default_factory=list)   # gemmaforge.leads/v1
    cwe: Optional[str] = None
    language: Optional[str] = None
    scanned_at: float = field(default_factory=time.time)


class LiveScanState:
    """Thread-safe holder for the most recent live scan.

    Single-slot intentionally — the Space is process-global and we don't
    want to leak file handles to historical scans.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: Optional[LiveScan] = None

    def set(self, scan: LiveScan) -> None:
        with self._lock:
            self._current = scan

    def get(self) -> Optional[LiveScan]:
        with self._lock:
            return self._current

    def clear(self) -> None:
        with self._lock:
            self._current = None


def build_scan_router(state: LiveScanState, calibration_path: Path) -> APIRouter:
    router = APIRouter(prefix="/gradio_api")

    def _row(scan: LiveScan, tau: float) -> dict:
        n_leads = len(scan.leads)
        n_above = sum(
            1 for l in scan.leads
            if float(l.get("gemmaforge_confidence", 0.0)) >= tau
        ) if tau > 0 else n_leads
        top_conf = max(
            (float(l.get("gemmaforge_confidence", 0.0)) for l in scan.leads),
            default=None,
        ) if scan.leads else None
        return {
            "repo_id": scan.repo_id,
            "cwe": scan.cwe,
            "language": scan.language,
            "n_traces": 0,
            "n_files": len(scan.files),
            "n_leads": n_leads,
            "n_leads_above_tau": n_above,
            "top_confidence": top_conf,
            "first_hit_rank": None,
            "reciprocal_rank": None,
            "has_leads": bool(scan.leads),
        }

    @router.get("/scan/index")
    def scan_index() -> dict:
        cal = load_calibration(calibration_path)
        tau = calibration_threshold(cal)
        scan = state.get()
        payload: dict = {
            "benchmark_root": None,
            "leads_dir": "live-scan",
            "report_path": None,
            "n_repos": 1 if scan else 0,
            "n_with_leads": 1 if (scan and scan.leads) else 0,
            "repos": [_row(scan, tau)] if scan else [],
        }
        if cal:
            payload["calibration"] = {
                "path": str(calibration_path),
                "f1_max": cal.get("f1_max"),
                "auc": cal.get("auc"),
                "n_leads": cal.get("n_leads"),
                "n_pos": cal.get("n_pos"),
                "n_neg": cal.get("n_neg"),
            }
        return clean_nan(payload)

    @router.get("/scan/file")
    def scan_file(repo: str = Query(...), path: str = Query(...)) -> dict:
        scan = state.get()
        if scan is None or scan.repo_id != repo:
            raise HTTPException(404, "no scan with that repo_id")
        allowed = {f["path"] for f in scan.files}
        if path not in allowed:
            raise HTTPException(403, f"path not in scan manifest: {path}")
        target = (scan.repo_dir / path).resolve()
        try:
            target.relative_to(scan.repo_dir.resolve())
        except ValueError:
            raise HTTPException(403, "path traversal blocked")
        if not target.is_file():
            raise HTTPException(404, "file missing — scan workdir may have been cleaned")
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = target.read_bytes().decode("utf-8", errors="replace")
        return clean_nan({
            "repo_id": scan.repo_id,
            "path": path,
            "text": text,
            "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        })

    @router.get("/scan/{repo_id}")
    def scan_detail(repo_id: str) -> dict:
        scan = state.get()
        if scan is None or scan.repo_id != repo_id:
            raise HTTPException(404, "no scan with that repo_id")
        manifest = {
            "repo_id": scan.repo_id,
            "repo_url": scan.repo_url,
            "cwe": scan.cwe,
            "language": scan.language,
            "files": scan.files,
            "vulnerability_traces": [],
        }
        return clean_nan({
            "repo_id": scan.repo_id,
            "manifest": manifest,
            "leads": scan.leads,
            "report_entry": None,
            "leads_path": None,
        })

    return router
