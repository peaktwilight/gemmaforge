# Probe evaluation report

Activations: `data/activations/activations_layer17.npz` (layer 17, N=1198, pos=599)
Pairs metadata: `data/pairs.jsonl`
Probe fit mode: `fixed pretrained probe`

## Per-split metrics

| split | AUC (95% CI) | F1 | R@5%FPR | R@10%FPR | Brier | ECE | n_test | pos |
|---|---|---|---|---|---|---|---|---|
| `random_stratified` | 0.965 (0.944-0.984) | 0.917 | 0.825 | 0.942 | 0.073 | 0.060 | 240 | 120 |
| `group_repo` | 0.998 (0.995-1.000) | 0.979 | 0.992 | 0.992 | 0.015 | 0.021 | 238 | 119 |
| `heldout_cwe::CWE-78` | 1.000 (0.999-1.000) | 0.994 | 1.000 | 1.000 | 0.007 | 0.019 | 165 | 82 |
| `heldout_cwe::CWE-338` | 0.990 (0.968-1.000) | 0.987 | 0.987 | 0.987 | 0.014 | 0.019 | 158 | 79 |
| `heldout_cwe::CWE-95` | 0.999 (0.996-1.000) | 0.987 | 1.000 | 1.000 | 0.014 | 0.028 | 159 | 78 |
| `heldout_cwe::CWE-94` | 0.992 (0.976-1.000) | 0.969 | 0.985 | 0.985 | 0.025 | 0.024 | 130 | 65 |
| `heldout_cwe::CWE-328` | 0.997 (0.990-1.000) | 0.991 | 0.982 | 0.982 | 0.012 | 0.021 | 111 | 55 |
| `heldout_lang::test=javascript` | 0.994 (0.985-1.000) | 0.984 | 0.992 | 0.992 | 0.015 | 0.016 | 498 | 249 |
| `heldout_lang::test=python` | 0.997 (0.994-0.999) | 0.981 | 0.991 | 0.991 | 0.016 | 0.009 | 700 | 350 |
| `heldout_source::CyberSecEval` | n/a (n/a-n/a) | 0.992 | n/a | n/a | n/a | n/a | 599 | 599 |
| `heldout_source::CyberSecEval-leadup` | n/a (n/a-n/a) | 0.000 | n/a | n/a | n/a | n/a | 599 | 0 |

## Probe vs baselines (AUC)

| split | probe | random | length | regex |
|---|---|---|---|---|
| `random_stratified` | 0.965 | 0.393 | 0.895 | 0.701 |
| `group_repo` | 0.998 | 0.508 | 0.911 | 0.685 |
| `heldout_cwe::CWE-78` | 1.000 | 0.520 | 0.840 | 0.721 |
| `heldout_cwe::CWE-338` | 0.990 | 0.474 | 0.885 | 0.782 |
| `heldout_cwe::CWE-95` | 0.999 | 0.446 | 0.884 | 0.675 |
| `heldout_cwe::CWE-94` | 0.992 | 0.476 | 0.935 | 0.748 |
| `heldout_cwe::CWE-328` | 0.997 | 0.473 | 0.904 | 0.991 |
| `heldout_lang::test=javascript` | 0.994 | 0.522 | 0.883 | 0.647 |
| `heldout_lang::test=python` | 0.997 | 0.519 | 0.885 | 0.719 |
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

- Random stratified (leaky): **AUC=0.965** (CI 0.944-0.984)
- Group-by-repo: **AUC=0.998** (CI 0.995-1.000)
- Worst credible OOD split (`heldout_cwe::CWE-338`): **AUC=0.990** (CI 0.968-1.000), F1=0.987, R@10%FPR=0.987

Recommended writeup number: **AUC=0.990 (0.968-1.000)** under `heldout_cwe::CWE-338`.
