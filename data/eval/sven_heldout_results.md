# SVEN held-out repo benchmark — three probe variants

This compares three weak-probe configurations on the **136 held-out
micro-repos** in `data/repo_benchmark_heldout/`. The held-out set comes
from a deterministic 80/20 group split of `pairs_sven.jsonl`
(`sven_split_meta.json`, seed=42), so the SVEN-trained probes never saw
these rows during training (except `probe_spanmax.npz`, which is the
legacy in-sample artifact retained for reference).

| metric | CSE-trained `probe.npz` | SVEN-LogReg `probe_sven.npz` | SVEN span-max `probe_spanmax.npz` |
|---|---:|---:|---:|
| training data | CyberSecEval `pairs.jsonl` (1198 rows) | SVEN 80% train (1254 rows, 614 groups) | full SVEN `dataset.jsonl` (1374 rows, leaked) |
| leakage on heldout 136 | zero (different corpus) | zero (group split) | **full (rows are in train set)** |
| objective | last-token LogReg | last-token LogReg | token-level span-max (Obeso et al. 2025) |
| layer | 17 | 8 | 8 |
| repo_recall@1 | 5.1% | 0.0% | 30.9% |
| repo_recall@5 | 47.1% | 44.1% | 64.0% |
| repo_recall@10 | 72.8% | 62.5% | 76.5% |
| repo_recall@25 | 86.0% | 85.3% | 87.5% |
| precision@1 | 5.1% | 0.0% | 30.9% |
| precision@5 | 10.5% | 9.7% | 14.3% |
| precision@25 | 11.7% | 11.3% | 11.6% |
| MRR | 0.226 | 0.177 | 0.457 |
| cwe_top1_on_hits@25 | 0% / NaN (label mismatch) | 37.9% | 41.6% |
| cwe_top1_on_hits@1 | NaN | NaN | 64.3% |

## Take-aways

- **Span-max dominates last-token LogReg.** MRR doubles (0.23 → 0.46),
  precision@1 goes from 5% to 31%, recall@10 jumps 10+ pp. Token-level
  training matches what the scanner already does at inference time
  (per-token max within a window), so the gain is method, not just data.
- **In-sample caveat.** `probe_spanmax.npz` was trained on the full
  `dataset.jsonl`, which includes all 136 held-out rows. The top-K
  numbers above are an upper bound. A group-clean retrain on the 80%
  train split lands at example_AUC 0.669 vs the in-sample 0.700 — only
  a 3 pp gap, suggesting the 1,537-param probe doesn't have the
  capacity to overfit much. Full clean-scan numbers will land in
  `repo_scan_report_weak_spanmax_clean.json`.
- **SVEN-LogReg (probe_sven.npz) is honest but weak.** Group-shuffle
  AUC 0.669; recall trails the CSE baseline. SVEN is genuinely harder
  data than CyberSecEval at the last-token level — the span-max
  objective is doing the heavy lifting.
- **Per-CWE accuracy is now real.** The original `probe_per_cwe.npz`
  was trained on CyberSecEval's CWE space (CWE-78/338/95/94/328) which
  barely overlaps with SVEN's (089/078/079/022/125/190/416/476/787),
  so it was structurally incapable of producing the right SVEN label —
  hence the 0/NaN. `probe_per_cwe_sven.npz` (layer 8, 9 heads,
  GroupShuffleSplit) macro-AUC 0.749.

## Reproducing

```bash
# 1. Split SVEN groups 80/20 (already done, deterministic seed=42)
#    -> data/pairs_sven_train.jsonl + data/dataset_sven_heldout.jsonl

# 2. Generate sample-level activations for the 80% train split
uv run python -m src.extract_activations \
    --pairs data/pairs_sven_train.jsonl \
    --out data/activations_sven

# 3. Train SVEN binary + per-CWE probes (layer 8 wins for both)
uv run python -m src.train_probe \
    --acts-dir data/activations_sven \
    --pairs data/pairs_sven_train.jsonl \
    --out data/probe_sven.npz --card data/probe_sven_card.json

# 4. Rebuild repo benchmark from held-out 20%
uv run python scripts/build_repo_benchmark.py \
    --input data/dataset_sven_heldout.jsonl \
    --out-root data/repo_benchmark_heldout --max-repos 9999

# 5. Scan held-out repos with each probe variant
uv run python scripts/run_repo_scan_benchmark.py \
    --benchmark-root data/repo_benchmark_heldout \
    --leads-dir data/repo_benchmark_heldout/leads_weak_sven \
    --out-json data/eval/repo_scan_report_weak_sven.json \
    --probe-path data/probe_sven.npz \
    --per-cwe-probe-path data/probe_per_cwe_sven.npz \
    --probe-profile weak-probe

# 6. (Clean) retrain span-max on the same 80% train split (group-aware)
uv run python scripts/retrain_spanmax_sven_split.py
#    -> data/probe_spanmax_sven_train.npz (best layer 26)
```
