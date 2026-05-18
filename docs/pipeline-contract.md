# GemmaForge → pwnkit pipeline contract

Three-tier cascade. Each tier emits a typed ND-JSON stream. Downstream tiers
read upstream output and filter on `cascade.decision` (Tier 2 onwards). No
tier touches a process boundary it does not own — the contracts below are
the only things that cross the boundary.

```
   repo/                                       Tier 1 — WEAK-PROBE  (this repo, Doruk)
   files       ─▶  src/scan.py        ─▶  gemmaforge.leads/v1      (ND-JSON)
                   Gemma 4 E2B               required: file, start_line, end_line,
                   linear probe              snippet, gemmaforge_confidence, model_id
                   layer 17
                                                       │
                                                       ▼
                                            Tier 2 — STRONG-PROBE  (this repo, Efe)
                                            src/cascade.py (stub)
                                            Gemma 4 E4B (or larger)
                                            re-scores top-K, decides:
                                              promote / drop / defer
                                                       │
                                                       ▼
                                            gemmaforge.scored/v1     (ND-JSON)
                                                       │
                                                       ▼
                                            Tier 3 — VERIFIER  (pwnkit, #371 + #372)
                                            pwnkit review
                                              --seed-findings <scored.ndjson>
                                              --runtime ollama
                                            Gemma 4 8B via Ollama
                                              file reads, grep, tool-calls
                                                       │
                                                       ▼
                                            pwnkit.events/v1
                                              tool_use · finding · verdict
                                            (already specified in pwnkit#371)
```

Three properties hold by design:

