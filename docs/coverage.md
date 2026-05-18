# Per-language vulnerability-probe coverage

This document summarises which programming languages the GemmaForge vulnerability probe currently covers, how strong the signal is per language, and where the obvious gaps lie. The combined coverage below comes from `data/pairs.jsonl` (CyberSecEval position-paired, 1198 rows) and `data/pairs_sven.jsonl` (SVEN before-fix functions, 1560 rows). Only `pairs.jsonl` is currently aligned to extracted activations at `data/activations_v2/activations_layer17.npz`, so within-language and cross-language probe metrics are only available for the two languages in that file (Python and JavaScript). SVEN rows are reported as coverage-only counts until matched activations are extracted.

## Methodology

- Probe: `sklearn.linear_model.LogisticRegression(C=1.0, max_iter=2000)` on the layer-17 residual-stream activations (1536-dim).
- Within-language metrics: 80/20 stratified split per language, `random_state=42`, single fit.
- Cross-language metrics: train on the full Python subset, test on the full JavaScript subset (and vice versa) — no row overlap by construction (language is disjoint).
- AUC = ROC AUC on the positive class. ACC = top-1 accuracy at the default 0.5 threshold.

## Coverage table

| lang        | n_positive | n_negative | within-language AUC | within-language ACC | cross-language AUC                | known gaps |
|-------------|-----------:|-----------:|--------------------:|--------------------:|-----------------------------------|------------|
| python      |        715 |        715 |              0.9604 |              0.9143 | 0.9292 (trained on JS → eval Py)  | SVEN Python (n=730) not yet activation-extracted; CWE coverage skewed toward CWE-022/078/079/089/502 |
| javascript  |        249 |        249 |              0.9576 |              0.8900 | 0.9073 (trained on Py → eval JS)  | No SVEN-style fix-pair set; CyberSecEval-leadup only; no DOM-XSS or prototype-pollution coverage |
| c           |        360 |        360 |                 n/a |                 n/a | n/a                               | Activations not yet extracted (SVEN-only); needs the activation-extraction pass to be re-run over `pairs_sven.jsonl` |
| cpp         |         55 |         55 |                 n/a |                 n/a | n/a                               | Sample too small (n=110 total) for a stable probe even after extraction; oversample from Juliet/Devign-cpp |

Headline cross-language number: training the probe on Python activations and evaluating on JavaScript yields **AUC = 0.907**, which matches the figure already cited in `WRITEUP.md` and confirms the probe is picking up a language-portable vulnerability signal rather than Python-specific surface features.

## Languages not in our dataset

- **rust** — next data source: CyberSecEval-2 (`vulnerability_detection` split has Rust subset) and the `rust-vulnerability-dataset` on Hugging Face. Effort: medium (need to re-run activation extraction).
- **go** — next data source: CyberSecEval-2 Go split, plus Go advisory database (`golang.org/x/vuln/vulndb`) for paired fix commits. Effort: medium; advisory DB needs scraping to produce before/after pairs.
- **ruby** — next data source: RubySec advisory database (`rubysec/ruby-advisory-db`) paired against the upstream commits, or the multi-language subset of CrossVul. Effort: high — no clean paired dataset exists today.
- **php** — next data source: SARD/Juliet PHP subset and the PHP CVE list from `FriendsOfPHP/security-advisories`. Effort: medium; SARD is already in machine-readable format.

## What would change the picture

- **Priority 1: extract activations over `pairs_sven.jsonl` (n=1560).** Effort: ~1 GPU-hour at `layer={08,17,26,34}`. Expected gain: unlocks C / C++ within-language AUC and a Python↔C cross-language number — the most useful generalisation signal for systems-language CVE triage.
- **Priority 2: balance JavaScript with a SVEN-style fix-pair corpus (target n_positive ≥ 500).** Effort: ~1 day of scraping `npm` advisories with linked fix commits (we already have the CVE pipeline). Expected gain: lifts JS within-language AUC variance and gives us a paired-fix evaluation set that mirrors the Python one.
- **Priority 3: add at least one systems-language outside SVEN (Rust or Go, n≥300 per class).** Effort: 2–3 days including extraction. Expected gain: lets us claim "language-portable" with three languages on the cross-language curve instead of two, which is the main credibility ask in the writeup.

Tracked in [#7](https://github.com/peaktwilight/gemmaforge/issues/7).
