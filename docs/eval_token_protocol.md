# GemmaForge token-level evaluation protocol

## 1. Overview

The token-level eval scores a per-token vulnerability probe against
character-range ground truth from `data/dataset.jsonl` (SVEN-paired before/after
files with `token_labels.*` char spans). Each test row supplies (a) a
per-token probability array $p \in [0,1]^{T_i}$ from the probe and (b) a
per-token offsets array $(s_t, e_t) \in \mathbb{Z}^{T_i \times 2}$ from the same
tokenizer the probe was trained on. The eval is tokenizer-agnostic: the caller
hands it offsets, never strings.

```text
data/dataset.jsonl            probe.npz                    token-level extractor
 + char-range token_labels     (trained per-token,           per-row probs + offsets
 + per-row code/label/cwe       see train_probe_spanmax.py)   (extract_token_activations.py)
            \                       |                          /
             \______________________|_________________________/
                                    v
                  src/eval/token_data.py
                    parse_spans -> char_spans_to_token_spans
                            -> token_labels_array
                                    v
                src/eval/token_protocol._collect_for_indices
                                    v
            three aggregation levels: {all, span, span_max}
                                    v
              src/eval/metrics.py: AUC + bootstrap CI + Brier + ECE
                                    v
          src/eval/splits.py: random / group_repo / heldout_cwe/lang/source
                                    v
             scripts/run_token_eval.py -> token_report.{md,json}
```

The CLI entry (`scripts/run_token_eval.py:56`) wires three on-disk artefacts:
`data/dataset.jsonl`, an `.npz` of `probs_row_NNNN` float arrays, and an
`.npz` of `offsets_row_NNNN` `(T, 2)` int32 arrays. Row counts must match;
mapping char-ranges to token indices happens inline per row.

## 2. Ground truth: char ranges to token labels

### 2.1 `token_labels` schema

`data/dataset.jsonl` rows carry `token_labels: dict[str, list[[int, int]]]`,
where each inner list is half-open `(start_char, end_char)` ranges into `code`.
Keys partition into two label classes (`src/eval/token_data.py:46`):

- **Positive** ($\ell = 1$): `evidence`, `vulnerable_line`, `sink`, `source`.
  Together these mark the file region that carries the vulnerability.
- **Negative** ($\ell = 0$): `sanitizer`. Marks the mitigated region in
  paired safe files.

Tokens *outside* the union of all annotated spans are treated as label 0 at
the `all` aggregation level and are excluded from `span` / `span_max` entirely.

### 2.2 Deduplication: `parse_spans`

`evidence` and `vulnerable_line` frequently overlap byte-for-byte (the SVEN
builder emits both for the same diff hunk). `parse_spans`
(`src/eval/token_data.py:64`) collapses these to a single positive span per
unique `(start, end)` pair. Sanitizers occupy a disjoint range in practice but
the function will refuse to overwrite an existing positive with a negative at
the same coordinates.

```text
parse_spans(row):
    seen <- {}
    for k in POSITIVE_KEYS (evidence, vulnerable_line, sink, source):
        for (s, e) in row.token_labels[k]:
            if (s, e) not in seen: seen[(s, e)] <- TokenSpan(s, e, 1, k)
    for k in NEGATIVE_KEYS (sanitizer):
        for (s, e) in row.token_labels[k]:
            if (s, e) not in seen: seen[(s, e)] <- TokenSpan(s, e, 0, k)
    return seen.values()
```

### 2.3 Char range to token indices: any-overlap rule

Given the row's `token_offsets`, each char-range $(c_s, c_e)$ maps to the
*inclusive* range of token indices $[i_{\text{first}}, i_{\text{last}}]$ where
token $i$ has offset $(t_s^i, t_e^i)$ satisfying $t_e^i > c_s$ and $t_s^i < c_e$
— i.e. any non-empty overlap. Tokens with zero-width offsets (specials like
BOS/EOS often emit `(0, 0)`) are naturally skipped by the same predicate.

```text
char_spans_to_token_spans(char_spans, token_offsets):
    out <- []
    for span in char_spans:
        first, last <- None, None
        for i, (ts, te) in enumerate(token_offsets):
            if te <= span.start_char: continue           # token ends before span
            if ts >= span.end_char:   break              # token starts after span
            if first is None: first <- i
            last <- i
        if first is not None: out.append((first, last, span.label))
    return out
```

