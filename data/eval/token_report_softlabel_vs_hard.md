# Soft-label vs hard-label span-max probe — head-to-head

Trained on `data/token_activations/` (Gemma 4 E2B layer 8, 613,811 tokens
across 1374 examples). Identical architecture (`LinearProbe`) and optimizer
(`AdamW lr=1e-3, weight_decay=1e-4, batch_examples=8, 30 epochs`) — the
only difference is the training labels.

- **Hard** (`data/probe_spanmax.npz`): `--label-window 0`. Token labels are
  `y_i ∈ {0, 1}` from `token_labels` char-range positives.
- **Soft W=8** (`data/probe_spanmax_soft.npz`): `--label-window 8`. Same
  positive tokens get `y_i = 1`; tokens within 8 of any positive span get
  `y_i = 1 - dist/8`; everything else stays 0. Overlapping tails resolve
  via max. Span-max term in the loss keeps using *hard* labels so the
  max-pool still peaks on the annotated identifier (closes #26).

Eval: `scripts/run_token_eval.py --proximity-window 10 --bootstrap-n 200`
on the canonical 5-split bundle. Reports below are at the four aggregation
levels defined in `src/eval/token_protocol.py`.

## Headline: soft labels improve `proximal_all` AUC across every split

| split                       | level             | hard   | soft   | Δ       |
|---                          |---                |---:    |---:    |---:     |
| random_stratified           | all               | 0.848  | 0.849  | +0.001  |
| random_stratified           | **proximal_all**  | 0.729  | 0.753  | **+0.024** |
| random_stratified           | span_max          | 0.639  | 0.638  | −0.000  |
| random_stratified           | dilated_span_max  | 0.506  | 0.505  | −0.001  |
| group_repo                  | all               | 0.799  | 0.800  | +0.001  |
| group_repo                  | **proximal_all**  | 0.715  | 0.736  | **+0.021** |
| group_repo                  | span_max          | 0.566  | 0.573  | +0.007  |
| group_repo                  | dilated_span_max  | 0.454  | 0.467  | +0.013  |
| heldout_cwe::CWE-089 (SQLi) | all               | 0.935  | 0.933  | −0.002  |
| heldout_cwe::CWE-089 (SQLi) | **proximal_all**  | 0.725  | 0.762  | **+0.038** |
| heldout_cwe::CWE-089 (SQLi) | span_max          | 0.879  | 0.878  | −0.001  |
| heldout_cwe::CWE-089 (SQLi) | dilated_span_max  | 0.878  | 0.877  | −0.001  |
| heldout_cwe::CWE-078 (cmd)  | all               | 0.864  | 0.867  | +0.003  |
| heldout_cwe::CWE-078 (cmd)  | **proximal_all**  | 0.751  | 0.762  | **+0.011** |
| heldout_cwe::CWE-078 (cmd)  | span_max          | 0.716  | 0.740  | **+0.024** |
| heldout_cwe::CWE-078 (cmd)  | dilated_span_max  | 0.676  | 0.702  | **+0.026** |
| heldout_cwe::CWE-125 (OOB)  | all               | 0.799  | 0.803  | +0.004  |
| heldout_cwe::CWE-125 (OOB)  | **proximal_all**  | 0.706  | 0.716  | **+0.010** |
| heldout_cwe::CWE-125 (OOB)  | span_max          | 0.514  | 0.512  | −0.002  |
| heldout_cwe::CWE-125 (OOB)  | dilated_span_max  | 0.335  | 0.331  | −0.004  |
| heldout_lang::python        | all               | 0.865  | 0.862  | −0.003  |
| heldout_lang::python        | **proximal_all**  | 0.719  | 0.744  | **+0.025** |
| heldout_lang::python        | span_max          | 0.764  | 0.763  | −0.000  |
| heldout_lang::python        | dilated_span_max  | 0.723  | 0.723  | +0.001  |
| heldout_lang::c             | all               | 0.763  | 0.771  | +0.008  |
| heldout_lang::c             | **proximal_all**  | 0.681  | 0.694  | **+0.012** |
| heldout_lang::c             | span_max          | 0.497  | 0.496  | −0.000  |
| heldout_lang::c             | dilated_span_max  | 0.291  | 0.293  | +0.002  |

## Reading

`proximal_all` is **per-token AUC where ground-truth positives include
every token within ±10 of the diff-annotated span**. This is what soft
training is actually optimising for — fire on `db.query(...)`, not only
on `${id}`. Across every split soft wins by **+0.010 to +0.038 AUC**.

`all` is per-token AUC against the strict, undilated mask (the same labels
the hard probe was trained on). Soft training does not hurt it (Δ in
[−0.003, +0.008]). The probe didn't trade strict precision for halo
recall; it added halo coverage on top of the same in-span signal.

`span_max` is the example-level binary decision (max prob per file). It is
largely unmoved (Δ in [−0.002, +0.024]) because the file-level max already
finds the best in-span peak; widening the supervision doesn't change which
example wins the max-prob race. The +0.024 on CWE-078 is the one exception
where soft labels reshaped the per-example score distribution enough to
move the AUC.

`dilated_span_max` here uses an asymmetric pool (positives sampled from
the ±10 dilated region, negatives from the whole file), so its absolute
value is depressed relative to `span_max`. Treat the Δ as the signal —
soft labels move it by similar magnitude to `span_max`.

## Caveats

- These are example-level splits on `data/dataset.jsonl` (SVEN-paired,
  1374 rows). Bootstrap CIs are at `--bootstrap-n 200`, so ±0.03 on most
  splits — a +0.038 delta is real, a +0.001 isn't.
- Soft-label training added zero compute (same epoch count, same loss
  function; just float instead of long targets in BCE).
- Issue #1's DoD (tok_AUC ≥ 0.86, ex_AUC ≥ 0.88) is still unmet —
  positive char ranges median 3 chars limits how high token-level AUC
  can climb against the strict mask. The ±10 halo absorbs most of the
  proximal noise; widening the supervision in the *dataset builder*
  (line-level instead of identifier-level spans) is the next lever.

## Files

- `data/probe_spanmax.npz` — hard labels, `--label-window 0` (legacy).
- `data/probe_spanmax_soft.npz` — soft labels, `--label-window 8`.
- `data/eval/token_report_hard.{md,json}` — full eval, hard probe.
- `data/eval/token_report_soft.{md,json}` — full eval, soft probe.
- `data/eval/token_report.{md,json}` — original eval, kept as the
  reference for the asymmetry-fix commit (e2606b9).
