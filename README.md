# GemmaForge

**Two Gemmas, one laptop — local repo-wide vulnerability auditing.**

GemmaForge is a two-tier, fully-local pipeline built on the Gemma 4 family.

**Tier 1 — activation-probe scan.** A linear probe over Gemma 4's hidden state sweeps a whole repo and emits ranked leads. Two variants under one scoring contract:
- **`weak-probe`** — Gemma 4 E2B backbone, bounded line/token windows, high recall, **laptop-class**. Default; what the metrics below validate.
- **`strong-probe`** — larger Gemma checkpoint as the probe backbone, larger windows, more repo context, better ranking. **Workstation-class.** Same `gemmaforge.leads/v1` schema.

**Tier 2 — pwnkit verifier.** Gemma 4 27B via Ollama drives a tool-using agent ([`pwnkit review --seed-findings --runtime ollama`](https://github.com/0sec-labs/pwnkit/pull/371)) that reads files, greps call sites, and produces audit verdicts a developer can cross-reference against the leads. Consumes leads from either probe.

Nothing leaves the laptop. The probe is what the metrics below validate. The agent verifier is shipped end-to-end at the CLI + runtime + dashboard layer in [`0sec-labs/pwnkit#371`](https://github.com/0sec-labs/pwnkit/pull/371) (merged 2026-05-18); promoting the seed findings to the agent's primary worklist is the named follow-up issue [`pwnkit#368`](https://github.com/0sec-labs/pwnkit/issues/368).

## Headline numbers

- **AUC 0.907 cross-language (Python → JavaScript)** — the honest OOD headline. Train on Python, eval on JavaScript with a disjoint CWE basket (`data/eval/report.md`).
- **AUC 0.940 Py → JS with MLP × ensemble stacked** (`data/probe_mlp_ensemble_xlang.json`) — closes ~80% of the gap to in-distribution; in-distribution stack saturates at 0.976.
- **22× T3 adversarial robustness via max-pool aggregation** — comment+reindent drops last-token AUC by 0.087; max-pool absorbs the same attack at Δ = −0.004 (`data/adversarial_full_suite.json`).
- **LoRA vuln-pattern emission: base = 3 hits → LoRA = 0** on the 5-prompt demo eval, after 30 SFT steps in 39s on MPS (`data/lora_eval.json`).
- Per-CWE multi-head probe: **macro AUC 0.9726** across CWE-78/338/95/94/328 (`data/probe_per_cwe_card.json`).
- In-distribution baseline AUC 0.963, group-by-repo AUC 0.958, held-out CWE 0.92–0.96. <1 ms per-token overhead on M1/M2/M3.

Full audit trail: [`RESULTS.md`](RESULTS.md). Submission write-up: [`WRITEUP.md`](WRITEUP.md).

![AUC ladder — every credible OOD split, plus the stacked headline](web/auc-ladder.png)

## What it looks like

![GemmaForge streaming UI — token-level risk overlay](web/screenshot-demo.png)

Two demo flows:

1. **IDE-mode (Tier 1 only)** — the probe rides every token Gemma 4 emits. Green (<0.4), yellow (0.4–0.7), red (>0.7). The red cluster above — `db.query(\`SELECT * FROM users WHERE id = ${id}\`)` — is a CWE-89 SQL-injection pattern. This is the streaming UI in `src/stream_with_probe.py` and the HuggingFace Space below.
2. **Repo-audit mode (Tier 1 → leads → Tier 2)** — `python -m src.scan ./repo --events live.ndjson > leads.jsonl` walks the codebase, emits ranked `gemmaforge.leads/v1` JSONL, streams `gemmaforge.events/v1` to the [pwnkit `/live` dashboard](https://github.com/0sec-labs/pwnkit/pull/371) (Lane 1 · Probe, Lane 2 · Leads), then hands the leads to `pwnkit review --seed-findings ... --runtime ollama` for Gemma 4 27B agentic verification.

**Live HF Space:** [`peaktwilight/gemma4ge`](https://huggingface.co/spaces/peaktwilight/gemma4ge) (HuggingFace Space, ZeroGPU).

## The story

In 2026 every IDE has an AI in it. Most of the code those AIs generate ships. Almost none of it is audited for security before it does. Existing SAST tools (Snyk, Semgrep, CodeQL) run *after* the code is written — and they require shipping the code somewhere. Solo maintainers, air-gapped enterprises, and developers in regions where a Snyk seat costs more than a month's rent are excluded.

GemmaForge asks a sharper question: **what if a small model could read your whole repo on your laptop and rank where it smells like a CVE, and a bigger version of the same model could read those spans and confirm — without anything leaving the device?**

Tier 1 is inspired by [Obeso, Arditi et al. (2025)](https://arxiv.org/abs/2509.03531), which showed linear probes on hidden states detect hallucinated entities at AUC > 0.9. We adapt the same technique to vulnerability likelihood on Gemma 4 E2B, trained on a labeled dataset of paired vulnerable/safe code drawn from public CVE disclosures, including [CVE-2026-33896](https://github.com/digitalbazaar/forge/security/advisories) in `node-forge`, which Doruk disclosed in March 2026.

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
| Per-CWE multi-head (macro) | 0.9726 | `data/probe_per_cwe_card.json` |
| T3 comment+reindent, last-token aggregation | Δ −0.087 | `data/adversarial_full_suite.json` |
| **T3 comment+reindent, max-pool aggregation** | **Δ −0.004** | `data/adversarial_full_suite.json` |
| Length-only baseline (length-matched eval) | 0.514 | `data/eval_length_matched.json` |
| Probe on the same length-matched eval | 0.843 | `data/eval_length_matched.json` |

## Why this is novel

- **A model-size family as the architecture.** `weak-probe` (Gemma 4 E2B) does cheap whole-repo triage on a laptop; `strong-probe` (larger Gemma checkpoint) does the same with bigger windows and richer context on a workstation; the `pwnkit verifier` (Gemma 4 27B via Ollama) does deep agentic auditing with tool use. Same model family, same tokenizer, same function-calling protocol, same license, same lead schema flowing between stages — that combination doesn't exist outside Gemma 4.
- **Domain transfer of streaming probes from hallucination → security.** Vulnerability likelihood is fuzzier than entity hallucination; a single linear probe still hits AUC 0.907 cross-language on a 2B model with no LoRA, ~1k pairs.
- **Author-informed training data.** Doruk's CVE-finding work — including the `node-forge` patch (CVE-2026-33896) — informed which CWE classes the dataset emphasises and how the probe was evaluated. Canonical training metrics are on CyberSecEval `pairs_v2` (`data/pairs_v2.jsonl`); Doruk's embargoed disclosures are deliberately excluded.
- **Runs locally, no network.** The probe path runs on laptop-class hardware. The 27B verifier needs a 24GB-class GPU or 32GB-class M-series Mac — the same tier that runs Stable Diffusion. Anyone Snyk-priced-out gets the same audit capability as a Fortune 500.
- **Honest OOD reporting.** We lead with the cross-language number, not the in-distribution one, because Python→JavaScript brings a near-disjoint CWE basket and tests language-portability of the underlying representation.

## Limitations (honest)

- **Length artefact (refuted, worth disclosing).** On the unmatched dataset, a length-only baseline gets AUC 0.883 on Py→JS (vs probe 0.907) — a real concern. On a length-matched eval (`data/eval_length_matched.json`, 230 pairs balanced to ±3 chars per class), the length baseline collapses to **0.514** while the probe still hits **0.843**. The probe-minus-length delta widens from +0.024 to **+0.329**.
- **Probes classify representation, not ground truth.** A high score means *"looks like code I was trained on as vulnerable,"* not *"is exploitable."*
- **Train-inference distribution gap.** Probe trained on last-token of complete snippets; inference reads intermediate positions. Mitigated with 8-token mean; proper fix is the token-level value head (above).
- **Surface-form sensitivity.** Identifier renames + SQL case shift mean |Δ| ≤ 0.007 (refutes "probe detects API names"). Only **T3 (comment+reindent)** dominates at Δ −0.089 under last-token. Max-pool flattens all 5 transforms to |Δ| ≤ 0.005 — 22× T3 robustness for −0.031 clean AUC. Streaming UI ships max-pool; offline eval reports last-token. See `data/adversarial_full_suite.json`.
- **Coverage.** Python/JS well-covered; C/C++ activations not yet extracted; Rust/Go/Ruby/PHP not in the dataset yet (tracked in [docs/coverage.md](docs/coverage.md)).
- **Regex still wins on CWE-328.** Static patterns hit AUC 0.991 on weak-hash; probe at 0.944 (`data/eval/sample_report.json` → CWE-328 → `baseline_aucs.regex`). Honest: a probe is not always better.

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

## Architecture — two-tier, end-to-end local

```
   ┌─────────────────────────  Tier 1 (this repo)  ──────────────────────────┐
   repo/  ──►  src/scan.py  ──►  Gemma 4 forward pass    ──►  hidden_state @ layer 17
              (line/token            ├── weak-probe: E2B (laptop)         │
               windows, lazy LM)     └── strong-probe: larger (workstation)
                                                                          ▼
                                                            σ(w·h+b) + per-CWE head
                                                                     │
                                                                     ▼
                                                 ranked leads JSONL (gemmaforge.leads/v1)
                                                 + events stream     (gemmaforge.events/v1)
                                                                     │
   ┌─────────────────────────  Tier 2 (0sec-labs/pwnkit#371)  ─────────────────┘
                                                                     │
              pwnkit `/live` dashboard ◄── SSE ──┐                    │
              (Lane 1 · Probe, Lane 2 · Leads,                         │
               Lane 3 · Hunt placeholder)                              │
                                                                     ▼
                              pwnkit review --seed-findings leads.jsonl
                                            --runtime ollama
                                                                     │
                                                                     ▼
                              Gemma 4 27B (Ollama /api/chat + tools[])
                              read_file · grep · follow-call-site
                                                                     │
                                                                     ▼
                              structured audit verdicts
                              (cross-referenced with leads today;
                               primary worklist in pwnkit#368)
```

**Tier 1 (this repo) — activation-probe scan, two variants:**

| Variant | Backbone | Window strategy | Hardware | Status |
|---|---|---|---|---|
| `weak-probe` | `google/gemma-4-E2B-it` (~2B) | bounded line/token windows, `top-k mean` aggregation | laptop-class | shipped, what the metrics validate |
| `strong-probe` | larger Gemma checkpoint (`--model-id <…>`) | larger windows, more repo context | workstation-class (24GB+ GPU or 32GB+ M-series) | supported by `src/scan.py`; probe head retrains against the larger backbone's hidden states |

- **Probe head:** linear classifier `σ(w·h + b)` with `w ∈ ℝᵈ`, `b ∈ ℝ`, trained on the chosen backbone's hidden states. `weak-probe` ships as `data/probe.npz` (`d = 1536`, layer 17, ~10 KB).
- **Per-CWE head:** 5-way one-vs-rest logits at the same layer for CWE-78/338/95/94/328 (`data/probe_per_cwe.npz`).
- **Two entry points:**
  - `python -m src.scan <repo>` — repo walk, sliding-window chunks, ranked `gemmaforge.leads/v1` JSONL on stdout, `gemmaforge.events/v1` ND-JSON to `--events <path>`. Schemas in [`docs/leads-schema.md`](docs/leads-schema.md) and [`docs/events.md`](docs/events.md).
  - `python -m src.stream_with_probe --serve` — single-snippet streaming SSE UI in `web/index.html`. Max-pool aggregation by default (T3-robust).
- **HF Space** (`hfspace/app.py`, Gradio + ZeroGPU) wraps the streaming demo.

**Tier 2 (pwnkit#371, merged 2026-05-18):**
- `--seed-findings <path|->` — parses our `gemmaforge.leads/v1` JSONL into typed `SeedFinding`s and threads them through the pipeline. Stable wire format.
- `--runtime ollama` — drives Ollama `/api/chat` with `tools[]`; defaults to `gemma4:27b`. Batched (non-streaming) tool-calling.
- `/live` dashboard — three lanes; Lanes 1+2 wired to SSE; Lane 3 (Hunt) is a UI placeholder for agent findings in this PR (live wiring is follow-up [pwnkit#370](https://github.com/0sec-labs/pwnkit/issues/370)).
- **Worklist promotion.** Today the leads are parsed, typed, and made available to the pipeline; the agent runs its own discovery pass over the same repo with its existing tool loop. Cross-referencing the agent's verdicts against `leads.jsonl` is done by the developer. Promoting the leads to the agent's primary worklist is the named follow-up issue [pwnkit#368](https://github.com/0sec-labs/pwnkit/issues/368). We do not pitch behaviour that hasn't shipped.

## Tracks targeted

- **Main Track** — A novel two-tier architecture that uses the Gemma 4 family across model sizes in a single product: `weak-probe` (E2B) on a laptop or `strong-probe` (larger Gemma) on a workstation for whole-repo triage; the `pwnkit verifier` (27B + tools) for deep agentic corroboration.
- **Impact / Safety & Trust** — Tier 1 peers literally *inside* the model (hidden-state introspection); Tier 2 produces auditable, tool-grounded verdicts a human can re-check. Both halves are explainability in two complementary senses.
- **Special Tech / Ollama** — Tier 2's agentic verifier runs on `gemma4:27b` via Ollama `/api/chat` with `tools[]`. Tier 1's probe variants both run locally. Zero data leaves the laptop.

## Team

**Doruk Tan Ozturk** — [@peaktwilight](https://github.com/peaktwilight) · [doruk.ch](https://doruk.ch) · security researcher, ex-ETH Zürich, building [0sec.ai](https://0sec.ai). Disclosed CVE-2026-33896 in `node-forge` and additional CVE-grade vulnerabilities across widely-deployed npm packages; the public patches inform our training set. **Built Tier 2** — the [`pwnkit`](https://github.com/0sec-labs/pwnkit) agentic verifier and its [GemmaForge integration PR](https://github.com/0sec-labs/pwnkit/pull/371).

**Mehmet Efe Akça** — MSc Data Science @ **ETH Zürich** · TA for *Mathematics of Signals, Networks, and Learning*. Coursework: *Reliable and Trustworthy AI: interpretability & verifiability*, *Probabilistic AI*, *Large-Scale AI*. **Built Tier 1** — the linear-probe path: dataset, activation capture, training, evaluation, the per-CWE multi-head, and the streaming/scan entry points. The interpretability technique sits directly in his area of study.

Doruk alone gives you a scanner; Efe alone gives you a probe. The whole point of GemmaForge is the two together — a probe that knows about danger, handing off to an agent that can prove it.

## How to run the demo

**Setup (one-time, both demos share it):**

```bash
git clone https://github.com/peaktwilight/gemmaforge && cd gemmaforge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Tier 1 — single-snippet streaming UI (probe only, no GPU required):**

```bash
python -m src.stream_with_probe --serve     # loads shipped data/probe.npz
# open http://localhost:8787/
```

Or visit the hosted Space: [`peaktwilight/gemma4ge`](https://huggingface.co/spaces/peaktwilight/gemma4ge).

**Tier 1 + 2 — whole-repo audit (requires Ollama with `gemma4:27b` pulled):**

```bash
# 1a. weak-probe (default) — laptop-class, shipped probe weights
python -m src.scan ./your-repo \
    --top-k 25 --languages py,js \
    --events live.ndjson > leads.jsonl

# 1b. strong-probe (workstation-class) — pass a larger Gemma backbone;
#     the probe head must be re-trained against that backbone first.
python -m src.scan ./your-repo \
    --model-id google/gemma-4-9B-it \
    --probe-path data/probe.strong.npz \
    --top-k 25 --languages py,js \
    --events live.ndjson > leads.jsonl

# 2. hand the leads to pwnkit's agentic auditor driving Gemma 4 27B locally
#    (install pwnkit from https://github.com/0sec-labs/pwnkit)
pwnkit review ./your-repo \
    --seed-findings leads.jsonl \
    --runtime ollama
```

The pwnkit `/live` dashboard (Lane 1 · Probe, Lane 2 · Leads) can be pointed at `live.ndjson` while the scan runs — see [`0sec-labs/pwnkit#371`](https://github.com/0sec-labs/pwnkit/pull/371) for the consumer side. Once [pwnkit#368](https://github.com/0sec-labs/pwnkit/issues/368) lands, the leads will be the agent's primary worklist; today the agent runs its own discovery pass and the developer cross-references its verdicts with `leads.jsonl`.

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

## Why Gemma 4 specifically — *the model-size family is the architecture*

This is the load-bearing argument. No closed model and no open non-Gemma model gives all of:

- **Raw hidden states at every layer** — required for Tier 1. GPT-5 / Claude don't expose them. Open-weight Llama / Qwen do, but only Gemma 4 gives you this *plus* the rest below.
- **A model-size family — three slots, one architecture.** `weak-probe` (E2B), `strong-probe` (larger Gemma), and the `pwnkit verifier` (27B) share the same vocabulary, the same hidden-state geometry conventions, and the same tool schema. The same `gemmaforge.leads/v1` schema flows between stages. Mixing a Llama probe with a Qwen verifier would mean two licenses, two prompt formats, and no guarantee the small model's notion of "vulnerable-looking" state maps to anything the big model's reasoning prior cares about.
- **Native function-calling + 131k context** — required for the verifier. Gemma 4 27B reads files, greps call sites, and asks follow-up questions inside a 131k-token window.
- **Apache-2.0–licensed project code; Gemma weights under the Gemma Terms of Use** (open weights, commercial use permitted). One legal review, not two.
- **Laptop-sized at the weak end, workstation-sized at the strong end.** E2B (`weak-probe`) comfortably fits on any modern MacBook; the larger checkpoints (`strong-probe`, verifier) fit on a 24GB-class GPU or a 32GB-class M-series Mac at Q4. The user picks their slot by hardware; the pipeline is the same. No cloud step is forced anywhere.

## What we'd build next

Tracked as open GitHub issues. Highlights:

- **Token-level probe head-to-head vs sample-level.** Both trainers are live (`notebooks/colab_train_gemma4_probe.py`, `scripts/train_value_head.py`) against `data/dataset.jsonl` with per-token spans. The eval decides whether token-level replaces sample-level as the production probe.
- **`strong-probe` validation run.** Train the linear head against a larger Gemma checkpoint's hidden states and publish the same metric table for it.
- **Full DPO LoRA on dedicated GPU.** `scripts/train_lora.py` already supports `--max_steps 500`; we need a clean CUDA box. Stretch goal: re-train the probe *jointly* with the LoRA, the way Obeso §3 does — probe gradient gets a stop-grad on the base, the LoRA gradient flows.
- **More languages.** Rust + Go via CyberSecEval-2; Ruby via RubySec advisory DB; PHP via SARD/Juliet. The activation-extraction pipeline is the bottleneck, not the probe.
- **VS Code extension** (scaffolded in `extensions/vscode/`) that reads the same SSE stream.

## Citations

- Obeso, Arditi et al. (2025). *Real-time hallucination detection with linear probes on hidden states.* [arXiv:2509.03531](https://arxiv.org/abs/2509.03531).
- Bailey et al. (ICLR 2026). *Surface-form robustness of activation probes.* [arXiv:2412.09565](https://arxiv.org/abs/2412.09565).
- *RL-Obfuscation* (2025). [arXiv:2506.14261](https://arxiv.org/abs/2506.14261).
- CyberSecEval-2 (Meta AI, 2024); SVEN (He & Vechev, 2023); CWE Top-25 (MITRE).

## License & ethics

- This project's code, probe weights, and training-data manifest: **Apache-2.0**, all in the repo.
- Gemma 4 model weights are used under the **Gemma Terms of Use** (open weights, commercial use permitted).
- Training data is derived from publicly disclosed CVEs and the published CyberSecEval / SVEN benchmarks; no private or embargoed vulnerability information was used.
- No user code leaves the laptop at inference time.