1. **Tier 1 output is a valid Tier 3 input.** Drop Tier 2 entirely and `pwnkit
   review --seed-findings leads.jsonl` still works (existing pwnkit#371 path).
   Tier 2 is a *quality lift*, not a hard requirement.
2. **Tier 2 output is a superset of Tier 1.** Every `leads/v1` record can be
   trivially upgraded to a single-score `scored/v1` record. Tier 2 never
   drops information.
3. **Schema IDs version independently.** Tier 1 stays on `leads/v1`. If Tier 2
   needs to ship breaking changes it bumps to `scored/v2` without touching
   the upstream contract.

## Boundary 1 — Tier 1 → Tier 2: `gemmaforge.leads/v1`

Already specified in [`leads-schema.md`](leads-schema.md). Unchanged for the
3-tier cascade. Tier 2 reads it record-by-record and decides.

## Boundary 2 — Tier 2 → Tier 3: `gemmaforge.scored/v1`

```json
{
  "schema": "gemmaforge.scored/v1",
  "file": "src/router.js",
  "start_line": 38,
  "end_line": 52,
  "snippet": "db.query(`SELECT * FROM u WHERE id=${id}`)",
  "scores": [
    {
      "tier": 1,
      "model_id": "google/gemma-4-E2B-it",
      "probe": "weak",
      "layer": 17,
      "confidence": 0.78,
      "top_cwe": "CWE-89",
      "cwe_distribution": {"CWE-89": 0.78, "CWE-94": 0.04},
      "ts": 1747584000.123
    },
    {
      "tier": 2,
      "model_id": "google/gemma-4-E4B-it",
      "probe": "strong",
      "layer": 23,
      "confidence": 0.93,
      "top_cwe": "CWE-89",
      "cwe_distribution": {"CWE-89": 0.93, "CWE-94": 0.02},
      "ts": 1747584012.456,
      "context_chars": 4096
    }
  ],
  "cascade": {
    "stage": 2,
    "decision": "promote",
    "reason": "strong_confidence>=0.85 AND cwe_agreement"
  },
  "rank": 0
}
```

### Required fields

| field | type | meaning |
|---|---|---|
| `schema` | string | Always `gemmaforge.scored/v1`. |
| `file`, `start_line`, `end_line`, `snippet` | — | Carried verbatim from the Tier 1 lead. |
| `scores` | array of score-objects, length ≥ 1 | Append-only audit trail. Index 0 is Tier 1; subsequent entries are added by each cascade stage in order. |
| `cascade` | object | Most recent cascade decision. See below. |

### Required `score` sub-fields

| field | type | meaning |
|---|---|---|
| `tier` | int (1, 2, …) | Which pipeline tier emitted this score. |
| `model_id` | string | HuggingFace model id used. |
| `probe` | string | `weak`, `strong`, or stage-specific tag. |
| `layer` | int | Hidden-state layer the probe reads. |
| `confidence` | float in `[0, 1]` | Calibrated sigmoid of the probe's logit. |
| `ts` | float | Unix-seconds emission timestamp. |

### Optional `score` sub-fields

| field | type | meaning |
|---|---|---|
| `top_cwe` | string | Argmax label from the per-CWE head, if available. |
| `cwe_distribution` | object | Full softmax over the CWE heads. Lets Tier 3 query the long tail. |
| `context_chars` | int | How many chars of surrounding source the probe saw beyond the snippet. Tier 1 = 0 (snippet only); strong-probe stages can ingest more. |
| `attention_pool` | string | `last_token`, `max_pool_8`, `mean_pool_8`, `attention`. Provenance for debugging. |

### `cascade` object

| field | type | meaning |
|---|---|---|
| `stage` | int | The tier that wrote this decision. Always matches the highest `tier` in `scores`. |
| `decision` | one of `promote`, `drop`, `defer` | What the cascade recommends to the next tier. |
| `reason` | string | Human-readable decision rationale. No schema constraint; useful for debugging. |

### Decision semantics

- **`promote`** — high-confidence lead, send to the next tier. Tier 3
  (pwnkit) treats `promote` records as worklist items.
- **`drop`** — strong-probe disagrees with weak-probe (e.g., E4B confidence
  < 0.3 on a record where E2B fired at 0.8). Tier 3 SHOULD skip these,
  but MAY include them in a "second-look" pass.
- **`defer`** — strong-probe is uncertain (confidence in `[0.4, 0.7]`).
  Tier 3 MUST treat as `promote` *and* surface the uncertainty to the
  human reviewer (Hunt-lane warning badge).

Tier 3 (pwnkit) filters its worklist by `decision ∈ {promote, defer}` by
default. The `--seed-findings` ingest path in pwnkit#371 needs a small
patch to read `scored/v1` in addition to `leads/v1` — track in a follow-up
PR. Until that lands, Tier 2 can write a sibling `*.leads.v1.jsonl`
projection alongside `*.scored.v1.jsonl` so pwnkit's existing ingest still
works (`src.cascade.write_legacy_projection`).

## Trivial upgrade: leads/v1 → scored/v1

```python
def upgrade(lead: dict) -> dict:
    """Embed a Tier 1 leads/v1 record into a scored/v1 record. Lossless."""
    return {
        "schema": "gemmaforge.scored/v1",
        "file": lead["file"],
        "start_line": lead["start_line"],
        "end_line": lead["end_line"],
        "snippet": lead["snippet"],
        "scores": [{
            "tier": 1,
            "model_id": lead["model_id"],
            "probe": "weak",
            "layer": lead.get("gemmaforge_layer"),
            "confidence": lead["gemmaforge_confidence"],
            "top_cwe": lead.get("gemmaforge_top_cwe"),
            "ts": lead.get("ts", time.time()),
        }],
        "cascade": {"stage": 1, "decision": "promote", "reason": "tier1_only"},
        "rank": lead.get("rank"),
    }
```

Tier 2 reads `gemmaforge.leads/v1` ND-JSON, calls `upgrade(...)`, appends
its own score, sets `cascade` to its own decision, writes `scored/v1`.

## Stability guarantees

Same as `leads/v1`:

- Additive changes within `scored/v1` are non-breaking. New optional fields
  ship freely.
- Renames, type changes, or required-field semantics changes bump to
  `scored/v2`.
- Consumers MUST parse `schema` and MUST ignore unknown optional fields.

## Reference producers / consumers

- Tier 1 producer: `src/scan.py` (existing, emits `leads/v1`).
- Tier 2 producer: `src/cascade.py` (stub to be written by Efe — see
  next section).
- Tier 3 consumer: pwnkit `--seed-findings` (currently `leads/v1` only;
  follow-up patch to consume `scored/v1`).

## Tier 2 reference stub (`src/cascade.py`, to be written by Efe)

```python
"""Tier 2 cascade — strong-probe re-scoring of Tier 1 leads.

Reads gemmaforge.leads/v1 ND-JSON on stdin (or --in), re-scores each
record with a strong probe (default Gemma 4 E4B layer ~23), writes
gemmaforge.scored/v1 ND-JSON to stdout (or --out)."""
import json, sys, time
from pathlib import Path

SCHEMA_IN  = "gemmaforge.leads/v1"
SCHEMA_OUT = "gemmaforge.scored/v1"

PROMOTE_THRESHOLD = 0.85
DROP_THRESHOLD    = 0.30
# everything in between is `defer`

def decide(strong_conf: float, weak_top_cwe: str | None, strong_top_cwe: str | None) -> tuple[str, str]:
    if strong_conf >= PROMOTE_THRESHOLD:
        agrees = strong_top_cwe == weak_top_cwe
        return ("promote", f"strong_confidence>={PROMOTE_THRESHOLD}" + (" AND cwe_agreement" if agrees else ""))
    if strong_conf < DROP_THRESHOLD:
        return ("drop", f"strong_confidence<{DROP_THRESHOLD}")
    return ("defer", f"strong_confidence in [{DROP_THRESHOLD}, {PROMOTE_THRESHOLD}]")

def score_one(lead: dict, strong_probe) -> dict:
    strong_conf, strong_top_cwe, strong_dist = strong_probe.score(lead["snippet"], context=…)
    weak_score = {
        "tier": 1,
        "model_id": lead["model_id"],
        "probe": "weak",
        "layer": lead.get("gemmaforge_layer"),
        "confidence": lead["gemmaforge_confidence"],
        "top_cwe": lead.get("gemmaforge_top_cwe"),
        "ts": lead.get("ts", time.time()),
    }
    strong_score = {
        "tier": 2,
        "model_id": strong_probe.model_id,
        "probe": "strong",
        "layer": strong_probe.layer,
        "confidence": strong_conf,
        "top_cwe": strong_top_cwe,
        "cwe_distribution": strong_dist,
        "ts": time.time(),
        "context_chars": strong_probe.context_chars,
    }
    decision, reason = decide(strong_conf, weak_score["top_cwe"], strong_top_cwe)
    return {
        "schema": SCHEMA_OUT,
        "file": lead["file"],
        "start_line": lead["start_line"],
        "end_line": lead["end_line"],
        "snippet": lead["snippet"],
        "scores": [weak_score, strong_score],
        "cascade": {"stage": 2, "decision": decision, "reason": reason},
        "rank": lead.get("rank"),
    }
```

`strong_probe` is whatever Efe ships — a class with `.score(snippet, context=…) -> (confidence, top_cwe, cwe_distribution)` and metadata (`model_id`, `layer`, `context_chars`). Anything fitting that protocol composes.
