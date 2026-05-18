# Probe evaluation report

Activations: `data/activations_e4b/activations_layer10.npz` (layer 10, N=1198, pos=599)
Pairs metadata: `data/pairs.jsonl`
Probe fit mode: `fixed pretrained probe`

## Per-split metrics

| split | AUC (95% CI) | F1 | R@5%FPR | R@10%FPR | Brier | ECE | n_test | pos |
|---|---|---|---|---|---|---|---|---|
| `random_stratified` | 0.996 (0.989-1.000) | 0.988 | 1.000 | 1.000 | 0.010 | 0.012 | 240 | 120 |
| `group_repo` | 0.969 (0.946-0.988) | 0.931 | 0.731 | 0.958 | 0.062 | 0.067 | 238 | 119 |
| `heldout_cwe::CWE-78` | 0.998 (0.992-1.000) | 0.982 | 1.000 | 1.000 | 0.014 | 0.016 | 165 | 82 |
| `heldout_cwe::CWE-338` | 0.992 (0.981-1.000) | 0.969 | 0.987 | 1.000 | 0.028 | 0.029 | 158 | 79 |
| `heldout_cwe::CWE-95` | 0.986 (0.962-1.000) | 0.975 | 0.987 | 1.000 | 0.025 | 0.022 | 159 | 78 |
| `heldout_cwe::CWE-94` | 1.000 (1.000-1.000) | 1.000 | 1.000 | 1.000 | 0.000 | 0.004 | 130 | 65 |
| `heldout_cwe::CWE-328` | 0.999 (0.996-1.000) | 0.982 | 0.982 | 1.000 | 0.015 | 0.016 | 111 | 55 |
| `heldout_lang::test=javascript` | 0.991 (0.980-0.998) | 0.982 | 0.996 | 1.000 | 0.016 | 0.012 | 498 | 249 |
| `heldout_lang::test=python` | 0.998 (0.997-1.000) | 0.987 | 0.997 | 1.000 | 0.011 | 0.010 | 700 | 350 |
| `heldout_source::CyberSecEval` | n/a (n/a-n/a) | 0.996 | n/a | n/a | n/a | n/a | 599 | 599 |
| `heldout_source::CyberSecEval-leadup` | n/a (n/a-n/a) | 0.000 | n/a | n/a | n/a | n/a | 599 | 0 |

## Probe vs baselines (AUC)

| split | probe | random | length | regex |
|---|---|---|---|---|
| `random_stratified` | 0.996 | 0.393 | 0.895 | 0.701 |
| `group_repo` | 0.969 | 0.508 | 0.911 | 0.685 |
| `heldout_cwe::CWE-78` | 0.998 | 0.520 | 0.840 | 0.721 |
| `heldout_cwe::CWE-338` | 0.992 | 0.474 | 0.885 | 0.782 |
| `heldout_cwe::CWE-95` | 0.986 | 0.446 | 0.884 | 0.675 |
| `heldout_cwe::CWE-94` | 1.000 | 0.476 | 0.935 | 0.748 |
| `heldout_cwe::CWE-328` | 0.999 | 0.473 | 0.904 | 0.991 |
| `heldout_lang::test=javascript` | 0.991 | 0.522 | 0.883 | 0.647 |
| `heldout_lang::test=python` | 0.998 | 0.519 | 0.885 | 0.719 |
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

- Random stratified (leaky): **AUC=0.996** (CI 0.989-1.000)
- Group-by-repo: **AUC=0.969** (CI 0.946-0.988)
- Worst credible OOD split (`heldout_cwe::CWE-95`): **AUC=0.986** (CI 0.962-1.000), F1=0.975, R@10%FPR=1.000

Recommended writeup number: **AUC=0.986 (0.962-1.000)** under `heldout_cwe::CWE-95`.
