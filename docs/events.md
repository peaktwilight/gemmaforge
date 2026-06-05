# GemmaForge live event stream

ND-JSON event stream emitted by `src/scan.py` and `src/stream_with_probe.py` when invoked with `--events <path|->`. Designed for live dashboards (e.g. the pwnkit dashboard `live` view, see [0sec-labs/pwnkit#370](https://0sec.ai/pwnkit)) and for replay tooling.

Schema id: `gemmaforge.events/v1`.

## Common envelope

Every event:

```json
{"schema": "gemmaforge.events/v1", "ts": 1747584000.123, "kind": "<event-kind>", ...}
```

- `ts` — Unix seconds, float. Monotonic within a single run.
- `kind` — one of the kinds below. Consumers MUST ignore unknown kinds.

## Event kinds

### `scan.start`
Emitted once at the beginning of a scan.
```json
{"kind": "scan.start", "ts": ..., "repo": "examples/express-app", "model_id": "google/gemma-4-E2B-it", "layer": 17, "chunker": "function"}
```

### `scan.file`
Emitted per file the scanner enters.
```json
{"kind": "scan.file", "ts": ..., "file": "src/router.js", "chunks": 12}
```

### `probe.score`
Emitted per chunk after the probe runs.
```json
{"kind": "probe.score", "ts": ..., "file": "src/router.js", "start_line": 38, "end_line": 52, "confidence": 0.93, "top_cwe": "CWE-89"}
```

### `scan.lead`
Emitted when a chunk passes the `--min-confidence` threshold and is written to the leads output.
```json
{"kind": "scan.lead", "ts": ..., "file": "src/router.js", "start_line": 38, "end_line": 52, "confidence": 0.93, "top_cwe": "CWE-89", "rank": 0}
```

### `probe.token` *(streaming demo only)*
Emitted per token by `stream_with_probe.py` while a model is generating code.
```json
{"kind": "probe.token", "ts": ..., "token": " req.params.id", "score": 0.91, "position": 47}
```

### `probe.alarm` *(streaming demo only)*
Emitted when the rolling probe score crosses the alarm threshold.
```json
{"kind": "probe.alarm", "ts": ..., "window": [38, 52], "top_cwe": "CWE-89", "confidence": 0.93}
```

### `scan.end`
Emitted once at the end of a scan.
```json
{"kind": "scan.end", "ts": ..., "files_seen": 184, "chunks_scored": 1402, "leads_emitted": 17, "elapsed_seconds": 23.4}
```

## Stability

Same rules as [`leads-schema.md`](leads-schema.md): additive within `v1`, breaking changes bump the schema id. Consumers must check `schema` and ignore unknown `kind`s.

## Transport

- `--events <path>`: write ND-JSON to file. The file is opened in append mode; safe to `tail -f`.
- `--events -`: write ND-JSON to stderr (so stdout stays clean for the leads stream).
- No on-the-wire framing beyond newline-delimited JSON. WebSocket/SSE transport is up to the consumer; the dashboard wraps the file tail.
