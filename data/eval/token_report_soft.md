# Token-level probe evaluation report

Dataset: `data/dataset.jsonl` (N=1374, pos=687)

## Per-split metrics (W=10 for dilated_span_max)

| split | level | AUC (95% CI) | F1 | R@10%FPR | Brier | n_total | n_pos |
|---|---|---|---|---|---|---:|---:|
| `random_stratified` | all | 0.849 (0.841-0.857) | 0.229 | 0.585 | 0.049 | 121499 | 2053 |
| `random_stratified` | proximal_all | 0.753 (0.748-0.762) | 0.271 | 0.420 | 0.063 | 121499 | 5862 |
| `random_stratified` | span | nan (nan-nan) | 0.591 | nan | nan | 2053 | 2053 |
| `random_stratified` | span_max | 0.638 (0.556-0.710) | 0.667 | 0.355 | 0.343 | 275 | 138 |
| `random_stratified` | dilated_span_max | 0.505 (0.423-0.591) | 0.591 | 0.348 | 0.383 | 275 | 138 |
| `group_repo` | all | 0.800 (0.791-0.808) | 0.198 | 0.493 | 0.047 | 128710 | 2275 |
| `group_repo` | proximal_all | 0.736 (0.730-0.742) | 0.243 | 0.395 | 0.062 | 128710 | 6323 |
| `group_repo` | span | nan (nan-nan) | 0.479 | nan | nan | 2275 | 2275 |
| `group_repo` | span_max | 0.573 (0.504-0.637) | 0.662 | 0.328 | 0.346 | 274 | 137 |
| `group_repo` | dilated_span_max | 0.467 (0.401-0.534) | 0.592 | 0.299 | 0.378 | 274 | 137 |
| `heldout_cwe::CWE-089` | all | 0.933 (0.928-0.938) | 0.302 | 0.813 | 0.085 | 79251 | 2204 |
| `heldout_cwe::CWE-089` | proximal_all | 0.762 (0.757-0.767) | 0.403 | 0.439 | 0.110 | 79251 | 9348 |
| `heldout_cwe::CWE-089` | span | nan (nan-nan) | 0.899 | nan | nan | 2204 | 2204 |
| `heldout_cwe::CWE-089` | span_max | 0.878 (0.842-0.912) | 0.667 | 0.647 | 0.394 | 408 | 204 |
| `heldout_cwe::CWE-089` | dilated_span_max | 0.877 (0.840-0.911) | 0.667 | 0.637 | 0.394 | 408 | 204 |
| `heldout_cwe::CWE-125` | all | 0.803 (0.792-0.814) | 0.107 | 0.449 | 0.030 | 158091 | 1335 |
| `heldout_cwe::CWE-125` | proximal_all | 0.716 (0.708-0.725) | 0.113 | 0.329 | 0.038 | 158091 | 3371 |
| `heldout_cwe::CWE-125` | span | nan (nan-nan) | 0.257 | nan | nan | 1335 | 1335 |
| `heldout_cwe::CWE-125` | span_max | 0.512 (0.430-0.584) | 0.656 | 0.151 | 0.304 | 212 | 106 |
| `heldout_cwe::CWE-125` | dilated_span_max | 0.331 (0.261-0.405) | 0.530 | 0.123 | 0.355 | 212 | 106 |
| `heldout_cwe::CWE-078` | all | 0.867 (0.861-0.876) | 0.283 | 0.621 | 0.086 | 64711 | 2145 |
| `heldout_cwe::CWE-078` | proximal_all | 0.762 (0.756-0.769) | 0.375 | 0.444 | 0.103 | 64711 | 6349 |
| `heldout_cwe::CWE-078` | span | nan (nan-nan) | 0.752 | nan | nan | 2145 | 2145 |
| `heldout_cwe::CWE-078` | span_max | 0.740 (0.681-0.807) | 0.667 | 0.362 | 0.380 | 210 | 105 |
| `heldout_cwe::CWE-078` | dilated_span_max | 0.702 (0.634-0.771) | 0.658 | 0.352 | 0.389 | 210 | 105 |
| `heldout_cwe::CWE-476` | all | 0.782 (0.766-0.796) | 0.095 | 0.425 | 0.033 | 76793 | 891 |
| `heldout_cwe::CWE-476` | proximal_all | 0.707 (0.697-0.718) | 0.082 | 0.308 | 0.042 | 76793 | 2002 |
| `heldout_cwe::CWE-476` | span | nan (nan-nan) | 0.191 | nan | nan | 891 | 891 |
| `heldout_cwe::CWE-476` | span_max | 0.483 (0.378-0.592) | 0.655 | 0.105 | 0.301 | 114 | 57 |
| `heldout_cwe::CWE-476` | dilated_span_max | 0.256 (0.170-0.369) | 0.530 | 0.035 | 0.355 | 114 | 57 |
| `heldout_cwe::CWE-079` | all | 0.750 (0.738-0.764) | 0.179 | 0.352 | 0.082 | 35082 | 1299 |
| `heldout_cwe::CWE-079` | proximal_all | 0.671 (0.663-0.681) | 0.185 | 0.254 | 0.103 | 35082 | 2760 |
| `heldout_cwe::CWE-079` | span | nan (nan-nan) | 0.426 | nan | nan | 1299 | 1299 |
| `heldout_cwe::CWE-079` | span_max | 0.518 (0.424-0.636) | 0.667 | 0.160 | 0.358 | 100 | 50 |
| `heldout_cwe::CWE-079` | dilated_span_max | 0.326 (0.234-0.447) | 0.649 | 0.080 | 0.377 | 100 | 50 |
| `heldout_lang::test=c` | all | 0.771 (0.763-0.777) | 0.086 | 0.404 | 0.033 | 394160 | 3920 |
| `heldout_lang::test=c` | proximal_all | 0.694 (0.688-0.699) | 0.092 | 0.296 | 0.043 | 394160 | 9951 |
| `heldout_lang::test=c` | span | nan (nan-nan) | 0.203 | nan | nan | 3920 | 3920 |
| `heldout_lang::test=c` | span_max | 0.496 (0.447-0.538) | 0.656 | 0.104 | 0.308 | 538 | 269 |
| `heldout_lang::test=c` | dilated_span_max | 0.293 (0.247-0.329) | 0.527 | 0.063 | 0.361 | 538 | 269 |
| `heldout_lang::test=cpp` | all | 0.765 (0.746-0.784) | 0.127 | 0.380 | 0.051 | 34815 | 647 |
| `heldout_lang::test=cpp` | proximal_all | 0.698 (0.687-0.711) | 0.147 | 0.296 | 0.066 | 34815 | 1670 |
| `heldout_lang::test=cpp` | span | nan (nan-nan) | 0.311 | nan | nan | 647 | 647 |
| `heldout_lang::test=cpp` | span_max | 0.483 (0.363-0.623) | 0.673 | 0.132 | 0.325 | 76 | 38 |
| `heldout_lang::test=cpp` | dilated_span_max | 0.262 (0.150-0.407) | 0.558 | 0.079 | 0.377 | 76 | 38 |
| `heldout_lang::test=python` | all | 0.862 (0.858-0.867) | 0.274 | 0.613 | 0.087 | 184836 | 6048 |
| `heldout_lang::test=python` | proximal_all | 0.744 (0.740-0.748) | 0.358 | 0.404 | 0.109 | 184836 | 19634 |
| `heldout_lang::test=python` | span | nan (nan-nan) | 0.752 | nan | nan | 6048 | 6048 |
| `heldout_lang::test=python` | span_max | 0.763 (0.728-0.799) | 0.667 | 0.503 | 0.386 | 760 | 380 |
| `heldout_lang::test=python` | dilated_span_max | 0.723 (0.680-0.763) | 0.658 | 0.497 | 0.392 | 760 | 380 |
| `heldout_source::SVEN-after` | all | nan (nan-nan) | 0.000 | nan | nan | 309943 | 0 |
| `heldout_source::SVEN-after` | proximal_all | nan (nan-nan) | 0.000 | nan | nan | 309943 | 0 |
| `heldout_source::SVEN-after` | span_max | nan (nan-nan) | 0.000 | nan | nan | 687 | 0 |
| `heldout_source::SVEN-after` | dilated_span_max | nan (nan-nan) | 0.000 | nan | nan | 687 | 0 |
| `heldout_source::SVEN-before` | all | 0.838 (0.835-0.842) | 0.329 | 0.567 | 0.054 | 303868 | 10615 |
| `heldout_source::SVEN-before` | proximal_all | 0.769 (0.766-0.772) | 0.353 | 0.454 | 0.083 | 303868 | 31255 |
| `heldout_source::SVEN-before` | span | nan (nan-nan) | 0.567 | nan | nan | 10615 | 10615 |
| `heldout_source::SVEN-before` | span_max | nan (nan-nan) | 0.991 | nan | nan | 687 | 687 |
| `heldout_source::SVEN-before` | dilated_span_max | nan (nan-nan) | 0.924 | nan | nan | 687 | 687 |

