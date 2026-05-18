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
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen
from urllib.error import URLError


DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent
DEFAULT_LEADS = REPO_ROOT / "examples" / "leads.jsonl"


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


def pwnkit_stream(handler: BaseHTTPRequestHandler) -> None:
    """Synthetic queued → exploit → report cycle. Pure illustration."""
    queued = 0
    exploited = 0
    reported = 0
    script = [
        ("queue", "queued lead #0 examples/vuln-express-app/src/ping.js:1 — CWE-78", "warn"),
        ("queue", "queued lead #1 examples/vuln-express-app/src/users.js:21 — CWE-89", "warn"),
        ("queue", "queued lead #2 examples/vuln-express-app/src/token.js:1 — CWE-330", "warn"),
        ("exploit", "triage: spawning sandbox for ping.js…", ""),
        ("exploit", "exploit verified: GET /ping?host=x;id  →  uid=33(www-data)", "ok"),
        ("exploit", "triage: spawning sandbox for users.js…", ""),
        ("exploit", "exploit verified: GET /users/1%20OR%201=1  →  leaks 4 rows", "ok"),
        ("exploit", "triage: token.js entropy check…", ""),
        ("exploit", "exploit verified: Math.random()-derived token guessable in 1.2s", "ok"),
        ("report", "report drafted: pwnkit-report-2026-vuln-express-app.md", "ok"),
    ]
    for kind, msg, level in script:
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

    # Idle keep-alive afterwards.
    while True:
        time.sleep(15)
        try:
            handler.wfile.write(b": keep-alive\n\n")
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


def make_handler(args):
    leads_path = Path(args.leads_file) if args.leads_file else DEFAULT_LEADS
    events_file = Path(args.events_file) if args.events_file else None
    replay_events = Path(args.replay_events) if args.replay_events else None
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
                pwnkit_stream(self)
                return
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")

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