`token_labels_array(n_tokens, token_spans)` (`src/eval/token_data.py:137`)
materialises the per-token target vector $\mathbf{y} \in \{0,1\}^T$ and the
boolean `in_span` mask. Out-of-span tokens get $y_i = 0$ and $\text{mask}_i =
\text{False}$.

## 3. The three aggregation levels

Let example $i$ contribute the score-label arrays
$(\mathbf{p}^{(i)}, \mathbf{y}^{(i)}) \in [0,1]^{T_i} \times \{0,1\}^{T_i}$
and an in-span mask $\mathbf{m}^{(i)} \in \{0,1\}^{T_i}$. Let $\mathcal{I}$ be
the test indices for a split.

### 3.1 `all` — every token of every test example

$$
\text{AUC}_{\text{all}} = \text{AUC}\big(\{(y_t^{(i)}, p_t^{(i)}) : i \in \mathcal{I},\, t \in [T_i]\}\big).
$$

Concatenate every token's score and label across the test set. Out-of-span
tokens count as negatives. This is the eval level dominated by the long tail
of safe code, so accuracy looks high (mid-90s on the example report) while F1
stays low.

```text
all_p, all_y <- concat([token_probs[i], token_labels_array(...)[0] for i in test_idx])
auc, ci_lo, ci_hi <- compute_auc + bootstrap CI
brier, ece <- calibration_metrics(all_y, all_p)
```

Well-defined iff $\{0, 1\} \subseteq \{y_t^{(i)} : i \in \mathcal{I}, t\}$.
Single-class test sets (e.g. `heldout_source::SVEN-after` is all-negative)
return NaN AUC.

### 3.2 `span` — tokens inside annotated spans only

$$
\text{AUC}_{\text{span}} = \text{AUC}\big(\{(y_t^{(i)}, p_t^{(i)}) : i \in \mathcal{I},\, t \in [T_i],\, m_t^{(i)} = 1\}\big).
$$

Restrict to tokens inside *any* span (positive or negative). In the current
dataset, sanitizer spans are extremely sparse: in every shipped split, every
in-span token is positive (see `n_pos == n_total` for every `span` row in
`data/eval/token_report.md` lines 10-43). With only one class present, AUC is
undefined and the metric reports NaN; precision / recall against the threshold
0.5 still compute and appear in the JSON. Until the dataset grows negative
(sanitizer) annotations, `span` is effectively a positive-recall reporter.

```text
span_p, span_y <- all_p[mask], all_y[mask]
auc <- AUC(span_y, span_p)  # NaN unless mask covers both classes
```

### 3.3 `span_max` — one decision per example

For each test example with at least one token,

$$
\text{AUC}_{\text{span\_max}} = \text{AUC}\big(\{(Y_i,\, \max_{t \in [T_i]} p_t^{(i)}) : i \in \mathcal{I}\}\big),
$$

where $Y_i$ is the row-level label from `row["label"]`. This is the operational
rule the streaming UI uses ("the file is risky iff any token's prob is high")
and the same aggregation `src/train_probe_spanmax.py` reports as `ex_AUC`.

```text
span_max_pairs <- [(row.label, max(token_probs[i])) for i in test_idx if T_i > 0]
sm_y, sm_p <- unzip(span_max_pairs)
auc, ci_lo, ci_hi <- compute_auc + bootstrap CI
```

**Recent fix (commit `e2606b9`, `src/eval/token_protocol.py:103-126`).** The
prior code emitted one pair per char-range span for positives (max over ~2
tokens) but one max-over-whole-file pair for negatives. With noisy probes,
max-over-many wins on noise: $\mathbb{E}[\max_{t \le n} \epsilon_t] \propto
\sqrt{2 \ln n}$. Pos pool $n \approx 2$, neg pool $n \approx 500$ → negatives'
expected max dominates, inverting $\text{AUC}_{\text{span\_max}}$ below 0.5
on every split. The fix imposes symmetric per-example aggregation (pool size
$T_i$ on both sides), restoring monotonicity in probe quality.

Well-defined iff at least one row of each class survives the
$T_i > 0$ filter. Otherwise NaN (see `heldout_source::*` rows in the example
report).

## 4. Metrics computed at each level

`_level_metrics` (`src/eval/token_protocol.py:66`) wraps everything below into
one flat dict, then `compute_clf_metrics` and `calibration_metrics` do the work.

### 4.1 AUC

