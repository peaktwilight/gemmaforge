# Token-level probe evaluation report

Dataset: `data/dataset.jsonl` (N=1374, pos=687)

## Per-split metrics (three aggregation levels)

| split | level | AUC (95% CI) | F1 | R@10%FPR | Brier | n_total | n_pos |
|---|---|---|---|---|---|---:|---:|
| `random_stratified` | all | 0.848 (0.840-0.857) | 0.258 | 0.596 | 0.037 | 121499 | 2053 |
| `random_stratified` | span | nan (nan-nan) | 0.510 | nan | nan | 2053 | 2053 |
| `random_stratified` | span_max | 0.639 (0.557-0.704) | 0.657 | 0.370 | 0.312 | 275 | 138 |
| `group_repo` | all | 0.799 (0.790-0.807) | 0.212 | 0.486 | 0.037 | 128710 | 2275 |
| `group_repo` | span | nan (nan-nan) | 0.400 | nan | nan | 2275 | 2275 |
| `group_repo` | span_max | 0.566 (0.494-0.636) | 0.646 | 0.299 | 0.320 | 274 | 137 |
| `heldout_cwe::CWE-089` | all | 0.935 (0.930-0.939) | 0.388 | 0.808 | 0.057 | 79251 | 2204 |
| `heldout_cwe::CWE-089` | span | nan (nan-nan) | 0.844 | nan | nan | 2204 | 2204 |
| `heldout_cwe::CWE-089` | span_max | 0.879 (0.843-0.914) | 0.670 | 0.618 | 0.347 | 408 | 204 |
| `heldout_cwe::CWE-125` | all | 0.799 (0.788-0.810) | 0.098 | 0.443 | 0.023 | 158091 | 1335 |
| `heldout_cwe::CWE-125` | span | nan (nan-nan) | 0.180 | nan | nan | 1335 | 1335 |
| `heldout_cwe::CWE-125` | span_max | 0.514 (0.430-0.587) | 0.637 | 0.170 | 0.285 | 212 | 106 |
| `heldout_cwe::CWE-078` | all | 0.864 (0.858-0.873) | 0.316 | 0.617 | 0.065 | 64711 | 2145 |
| `heldout_cwe::CWE-078` | span | nan (nan-nan) | 0.671 | nan | nan | 2145 | 2145 |
| `heldout_cwe::CWE-078` | span_max | 0.716 (0.649-0.789) | 0.665 | 0.324 | 0.345 | 210 | 105 |
| `heldout_cwe::CWE-476` | all | 0.761 (0.744-0.776) | 0.070 | 0.374 | 0.025 | 76793 | 891 |
| `heldout_cwe::CWE-476` | span | nan (nan-nan) | 0.108 | nan | nan | 891 | 891 |
| `heldout_cwe::CWE-476` | span_max | 0.478 (0.371-0.583) | 0.614 | 0.088 | 0.290 | 114 | 57 |
| `heldout_cwe::CWE-079` | all | 0.751 (0.739-0.764) | 0.174 | 0.369 | 0.066 | 35082 | 1299 |
| `heldout_cwe::CWE-079` | span | nan (nan-nan) | 0.325 | nan | nan | 1299 | 1299 |
| `heldout_cwe::CWE-079` | span_max | 0.505 (0.407-0.621) | 0.653 | 0.140 | 0.333 | 100 | 50 |
| `heldout_lang::test=c` | all | 0.763 (0.755-0.769) | 0.072 | 0.380 | 0.026 | 394160 | 3920 |
| `heldout_lang::test=c` | span | nan (nan-nan) | 0.129 | nan | nan | 3920 | 3920 |
| `heldout_lang::test=c` | span_max | 0.497 (0.449-0.545) | 0.634 | 0.112 | 0.291 | 538 | 269 |
| `heldout_lang::test=cpp` | all | 0.756 (0.736-0.775) | 0.114 | 0.383 | 0.040 | 34815 | 647 |
| `heldout_lang::test=cpp` | span | nan (nan-nan) | 0.213 | nan | nan | 647 | 647 |
| `heldout_lang::test=cpp` | span_max | 0.493 (0.363-0.614) | 0.661 | 0.105 | 0.303 | 76 | 38 |
| `heldout_lang::test=python` | all | 0.865 (0.861-0.870) | 0.321 | 0.621 | 0.064 | 184836 | 6048 |
| `heldout_lang::test=python` | span | nan (nan-nan) | 0.678 | nan | nan | 6048 | 6048 |
| `heldout_lang::test=python` | span_max | 0.764 (0.728-0.799) | 0.665 | 0.516 | 0.346 | 760 | 380 |
| `heldout_source::SVEN-after` | all | nan (nan-nan) | 0.000 | nan | nan | 309943 | 0 |
| `heldout_source::SVEN-after` | span_max | nan (nan-nan) | 0.000 | nan | nan | 687 | 0 |
| `heldout_source::SVEN-before` | all | 0.836 (0.832-0.840) | 0.338 | 0.567 | 0.044 | 303868 | 10615 |
| `heldout_source::SVEN-before` | span | nan (nan-nan) | 0.491 | nan | nan | 10615 | 10615 |
| `heldout_source::SVEN-before` | span_max | nan (nan-nan) | 0.971 | nan | nan | 687 | 687 |

