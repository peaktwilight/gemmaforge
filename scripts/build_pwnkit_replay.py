#!/usr/bin/env python3
"""Transform pwnkit pipeline_events + findings into Panel 4 replay events.

Pulls events from pwnkit's SQLite DB (default ~/.pwnkit/pwnkit.db) for one
scan id, projects them into the `pk.log` / `pk.counts` shape that
`dashboard/server.py` already speaks, and writes ND-JSON to
`examples/pwnkit-events.ndjson` for replay on the HF Space.

Usage::

    scripts/build_pwnkit_replay.py <scan_id>
        [--db ~/.pwnkit/pwnkit.db]
        [--out examples/pwnkit-events.ndjson]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path


def fetch(db: Path, scan_id: str):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    events = list(
        con.execute(
            "SELECT timestamp, stage, eventType, payload "
            "FROM pipeline_events WHERE scanId=? ORDER BY timestamp",
            (scan_id,),
        )
    )
    findings = list(
        con.execute(
            "SELECT id, title, severity, status, category "
            "FROM findings WHERE scanId=? ORDER BY timestamp",
            (scan_id,),
        )
    )
    con.close()
    return events, findings


def project(events, findings) -> list[dict]:
    """Return a list of {kind, message, level, ...} dicts to emit in order."""
    out: list[dict] = []
    queued = exploited = reported = 0

    def log(msg: str, level: str = ""):
        out.append({"kind": "pk.log", "message": msg, "level": level})

    def counts():
        out.append({"kind": "pk.counts", "queued": queued, "exploited": exploited, "reported": reported})

    findings_iter = iter(findings)

    for ev in events:
        stage = ev["stage"]
        kind = ev["eventType"]
        try:
            payload = json.loads(ev["payload"] or "{}")
        except json.JSONDecodeError:
            payload = {}

        if kind == "stage_start":
            label = {
                "prepare": "preparing target",
                "analyze": "analyze stage — running semgrep + ingesting seeds",
                "research": "research stage — spawning the review agent",
                "verify": "verify stage — replaying findings against the repo",
                "report": "report stage",
            }.get(stage, f"{stage} stage")
            log(label)

        elif kind == "stage_complete":
            if stage == "prepare":
                t = payload.get("resolvedType", "?")
                log(f"target resolved · {t}", "ok")
            elif stage == "analyze":
                seg = payload.get("semgrepFindings", 0)
                nau = payload.get("npmAuditFindings", 0)
                log(f"analyze complete · semgrep {seg} · npm-audit {nau}", "ok")
            elif stage == "research":
                n = payload.get("findings", 0)
                log(f"research complete · {n} findings drafted", "ok")
            elif stage == "verify":
                conf = payload.get("confirmed", 0)
                rej = payload.get("rejected", 0)
                lvl = "ok" if conf > 0 else "warn"
                log(f"verify complete · {conf} confirmed · {rej} rejected (static repo, no live target)", lvl)
            elif stage == "report":
                reported = payload.get("totalAttacks", reported) or reported
                log("report drafted · pwnkit-report-vuln-express-app.md", "ok")
                counts()

        elif kind == "seed_findings_loaded":
            n = payload.get("count", 0)
            srcs = ", ".join(payload.get("sources", [])) or "external"
            queued = n
            log(f"ingested {n} seed lead(s) · sources: {srcs}", "warn")
            counts()

        elif kind == "agent_start":
            sid = payload.get("sessionId", "?")[:8]
            tools = payload.get("toolCount", "?")
            log(f"agent online · session {sid} · {tools} tools available · Gemma 4 8B via Ollama")

        elif kind == "tool_calls":
            tools = payload.get("tools", [])
            for tool in tools:
                if tool == "done":
                    continue
                lvl = "ok" if tool == "save_finding" else ""
                # When the agent emits save_finding, dequeue one finding's title for context.
                if tool == "save_finding":
                    f = next(findings_iter, None)
                    if f is not None:
                        exploited += 1
                        title = f["title"]
                        log(f"tool_use · save_finding · {title}", "ok")
                        counts()
                        continue
                log(f"tool_use · {tool}")

        elif kind == "agent_complete":
            tc = payload.get("turnCount", "?")
            fc = payload.get("findingCount", 0)
            log(f"agent complete · {tc} turn(s) · {fc} finding(s)", "ok")

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scan_id", help="pwnkit scan id (uuid)")
    ap.add_argument("--db", default=str(Path.home() / ".pwnkit" / "pwnkit.db"), type=Path)
    ap.add_argument("--out", default="examples/pwnkit-events.ndjson", type=Path)
    args = ap.parse_args()

    if not args.db.exists():
        print(f"error: pwnkit db not found at {args.db}", file=sys.stderr)
        return 1

    events, findings = fetch(args.db, args.scan_id)
    if not events:
        print(f"error: no pipeline_events for scan {args.scan_id}", file=sys.stderr)
        return 1

    projected = project(events, findings)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for ev in projected:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(
        f"[pwnkit-replay] wrote {len(projected)} events to {args.out} "
        f"({len(events)} source events · {len(findings)} findings)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
