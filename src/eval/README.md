# `src/eval/` — GemmaForge probe evaluation framework

Two evaluation paths, both adapted from the hallucination-probes paper
methodology (Obeso et al. 2025, [arxiv.org/abs/2509.03531](https://arxiv.org/abs/2509.03531))
and specialised to vulnerability-detection probes on Gemma 4 hidden states.

## Two paths

|   | Sample-level (legacy / baseline) | Token-level (new / primary) |
|---|---|---|
| Dataset | `data/pairs.jsonl` (one row per file) | `data/dataset.jsonl` (one row per file + char-range `token_labels`) |
| Activations | `data/activations_v2/activations_layer*.npz` (last-token vector per file) | per-token vectors (extractor blocked by [#17](https://github.com/peaktwilight/gemmaforge/issues/17)) |
| Probe artifact | `data/probe.npz` (the shipped sample-level probe) | output of `src/train_probe_spanmax.py` |
| Decision granularity | one score per file | one score per token |
| Library entry point | `src.eval.protocol.full_report` | `src.eval.token_protocol.full_token_report` |
| CLI | `scripts/run_eval_framework.py` | `scripts/run_token_eval.py` |
| Notebooks | `eval_probe_report`, `eval_calibration`, `eval_baselines` | `eval_token_probe` |
| Smoke test | `scripts/test_eval_framework.py` | `scripts/test_token_eval.py` |

The shipped sample-level probe is treated as a **baseline** in either
path via `baselines.ProbeBaseline` / `BroadcastProbeBaseline` — so it
shows up alongside `random` / `length` / `regex` in the comparison
tables, not as the headline.

## What's in here

| File | Role |
|---|---|
| `metrics.py` | `compute_clf_metrics`, `bootstrap_auc_ci`, `calibration_metrics` (Brier, ECE), `reliability_curve`, `span_max_metrics`. |
| `splits.py` | Leakage-aware splits: `random_stratified`, `group_repo`, `heldout_cwe`, `heldout_lang`, `heldout_source`. `pair_group_key()` keys on `_origin_repo` → `(_file_name, _func_name)` → row identity. |
| `baselines.py` | `RandomBaseline`, `LengthBaseline`, `RegexBaseline`, `ProbeBaseline`, `BroadcastProbeBaseline`. |
| `probe_io.py` | `Probe` dataclass, `load_probe`, `load_activations`, `load_pairs`, `fit_logreg_on_split`. |
| `protocol.py` | Sample-level: `evaluate_split`, `full_report`. |
| `token_data.py` | Token-level dataset: `load_token_dataset`, `parse_spans`, `char_spans_to_token_spans`. |
| `token_protocol.py` | Token-level: `evaluate_token_split`, `full_token_report` with `all`/`span`/`span_max` aggregations. |
| `repo_protocol.py` | Repo-level scan metrics: `repo_recall@K`, `trace_recall@K`, `precision@K`, MRR, CWE accuracy on hit leads. |
| `report.py` | Markdown + JSON renderers for the sample-level path. |
| `runtime.py` | Per-token probe overhead measurement (model-agnostic). |

## Three aggregation levels (paper Section 4)

| Level | Definition | Use case |
|---|---|---|
| `all` | every token, in or out of span | streaming-UI noise floor — measures false-alarm rate over arbitrary safe code |
| `span` | tokens inside annotated spans only | localisation quality on the labelled regions |
| `span_max` | one decision per span: `max(probs[start:end+1])` | example-level decision metric |

**Note on the current SVEN dataset.** `data/dataset.jsonl` has zero
sanitizer spans, so the `span` level is single-class and AUC is NaN
there. The framework pads negative examples (label=0) with a synthetic
whole-file negative span for the `span_max` computation
(`pad_negatives_for_span_max=True`), so span_max becomes a proper binary
classifier matching the streaming-UI operational metric.

## What we do that the paper doesn't

- **Leakage-aware splits**. The paper's long-form data isn't paired;
  ours is, so a random split puts the safe and vulnerable versions of
  the same file in train AND test. The framework defaults to
  `refit=True` so every OOD claim is honest.
- **Bootstrap 95% CI on AUC**. With ~150–700 test examples per split,
  the AUC standard error is the same order as the gap between splits.
- **Calibration (Brier + ECE)**. The streaming UI uses a fixed
  threshold, so the score has to mean something, not just rank.
- **Trivial baselines on every split**. The probe is only impressive
  insofar as it beats `length` and `regex`. Surfacing this comparison
  is the framework's main contribution to the writeup's honesty.

## How to use

### Sample-level CLI

```bash
uv run --with scikit-learn --with numpy python scripts/run_eval_framework.py \
    --activations data/activations_v2/activations_layer17.npz \
    --pairs       data/pairs.jsonl \
    --layer       17 \
    --out-md      data/eval/report.md \
    --out-json    data/eval/report.json
```

Two probe modes:
- `--refit` (default) refits a fresh logreg per split. Right for OOD claims.
- `--no-refit --probe data/probe.npz` uses a fixed shipped probe and only
  scores test slices. Useful for "how does the deployed probe behave on
  slice X" — but note that if the shipped probe was trained on the full
  dataset, every "OOD" split here is in-distribution for it.

### Token-level CLI

```bash
uv run --with scikit-learn --with numpy python scripts/run_token_eval.py \
    --dataset       data/dataset.jsonl \
    --token-probs   data/activations_v2/token_probs.npz \
    --token-offsets data/activations_v2/token_offsets.npz \
    --out-md        data/eval/token_report.md \
    --out-json      data/eval/token_report.json
```

The two `.npz` inputs are per-row probability arrays + per-row
`(T, 2)` char offsets; format: `probs_row_NNNN` / `offsets_row_NNNN`
keys. They land once the extractor in `src/extract_token_activations.py`
is fixed ([#17](https://github.com/peaktwilight/gemmaforge/issues/17)).
The notebook below runs in demo mode against synthetic oracle scores
while waiting.

### Repo-level generated benchmark

```bash
uv run python scripts/build_repo_benchmark.py \
    --input data/dataset.jsonl \
    --out-root data/repo_benchmark \
    --max-repos 100 \
    --decoys-per-repo 3 \
    --require-fixed-counterpart
```

This writes scanner-ready micro-repos plus `manifest.jsonl`. Each manifest
contains file/line/char traces for vulnerable regions and safe regions for
fixed counterparts/decoys. See `docs/repo-benchmark-schema.md`.

Once scan leads have been written as `<repo_id>.jsonl` files:

```bash
uv run python scripts/eval_repo_leads.py \
    --manifest data/repo_benchmark/manifest.jsonl \
    --leads-dir data/repo_benchmark/leads \
    --out-json data/eval/repo_scan_report.json
```

### GPU repo-scan run

The full 687-repo benchmark is slow on laptop CPU/MPS. Use the GPU wrapper
on a CUDA machine:

```bash
CUDA_VISIBLE_DEVICES=0 bash scripts/run_repo_scan_gpu.sh
```

The wrapper is resumable by default and writes:

- leads: `data/repo_benchmark/leads_weak_full/<repo_id>.jsonl`
- report: `data/eval/repo_scan_report_weak_full.json`

For multiple GPUs or machines, shard the manifest:

```bash
CUDA_VISIBLE_DEVICES=0 NUM_SHARDS=4 SHARD_INDEX=0 bash scripts/run_repo_scan_gpu.sh
CUDA_VISIBLE_DEVICES=1 NUM_SHARDS=4 SHARD_INDEX=1 bash scripts/run_repo_scan_gpu.sh
CUDA_VISIBLE_DEVICES=2 NUM_SHARDS=4 SHARD_INDEX=2 bash scripts/run_repo_scan_gpu.sh
CUDA_VISIBLE_DEVICES=3 NUM_SHARDS=4 SHARD_INDEX=3 bash scripts/run_repo_scan_gpu.sh
```

After all shards finish, aggregate over the shared leads directory:

```bash
uv run python scripts/eval_repo_leads.py \
    --manifest data/repo_benchmark/manifest.jsonl \
    --leads-dir data/repo_benchmark/leads_weak_full \
    --out-json data/eval/repo_scan_report_weak_full.json
```

For a quick GPU smoke test:

```bash
MAX_REPOS=5 CUDA_VISIBLE_DEVICES=0 bash scripts/run_repo_scan_gpu.sh
```

### Notebooks

- `notebooks/eval_probe_report.ipynb` — sample-level top-line.
- `notebooks/eval_calibration.ipynb` — sample-level reliability + threshold.
- `notebooks/eval_baselines.ipynb` — sample-level probe vs trivial baselines.
- `notebooks/eval_token_probe.ipynb` — token-level three-level table, demo + real modes.

`.py` (jupytext-percent) is the source. Convert via:

```bash
uvx jupytext --to ipynb notebooks/eval_token_probe.py
```

### Library

```python
# Sample-level
from src.eval import probe_io, protocol, baselines, report

X, y = probe_io.load_activations("data/activations_v2/activations_layer17.npz")
rows = probe_io.load_pairs("data/pairs.jsonl")
full = protocol.full_report(
    X, y, rows,
    activations_path="data/activations_v2/activations_layer17.npz",
    pairs_path="data/pairs.jsonl",
    layer=17,
    refit=True,
    baselines=baselines.with_probe_baseline("data/probe.npz"),
)
report.write_report(full, "data/eval/report.md", "data/eval/report.json")

# Token-level (once #17 lands)
from src.eval import token_data, token_protocol

rows = token_data.load_token_dataset("data/dataset.jsonl")
# probs_per_row, offsets_per_row: load from extractor outputs
full = token_protocol.full_token_report(
    rows, probs_per_row, token_spans_per_row,
    dataset_path="data/dataset.jsonl",
    baselines=baselines.with_probe_baseline("data/probe.npz", broadcast=True),
)
```

## Smoke tests

```bash
uv run --with scikit-learn --with numpy python scripts/test_eval_framework.py
uv run --with scikit-learn --with numpy python scripts/test_token_eval.py
```

The second runs against synthetic oracle scores on the real
`data/dataset.jsonl` spans; both should pass in < 10 s.
