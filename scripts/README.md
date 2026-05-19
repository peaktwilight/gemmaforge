# Script Map

The root `scripts/` directory keeps runnable entry points whose paths are still
referenced by docs, reports, or Makefile targets.

## Primary

| Task | Script |
|---|---|
| Build SVEN before/after token dataset | `build_dataset.py` |
| Validate datasets | `validate_dataset.py`, `validate_rich_labels.py` |
| Build repo benchmark fixtures | `build_repo_benchmark.py` |
| Run repo scanner benchmark | `run_repo_scan_benchmark.py` |
| Run sample-level eval framework | `run_eval_framework.py` |
| Run token eval | `run_token_eval.py` |
| Retrain clean SVEN span-max probe | `retrain_spanmax_sven_split.py` |
| Smoke checks | `smoke_probe.py`, `smoke_extract_token.py`, `test_eval_framework.py`, `test_token_eval.py`, `test_stream.py` |
| Deploy HF Space | `deploy_hf.sh` |

## Baseline and Research

These remain in place for reproducibility, but are not the main pipeline:

- Dataset variants: `build_dataset_v2.py`, `build_dataset_sven.py`, `build_length_matched_eval.py`, `derive_rich_labels.py`.
- Probe variants: `train_attention_probe.py`, `train_mlp_probe.py`, `train_probe_ensemble.py`, `train_per_cwe_probe.py`, `train_value_head.py`.
- Eval variants: `eval_*`, `adversarial_*`, `data_efficiency_curve.py`.
- LoRA and publishing: `train_lora.py`, `eval_lora.py`, `publish_to_hub.py`, `push_kaggle_gemmaforge.sh`.

Move any future one-off script into `experiments/` unless it is part of the
primary path above.
