### Max-pool aggregation (RL-Obfuscation, 2025)

Cohen et al. ([arXiv 2506.14261](https://arxiv.org/abs/2506.14261), §4) report
that taking the **max** of the probe score across every token position of a
snippet stays robust under adversarial finetuning where last-token, mean, and
median pooling all collapse. The probe weights are unchanged — this is purely
an inference-time aggregation change. We replayed the held-out 20% split
(`random_state=7`) through Gemma 4 E2B and computed both aggregations on a
60-example stratified subset.

| pooling                    | n   | AUC   |
|----------------------------|-----|-------|
| last-token (full held-out) | 240 | 0.963 |
| last-token (subset)        | 60  | 0.974 |
| max-pool   (subset)        | 60  | 0.972 |

On clean in-distribution data max-pool is a wash (Δ −0.002 on the matched 60
examples). The paper's claim is about adversarial-finetuning robustness, not
clean-data gains, so this is consistent — but absent an actual adversarially-
finetuned Gemma the only positive evidence here is indirect (see next section).

### Adversarial probe robustness

Following Bailey et al. ([arXiv 2412.09565](https://arxiv.org/abs/2412.09565),
ICLR 2026) and the SLODA benchmark (Risse & Böhme, FSE 2025), we sampled 20
held-out positives and applied two semantic-preserving transforms: **T1**
identifier renames (`db.query`→`database.execute`, `cursor.execute`→`db.run`,
`req.params.id`→`userId`, …), and **T3** a benign comment + +2-space reindent.

| condition  | mean score (last-token) | flip-rate (<0.5) |
|------------|-------------------------|------------------|
| baseline   | 0.966                   | —                |
| T1 rename  | 0.964 (Δ −0.002)        | 0.00             |
| T3 comment | 0.879 (Δ −0.087)        | 0.05             |

T1 only matched 1/20 sampled positives (the held-out positives are
predominantly CWE-95 / CWE-338 / CWE-798, not CWE-89 SQLi), but on that one
example the last-token score dropped 0.071 — suggestive but not conclusive.
T3 produced a clean **8.7-point** mean drop from comment + indent alone, so
the probe is partially keying on superficial formatting rather than taint
flow. Both effects largely vanish under max-pool (T3 Δ −0.004), which is the
strongest argument we have for shipping the max-pool wrapper. We add this
limitation to the writeup's Limitations section.