ROC AUC,

$$
\text{AUC} = \mathbb{P}\!\left[p_+ > p_-\right] + \tfrac{1}{2} \mathbb{P}\!\left[p_+ = p_-\right],
$$

over a random positive / negative pair. Computed via `sklearn.metrics.roc_auc_score`.
Returns NaN when only one class is present (`_safe_auc`,
`src/eval/metrics.py:54`). Reference: Hanley & McNeil 1982.

### 4.2 Bootstrap 95% CI

Percentile bootstrap (`src/eval/metrics.py:122`), $B = 1000$ resamples
(default `--bootstrap-n 1000`). For each $b$, draw indices $\sim
\text{Uniform}([n])$ with replacement, recompute $\widehat{\text{AUC}}_b$,
report $[\widehat{\text{AUC}}_{(0.025)}, \widehat{\text{AUC}}_{(0.975)}]$.
Single-class resamples are silently dropped. CI half-widths typically land at
$\pm 0.03$-$0.08$, comparable to between-split gaps — hence the CI columns.
References: Efron 1979 (percentile bootstrap origin); DeLong et al. 1988 is
the closed-form AUC-variance counterpart — bootstrap is preferred here for
non-parametric robustness on small heterogeneous splits.

### 4.3 F1, precision, recall

At threshold $\tau = 0.5$ (`preds = (probs >= 0.5).astype(int)`,
`src/eval/token_protocol.py:74`):

$$
F_1 = \frac{2 \cdot \text{prec} \cdot \text{rec}}{\text{prec} + \text{rec}}, \quad
\text{prec} = \frac{\text{TP}}{\text{TP}+\text{FP}}, \quad
\text{rec} = \frac{\text{TP}}{\text{TP}+\text{FN}}.
$$

The 0.5 threshold is rarely calibrated — see the Brier / ECE numbers and the
`optimal_threshold` field for the threshold-tuned accuracy.

### 4.4 Recall at fixed FPR

For target $\alpha \in \{0.01, 0.05, 0.10, 0.20\}$ (`FPR_TARGETS`,
`src/eval/metrics.py:31`),

$$
R@\alpha = \max\{\text{TPR}(\tau) : \text{FPR}(\tau) \le \alpha\}.
$$

