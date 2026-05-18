# GemmaForge

**Real-time vulnerability detection inside Gemma 4 — see when AI is about to write insecure code, before it does.**

A linear probe on Gemma 4's hidden states detects vulnerable code patterns token-by-token, mid-generation. No external scanner. No after-the-fact lint. The signal comes from *inside* the model, as the first risky token is forming.

## Headline numbers

- **AUC 0.907 cross-language (Python → JavaScript)** — the honest OOD headline. Train on Python, eval on JavaScript with a disjoint CWE basket (`data/eval/report.md`).
- **AUC 0.940 Py → JS with MLP × ensemble stacked** (`data/probe_mlp_ensemble_xlang.json`) — closes ~80% of the gap to in-distribution; in-distribution stack saturates at 0.976.
- **22× T3 adversarial robustness via max-pool aggregation** — comment+reindent drops last-token AUC by 0.087; max-pool absorbs the same attack at Δ = −0.004 (`data/adversarial_full_suite.json`).
- **LoRA vuln-pattern emission: base = 3 hits → LoRA = 0** on the 5-prompt demo eval, after 30 SFT steps in 39s on MPS (`data/lora_eval.json`).
- Per-CWE multi-head probe: **macro AUC 0.9726**, top-1 routing 94.7% across CWE-78/338/95/94/328.
- In-distribution baseline AUC 0.963, group-by-repo AUC 0.958, held-out CWE 0.92–0.96. <1 ms per-token overhead on M1/M2/M3.

Full audit trail: [`RESULTS.md`](RESULTS.md). Submission write-up: [`WRITEUP.md`](WRITEUP.md).

![AUC ladder — every credible OOD split, plus the stacked headline](web/auc-ladder.png)

## What it looks like

![GemmaForge streaming UI — token-level risk overlay](web/screenshot-demo.png)

The probe rides every token Gemma 4 emits. Green (<0.4), yellow (0.4–0.7), red (>0.7). The red cluster in the screenshot — `db.query(\`SELECT * FROM users WHERE id = ${id}\`)` — is a CWE-89 SQL-injection pattern, flagged token-by-token while Gemma 4 is still writing it.