## Baselines (AUC at each level)

| split | baseline | all | span | span_max | dilated_span_max |
|---|---|---:|---:|---:|---:|
| `random_stratified` | random | 0.406 | nan | 0.515 | 0.515 |
| `random_stratified` | length | 0.243 | nan | 0.472 | 0.472 |
| `random_stratified` | regex | 0.497 | nan | 0.483 | 0.483 |
| `random_stratified` | probe_layer17 | 0.487 | nan | 0.510 | 0.510 |
| `group_repo` | random | 0.468 | nan | 0.471 | 0.471 |
| `group_repo` | length | 0.301 | nan | 0.489 | 0.489 |
| `group_repo` | regex | 0.459 | nan | 0.504 | 0.504 |
| `group_repo` | probe_layer17 | 0.436 | nan | 0.525 | 0.525 |
| `heldout_cwe::CWE-089` | random | 0.501 | nan | 0.504 | 0.504 |
| `heldout_cwe::CWE-089` | length | 0.369 | nan | 0.499 | 0.499 |
| `heldout_cwe::CWE-089` | regex | 0.504 | nan | 0.518 | 0.518 |
| `heldout_cwe::CWE-089` | probe_layer17 | 0.437 | nan | 0.510 | 0.510 |
| `heldout_cwe::CWE-125` | random | 0.553 | nan | 0.515 | 0.515 |
| `heldout_cwe::CWE-125` | length | 0.220 | nan | 0.490 | 0.490 |
| `heldout_cwe::CWE-125` | regex | 0.498 | nan | 0.500 | 0.500 |
| `heldout_cwe::CWE-125` | probe_layer17 | 0.433 | nan | 0.529 | 0.529 |
| `heldout_cwe::CWE-078` | random | 0.531 | nan | 0.494 | 0.494 |
| `heldout_cwe::CWE-078` | length | 0.375 | nan | 0.490 | 0.490 |
| `heldout_cwe::CWE-078` | regex | 0.527 | nan | 0.529 | 0.529 |
| `heldout_cwe::CWE-078` | probe_layer17 | 0.422 | nan | 0.487 | 0.487 |
| `heldout_cwe::CWE-476` | random | 0.480 | nan | 0.417 | 0.417 |
| `heldout_cwe::CWE-476` | length | 0.198 | nan | 0.479 | 0.479 |
| `heldout_cwe::CWE-476` | regex | 0.472 | nan | 0.491 | 0.491 |
| `heldout_cwe::CWE-476` | probe_layer17 | 0.339 | nan | 0.486 | 0.486 |
| `heldout_cwe::CWE-079` | random | 0.439 | nan | 0.576 | 0.576 |
| `heldout_cwe::CWE-079` | length | 0.324 | nan | 0.483 | 0.483 |
| `heldout_cwe::CWE-079` | regex | 0.478 | nan | 0.500 | 0.500 |
| `heldout_cwe::CWE-079` | probe_layer17 | 0.563 | nan | 0.518 | 0.518 |
| `heldout_lang::test=c` | random | 0.550 | nan | 0.499 | 0.499 |
| `heldout_lang::test=c` | length | 0.265 | nan | 0.490 | 0.490 |
| `heldout_lang::test=c` | regex | 0.467 | nan | 0.500 | 0.500 |
| `heldout_lang::test=c` | probe_layer17 | 0.390 | nan | 0.507 | 0.507 |
| `heldout_lang::test=cpp` | random | 0.655 | nan | 0.630 | 0.630 |
| `heldout_lang::test=cpp` | length | 0.249 | nan | 0.452 | 0.452 |
| `heldout_lang::test=cpp` | regex | 0.481 | nan | 0.500 | 0.500 |
| `heldout_lang::test=cpp` | probe_layer17 | 0.336 | nan | 0.499 | 0.499 |
| `heldout_lang::test=python` | random | 0.485 | nan | 0.495 | 0.495 |
| `heldout_lang::test=python` | length | 0.386 | nan | 0.492 | 0.492 |
| `heldout_lang::test=python` | regex | 0.497 | nan | 0.517 | 0.517 |
| `heldout_lang::test=python` | probe_layer17 | 0.479 | nan | 0.513 | 0.513 |
| `heldout_source::SVEN-after` | random | nan | nan | nan | nan |
| `heldout_source::SVEN-after` | length | nan | nan | nan | nan |
| `heldout_source::SVEN-after` | regex | nan | nan | nan | nan |
| `heldout_source::SVEN-after` | probe_layer17 | nan | nan | nan | nan |
| `heldout_source::SVEN-before` | random | 0.508 | nan | nan | nan |
| `heldout_source::SVEN-before` | length | 0.263 | nan | nan | nan |
| `heldout_source::SVEN-before` | regex | 0.475 | nan | nan | nan |
| `heldout_source::SVEN-before` | probe_layer17 | 0.432 | nan | nan | nan |
