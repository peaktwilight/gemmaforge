# GemmaForge live dashboard

One-page dashboard that visualises the whole GemmaForge pipeline in real
time. This is the submission demo surface — open it once and you see, on
the same screen, the model streaming code with risk-coloured tokens, a
repo being scanned chunk-by-chunk, ranked leads showing up as they emerge,
and the downstream hand-off to pwnkit.

## Install + run

No build step, no JS dependencies. Python 3.10+ stdlib only.

From the repo root:

```bash
# 1. (optional but recommended) start the streaming probe server for Panel 1.
python -m src.stream_with_probe --serve   # binds :8787

# 2. start the dashboard.
python -m dashboard.server                # binds :8888

# 3. open the dashboard.
open http://localhost:8888/
```

That's it. The dashboard works in two modes:

- **Demo mode (default).** No `--events-file` argument. The server replays
  `examples/leads.jsonl` as a synthetic ~10-second scan walkthrough so the
  page is alive the moment you open it.
- **Live mode.** Pass `--events-file path/to/events.jsonl` and the server
  tails that file. Wire it up by running:
  ```bash
  python -m src.scan examples/vuln-express-app \
      --events live-events.jsonl \
      --output leads.jsonl
  python -m dashboard.server --events-file live-events.jsonl
  ```

## Architecture

```
              Panel 1                 Panel 2 / 3              Panel 4
              ↑                       ↑                        ↑
              /sse/stream             /sse/events              /sse/pwnkit
              ↑                       ↑                        ↑
   ┌──────────┴───────────────────────┴────────────────────────┴────┐
   │  dashboard/server.py  (ThreadingHTTPServer, :8888)              │
   └──────────┬───────────────────────┬────────────────────────┬────┘
              ↓                       ↓                        ↓
   localhost:8787/stream     events JSONL file        (synthetic stream)
   (src/stream_with_probe)   (src/scan.py --events)
```

- **Panel 1** consumes the existing `gemmaforge.events/v1`-adjacent SSE
  shape that `stream_with_probe.py` already speaks. The dashboard server
  just proxies it through so the browser stays on one origin.
- **Panels 2 + 3** consume the `gemmaforge.events/v1` ND-JSON event
  schema (`scan.start`, `scan.file`, `probe.score`, `scan.lead`,
  `scan.end`; see `docs/events.md`).
- **Panel 4** is illustrative — the server emits a fixed
  queued → exploit → report sequence. pwnkit isn't actually running.

## How judges will use this

1. Open `http://localhost:8888/` cold. Panels 2 and 3 immediately start
   replaying the cached `examples/leads.jsonl` scan — they see files
   appearing, chunks scoring, and leads sorting in by confidence.
2. (Optional) start the probe server on `:8787` first and click one of
   the four presets in Panel 1 to watch Gemma 4 generate a vulnerable
   snippet with the probe colouring each token in real time.
3. Panel 4 cycles through the hand-off animation so they see what
   downstream pwnkit triage would do with our leads.
4. Click any row in the leads table (Panel 3) to expand the full snippet,
   coloured by the probe-token heuristic for in-line risk.

Everything degrades gracefully — if `:8787` isn't up, Panels 2/3/4 still
work and the Panel 1 status pill goes red with a "stream unreachable"
message instead of hanging.
