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

## Length-matched eval

Issue [#22](https://github.com/peaktwilight/gemmaforge/issues/22) flagged that in `data/pairs.jsonl` positives are truncated AFTER the vulnerable line and negatives BEFORE it, so positives are ~2x longer (mean 396 vs 200 chars). A length-only baseline gets AUC 0.883 on Py->JS — the probe's 0.907 was only +0.024 above that. To control for length we matched each positive to a same-language negative within +/- 10% character length (greedy, closest delta, each negative used at most once) and re-ran the layer-17 LogReg probe on the surviving rows using the cached activations from `data/activations_v2/activations_layer17.npz`. Pipeline: `scripts/build_length_matched_eval.py` -> `data/pairs_length_matched.jsonl` -> `scripts/eval_length_matched.py` -> `data/eval_length_matched.json`. Kept **230 matched pairs** (135 Python, 95 JavaScript). Post-match mean character length is ~284 / ~285 (JS) and ~304 / ~307 (Py) across the two classes, i.e. effectively balanced.

| Split                              | Probe AUC | Length-only AUC | Delta  |
|------------------------------------|----------:|----------------:|-------:|
| Full pairs.jsonl (random 80/20)    |     0.963 |           0.737 | +0.226 |
| Py->JS, full                       |     0.907 |           0.883 | +0.024 |
| Length-matched subset (80/20)      |     0.903 |           0.614 | +0.288 |
| Py->JS, length-matched             |     0.843 |           0.514 | +0.329 |

Verdict: the probe holds up. Once positives and negatives have matched character lengths, the length baseline collapses to near-chance (Py->JS 0.514) while the probe stays at AUC 0.843 — a delta of +0.329 versus the +0.024 delta we had with the length artifact still present. The probe drops modestly (0.907 -> 0.843 on Py->JS, an absolute -0.064) but it is now beating length by an order of magnitude wider margin, so the 0.907 headline was **not** mostly length. This is post-hoc evidence and the writeup should still keep the disclosure of the original artifact, but it closes [#22](https://github.com/peaktwilight/gemmaforge/issues/22) on the "probe partially learns length" question.