## Baselines (AUC at each level)

| split | baseline | all | span | span_max |
|---|---|---:|---:|---:|
| `random_stratified` | random | 0.406 | nan | 0.515 |
| `random_stratified` | length | 0.243 | nan | 0.472 |
| `random_stratified` | regex | 0.497 | nan | 0.483 |
| `random_stratified` | probe_layer17 | 0.481 | nan | 0.508 |
| `group_repo` | random | 0.468 | nan | 0.471 |
| `group_repo` | length | 0.301 | nan | 0.489 |
| `group_repo` | regex | 0.459 | nan | 0.504 |
| `group_repo` | probe_layer17 | 0.451 | nan | 0.523 |
| `heldout_cwe::CWE-089` | random | 0.501 | nan | 0.504 |
| `heldout_cwe::CWE-089` | length | 0.369 | nan | 0.499 |
| `heldout_cwe::CWE-089` | regex | 0.504 | nan | 0.518 |
| `heldout_cwe::CWE-089` | probe_layer17 | 0.461 | nan | 0.513 |
| `heldout_cwe::CWE-125` | random | 0.553 | nan | 0.515 |
| `heldout_cwe::CWE-125` | length | 0.220 | nan | 0.490 |
| `heldout_cwe::CWE-125` | regex | 0.498 | nan | 0.500 |
| `heldout_cwe::CWE-125` | probe_layer17 | 0.421 | nan | 0.535 |
| `heldout_cwe::CWE-078` | random | 0.531 | nan | 0.494 |
| `heldout_cwe::CWE-078` | length | 0.375 | nan | 0.490 |
| `heldout_cwe::CWE-078` | regex | 0.527 | nan | 0.529 |
| `heldout_cwe::CWE-078` | probe_layer17 | 0.461 | nan | 0.477 |
| `heldout_cwe::CWE-476` | random | 0.480 | nan | 0.417 |
| `heldout_cwe::CWE-476` | length | 0.198 | nan | 0.479 |
| `heldout_cwe::CWE-476` | regex | 0.472 | nan | 0.491 |
| `heldout_cwe::CWE-476` | probe_layer17 | 0.365 | nan | 0.474 |
| `heldout_cwe::CWE-079` | random | 0.439 | nan | 0.576 |
| `heldout_cwe::CWE-079` | length | 0.324 | nan | 0.483 |
| `heldout_cwe::CWE-079` | regex | 0.478 | nan | 0.500 |
| `heldout_cwe::CWE-079` | probe_layer17 | 0.514 | nan | 0.523 |
| `heldout_lang::test=c` | random | 0.550 | nan | 0.499 |
| `heldout_lang::test=c` | length | 0.265 | nan | 0.490 |
| `heldout_lang::test=c` | regex | 0.467 | nan | 0.500 |
| `heldout_lang::test=c` | probe_layer17 | 0.383 | nan | 0.506 |
| `heldout_lang::test=cpp` | random | 0.655 | nan | 0.630 |
| `heldout_lang::test=cpp` | length | 0.249 | nan | 0.452 |
| `heldout_lang::test=cpp` | regex | 0.481 | nan | 0.500 |
| `heldout_lang::test=cpp` | probe_layer17 | 0.313 | nan | 0.481 |
| `heldout_lang::test=python` | random | 0.485 | nan | 0.495 |
| `heldout_lang::test=python` | length | 0.386 | nan | 0.492 |
| `heldout_lang::test=python` | regex | 0.497 | nan | 0.517 |
| `heldout_lang::test=python` | probe_layer17 | 0.491 | nan | 0.514 |
| `heldout_source::SVEN-after` | random | nan | nan | nan |
| `heldout_source::SVEN-after` | length | nan | nan | nan |
| `heldout_source::SVEN-after` | regex | nan | nan | nan |
| `heldout_source::SVEN-after` | probe_layer17 | nan | nan | nan |
| `heldout_source::SVEN-before` | random | 0.508 | nan | nan |
| `heldout_source::SVEN-before` | length | 0.263 | nan | nan |
| `heldout_source::SVEN-before` | regex | 0.475 | nan | nan |
| `heldout_source::SVEN-before` | probe_layer17 | 0.449 | nan | nan |
