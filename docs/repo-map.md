# Repository Map

This repo now has one primary product path and several historical research paths.
Keep new work on the primary path unless an experiment explicitly says otherwise.

## Primary Pipeline

The scanner path is:

```text
scripts/build_dataset.py
  -> data/dataset.jsonl
  -> src/extract_token_activations.py
  -> data/token_activations/token_activations_layer*.npz
  -> src/train_probe_spanmax.py
  -> data/probe_spanmax.npz
  -> src.scan + integrations/pwnkit/adapter.py
  -> gemmaforge.leads/v1
```

Canonical runtime and evaluation code:

| Area | Path |
|---|---|
| Scanner runtime | `src/scan.py` |
| Streaming/snippet UI | `src/stream_with_probe.py`, `web/index.html` |
| Event schema/runtime | `src/events.py`, `docs/events.md` |
| Lead schema | `docs/leads-schema.md` |
| pwnkit bridge | `integrations/pwnkit/` |
| Eval framework | `src/eval/` |
| Repo benchmark build/scan | `scripts/build_repo_benchmark.py`, `scripts/run_repo_scan_benchmark.py` |
| Token eval | `scripts/run_token_eval.py`, `src/eval/token_protocol.py` |
| Local dashboard | `dashboard/` |
| Current HF app | `hfspace_gradio/` |

## History From Git and Issues

The repo moved through five work streams:

1. Sample-level probe on CyberSecEval pairs.
2. Leakage-aware eval, length baselines, adversarial/max-pool checks.
3. Token/span-max SVEN work and repo-level held-out benchmark.
4. pwnkit handoff, lead/event schemas, and dashboard integrations.
5. Submission assets, video scripts, HF/Kaggle/Colab packaging.

GitHub issues reflect that sequence. Closed issues `#17` through `#26` cover the
token extractor fix, span-max/proximity eval, scanner CLI, events, and robustness
work. Open research issues remain for richer token labels, 26B replication, LoRA,
and the train/inference semantic mismatch.

## Archive and Experiments

`archive/` contains material that should not be part of day-to-day runtime:

- `archive/submission/` - final submission drafts, video scripts, voiceover, recordings.
- `archive/process/` - critique rounds, iteration plans, gate checks, judging criteria.
- `archive/deploy/hfspace-dashboard/` - older Docker/dashboard HF Space path.

`experiments/` contains notebooks and remote runs that are useful for provenance
but not canonical runtime code:

- `experiments/notebooks/reports/`
- `experiments/notebooks/training/`
- `experiments/notebooks/remote/`

## Reorganization Rule

Do not move default `data/*` artifacts or active `scripts/*` entry points without
updating code defaults, README commands, and report reproduction notes in the
same change. Many scripts still assume paths like `data/probe_spanmax.npz`,
`data/dataset.jsonl`, and `data/eval/...`.
