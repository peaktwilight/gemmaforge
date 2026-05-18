# `strong-probe` (E4B) vs `weak-probe` (E2B) — head-to-head

Both probes are linear heads `σ(w·h + b)` trained by `python -m src.train_probe
--pairs data/pairs.jsonl` (group-split via `pair_group_key`, closes #18). The
only difference is the backbone whose hidden states `h` come from.

| | weak-probe | strong-probe |
|---|---|---|
| Backbone | `google/gemma-4-E2B-it` | `google/gemma-4-E4B-it` |
| Decoder layers | 35 | 42 |
| Hidden dim `d` | 1536 | 2560 |
| Captured layers | 8 / 17 / 26 / 34 | 10 / 21 / 31 / 41 |
| Best layer (group-split AUC) | **17** (49% depth) | **10** (24% depth) |
| Probe artifact | `data/probe.npz` | `data/probe_strong.npz` |
| Eval report | `data/eval/weak_probe_report.{md,json}` | `data/eval/strong_probe_report.{md,json}` |

## Headline (`data/pairs.jsonl`, group-split, 1198 rows, 95% bootstrap CI n=1000)

| split | weak (E2B L17) | strong (E4B L10) | Δ |
|---|---:|---:|---:|
| random_stratified | 0.999 (0.997–1.000) | 0.996 (0.989–1.000) | −0.003 |
| **group_repo** | 0.960 (0.932–0.982) | **0.969 (0.946–0.988)** | **+0.009** |
| heldout CWE-78 (cmd inj) | 0.986 (0.961–1.000) | **0.998 (0.992–1.000)** | **+0.012** |
| heldout CWE-338 (weak rng) | 0.995 (0.983–1.000) | 0.992 (0.981–1.000) | −0.003 |
| heldout CWE-95 (eval) | 0.995 (0.986–1.000) | 0.986 (0.962–1.000) | −0.009 |
| heldout CWE-94 (code inj) | 1.000 (1.000–1.000) | 1.000 (1.000–1.000) | +0.000 |
| heldout CWE-328 (weak hash) | 0.990 (0.968–1.000) | 0.999 (0.996–1.000) | +0.009 |
| heldout lang=javascript | 0.996 (0.990–1.000) | 0.991 (0.980–0.998) | −0.005 |
| heldout lang=python | 0.991 (0.983–0.998) | 0.998 (0.997–1.000) | +0.007 |

## Reading

**It's a wash on this dataset.** Strong wins 4 splits by 0.007–0.012, loses 3 by
0.003–0.009, ties 1. Both probes sit at AUC 0.99x almost everywhere. The deltas
are inside the CIs on every split — no statistically meaningful gap.

This is the saturation ceiling of `data/pairs.jsonl` (1198 CyberSecEval pairs).
The length confound that inflates this corpus (#22) gives both probes the same
free lift (random baseline AUC ≈ 0.5, length baseline AUC ≈ 0.89), so doubling
the backbone size can only buy small fractional improvements above an already
near-perfect score.

**The interesting structural finding:** the best layer drops from 17 (49% of 35)
on E2B to **10 (24% of 42)** on E4B. The linear vulnerability direction lives in
earlier representations of the larger model. Operationally this is good — early-
layer probes are cheaper at inference (you can stop the forward pass at layer
10 if the probe is the only consumer, instead of running through layer 17 of
35). For the *streaming* use case (where the LM completes its full forward
anyway) the cost is unchanged.

## Limitations

- `data/pairs.jsonl` is CyberSecEval-only (1198 rows, position-paired). It does
  not exercise the strong-probe's larger context window. **Better repo-level
  datasets are coming**; the strong-probe metric table should be re-run against
  those before claiming superiority. Until then this table establishes that
  `strong-probe` at least matches `weak-probe` on the corpus the writeup uses
  for its headline number.
- The token-level path (`data/probe_spanmax.npz`, `data/probe_spanmax_soft.npz`)
  is unchanged here — strong-probe is the sample-level path. A token-level
  strong-probe would need re-extracting the per-token activations on E4B
  (~30 GB on disk) and retraining `train_probe_spanmax.py`.
- Best layer 10 is suspiciously early — could be a small-effect artifact of
  group-split variance rather than a true depth shift. The bootstrap CI on
  group_repo for E4B L10 is (0.946–0.988), and L21/L31/L41 are within 0.022
  AUC of L10. Until repo-level eval confirms, treat the layer choice as
  provisional.

## Reproduce

```bash
# extract
HF_TOKEN=... python -m src.extract_activations \
  --model google/gemma-4-E4B-it \
  --pairs data/pairs.jsonl \
  --out data/activations_e4b

# train (group-split)
python -m src.train_probe \
  --acts-dir data/activations_e4b \
  --pairs data/pairs.jsonl \
  --out data/probe_strong.npz \
  --card data/probe_strong_card.json

# evaluate
python scripts/run_eval_framework.py \
  --activations data/activations_e4b/activations_layer10.npz \
  --pairs data/pairs.jsonl \
  --layer 10 \
  --no-refit --probe data/probe_strong.npz \
  --out-md data/eval/strong_probe_report.md \
  --out-json data/eval/strong_probe_report.json
```

`data/activations_e4b/` is gitignored alongside the other extraction outputs
(weights are 22 MB; trivially regenerable from the command above).
