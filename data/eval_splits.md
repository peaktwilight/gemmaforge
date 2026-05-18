# Leakage-aware re-evaluation of the layer-17 probe

Data: `data/activations_v2/activations_layer17.npz` (N=1198, dim=1536, pos=599)

Probe: `LogisticRegression(max_iter=1000, C=1.0)` on layer 17.

| Split | AUC | ACC | n_train | n_test |
|---|---:|---:|---:|---:|
| `random_stratified` | 0.963 | 0.921 | 958 | 240 |
| `group_repo` | 0.958 | 0.916 | 960 | 238 |
| `heldout_cwe::CWE-78` | 0.924 | 0.848 | 1033 | 165 |
| `heldout_cwe::CWE-338` | 0.923 | 0.829 | 1040 | 158 |
| `heldout_cwe::CWE-95` | 0.942 | 0.893 | 1039 | 159 |
| `heldout_cwe::CWE-94` | 0.960 | 0.908 | 1068 | 130 |
| `heldout_cwe::CWE-328` | 0.945 | 0.829 | 1087 | 111 |
| `heldout_lang::test=python` | 0.929 | 0.857 | 498 | 700 |
| `heldout_lang::test=javascript` | 0.907 | 0.819 | 700 | 498 |

## Notes

- `random_stratified` is the leaky baseline used by `src/train_probe.py`. The paired safe/vulnerable variants of a snippet share `_origin_repo`, so a random split puts both halves of the same pair in train AND test.
- `group_repo` uses `GroupShuffleSplit` on `_origin_repo` -- the same repo never appears in both partitions.
- `heldout_cwe::*` trains on every CWE except the named one and tests only on that CWE (negatives inherit their pair's CWE so held-out CWE pulls both halves out together).
- `heldout_lang::*` trains on the other language and tests on the named one.
- `heldout_source`: skipped. In `pairs.jsonl` the v2 `source` field is `CyberSecEval` for positives and `CyberSecEval-leadup` for negatives (['CyberSecEval', 'CyberSecEval-leadup']), so a leave-one-source-out split would have a single-class test set and AUC would be undefined.

## Headline

- Random stratified (leaky baseline): **AUC=0.963** / ACC=0.921
- Repo-grouped: **AUC=0.958** / ACC=0.916
- Worst credible split (`heldout_lang::test=javascript`): **AUC=0.907** / ACC=0.819

Recommended writeup number: **AUC=0.907** under `heldout_lang::test=javascript` (the strictest credible stress test).