Computed from `roc_curve` then `tpr[idx[-1]]` over `fpr <= target`
(`src/eval/metrics.py:103`). Returns 0.0 if no threshold meets the FPR budget.
$R@0.05$ is the operational pin for the streaming UI ("one false alarm per
~20 tokens of safe code").

### 4.5 Brier score

$$
\text{Brier} = \frac{1}{n} \sum_{i=1}^n (p_i - y_i)^2.
$$

Proper scoring rule, decomposes into reliability + resolution − uncertainty
(Murphy 1973). Penalises miscalibrated overconfidence. Reference: Brier 1950,
"Verification of Forecasts Expressed in Terms of Probability", *Monthly
Weather Review* 78(1).

### 4.6 ECE (expected calibration error)

Bin probs into 15 equal-*width* bins $B_1, \dots, B_{15}$ over $[0, 1]$
(`src/eval/metrics.py:176`):

$$
\text{ECE} = \sum_{b=1}^{15} \frac{|B_b|}{n} \left| \tfrac{1}{|B_b|}\sum_{i \in B_b} p_i - \tfrac{1}{|B_b|}\sum_{i \in B_b} y_i \right|.
$$

i.e. average $|\text{confidence} - \text{accuracy}|$ over bins, weighted by
bin mass. Reference: Naeini, Cooper & Hauskrecht 2015, "Obtaining Well
Calibrated Probabilities Using Bayesian Binning", *AAAI*. Note: this code uses
equal-*width* bins, not the equal-*mass* binning some implementations prefer;
empty bins are skipped without down-weighting.

## 5. Splits

`make_splits` (`src/eval/splits.py:153`) emits the canonical bundle. Each
split is constructed at the *example* level; token-level eval then slices the
per-row arrays by example index. Splits encode five distinct generalisation
claims (`src/eval/splits.py:14-19`):

### 5.1 `random_stratified`

`train_test_split(idx, test_size=0.2, stratify=y)` (`src/eval/splits.py:81`).
Leaky baseline: pairs share group keys and end up split across train/test, so
the probe can memorise SVEN repos. Used only to anchor the upper bound; not
evidence of generalisation.

### 5.2 `group_repo` — pair-aware leakage control

`GroupShuffleSplit` (`src/eval/splits.py:87`) with the group key from
`pair_group_key(row)` (`src/eval/splits.py:38`):

$$
\text{key}(r) = \begin{cases}
\texttt{repo::} \oplus r.\!\_origin\_repo & \text{if non-empty (CyberSecEval / CyberNative)} \\
\texttt{func::} \oplus r.\!\_file\_name \oplus \texttt{::} \oplus r.\!\_func\_name & \text{else if either set (SVEN)} \\
\texttt{row::} \oplus \text{id}(r) & \text{else (singleton)}
\end{cases}
$$

Backstory (#18): SVEN rows have no `_origin_repo` but do have
`(_file_name, _func_name)` from the diff; the naive group-on-`_origin_repo`
collapsed all SVEN rows into the `None` group and made `group_repo` equivalent
to `random_stratified` on that corpus. The fallback chain in `pair_group_key`
fixes that — see the `n_groups=677` annotation in the example report.

### 5.3 `heldout_cwe`

`split_heldout_cwe` (`src/eval/splits.py:99`) finds the top-5 most common
positive CWEs by `Counter(pos_cwes).most_common(5)` and emits one split per
CWE: test = all rows with that CWE (positive or negatively-paired), train =
everything else. `attach_paired_cwe` (`src/eval/splits.py:61`) propagates CWE
from each pair's positive row to its negative twin via `pair_group_key`, so
heldout-CWE keeps pairs together and doesn't leak the negative half. Tests
"generalises to unseen vulnerability classes".

### 5.4 `heldout_lang`

One split per `lang` value in `{python, c, cpp, ...}`. Test = rows in that
language, train = the rest (`src/eval/splits.py:111`). If the test set is
single-class, the split is still emitted but flagged in `note=`; AUC will be
NaN.

### 5.5 `heldout_source`

One split per `source` value (e.g. `SVEN-before`, `SVEN-after`)
(`src/eval/splits.py:133`). On the shipped dataset, both halves are
single-class (`SVEN-before` is 100% positive, `SVEN-after` is 100% negative)
so AUC is structurally undefined — these splits sanity-check the pipeline
plumbing rather than generalisation.

## 6. Baselines

All baselines score one float per example, then `evaluate_token_split`
(`src/eval/token_protocol.py:202`) *broadcasts* that scalar to every token in
the row. This gives a flat baseline against which token-resolution probes have
to beat at `all` and `span` levels; at `span_max` the comparison collapses
to one-score-per-example, the natural setting for a sample-level model.

### 6.1 `RandomBaseline`

$p_i \sim \text{Uniform}(0,1)$ per example
(`src/eval/baselines.py:61`). Expected AUC = 0.5; observed numbers in the
report straddle 0.4-0.6 due to finite-sample noise. Floor.

### 6.2 `LengthBaseline`

$p_i = \text{minmax}(\text{len}(\text{code}_i))$ (`src/eval/baselines.py:72`).
Tests for the length confound (#22): if longer files are systematically
positive in the corpus, length alone gets a high AUC and inflates probe
numbers that are partly explained by length. On the token report
(`heldout_lang::test=python` row) length scores `all_auc = 0.386`, well below
the probe's 0.865 — token-level on `data/dataset.jsonl` is not length-confounded.

### 6.3 `RegexBaseline`

Counts matches across a hand-curated Semgrep-style pattern dict
(`VULN_PATTERNS`, `src/eval/baselines.py:23`), squashed via
$p = 1 - e^{-\text{count}}$. Sample patterns:

```python
"eval-call":          r"\beval\s*\("
"sql-template-string": r"`[^`]*SELECT[^`]*\$\{"
"shell-true":         r"shell\s*=\s*True"
"strcpy":             r"\bstrcpy\s*\("
"pickle-loads":       r"\bpickle\.loads?\s*\("
```

Worst-case baseline a deployed probe must beat: anyone could ship the regex
in an afternoon. In the example report regex sits at 0.46-0.53 `all_auc` —
the probe's 0.85+ is real signal over regex.

### 6.4 `BroadcastProbeBaseline`

The shipped sample-level probe (one logistic head over a single last-token
activation, `data/probe.npz`) wrapped as a baseline
(`src/eval/baselines.py:147`). Per example it returns
$\sigma(\mathbf{w}^\top \mathbf{x}_i + b)$, broadcast to every token. Its
purpose: quantify the resolution upgrade from sample-level to token-level —
the sample-level probe outputs one decision per file, so broadcasting it to
tokens gives the AUC the streaming UI would see if you fed the file-level
decision into the per-token UI. In the example report it scores `all_auc`
≈ 0.45-0.51 — at chance, because the sample-level probe was trained on
CyberSecEval and the token eval lives on SVEN (corpus mismatch).

## 7. Known limitations

1. **SVEN char ranges are diff-derived and surgical.** Median char-range width
   is 3 chars, p90 is 28. After char→token mapping the median positive span
   is ~2 tokens. Everything outside is treated as a negative, which punishes
   any probe that fires "near" the bug rather than "on" the bug.
   Proximity-aware soft labels (Gaussian decay over distance to nearest
   positive token, or IoU-based credit) are the right fix; until then the
   `all`-level numbers under-estimate semantically-correct firing.

2. **Sample-level probe at AUC ≈ 0.5 when broadcast** to token-level data is
   not a probe-quality result, it's a corpus-mismatch result. The sample
   probe was trained on `data/pairs.jsonl` (CyberSecEval lineage); the token
   eval runs on `data/dataset.jsonl` (SVEN). It establishes that the new
   token probe is doing something the old probe wasn't, not that the old
   probe is bad.

3. **Length confound (#22)** inflates sample-level numbers on
   `data/pairs.jsonl`. On token-level `data/dataset.jsonl` it's weaker:
   `length` AUC is 0.20-0.39 across splits vs probe 0.75-0.93. Closed via
   length-matched eval (commits `498005e`, `95c29db`); watch on future
   corpus additions.

4. **`span_max` brittleness.** Even after the symmetry fix, median-2-token
   positive spans against $T_i \approx 500$-token negative pools is tight
   SNR: max of 500 noisy negatives often matches max of 2 noisy positives.
   CIs reflect this — $\pm 0.07$ half-widths on `span_max` AUC are common.
   Proximity-aware metrics or learned aggregation (mean-top-k,
   attention-pool) would stabilise the level.

5. **`span` level is positive-only** on the current dataset (every shipped
   split has $n_{\text{pos}} = n_{\text{total}}$ at `span`, AUC = NaN).
   Needs more sanitizer annotations, or a redefinition as "in-span positive
   vs out-of-span negative subset".

6. **`heldout_source::SVEN-*` AUCs are structurally NaN** (each half is
   single-class). Plumbing smoke test, not a generalisation metric.

## 8. References

- **Obeso, Arditi, et al. 2025.** "On the language-model side of hallucination
  probes." arXiv:2509.03531. The span-max loss in §3 (per-example
  $\max$-aggregation with a per-token logistic backbone) is what
  `src/train_probe_spanmax.py` implements; the three aggregation levels here
  follow §4 of the same paper.

- **He & Vechev 2023.** "Large Language Models for Code: Security Hardening
  and Adversarial Testing" (SVEN). arXiv:2302.05319. Source of the
  `data/dataset.jsonl` paired before/after samples and the char-range
  `token_labels` (derived from the SVEN diff hunks).

- **Bhatt et al. 2023.** "Purple Llama CyberSecEval: A Secure Coding
  Benchmark for Language Models." arXiv:2312.04724. Source of the
  sample-level `data/pairs.jsonl` corpus that backs `BroadcastProbeBaseline`
  and the `_origin_repo` group key.

- **Efron 1979.** "Bootstrap Methods: Another Look at the Jackknife."
  *Annals of Statistics* 7(1):1-26. Origin of the percentile bootstrap.

- **DeLong, DeLong & Clarke-Pearson 1988.** "Comparing the Areas Under Two
  or More Correlated ROC Curves." *Biometrics* 44(3):837-845. Standard
  closed-form AUC variance reference; the percentile bootstrap here is its
  non-parametric counterpart.

- **Hanley & McNeil 1982.** "The meaning and use of the area under a
  receiver operating characteristic (ROC) curve." *Radiology* 143(1):29-36.

- **Brier 1950.** "Verification of Forecasts Expressed in Terms of
  Probability." *Monthly Weather Review* 78(1):1-3.

- **Naeini, Cooper & Hauskrecht 2015.** "Obtaining Well Calibrated
  Probabilities Using Bayesian Binning." *AAAI* 2015. ECE definition.
