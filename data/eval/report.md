# Probe evaluation report

Activations: `data/activations_v2/activations_layer17.npz` (layer 17, N=1198, pos=599)
Pairs metadata: `data/pairs.jsonl`
Probe fit mode: `refit per split (OOD)`

## Per-split metrics

| split | AUC (95% CI) | F1 | R@5%FPR | R@10%FPR | Brier | ECE | n_test | pos |
|---|---|---|---|---|---|---|---|---|
| `random_stratified` | 0.963 (0.943-0.983) | 0.921 | 0.833 | 0.942 | 0.071 | 0.065 | 240 | 120 |
| `group_repo` | 0.958 (0.937-0.979) | 0.924 | 0.790 | 0.924 | 0.075 | 0.082 | 238 | 119 |
| `heldout_cwe::CWE-78` | 0.923 (0.884-0.959) | 0.857 | 0.561 | 0.793 | 0.125 | 0.139 | 165 | 82 |
| `heldout_cwe::CWE-338` | 0.923 (0.881-0.960) | 0.809 | 0.658 | 0.785 | 0.134 | 0.137 | 158 | 79 |
| `heldout_cwe::CWE-95` | 0.942 (0.898-0.974) | 0.890 | 0.782 | 0.897 | 0.096 | 0.089 | 159 | 78 |
| `heldout_cwe::CWE-94` | 0.960 (0.926-0.984) | 0.908 | 0.846 | 0.908 | 0.077 | 0.073 | 130 | 65 |
| `heldout_cwe::CWE-328` | 0.944 (0.912-0.975) | 0.822 | 0.600 | 0.745 | 0.120 | 0.106 | 111 | 55 |
| `heldout_lang::test=javascript` | 0.907 (0.878-0.933) | 0.815 | 0.602 | 0.695 | 0.145 | 0.121 | 498 | 249 |
| `heldout_lang::test=python` | 0.929 (0.914-0.946) | 0.864 | 0.637 | 0.717 | 0.117 | 0.089 | 700 | 350 |
| `heldout_source::CyberSecEval` | n/a (n/a-n/a) | n/a | n/a | n/a | n/a | n/a | 599 | 599 |
| `heldout_source::CyberSecEval-leadup` | n/a (n/a-n/a) | n/a | n/a | n/a | n/a | n/a | 599 | 0 |

## Probe vs baselines (AUC)

| split | probe | random | length | regex |
|---|---|---|---|---|
| `random_stratified` | 0.963 | 0.393 | 0.895 | 0.701 |
| `group_repo` | 0.958 | 0.508 | 0.911 | 0.685 |
| `heldout_cwe::CWE-78` | 0.923 | 0.520 | 0.840 | 0.721 |
| `heldout_cwe::CWE-338` | 0.923 | 0.474 | 0.885 | 0.782 |
| `heldout_cwe::CWE-95` | 0.942 | 0.446 | 0.884 | 0.675 |
| `heldout_cwe::CWE-94` | 0.960 | 0.476 | 0.935 | 0.748 |
| `heldout_cwe::CWE-328` | 0.944 | 0.473 | 0.904 | 0.991 |
| `heldout_lang::test=javascript` | 0.907 | 0.522 | 0.883 | 0.647 |
| `heldout_lang::test=python` | 0.929 | 0.519 | 0.885 | 0.719 |
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
- `heldout_source::CyberSecEval`: train set single-class
- `heldout_source::CyberSecEval-leadup`: train set single-class

## Headline

- Random stratified (leaky): **AUC=0.963** (CI 0.943-0.983)
- Group-by-repo: **AUC=0.958** (CI 0.937-0.979)
- Worst credible OOD split (`heldout_lang::test=javascript`): **AUC=0.907** (CI 0.878-0.933), F1=0.815, R@10%FPR=0.695

Recommended writeup number: **AUC=0.907 (0.878-0.933)** under `heldout_lang::test=javascript`.
