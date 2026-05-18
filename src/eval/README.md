# `src/eval/` — GemmaForge probe evaluation framework

Adapted from the hallucination-probes paper methodology
(Obeso et al. 2025, [arxiv.org/abs/2509.03531](https://arxiv.org/abs/2509.03531))
and specialised to vulnerability-detection probes on Gemma 4 hidden states.

## What's in here

| File | Role |
|---|---|
| `metrics.py` | `compute_clf_metrics`, `bootstrap_auc_ci`, `calibration_metrics` (Brier, ECE), `reliability_curve`, `span_max_metrics`. |
| `splits.py` | Leakage-aware splits: `random_stratified`, `group_repo`, `heldout_cwe`, `heldout_lang`, `heldout_source`. |
| `baselines.py` | `RandomBaseline`, `LengthBaseline`, `RegexBaseline` (sharing patterns with `scripts/eval_lora.py`). |
| `probe_io.py` | `Probe` dataclass, `load_probe`, `load_activations`, `load_pairs`, `fit_logreg_on_split`. |
| `protocol.py` | `evaluate_split`, `full_report` orchestration. |
| `report.py` | Markdown + JSON renderers. |
| `runtime.py` | Per-token probe overhead measurement. |

## What the paper does that we do too

- Compute classification metrics at multiple aggregation levels.
  The paper's three levels are `all` / `span` / `span_max`; with our
  current example-level activations only `span_max` is meaningful (one
  vector per file = one decision per file). `span_max_metrics` in
  `metrics.py` is the implementation that turns on once
  `extract_token_activations.py` is wired in.
- Recall at fixed FPR (`0.05`, `0.10`, `0.20`) — the paper uses 0.1 FPR
  as a key operational metric for the streaming UI; we add 0.05 because
  the streaming UI here has higher false-alarm cost (one alarm per ~20
  tokens of safe code).
- Optimal threshold + threshold-optimised accuracy.
- ROC curve plotting with FPR markers.

## What we do that the paper doesn't

- **Leakage-aware splits** (`splits.py`). The paper's long-form data is
  not paired; ours is, so a random split puts the safe and vulnerable
  versions of the same file in train AND test. The framework defaults to
  `refit=True` so every OOD claim is honest.
- **Bootstrap 95 % CI on AUC**. With ~150–700 test examples per split,
  the AUC standard error is the same order as the gap between splits.
- **Calibration (Brier + ECE)**. The streaming UI uses a fixed threshold,
  so the score has to mean something, not just rank correctly.
- **Trivial baselines on every split**. The probe is only impressive
  insofar as it beats `length` and `regex`. Surfacing this comparison
  is the framework's main contribution to the writeup's honesty.

## How to use

### CLI (one-shot)

```bash
uv run python scripts/run_eval_framework.py \
    --activations data/activations_v2/activations_layer17.npz \
    --pairs       data/pairs.jsonl \
    --layer       17 \
    --out-md      data/eval/report.md \
    --out-json    data/eval/report.json
```

### Notebooks

- `notebooks/eval_probe_report.ipynb` — top-line: AUC + CI per split, ROC,
  per-layer comparison, headline plot.
- `notebooks/eval_calibration.ipynb` — reliability diagram per split,
  threshold sweep, deployment-threshold recommendation.
- `notebooks/eval_baselines.ipynb` — probe vs random/length/regex,
  ROC overlay on the worst-credible split.

`.py` (jupytext-percent) is the source. Convert via:

```bash
uvx jupytext --to ipynb notebooks/eval_probe_report.py
```

### Library

```python
from src.eval import probe_io, protocol, baselines, report

X, y = probe_io.load_activations("data/activations_v2/activations_layer17.npz")
rows = probe_io.load_pairs("data/pairs.jsonl")

full = protocol.full_report(
    X, y, rows,
    activations_path="data/activations_v2/activations_layer17.npz",
    pairs_path="data/pairs.jsonl",
    layer=17,
    refit=True,
    baselines=baselines.all_baselines(),
)
report.write_report(full, "data/eval/report.md", "data/eval/report.json")
```

## Smoke test

```bash
uv run python scripts/test_eval_framework.py
```

Synthetic dataset, every code path exercised. Should pass in < 3 s.
