# GemmaForge → external-tool leads schema

The contract that downstream agentic hunters (e.g. [pwnkit](https://0sec.ai/pwnkit) via `--seed-findings`) consume from `gemmaforge scan`.

Wire format: **ND-JSON** (one JSON object per line, UTF-8, LF-terminated). One file per scan; one record per ranked candidate vulnerable region.

Schema id: `gemmaforge.leads/v1`.

## Record shape

```json
{
  "schema": "gemmaforge.leads/v1",
  "file": "src/router.js",
  "start_line": 38,
  "end_line": 52,
  "snippet": "app.get('/u/:id', (req, res) => {\n  db.query('SELECT * FROM users WHERE id=' + req.params.id, (err, rows) => res.json(rows));\n});",
  "gemmaforge_confidence": 0.93,
  "gemmaforge_top_cwe": "CWE-89",
  "gemmaforge_cwe_match": 1.0,
  "gemmaforge_layer": 17,
  "model_id": "google/gemma-4-E2B-it",
  "rank": 0
}
```

### Required fields

| field | type | meaning |
|---|---|---|
| `schema` | string | Always `gemmaforge.leads/v1`. Consumers branch on this. |
| `file` | string | Repo-relative POSIX path. |
| `start_line` / `end_line` | int (1-indexed, inclusive) | Span of the candidate region in the source file. |
| `snippet` | string | The actual text of the span. Carried inline so consumers don't need filesystem access. |
| `gemmaforge_confidence` | float in `[0, 1]` | Sigmoid of the binary probe over Gemma 4 layer 17. |
| `model_id` | string | The Gemma model id used to extract activations. |

### Optional fields

| field | type | meaning |
|---|---|---|
| `gemmaforge_top_cwe` | string \| null | Argmax CWE-head label, if the per-CWE probe ran. One of `CWE-78`, `CWE-338`, `CWE-95`, `CWE-94`, `CWE-328` currently. |
| `gemmaforge_cwe_match` | float \| null | Agreement between an externally-claimed CWE and the probe's argmax. `1.0` exact, `0.5` top-2, `0.0` neither, `null` if no external claim was provided. For `gemmaforge scan` (no external claim) this field is always omitted. |
| `gemmaforge_layer` | int | Hidden-state layer the probe was trained on. Provenance only. |
| `rank` | int | Zero-indexed rank within this scan, descending by score. Convenience for consumers. |

## Ranking

Records are ordered by:

```
rank_score = gemmaforge_confidence * (1 + 0.5 * cwe_match_bonus)
```

where `cwe_match_bonus` is `1.0` if `gemmaforge_top_cwe` is set (per-CWE probe was available), else `0.0`. The intent: when we have a confident CWE attribution, surface it above an equally-confident generic positive.

## Stability guarantees

- Within `gemmaforge.leads/v1`, additive changes (new optional fields) are non-breaking.
- Any field rename, type change, or semantic change to required fields ships under a new schema id (`gemmaforge.leads/v2`). Old consumers can pin by checking `schema`.
- Field order within a record is **not** guaranteed; consumers must parse, not pattern-match.

## Companion: event stream

`gemmaforge scan` also accepts `--events <path>` for a live ND-JSON event stream (probe firings, lead emissions, scan progress). That schema is `gemmaforge.events/v1` and is documented in [`events.md`](events.md).
