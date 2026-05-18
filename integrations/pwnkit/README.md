# GemmaForge → pwnkit Adapter

A confidence filter that pwnkit's triage layer can call to re-rank CVE
findings using the GemmaForge linear probes over Gemma 4 hidden states.

## What it does

Given a pwnkit finding of shape:

```json
{
  "claim":      "SQL injection at line 42 of router.js",
  "snippet":    "db.query('SELECT * FROM u WHERE id = ' + req.params.id)",
  "cwe":        "CWE-89",
  "confidence": "high"
}
```

the adapter returns the finding plus two new fields:

- `gemmaforge_confidence` — float in `[0, 1]`. Probability the snippet is
  vulnerable per the GemmaForge binary probe (Gemma 4 layer 17 → logistic
  regression, AUC ≈ 0.96 on the held-out CyberSecEval split).
- `gemmaforge_cwe_match` — `1.0` if the claimed CWE is the argmax head of
  the per-CWE probe; `0.5` if it's in the top-2; `0.0` otherwise; `None`
  if the claimed CWE isn't one of the five trained heads (CWE-78, CWE-338,
  CWE-95, CWE-94, CWE-328).

## Wiring from pwnkit

```python
from integrations.pwnkit.adapter import GemmaForgeFilter

# Constructed once; the heavy LM is lazy-loaded on the first call.
gf = GemmaForgeFilter(
    probe_path="data/probe.npz",
    per_cwe_probe_path="data/probe_per_cwe.npz",
    model_id="google/gemma-4-E2B-it",
)

for finding in pwnkit_findings:
    scored = gf.score_finding(finding)
    if scored["gemmaforge_confidence"] < 0.4:
        # very likely a false positive — drop or quarantine
        continue
    triage_queue.append(scored)
```

## Suggested triage policy

| `gemmaforge_confidence` | Action                                               |
|-------------------------|------------------------------------------------------|
| `< 0.4`                 | Tag `low-signal`, demote below all probe-supported findings (or drop if pwnkit emitted it with `confidence: "low"`). |
| `0.4 – 0.7`             | Keep, no rank change.                                |
| `> 0.7`                 | Promote; if `gemmaforge_cwe_match == 1.0` also auto-route to the CWE-specific reviewer queue. |

The `gemmaforge_cwe_match` field is intentionally tri-valued so the triage
layer can distinguish "claim disagrees with probe" from "claim is outside
the probe's trained CWE set".

## Performance

- The LM forward pass dominates runtime (~hundreds of ms on M-series MPS,
  longer on CPU). The probes themselves are O(d) dot products.
- The `GemmaForgeFilter` instance caches the model — keep it around for
  the full batch.

## Files

- `adapter.py` — the `GemmaForgeFilter` class.
- `example_findings.json` — sample pwnkit-shaped findings.
- `test_adapter.py` — pytest covering the API contract with the LM mocked.
