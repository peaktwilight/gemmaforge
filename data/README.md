# Data Artifacts

`data/` is intentionally still flat enough to preserve code defaults. Treat this
file as the source-of-truth index until the path defaults are refactored.

## Current Artifacts

| Purpose | Canonical files |
|---|---|
| Sample-level weak probe | `probe.npz`, `probe_card.json` |
| Sample-level per-CWE weak probe | `probe_per_cwe.npz`, `probe_per_cwe_card.json` |
| Strong probe | `probe_strong.npz`, `probe_strong_card.json`, `probe_strong_per_cwe.npz`, `probe_strong_per_cwe_card.json` |
| SVEN span-max probe | `probe_spanmax.npz`, `probe_spanmax_card.json` |
| Clean SVEN held-out span-max probe | `probe_spanmax_sven_train.npz`, `probe_spanmax_sven_train_card.json` |
| SVEN per-CWE heads | `probe_per_cwe_sven.npz`, `probe_per_cwe_sven_card.json` |
| Current token dataset | `dataset.jsonl` |
| SVEN held-out dataset | `dataset_sven_heldout.jsonl`, `sven_split_meta.json` |
| Current repo benchmark | `repo_benchmark_heldout/` |
| Current held-out report | `eval/sven_heldout_results.md` |

## Legacy or Experimental

These are retained for auditability but should not become headline artifacts
without a fresh reproduction note:

- `probe_attention*`
- `probe_ensemble*`
- `probe_grouped*`
- `probe_mlp*`
- `probe_multilayer*`
- `probe_strict*`
- `probe_v2*`
- `lora_adapter/`
- `activations_v2/`
- `repo_benchmark/`

## Generated Copies

Deployment copies under `hfspace_gradio/data/` and `hfspace_gradio/probes/` are
not canonical. Recreate them from this directory when preparing the Space.
