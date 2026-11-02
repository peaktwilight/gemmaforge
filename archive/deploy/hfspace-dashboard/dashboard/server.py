"""Small SSE-proxying server that fronts the GemmaForge live dashboard.

Endpoints:
  GET /                 -> dashboard/index.html
  GET /style.css        -> dashboard/style.css
  GET /sse/stream       -> proxies SSE from localhost:8787/stream (Panel 1)
  GET /sse/events       -> watches an ND-JSON events file (Panels 2/3),
                           or replays examples/leads.jsonl synthetically
  GET /sse/pwnkit       -> synthetic queued/exploit/report stream (Panel 4)

Usage:
  python -m dashboard.server                       # demo mode (replays leads.jsonl)
  python -m dashboard.server --events-file path    # live mode (tails the file)
  python -m dashboard.server --port 8888

The dashboard works with zero dependencies beyond Python's stdlib + a local
copy of ``examples/leads.jsonl``. The streaming probe server on :8787 only
needs to be running for Panel 1; the other three panels degrade gracefully.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen
from urllib.error import URLError


DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent
DEFAULT_LEADS = REPO_ROOT / "examples" / "leads.jsonl"

# In-memory run registry. Keys (API tokens) live only for the lifetime of
# the run + a short grace period — never written to disk, never logged.
# {run_id: {"api_key": "...", "model": "...", "base_url": "...",
#           "scan_id": None | "...", "process": Popen | None,
#           "started_at": float, "done": bool}}
_RUNS: dict[str, dict] = {}
_RUNS_LOCK = threading.Lock()


def _new_run_id() -> str:
    return secrets.token_urlsafe(12)


def _sse_headers(handler: BaseHTTPRequestHandler) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()


def _send_static(handler: BaseHTTPRequestHandler, path: Path, ctype: str) -> None:
    if not path.exists():
        handler.send_response(404)
        handler.end_headers()
        handler.wfile.write(b"not found")
        return
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    handler.wfile.write(path.read_bytes())


def _emit(handler: BaseHTTPRequestHandler, obj: dict) -> bool:
    """Write one SSE frame. Returns False once the client has gone away."""
    try:
        handler.wfile.write(f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode())
        handler.wfile.flush()
        return True
    except (BrokenPipeError, ConnectionResetError):
        return False


def proxy_stream(handler: BaseHTTPRequestHandler, qs: dict) -> None:
    """Proxy SSE from the streaming probe server at :8787.

    We do a streaming GET via urlopen and re-emit each line as soon as it
    arrives. The upstream server already speaks `text/event-stream`, so we
    just relay the framing.
    """
    from urllib.parse import quote

    prompt = qs.get("prompt", [""])[0]
    max_tokens = qs.get("max_tokens", ["200"])[0]
    upstream_url = (
        f"http://localhost:8787/stream"
        f"?prompt={quote(prompt, safe='')}"
        f"&max_tokens={quote(max_tokens, safe='')}"
    )
    _sse_headers(handler)
    try:
        with urlopen(upstream_url, timeout=600) as resp:
            for raw in resp:
                if not raw:
                    continue
                try:
                    handler.wfile.write(raw)
                    handler.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
    except URLError as e:
        _emit(handler, {"event": "error", "message": f"upstream :8787 unreachable: {e.reason}"})
    except Exception as e:  # noqa: BLE001
        _emit(handler, {"event": "error", "message": str(e)})


def replay_events_demo(handler: BaseHTTPRequestHandler, leads_path: Path) -> None:
    """Synthesise a scan run from a pre-computed leads.jsonl file.

    For each lead we emit: scan.file (once per distinct file), a few
    probe.score events leading up to it, a scan.lead, and a scan.lead.record
    (carries the snippet so Panel 3 can colour-render it). At the end we
    emit scan.end. Total walkthrough ~10 seconds.
    """
    if not leads_path.exists():
        _emit(handler, {
            "schema": "gemmaforge.events/v1", "ts": time.time(),
            "kind": "scan.end",
            "files_seen": 0, "chunks_scored": 0, "leads_emitted": 0,
            "elapsed_seconds": 0,
        })
        return

    leads = []
    for line in leads_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            leads.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not _emit(handler, {
        "schema": "gemmaforge.events/v1", "ts": time.time(),
        "kind": "scan.start",
        "repo": str(REPO_ROOT / "examples" / "vuln-express-app"),
        "model_id": leads[0].get("model_id", "google/gemma-4-E2B-it") if leads else "google/gemma-4-E2B-it",
        "layer": leads[0].get("gemmaforge_layer", 17) if leads else 17,
        "chunker": "sliding-window:30/20",
    }):
        return

    # Group leads by file so we can emit scan.file events with the right chunk count.
    by_file: dict[str, list[dict]] = {}
    for lead in leads:
        by_file.setdefault(lead["file"], []).append(lead)

    chunks_scored = 0
    leads_emitted = 0
    started = time.time()

    for file, file_leads in by_file.items():
        # Pretend the file had ~2x as many chunks as it produced leads (some scored below threshold).
        n_chunks = max(3, len(file_leads) * 2)
        if not _emit(handler, {
            "schema": "gemmaforge.events/v1", "ts": time.time(),
            "kind": "scan.file", "file": file, "chunks": n_chunks,
        }):
            return
        time.sleep(0.4)

        # Sprinkle low-confidence probe.score events between the real leads
        # so the strip looks lively rather than uniformly red.
        synth_lows = max(0, n_chunks - len(file_leads))
        for i in range(synth_lows):
            if not _emit(handler, {
                "schema": "gemmaforge.events/v1", "ts": time.time(),
                "kind": "probe.score", "file": file,
                "start_line": 1 + i * 10, "end_line": 10 + i * 10,
                "confidence": round(0.1 + 0.2 * (i % 2), 3),
                "top_cwe": None,
            }):
                return
            chunks_scored += 1
            time.sleep(0.15)

        # Real high-confidence hits.
        for lead in file_leads:
            if not _emit(handler, {
                "schema": "gemmaforge.events/v1", "ts": time.time(),
                "kind": "probe.score", "file": file,
                "start_line": lead["start_line"], "end_line": lead["end_line"],
                "confidence": lead["gemmaforge_confidence"],
                "top_cwe": lead.get("gemmaforge_top_cwe"),
            }):
                return
            chunks_scored += 1
            time.sleep(0.25)

    # Now sort leads by confidence (highest first) and emit scan.lead + scan.lead.record.
    leads_sorted = sorted(leads, key=lambda l: l.get("gemmaforge_confidence", 0), reverse=True)
    for rank, lead in enumerate(leads_sorted):
        # scan.lead is the canonical event (no snippet, per docs/events.md).
        if not _emit(handler, {
            "schema": "gemmaforge.events/v1", "ts": time.time(),
            "kind": "scan.lead",
            "file": lead["file"],
            "start_line": lead["start_line"],
            "end_line": lead["end_line"],
            "confidence": lead["gemmaforge_confidence"],
            "top_cwe": lead.get("gemmaforge_top_cwe"),
            "rank": rank,
        }):
            return
        # scan.lead.record is a dashboard-only synthetic kind that carries the snippet.
        if not _emit(handler, {
            "schema": "gemmaforge.events/v1", "ts": time.time(),
            "kind": "scan.lead.record",
            "file": lead["file"],
            "start_line": lead["start_line"],
            "end_line": lead["end_line"],
            "confidence": lead["gemmaforge_confidence"],
            "top_cwe": lead.get("gemmaforge_top_cwe"),
            "rank": rank,
            "snippet": lead.get("snippet"),
        }):
            return
        leads_emitted += 1
        time.sleep(0.3)

    _emit(handler, {
        "schema": "gemmaforge.events/v1", "ts": time.time(),
        "kind": "scan.end",
        "files_seen": len(by_file),
        "chunks_scored": chunks_scored,
        "leads_emitted": leads_emitted,
        "elapsed_seconds": round(time.time() - started, 2),
    })

    # Keep the connection open with periodic keep-alives so the browser
    # doesn't auto-reconnect and replay the whole demo over and over.
    while True:
        time.sleep(15)
        try:
            handler.wfile.write(b": keep-alive\n\n")
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


def replay_events_file(
    handler: BaseHTTPRequestHandler,
    events_path: Path,
    leads_path: Path,
    speedup: float = 4.0,
    max_gap: float = 1.2,
) -> None:
    """Replay a recorded gemmaforge.events/v1 ND-JSON file with original
    inter-event timing (compressed by ``speedup`` and capped at ``max_gap``).

    Injects ``scan.lead.record`` events after each ``scan.lead`` by looking
    up the snippet in ``leads_path`` — that synthetic kind is what Panel 3
    of the dashboard reads to render code with line numbers.
    """
    if not events_path.exists():
        return

    events: list[dict] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not events:
        return

    lead_snippets: dict[tuple[str, int, int], str] = {}
    if leads_path.exists():
        for line in leads_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                lead = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (lead.get("file"), lead.get("start_line"), lead.get("end_line"))
            if all(k is not None for k in key) and lead.get("snippet"):
                lead_snippets[key] = lead["snippet"]

    t_origin = events[0]["ts"]
    started = time.time()
    last_target = 0.0
    rank = 0

    for ev in events:
        raw_offset = float(ev.get("ts", t_origin)) - t_origin
        raw_gap = max(0.0, raw_offset - last_target)
        gap = min(raw_gap, max_gap) / max(speedup, 0.1)
        target = last_target + gap
        elapsed = time.time() - started
        if target > elapsed:
            time.sleep(target - elapsed)
        last_target = target

        if not _emit(handler, ev):
            return

        if ev.get("kind") == "scan.lead":
            key = (ev.get("file"), ev.get("start_line"), ev.get("end_line"))
            snippet = lead_snippets.get(key)
            if snippet:
                record = {**ev, "kind": "scan.lead.record", "rank": rank, "snippet": snippet}
                if not _emit(handler, record):
                    return
            rank += 1

    while True:
        time.sleep(15)
        try:
            handler.wfile.write(b": keep-alive\n\n")
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


def tail_events_file(handler: BaseHTTPRequestHandler, path: Path) -> None:
    """Tail an ND-JSON events file. Re-reads existing lines first, then follows."""
    # Backfill existing lines so a late connector sees the scan to date.
    pos = 0
    if path.exists():
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not _emit(handler, obj):
                    return
            pos = fp.tell()
    # Follow.
    while True:
        if not path.exists():
            time.sleep(0.5)
            continue
        with path.open("r", encoding="utf-8") as fp:
            fp.seek(pos)
            for line in fp:
                if not line.endswith("\n"):
                    # Partial write — back off and retry.
                    pos = fp.tell() - len(line.encode("utf-8"))
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not _emit(handler, obj):
                    return
            pos = fp.tell()
        time.sleep(0.4)


PWNKIT_SYNTHETIC_FALLBACK = [
    # Used only when no recorded pwnkit-events.ndjson is on disk.
    ("queue", "queued lead #0 examples/vuln-express-app/src/ping.js:1 — CWE-78", "warn"),
    ("queue", "queued lead #1 examples/vuln-express-app/src/users.js:21 — CWE-89", "warn"),
    ("exploit", "triage: spawning sandbox for ping.js…", ""),
    ("exploit", "exploit verified: GET /ping?host=x;id  →  uid=33(www-data)", "ok"),
    ("report", "report drafted: pwnkit-report-vuln-express-app.md", "ok"),
]


def pwnkit_stream(handler: BaseHTTPRequestHandler, replay_path: Path | None = None) -> None:
    """Stream `pk.log` / `pk.counts` events for Panel 4.

    If ``replay_path`` points at an existing ND-JSON file, replay it
    verbatim — the file is built from a real ``pwnkit review`` run by
    ``scripts/build_pwnkit_replay.py`` (pulled out of pwnkit's SQLite
    db). Falls back to a short synthetic illustration when the recording
    is absent.
    """
    queued = exploited = reported = 0

    if replay_path is not None and replay_path.exists():
        for line in replay_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not _emit(handler, ev):
                return
            # Pacing: ~1.2s per event so the panel reads as live, not as a dump.
            time.sleep(1.2)
    else:
        for kind, msg, level in PWNKIT_SYNTHETIC_FALLBACK:
            if kind == "queue":
                queued += 1
            elif kind == "exploit" and level == "ok":
                exploited += 1
            elif kind == "report":
                reported += 1
            if not _emit(handler, {"kind": "pk.log", "message": msg, "level": level}):
                return
            if not _emit(handler, {
                "kind": "pk.counts",
                "queued": queued, "exploited": exploited, "reported": reported,
            }):
                return
            time.sleep(1.4)

    while True:
        time.sleep(15)
        try:
            handler.wfile.write(b": keep-alive\n\n")
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


def _spawn_pwnkit(run_id: str, leads_path: Path, repo_path: Path, pwnkit_cli: Path, pwnkit_db: Path) -> None:
    """Background thread target: spawn pwnkit-cli for the given run_id.

    Reads the run config (api_key, model, base_url) from _RUNS[run_id],
    executes pwnkit, and records the resulting pwnkit scan id back into
    _RUNS[run_id]['scan_id'] once the new pipeline_events row appears.
    """
    with _RUNS_LOCK:
        cfg = _RUNS.get(run_id, {}).copy()
    if not cfg:
        return

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = cfg["api_key"]
    env["OPENAI_BASE_URL"] = cfg["base_url"]
    env["OPENAI_MODEL"] = cfg["model"]
    env["PWNKIT_DB_PATH"] = str(pwnkit_db)
    env["PWNKIT_HEARTBEAT"] = "1"
    # Note: api_key is in env for this subprocess only — never logged.

    cmd = [
        "node", str(pwnkit_cli),
        "review", str(repo_path),
        "--seed-findings", str(leads_path),
        "--seed-only",
        "--runtime", "api",
        "--model", cfg["model"],
        "--verbose",
        "--timeout", "600000",
        "--db-path", str(pwnkit_db),
    ]

    try:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with _RUNS_LOCK:
            if run_id in _RUNS:
                _RUNS[run_id]["process"] = proc
        # Read stderr in background to avoid filling the pipe buffer.
        for line in iter(proc.stderr.readline, b""):
            # We don't store/log this — it can contain the OpenAI base url
            # and prompts, no api_key but still noisy.
            pass
        proc.wait()
    except Exception as e:
        sys.stderr.write(f"[pwnkit-run {run_id}] spawn error: {e}\n")
    finally:
        with _RUNS_LOCK:
            if run_id in _RUNS:
                _RUNS[run_id]["done"] = True
                _RUNS[run_id]["api_key"] = ""  # forget the key immediately


def _scan_id_for_run(run_id: str, pwnkit_db: Path, started_at: float) -> str | None:
    """Find the pwnkit scan id created by our spawn after ``started_at``.

    Pwnkit creates a row in `scans` shortly after launch; we identify it
    by being the most recent scan whose startedAt is after our spawn.
    """
    if not pwnkit_db.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{pwnkit_db}?mode=ro", uri=True)
        cur = con.execute("SELECT id, startedAt FROM scans ORDER BY startedAt DESC LIMIT 5")
        for sid, started_iso in cur:
            # startedAt is ISO-8601; parse to epoch.
            try:
                from datetime import datetime, timezone
                t = datetime.fromisoformat(started_iso.replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if t >= started_at - 2:  # 2s skew tolerance
                con.close()
                return sid
        con.close()
    except sqlite3.Error:
        pass
    return None


def stream_pwnkit_run(handler: BaseHTTPRequestHandler, run_id: str, pwnkit_db: Path) -> None:
    """Stream pipeline_events for a live pwnkit run as pk.log/pk.counts."""
    _sse_headers(handler)

    with _RUNS_LOCK:
        run = _RUNS.get(run_id, {}).copy()
    if not run:
        _emit(handler, {"kind": "pk.log", "message": f"unknown run {run_id}", "level": "warn"})
        return

    started_at = run["started_at"]
    _emit(handler, {"kind": "pk.log", "message": f"spawning pwnkit · model={run['model']}", "level": ""})

    # Wait for the scan row to appear (up to 30s).
    scan_id = None
    deadline = time.time() + 30
    while time.time() < deadline and scan_id is None:
        scan_id = _scan_id_for_run(run_id, pwnkit_db, started_at)
        if scan_id is None:
            if not _emit(handler, {"kind": "pk.log", "message": "waiting for pwnkit to register the scan…"}):
                return
            time.sleep(2)

    if scan_id is None:
        _emit(handler, {"kind": "pk.log", "message": "pwnkit didn't register a scan within 30s — abort", "level": "warn"})
        return

    _emit(handler, {"kind": "pk.log", "message": f"scan registered · id={scan_id[:8]}", "level": "ok"})

    # Poll for new pipeline_events.
    last_ts = 0
    queued = exploited = reported = 0
    finished = False
    poll_deadline = time.time() + 600  # hard cap 10 min stream

    while not finished and time.time() < poll_deadline:
        try:
            con = sqlite3.connect(f"file:{pwnkit_db}?mode=ro", uri=True)
            cur = con.execute(
                "SELECT timestamp, stage, eventType, payload FROM pipeline_events "
                "WHERE scanId=? AND timestamp > ? ORDER BY timestamp",
                (scan_id, last_ts),
            )
            rows = cur.fetchall()
            con.close()
        except sqlite3.Error as e:
            _emit(handler, {"kind": "pk.log", "message": f"db read error: {e}", "level": "warn"})
            rows = []

        for ts, stage, kind, raw_payload in rows:
            last_ts = ts
            try:
                payload = json.loads(raw_payload or "{}")
            except json.JSONDecodeError:
                payload = {}

            if kind == "seed_findings_loaded":
                queued = payload.get("count", queued)
                _emit(handler, {"kind": "pk.log", "message": f"ingested {queued} seed(s) · sources: {','.join(payload.get('sources', []))}", "level": "warn"})
                _emit(handler, {"kind": "pk.counts", "queued": queued, "exploited": exploited, "reported": reported})
            elif kind == "stage_start":
                _emit(handler, {"kind": "pk.log", "message": f"{stage} stage started"})
            elif kind == "stage_complete":
                _emit(handler, {"kind": "pk.log", "message": f"{stage} stage complete", "level": "ok"})
                if stage == "report":
                    reported = payload.get("totalFindings", reported)
                    _emit(handler, {"kind": "pk.counts", "queued": queued, "exploited": exploited, "reported": reported})
            elif kind == "agent_start":
                _emit(handler, {"kind": "pk.log", "message": f"agent online · {payload.get('toolCount', '?')} tools · model via OpenRouter"})
            elif kind == "tool_calls":
                for tool in payload.get("tools", []):
                    if tool == "save_finding":
                        exploited += 1
                        _emit(handler, {"kind": "pk.log", "message": "tool_use · save_finding", "level": "ok"})
                        _emit(handler, {"kind": "pk.counts", "queued": queued, "exploited": exploited, "reported": reported})
                    elif tool != "done":
                        _emit(handler, {"kind": "pk.log", "message": f"tool_use · {tool}"})
            elif kind == "agent_complete":
                fc = payload.get("findingCount", 0)
                _emit(handler, {"kind": "pk.log", "message": f"agent complete · {fc} finding(s) · {payload.get('turnCount', '?')} turn(s)", "level": "ok"})
            elif kind == "agent_error":
                _emit(handler, {"kind": "pk.log", "message": f"agent error: {payload.get('error', '?')[:200]}", "level": "warn"})

        # Check whether the run is done.
        with _RUNS_LOCK:
            run = _RUNS.get(run_id, {})
        if run.get("done"):
            finished = True
        else:
            time.sleep(1.5)

    _emit(handler, {"kind": "pk.log", "message": "pwnkit run finished — stream closing", "level": ""})


def make_handler(args):
    leads_path = Path(args.leads_file) if args.leads_file else DEFAULT_LEADS
    events_file = Path(args.events_file) if args.events_file else None
    replay_events = Path(args.replay_events) if args.replay_events else None
    pwnkit_replay = Path(args.pwnkit_replay) if args.pwnkit_replay else None
    pwnkit_cli = Path(args.pwnkit_cli) if args.pwnkit_cli else None
    pwnkit_db = Path(args.pwnkit_db) if args.pwnkit_db else Path("/tmp/pwnkit.db")
    speedup = float(args.replay_speedup)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *largs):
            sys.stderr.write("[dashboard] " + fmt % largs + "\n")

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if path in ("/", "/index.html"):
                _send_static(self, DASHBOARD_DIR / "index.html", "text/html; charset=utf-8")
                return
            if path == "/style.css":
                _send_static(self, DASHBOARD_DIR / "style.css", "text/css; charset=utf-8")
                return
            if path == "/sse/stream":
                proxy_stream(self, parse_qs(parsed.query))
                return
            if path == "/sse/events":
                _sse_headers(self)
                if replay_events is not None:
                    replay_events_file(self, replay_events, leads_path, speedup=speedup)
                elif events_file is not None:
                    tail_events_file(self, events_file)
                else:
                    replay_events_demo(self, leads_path)
                return
            if path == "/sse/pwnkit":
                _sse_headers(self)
                pwnkit_stream(self, pwnkit_replay)
                return
            if path == "/sse/pwnkit/live":
                qs = parse_qs(parsed.query)
                run_id = qs.get("runId", [""])[0]
                if not run_id:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"missing runId")
                    return
                if pwnkit_cli is None:
                    _sse_headers(self)
                    _emit(self, {"kind": "pk.log", "message": "pwnkit-cli not installed in this build", "level": "warn"})
                    return
                stream_pwnkit_run(self, run_id, pwnkit_db)
                return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path != "/api/pwnkit/start":
                self.send_response(404)
                self.end_headers()
                return
            if pwnkit_cli is None:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"pwnkit-cli not installed"}')
                return

            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"invalid json"}')
                return

            api_key = (body.get("apiKey") or "").strip()
            if not api_key.startswith("sk-or-") and not api_key.startswith("AIza"):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"apiKey looks invalid (expect OpenRouter sk-or- or Google AIza)"}')
                return

            model = body.get("model") or "google/gemma-4-31b-it"
            base_url = body.get("baseUrl") or (
                "https://generativelanguage.googleapis.com/v1beta/openai"
                if api_key.startswith("AIza")
                else "https://openrouter.ai/api/v1"
            )

            # Pick the repo to scan — bake in our vuln-express-app demo.
            repo_path = REPO_ROOT / "examples" / "vuln-express-app"
            if not repo_path.exists():
                # Fallback: use whatever's under /app/examples/vuln-express-app
                repo_path = Path("/app/examples/vuln-express-app")

            run_id = _new_run_id()
            with _RUNS_LOCK:
                if sum(not run["done"] for run in _RUNS.values()) >= 2:
                    self.send_response(429)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":"pwnkit run capacity reached"}')
                    return
                _RUNS[run_id] = {
                    "api_key": api_key,
                    "model": model,
                    "base_url": base_url,
                    "scan_id": None,
                    "process": None,
                    "started_at": time.time(),
                    "done": False,
                }
            threading.Thread(
                target=_spawn_pwnkit,
                args=(run_id, leads_path, repo_path, pwnkit_cli, pwnkit_db),
                daemon=True,
            ).start()

            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"runId": run_id, "model": model}).encode())

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8888)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument(
        "--events-file",
        default=None,
        help="ND-JSON events file to *live-tail* (gemmaforge.events/v1). For "
        "the local dev loop alongside `src/scan.py --events <file>`. Use "
        "--replay-events for a finished recording.",
    )
    ap.add_argument(
        "--replay-events",
        default=None,
        help="Recorded ND-JSON events file to *replay* with original-relative "
        "timing (compressed by --replay-speedup, capped per-gap at 1.2s). "
        "Faithful playback of a real scan — every byte is what `src/scan.py` "
        "actually emitted. This is what the hosted HF Space uses.",
    )
    ap.add_argument(
        "--replay-speedup",
        type=float,
        default=4.0,
        help="Time-compression factor when --replay-events is set.",
    )
    ap.add_argument(
        "--pwnkit-replay",
        default=None,
        help="ND-JSON file of pk.log/pk.counts events for Panel 4. Built by "
        "scripts/build_pwnkit_replay.py from a real pwnkit review run. When "
        "omitted, falls back to a short synthetic illustration.",
    )
    ap.add_argument(
        "--pwnkit-cli",
        default=None,
        help="Path to a built pwnkit-cli/dist/index.js. When set, enables the "
        "POST /api/pwnkit/start + GET /sse/pwnkit/live endpoints so visitors "
        "can run a live pwnkit review against examples/vuln-express-app using "
        "their own OpenRouter (or Google AI Studio) API key. The key is "
        "passed as an env var to one subprocess and immediately discarded.",
    )
    ap.add_argument(
        "--pwnkit-db",
        default="/tmp/pwnkit.db",
        help="SQLite db path for pwnkit pipeline_events (must match the one "
        "pwnkit-cli writes to via --db-path).",
    )
    ap.add_argument(
        "--leads-file",
        default=str(DEFAULT_LEADS),
        help="leads.jsonl whose snippets are injected as scan.lead.record "
        "events alongside scan.lead during replay/demo.",
    )
    args = ap.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(args))
    if args.replay_events:
        mode = f"replay {args.replay_events} @ {args.replay_speedup:g}x"
    elif args.events_file:
        mode = f"tailing {args.events_file}"
    else:
        mode = f"demo synthesis ({Path(args.leads_file).name})"
    sys.stderr.write(
        f"[dashboard] listening on http://{args.host}:{args.port}/  ({mode})\n"
        f"[dashboard] Panel 1 needs `python -m src.stream_with_probe --serve` on :8787\n"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\n[dashboard] bye\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