**Live demo:** [`peaktwilight/gemma4ge`](https://huggingface.co/spaces/peaktwilight/gemma4ge) (HuggingFace Space, ZeroGPU).

## The story

In 2026 every IDE has an AI in it. Most of the code those AIs generate ships. Almost none of it is checked for security before it does. Existing tools (Snyk, Semgrep, CodeQL) run *after* the code is written. By then the model has already shown the developer something insecure and most will copy it. The damage is done.

GemmaForge asks a different question: **what if the model itself could tell you, mid-generation, that the next 50 tokens it's about to emit look exactly like the kind of code a CVE gets filed against?**

Recent research [(Obeso, Arditi et al., 2025)](https://arxiv.org/abs/2509.03531) shows linear probes on hidden states can detect hallucinated entities in real time, AUC > 0.9, at near-zero inference cost. We adapt the same technique to a different signal — **vulnerability likelihood** — using Gemma 4 as the target model and a labeled dataset built from real CVE disclosures, including [CVE-2026-33896](https://github.com/digitalbazaar/forge/security/advisories) (`node-forge`, 33M weekly downloads), which the author of this project disclosed in March 2026.

## Two probe paths

Every number above is from the **sample-level** path — one label per snippet, linear probe on the last-token hidden state (`src/extract_activations.py` + `src/train_probe.py`). That is what ships in the demo today.

In parallel we are training a **token-level** path — per-token spans (`evidence` / `sink` / `source` / `sanitizer`), value head on every position, BCE + span-max loss à la Obeso §3 — via `notebooks/colab_train_gemma4_probe.py` and `scripts/train_value_head.py`. Current token-level numbers on SVEN-diff at layer 8: **token AUC 0.768 / example AUC 0.700** (`data/probe_spanmax_card.json`). The token-level path is the principled streaming version; the intent is for it to *replace* sample-level once the head-to-head eval lands.

## Results at a glance

| Eval split | AUC | Source |
|---|---:|---|
| Random stratified (in-dist) | 0.963 | `data/probe_card.json` |
| Group-by-repo (honest) | 0.958 | `data/eval/report.md` |
| Held-out CWE (5-class range) | 0.92–0.96 | `data/probe_strict.json` |
| **Cross-language Py → JS (OOD headline)** | **0.907** | `data/eval/report.md` |
| 4-layer ensemble (random) | 0.976 | `data/probe_ensemble.json` |
| MLP head (Py → JS) | 0.919 | `data/probe_mlp_ablation.json` |
| **MLP × ensemble (Py → JS, stacked)** | **0.940** | `data/probe_mlp_ensemble_xlang.json` |
| Per-CWE multi-head (macro, top-1 routing 94.7%) | 0.9726 | `data/probe_per_cwe_card.json` |
| T3 comment+reindent, last-token aggregation | Δ −0.087 | `data/adversarial_full_suite.json` |
| **T3 comment+reindent, max-pool aggregation** | **Δ −0.004** | `data/adversarial_full_suite.json` |
| Length-only baseline (length-matched eval) | 0.514 | `data/eval_length_matched.json` |
| Probe on the same length-matched eval | 0.843 | `data/eval_length_matched.json` |

## Why this is novel

- **Domain transfer of streaming probes from hallucination → security.** Vulnerability likelihood is fuzzier than entity hallucination; a single linear probe still works at AUC 0.907 cross-language on a 2B model with no LoRA, ~1k pairs.
- **Author-grounded training data.** Pairs include CVEs Doruk personally disclosed — `node-forge` (CVE-2026-33896, 33M weekly downloads) + 10+ more in 200M+ DL/mo packages.
- **Runs locally, no network.** A maintainer in a country with no Snyk budget gets the same vulnerability-aware completion as someone on a $200/seat enterprise plan.
- **Honest OOD reporting.** We lead with the cross-language number, not the in-distribution one, because Python→JavaScript brings a near-disjoint CWE basket and tests language-portability of the underlying representation.

## Limitations (honest)

- **Length artefact (refuted, worth disclosing).** On the unmatched dataset, a length-only baseline gets AUC 0.883 on Py→JS (vs probe 0.907) — a real concern. On a length-matched eval (`data/eval_length_matched.json`, 230 pairs balanced to ±3 chars per class), the length baseline collapses to **0.514** while the probe still hits **0.843**. The probe-minus-length delta widens from +0.024 to **+0.329**.
- **Probes classify representation, not ground truth.** A high score means *"looks like code I was trained on as vulnerable,"* not *"is exploitable."*
- **Train-inference distribution gap.** Probe trained on last-token of complete snippets; inference reads intermediate positions. Mitigated with 8-token mean; proper fix is the token-level value head (above).
- **Surface-form sensitivity.** Identifier renames + SQL case shift mean |Δ| ≤ 0.007 (refutes "probe detects API names"). Only **T3 (comment+reindent)** dominates at Δ −0.089 under last-token. Max-pool flattens all 5 transforms to |Δ| ≤ 0.005 — 22× T3 robustness for −0.031 clean AUC. Streaming UI ships max-pool; offline eval reports last-token. See `data/adversarial_full_suite.json`.
- **Coverage.** Python/JS well-covered; C/C++ activations not yet extracted; Rust/Go/Ruby/PHP not in the dataset yet (tracked in [docs/coverage.md](docs/coverage.md)).
- **Regex still wins on CWE-328.** Static patterns hit AUC 0.991 on weak-hash; probe at 0.944. Honest: a probe is not always better.

## Dataset composition

| File | Rows | Pos/Neg | Languages | Source |
|---|---:|---|---|---|
| `data/pairs_v2.jsonl` (canonical training set) | 1,198 | 599 / 599 | python (700), javascript (498) | CyberSecEval position-paired |
| `data/pairs_sven.jsonl` | 1,560 | 780 / 780 | python (730), c (720), cpp (110) | SVEN-before / SVEN-before-leadup |
| `data/pairs_merged.jsonl` | 2,758 | 1,379 / 1,379 | python (1,430), c (720), javascript (498), cpp (110) | union of v2 + sven |
| `data/dataset.jsonl` (Colab token-level path) | 1,374 | 687 / 687 | python (760), c (538), cpp (76) | SVEN-before / SVEN-after |
| `data/pairs_rich.jsonl` | 100 | token labels | python (58), javascript (42) | derived for token-level probe |

CWE coverage in `pairs_v2.jsonl`: CWE-22/78/79/89/94/95/185/208/312/319/328/338/345/502/770/798/908/1333 (Python-heavy on CWE-78/94/89/328/502; JS-heavy on CWE-95/345/208/22/185). Only CWE-338 is meaningfully bilingual — this is *why* the Py→JS number is non-trivial, the held-out language brings a near-disjoint CWE basket with it.

![Five-prompt demo grid — base vs LoRA, with token-level risk overlay](web/demo-grid.png)

## Architecture

Two laptop processes, no network:

1. **Gemma 4** unmodified — Ollama for chat/tool-calling (`gemma4:8b`), HuggingFace `transformers` + MPS for the activation hook that gives the probe access to the layer-17 hidden state.
2. **The probe** — `LogisticRegression(w ∈ ℝ¹⁵³⁶, b, layer)` loaded from `data/probe.npz`. Per generated token: read last-token hidden state, compute `σ(w·h + b)`, emit `(token, risk)` over Server-Sent Events.

A single-file HTML page (`web/index.html`, vanilla JS + SSE, no build step) consumes the SSE feed and colours each token. The same SSE feed powers the HuggingFace Space deployment in `hfspace/app.py` (Gradio + ZeroGPU).

## Technical brief

- **Model:** `gemma4:8b` E2B-it (8B params, 1536-dim hidden states, 131k context, native function-calling).
- **Probe:** 1,536-input linear classifier on the layer-17 (of 35) hidden state. Shipped weights at `data/probe.npz`, ~10 KB.
- **Training data:** 1,198 CyberSecEval position-paired rows + 1,560 SVEN char-level rows → 2,758 merged. Covers Python, JS, C, C++ across CWE-22/78/79/89/94/95/295/327/328/330/338/352/502/798/918/1333. ~55 natural-language negatives so the probe doesn't fire on chat preamble.
- **Inference:** read last-token hidden state per generated token, compute `σ(w·h + b)`, emit `(token, risk)`. < 1 ms overhead on Apple Silicon.
- **Architecture:** Two laptop processes, no network. Gemma 4 runs unmodified (Ollama for chat/tool-calling, HF `transformers` + MPS for the activation hook). The probe streams over Server-Sent Events to `web/index.html`.

## Tracks targeted

- **Main Track** — Best overall: a novel safety mechanism applied to the headline model of the hackathon.
- **Impact / Safety & Trust** — The probe peers *inside* the model — the most literal interpretation of explainability we could think of.
- **Special Tech / Ollama** — Local-only, no cloud. Model runs on Ollama. Probe runs on the developer's laptop. Zero data leaves the device.

## Team

**Doruk Tan Ozturk** — [@peaktwilight](https://github.com/peaktwilight) · [doruk.ch](https://doruk.ch) · security researcher, ex-ETH Zürich, building [0sec.ai](https://0sec.ai). **10+ CVE-grade vulnerabilities discovered in npm packages with 200M+ combined monthly downloads**, including CVE-2026-33896 in `node-forge`. The vulnerable functions from those disclosures are part of this probe's training set.

**Mehmet Efe Akça** — MSc Data Science @ **ETH Zürich** · TA for *Mathematics of Signals, Networks, and Learning*. Coursework: *Reliable and Trustworthy AI: interpretability & verifiability*, *Probabilistic AI*, *Large-Scale AI*. Brings the interpretability-research side of the project — the linear-probe technique adopted here sits directly in his area of study.

A security researcher who knows what danger looks like in source code + an interpretability researcher who knows how to read what neural networks are thinking. The whole point of GemmaForge is that those two skills only become useful when you put them together.

## How to run the demo

```bash
git clone https://github.com/peaktwilight/gemmaforge && cd gemmaforge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.stream_with_probe --serve     # loads shipped data/probe.npz
# open http://localhost:8787/
```

Or just visit the hosted Space: [`peaktwilight/gemma4ge`](https://huggingface.co/spaces/peaktwilight/gemma4ge).

## Pipeline: GemmaForge → pwnkit (small Gemma finds, big Gemma hunts)

The probe doesn't have to stop at "this looks risky" — it can hand findings to an agentic hunter that actually exploits them. Today GemmaForge ships a first-party integration with [pwnkit](https://github.com/0sec-labs/pwnkit), an open-source agentic-AI pentest framework:

```bash
# 1. scan a repo with the probe → ND-JSON leads (gemmaforge.leads/v1)
python -m src.scan examples/vuln-express-app --top-k 10 > /tmp/leads.jsonl

# 2. hand the leads to pwnkit; agent loop runs on local Gemma 4 27B via Ollama
pwnkit-cli review examples/vuln-express-app \
    --seed-findings /tmp/leads.jsonl \
    --runtime ollama \
    --model gemma4:latest
```

Same Gemma family, two roles: small 8B probe finds, big 27B agent hunts. Zero cloud spend, zero data leaving the laptop. Schema contracts at [`docs/leads-schema.md`](docs/leads-schema.md) and [`docs/events.md`](docs/events.md). Pre-computed [`examples/leads.jsonl`](examples/leads.jsonl) is shipped so judges without local Gemma weights can run step 2 alone. The pwnkit side landed in [PR #371](https://github.com/0sec-labs/pwnkit/pull/371) and [PR #372](https://github.com/0sec-labs/pwnkit/pull/372).

## How to reproduce the headline numbers

```bash
# 0. one-time: build the merged CyberSecEval + SVEN dataset
python scripts/build_dataset.py            # writes data/pairs_v2.jsonl
# 1. cache Gemma 4 hidden states (layers 8/17/26/34), ~10 min M1 Max / ~5 min 3090
python -m src.extract_activations
# 2. AUC 0.907 cross-language, 0.963 in-distribution (~90s, writes data/probe.npz)
python -m src.train_probe
# 3. AUC 0.940 stacked headline — MLP × per-layer ensemble, Py→JS
python scripts/eval_mlp_ensemble.py        # data/probe_mlp_ensemble_xlang.json
# 4. 22× T3 robustness via max-pool aggregation
python scripts/eval_maxpool_full.py        # data/eval_maxpool_full.json
python scripts/adversarial_full_suite.py   # data/adversarial_full_suite.json
# 5. LoRA base=3 → LoRA=0 vuln-pattern delta
python scripts/train_lora.py && python scripts/eval_lora.py   # data/lora_eval.json
```

Every number in [`RESULTS.md`](RESULTS.md) is regenerated from these scripts; floating-point drift in the 4th decimal is expected.

## Colab training

To train and publish the probe from a fresh GPU Colab runtime, open
[`notebooks/colab_train_gemma4_probe.ipynb`](notebooks/colab_train_gemma4_probe.ipynb).
The notebook clones this repo, installs the Hugging Face stack, builds the dataset,
trains/evaluates a frozen-model token-level value head on a Gemma 4 decoder layer,
and uploads the resulting bundle to Hugging Face Hub.

Before running it, add a Colab Secret named `HF_TOKEN` or `HF_WRITE_TOKEN` with write
access to the destination model repo, then update `HF_REPO_ID` in the first settings
cell. `GITHUB_TOKEN` is optional (only needed for private `REPO_URL` values).

The notebook supports the rebuilt SVEN before/after dataset format from
`scripts/build_dataset.py`. Leave `DATASET_PATH = None` to build `data/dataset.jsonl`,
or point it at an existing JSONL file with rows like:

```json
{"code": "db.query(`SELECT * FROM users WHERE id=${id}`)", "label": 1, "token_labels": {"sink": [[0, 8]], "source": [[38, 40]], "sanitizer": [], "evidence": [[0, 40]], "vulnerable_line": [[0, 40]]}}
```

Rows with `token_labels` train on the annotated token activations. Positive ranges
come from `evidence`, `vulnerable_line`, `sink`, and `source`; `sanitizer` ranges are
treated as negative. Safe after-patch rows from the rebuilt builder have empty
`token_labels` and train as negative examples.

The streaming web UI uses the Server-Sent-Events feed at `/stream?prompt=…`. The CLI mode (`--prompt "…"`) renders the same risk-coloured stream in your terminal with ANSI colour codes.

## What's where

| Path | What lives here |
|---|---|
| `src/` | Probe core: activation extraction, train (`train_probe.py`, `train_probe_spanmax.py`), streaming inference + SSE server (`stream_with_probe.py`), calibration, attention-probe variant. |
| `data/` | Datasets (`pairs_v2.jsonl`, `pairs_sven.jsonl`, `dataset.jsonl`), cached activations (`activations_v2/`), shipped probe weights (`probe.npz`), every eval JSON cited in `RESULTS.md`. |
| `scripts/` | Pipeline runners: `build_dataset.py`, `eval_*.py` (maxpool, per-CWE, ensemble, MLP-ensemble, length-matched, LoRA), `train_lora.py`, `train_value_head.py`, `adversarial_full_suite.py`, `make_demo_grid.py`, `record_demo.py`, `deploy_hf.sh`. |
| `notebooks/` | Colab/Kaggle training (`colab_train_gemma4_probe.ipynb` + `.py`, `colab_train_lora_dpo.py`, `kaggle_train_lora_dpo.py`) and eval companions (`eval_token_probe.ipynb`, `eval_baselines.ipynb`, `eval_calibration.ipynb`, `eval_probe_report.ipynb`). |
| `docs/` | `coverage.md` (per-language probe coverage), `attention_probe_notes.md`, `findings_writeup_snippet.md`. |
| `web/` | Single-file streaming UI (`index.html`, vanilla JS + SSE), cover art (`cover.svg`), demo screenshots (`screenshot-demo.png`, `demo-grid.png`), result charts (`auc-ladder.png`, `data-efficiency-curve.png`). |
| `hfspace/` | HuggingFace Space deployment (Gradio + ZeroGPU `app.py`, requirements, space metadata). |

Top-level docs: [`WRITEUP.md`](WRITEUP.md) (Kaggle submission, ~1400 words), [`RESULTS.md`](RESULTS.md) (full metrics dashboard), [`SUBMISSION.md`](SUBMISSION.md) (submission checklist), [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md) (2:50 demo script), [`LINKEDIN.md`](LINKEDIN.md) (launch post).

## Data efficiency

How does AUC scale with training size? Subsample to {5, 10, 20, 30, 50, 75, 100}% × 5 seeds, fit `LogisticRegression(C=1.0)`, eval on the fixed 240-example held-out (`data/data_efficiency.json`):

- Random AUC crosses 0.9 at ~10–20% of the dataset (n ≈ 100–200).
- Cross-language (Py→JS) AUC peaks at **0.912 at n=525** and ticks back down to 0.907 at full → **the curve flattens**, so more Python data alone probably won't close the gap to in-distribution. The remaining 0.04 lives in the representation, not the training-set size. This is what motivates the token-level path.

See `web/data-efficiency-curve.png` (rendered by `scripts/plot_data_efficiency.py`).

## Evaluation methodology

Every credible OOD axis is reported. Splits are constructed by `scripts/eval_splits.py` and stored at `data/eval/report.md`:

- **`random_stratified`** — 80/20 stratified on label. Leaky because positive/negative halves of a pair share `_origin_repo`; reported as the in-distribution ceiling, not the headline.
- **`group_repo`** — `GroupShuffleSplit` on `_origin_repo`. The same repository never appears in both train and test. Gap to random is **only 0.005 AUC** → leakage was real but small.
- **`heldout_cwe::CWE-N`** — train on all CWEs except N, test only on N (with positives *and* negatives for that CWE both moving to the test side). Tests "can the probe recognise a vulnerability class it has never seen?"
- **`heldout_lang::test=javascript`** — train on the full Python subset, test on the full JavaScript subset. Languages are disjoint by construction; this is the headline OOD number (0.907).
- **`heldout_lang::test=python`** — symmetric reverse split (0.929).

Confidence intervals are 95% bootstrap on the per-test predictions. R@5%FPR / R@10%FPR / Brier / ECE all reported in `data/eval/report.md` for every split.

## Per-CWE breakdown

Five logits on layer 17, one-vs-rest, same dataset (`data/probe_per_cwe_card.json`). Top-1 routing accuracy across the five heads is **94.7%** — when the binary probe says "vulnerable," the right per-CWE head is the strongest one ~95 times out of 100.

| CWE | AUC | ACC | n_pos |
|---|---:|---:|---:|
| CWE-78 (OS command injection) | 0.979 | 0.949 | 82 |
| CWE-338 (weak PRNG) | 0.990 | 0.971 | 79 |
| CWE-95 (eval injection) | 0.926 | 0.919 | 78 |
| CWE-94 (code injection) | 0.988 | 0.962 | 65 |
| CWE-328 (weak hash) | 0.981 | 0.947 | 55 |
| **Macro** | **0.9726** | — | — |

Even when the binary probe has never seen *any* example of the held-out CWE class, it still scores 0.92+ AUC on it across the five most-represented CWEs — the strongest evidence we have that the signal is "vulnerable-shaped representation" rather than memorised lexical surface.

## Why Gemma 4 specifically

GemmaForge can't be built on a closed model:

- **Raw hidden states** — GPT-5 / Claude don't expose them; the probe needs `output_hidden_states=True`.
- **Native function calling + 131k context** — one Gemma instance can drive both the probe and a normal IDE assistant flow.
- **Apache-2.0-equivalent license** — no legal review for any maintainer who wants to embed this.
- **Laptop-sized** — E2B does >20 tok/s on Apple Silicon, which is what makes "in-IDE token-level overlay" actually feasible.

## What we'd build next

Tracked as 13 open GitHub issues. Highlights:

- **Token-level probe → head-to-head vs sample-level.** Both trainers are live (`notebooks/colab_train_gemma4_probe.py`, `scripts/train_value_head.py`) against `data/dataset.jsonl` with per-token spans. The eval decides whether token-level replaces the shipped sample-level probe.
- **Full DPO LoRA on dedicated GPU.** `scripts/train_lora.py` already supports `--max_steps 500`; we need a clean CUDA box. Stretch goal: re-train the probe *jointly* with the LoRA, the way Obeso §3 does — probe gradient gets a stop-grad on the base, the LoRA gradient flows.
- **More languages.** Rust + Go via CyberSecEval-2; Ruby via RubySec advisory DB; PHP via SARD/Juliet. The activation-extraction pipeline is the bottleneck, not the probe.
- **VS Code extension** that reads the same SSE stream.

## Citations

- Obeso, Arditi et al. (2025). *Real-time hallucination detection with linear probes on hidden states.* [arXiv:2509.03531](https://arxiv.org/abs/2509.03531).
- Bailey et al. (ICLR 2026). *Surface-form robustness of activation probes.* [arXiv:2412.09565](https://arxiv.org/abs/2412.09565).
- *RL-Obfuscation* (2025). [arXiv:2506.14261](https://arxiv.org/abs/2506.14261).
- CyberSecEval-2 (Meta AI, 2024); SVEN (He & Vechev, 2023); CWE Top-25 (MITRE).

## License & ethics

Apache-2.0. Training data is derived from publicly disclosed CVEs and the published CyberSecEval / SVEN benchmarks; no private vulnerability information was used.
