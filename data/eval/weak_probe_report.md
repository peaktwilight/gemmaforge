# Probe evaluation report

Activations: `data/activations/activations_layer17.npz` (layer 17, N=1198, pos=599)
Pairs metadata: `data/pairs.jsonl`
Probe fit mode: `fixed pretrained probe`

## Per-split metrics

| split | AUC (95% CI) | F1 | R@5%FPR | R@10%FPR | Brier | ECE | n_test | pos |
|---|---|---|---|---|---|---|---|---|
| `random_stratified` | 0.999 (0.997-1.000) | 0.992 | 0.992 | 1.000 | 0.010 | 0.016 | 240 | 120 |
| `group_repo` | 0.960 (0.932-0.982) | 0.923 | 0.773 | 0.958 | 0.071 | 0.068 | 238 | 119 |
| `heldout_cwe::CWE-78` | 0.986 (0.961-1.000) | 0.976 | 0.988 | 0.988 | 0.023 | 0.024 | 165 | 82 |
| `heldout_cwe::CWE-338` | 0.995 (0.983-1.000) | 0.981 | 0.987 | 0.987 | 0.014 | 0.017 | 158 | 79 |
| `heldout_cwe::CWE-95` | 0.995 (0.986-1.000) | 0.975 | 1.000 | 1.000 | 0.021 | 0.030 | 159 | 78 |
| `heldout_cwe::CWE-94` | 1.000 (1.000-1.000) | 1.000 | 1.000 | 1.000 | 0.002 | 0.015 | 130 | 65 |
| `heldout_cwe::CWE-328` | 0.990 (0.968-1.000) | 0.973 | 0.982 | 0.982 | 0.023 | 0.020 | 111 | 55 |
| `heldout_lang::test=javascript` | 0.996 (0.990-1.000) | 0.984 | 1.000 | 1.000 | 0.013 | 0.015 | 498 | 249 |
| `heldout_lang::test=python` | 0.991 (0.983-0.998) | 0.983 | 0.991 | 0.991 | 0.016 | 0.010 | 700 | 350 |
| `heldout_source::CyberSecEval` | n/a (n/a-n/a) | 0.996 | n/a | n/a | n/a | n/a | 599 | 599 |
| `heldout_source::CyberSecEval-leadup` | n/a (n/a-n/a) | 0.000 | n/a | n/a | n/a | n/a | 599 | 0 |

## Probe vs baselines (AUC)

| split | probe | random | length | regex |
|---|---|---|---|---|
| `random_stratified` | 0.999 | 0.393 | 0.895 | 0.701 |
| `group_repo` | 0.960 | 0.508 | 0.911 | 0.685 |
| `heldout_cwe::CWE-78` | 0.986 | 0.520 | 0.840 | 0.721 |
| `heldout_cwe::CWE-338` | 0.995 | 0.474 | 0.885 | 0.782 |
| `heldout_cwe::CWE-95` | 0.995 | 0.446 | 0.884 | 0.675 |
| `heldout_cwe::CWE-94` | 1.000 | 0.476 | 0.935 | 0.748 |
| `heldout_cwe::CWE-328` | 0.990 | 0.473 | 0.904 | 0.991 |
| `heldout_lang::test=javascript` | 0.996 | 0.522 | 0.883 | 0.647 |
| `heldout_lang::test=python` | 0.991 | 0.519 | 0.885 | 0.719 |
| `heldout_source::CyberSecEval` | n/a | n/a | n/a | n/a |
| `heldout_source::CyberSecEval-leadup` | n/a | n/a | n/a | n/a |

## Split notes

- `random_stratified`: leaky baseline; pairs share group key
- `group_repo`: GroupShuffleSplit on pair_group_key (n_groups=589)
- `heldout_cwe::CWE-78`: train all-except / test only
- `heldout_cwe::CWE-338`: train all-except / test only
- `heldout_cwe::CWE-95`: train all-except / test only
- `heldout_cwe::CWE-94`: train all-except / test only
- `heldout_cwe::CWE-328`: train all-except / test only
- `heldout_source::CyberSecEval`: single-class test (599/599 pos); skipped
- `heldout_source::CyberSecEval-leadup`: single-class test (0/599 pos); skipped

## Headline

- Random stratified (leaky): **AUC=0.999** (CI 0.997-1.000)
- Group-by-repo: **AUC=0.960** (CI 0.932-0.982)
- Worst credible OOD split (`heldout_cwe::CWE-78`): **AUC=0.986** (CI 0.961-1.000), F1=0.976, R@10%FPR=0.988

Recommended writeup number: **AUC=0.986 (0.961-1.000)** under `heldout_cwe::CWE-78`.
