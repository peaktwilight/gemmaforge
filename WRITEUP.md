# GemmaForge — Two Gemmas, One Laptop: Local Repo-Wide Vulnerability Auditing

**Tracks:** Main Track · Impact: Safety & Trust · Special Tech: Ollama

**Repo:** https://github.com/peaktwilight/gemmaforge
**Live demo:** https://huggingface.co/spaces/peaktwilight/gemma4ge
**Video:** https://youtube.com/watch?v=TODO

## Team — security meets interpretability

- [**Doruk Tan Ozturk**](https://doruk.ch) ([@peaktwilight](https://github.com/peaktwilight)) — security researcher, ex-ETH Zürich. Disclosed [CVE-2026-33896](https://github.com/digitalbazaar/forge/security/advisories) in `node-forge`, plus a number of additional CVE-grade vulnerabilities across widely-deployed npm packages. Builder of [`pwnkit`](https://github.com/0sec-labs/pwnkit) (agentic AI pentest framework) and [**0sec.ai**](https://0sec.ai). Knows what a bug looks like in source — and built the Tier-2 agent runtime this submission depends on.
- **Mehmet Efe Akça** — MSc Data Science, ETH Zürich. Coursework in *Reliable and Trustworthy AI*, *Probabilistic AI*. TA for *Mathematics of Signals, Networks, and Learning*. Built the linear-probe path: dataset, activation capture, training, evaluation. Knows how to read what a neural network is thinking.

Doruk alone gives you a scanner; Efe alone gives you a probe. Together: **a probe that knows about danger, and an agent that can prove it.**

## The pitch in one paragraph

GemmaForge is a two-tier, fully-local vulnerability auditing pipeline on the Gemma 4 family. **Tier 1** is an activation-probe scan that emits ranked JSONL leads with predicted CWE classes — `weak-probe` (Gemma 4 E2B, laptop-class, default) or `strong-probe` (larger Gemma, workstation-class, same lead schema). **Tier 2** is the pwnkit verifier — Gemma 4 8B driving a tool-using agent (`pwnkit review --seed-findings --runtime ollama`) that reads files, greps call sites, and streams tool-grounded verdicts into the dashboard's Hunt lane. **Nothing leaves the laptop.** Same model family, same tokenizer, same Apache-2.0 glue code.

## The problem

AI coding assistants ship vulnerable code at scale — SQL injection, path traversal, command injection, weak crypto, hardcoded credentials. "Scan afterwards" (Snyk, Semgrep, CodeQL) is too late (developer pasted first), cloud-bound (excludes solo maintainers, air-gapped enterprises, regulated industries), and rule-static (never tells you *the model itself* was uncertain).

**What if the model could tell you which parts of your repo look like the code that gets CVEs filed against it — and then a bigger version of the same model could read the file and confirm?** That product is GemmaForge.

## The technique

### Tier 1 — activation-probe scan (this repo)

A linear classifier on a Gemma 4 hidden state. Binary label: *"the code is the vulnerable side of a known patch pair."* Head is ~1,536 weights, sub-ms per token. Inspired by [Obeso, Arditi et al. (2025)](https://arxiv.org/abs/2509.03531) (linear probe on hidden states detects hallucinated entities at AUC > 0.9); we adapt the technique to vulnerability likelihood.

**Two probe variants, same scoring contract.** `weak-probe` (shipped, validated below): `google/gemma-4-E2B-it`, layer 17, bounded windows, top-k mean. `strong-probe` (shipped, Gemma 4 E4B, layer 10): same code, larger backbone. Head-to-head on `data/pairs.jsonl` (n=1198, 95% bootstrap CI): strong wins **group_repo 0.969 vs 0.960**, **CWE-78 0.998 vs 0.986**, **lang=python 0.998 vs 0.991**; loses CWE-95 by −0.009; deltas inside CIs — both saturate near 0.99x. **Structural finding:** best layer drops from **L17/35 (49% depth)** to **L10/42 (24% depth)** on E4B — the linear vuln direction lives earlier in the bigger model. Receipts: `data/eval/strong_vs_weak_probe.md`, `data/probe_strong.npz`. Both emit `gemmaforge.leads/v1`.

**Sample-level vs token-level.** Numbers below are from the **sample-level** path (last-token state, shipped, `src/train_probe.py`). A parallel **token-level** path (per-token spans, BCE + span-max loss à la Obeso §3) reaches **token AUC 0.768 / example AUC 0.700** at layer 8 (`data/probe_spanmax_card.json`) — candidate successor.

**Result for `weak-probe` on Gemma 4 E2B (layer 17, 1,198 CyberSecEval position-paired rows):**

| Eval split | AUC | accuracy | what it tests |
|---|---:|---:|---|
| Random stratified | 0.960 | 92.0% | in-distribution baseline |
| Group-by-repo | 0.958 | 91.6% | leakage ≤ 0.005 |
| Held-out CWE | 0.92–0.96 | 83–91% | unseen vulnerability class |
| **Cross-language (Py→JS)** | **0.907** | **81.9%** | **honest headline — train Python, evaluate JavaScript** |

Best layer: **17 of 35**. Stacked ablations: 4-layer ensemble → 0.976 random; MLP head → 0.919 cross-lang; **MLP × ensemble → 0.940 Py→JS** (+0.033).

![AUC ladder](web/auc-ladder.png)

**Per-CWE multi-head probe** — 5 one-vs-rest logits on layer 17 covering CWE-78/338/95/94/328. **Macro AUC 0.9726.** The argmax populates `gemmaforge_top_cwe` so the Tier 2 agent receives both *where* and *what kind of bug* the probe suspects.

### Tier 2 — big Gemma + agentic verifier (consumer: [`0sec-labs/pwnkit#371`](https://github.com/0sec-labs/pwnkit/pull/371), merged 2026-05-18)

Tier 1 emits a `gemmaforge.leads/v1` JSONL stream (see `docs/leads-schema.md`):

```json
{"file": "src/router.js", "start_line": 38, "end_line": 52,
 "snippet": "db.query(`SELECT * FROM u WHERE id=${id}`)",
 "gemmaforge_confidence": 0.93, "gemmaforge_top_cwe": "CWE-89",
 "gemmaforge_layer": 17, "model_id": "google/gemma-4-E2B-it", "rank": 0}
```

Doruk's pwnkit consumes this via `pwnkit review --seed-findings leads.jsonl --seed-only --runtime ollama` and runs an agentic auditor driven by Gemma 4 8B through Ollama. The runtime hits Ollama's `/api/chat` with `tools[]` and translates tool-calls into pwnkit `tool_use` blocks — native function-calling, no API key, no network. **Shipped end-to-end today (two merged PRs, 2026-05-18):** [`pwnkit#371`](https://github.com/0sec-labs/pwnkit/pull/371) adds `--seed-findings`, the `--runtime ollama` driver for Gemma 4 8B, and the `/live` three-lane dashboard. [`pwnkit#372`](https://github.com/0sec-labs/pwnkit/pull/372) adds worklist injection (leads prepended as `SemgrepFinding`-shaped records), streaming tool-calls, and the Hunt-lane SSE channel with click-to-highlight provenance back to the originating lead. Two Gemma sizes, two roles, zero cloud.

## Why Gemma 4 specifically — *the model-size family is the architecture*

No closed model and no open non-Gemma model gives all three structural features at once. **Raw hidden states** at every layer (required for Tier 1) — GPT-5 and Claude don't expose them. **Native function-calling + 131k context** (required for the verifier) — Gemma 4 8B reads files and greps call sites in one window. **A model-size family with one architecture** — `weak-probe` on E2B, `strong-probe` on a larger Gemma, verifier on Gemma 4 8B, all sharing tokenizer, hidden-state geometry, and tool schema, so `gemmaforge.leads/v1` flows cleanly between them. Mixing a Llama probe with a Qwen verifier would mean two licenses, two prompt formats, and no guarantee the small model's "vulnerable-looking" hidden state maps to anything the big model cares about.

## What the demo shows

**(1) Streaming token demo (Tier 1 in IDE mode):** two presets frame the same Express handler unsafely vs safely; on unsafe the probe's running mean lifts into yellow/red, clustered around the risky lines (string-interpolated SQL, missing validation). **Mean risk lifts ~10 points** between framings. **(2) Whole-repo audit:** `python -m src.scan ./example-app --events live.ndjson > leads.jsonl` walks the repo; the `/live` dashboard fills in real time (Lane 1 = probe firing, Lane 2 = leads). `pwnkit review --seed-findings leads.jsonl --seed-only --runtime ollama` then hands leads to the Gemma 4 8B agent, which streams verdicts into Lane 3 with click-to-highlight provenance back to the originating lead.

## Limitations (honest)

- **Tier 1 — length artefact (raised and refuted).** On the unmatched dataset a length-only baseline reaches AUC 0.883 on Py→JS (vs probe 0.907); on a length-matched eval the length baseline collapses to chance (0.514) while the probe still hits 0.843, widening the probe-minus-length delta to +0.329 — the 0.907 wasn't mostly length. Regex still beats us on CWE-328 (0.991 vs 0.944).
- **Tier 1 — probes classify representation, not ground truth.** A high score means *"looks like code I was trained on as vulnerable,"* not *"is exploitable"* — which is exactly why Tier 2 exists.
- **Tier 1 — train-inference gap.** Probe trains on last-token activations; streaming inference reads intermediate positions, mitigated by 8-token max-pool at serving time (drops adversarial T3 from Δ −0.087 to |Δ| ≤ 0.005 at −0.031 clean AUC — a **22× robustness improvement**).
- **Tier 1 — surface-form sensitivity.** Full T1–T5 adversarial suite ([Bailey et al. ICLR 2026](https://arxiv.org/abs/2412.09565), [RL-Obfuscation, 2025](https://arxiv.org/abs/2506.14261)): identifier renames + SQL case shift give |Δ| ≤ 0.007; only T3 (comment + reindent) is meaningfully adversarial, and max-pool flattens it.
- **Tier 1 — coverage.** Python and JS first-class; C/C++ have SVEN char-level spans but no full activation pass; Rust/Go/Ruby/PHP score out-of-distribution.
- **Tier 2 — agent quality is bounded by tool design + Gemma 4 8B's tool-following.**

Receipts: `data/eval_length_matched.json`, `data/adversarial_full_suite.json`.

## Bonus: LoRA-augmented safe-code generation

Obeso §3 trains a LoRA alongside the probe; we wired the analogue (`scripts/train_lora.py`, r=8, α=16) on CyberNative DPO chosen completions — 30 SFT steps, 39s on MPS, **base = 3 vulnerable patterns, LoRA = 0** on the 5 demo prompts (`data/lora_eval.json`).

## What we'd build next

Token-level strong-probe on E4B (the bigger backbone should still have headroom past the saturated sample-level corpus); token-level vs sample-level head-to-head; full DPO LoRA on a dedicated GPU; VS Code extension (scaffolded in `extensions/vscode/`).

## License & ethics

Code, probe weights, training-data manifest: **Apache-2.0**. Gemma 4 weights under the **Gemma Terms of Use** (commercial use permitted). Training set uses **only patterns from already-public CVE disclosures** — Doruk's embargoed disclosures were excluded. No user code leaves the laptop at inference time.

## Acknowledgements

- The Gemma team at Google DeepMind, for shipping a model whose weights open cleanly in a debugger *and* an instruction-tuned variant that does native tool-calling.
- [Obeso, Arditi, Ferrando, Freeman, Holmes, Nanda (2025)](https://arxiv.org/abs/2509.03531) — the streaming-probe paper Tier 1 adapts.
- `CyberNative` for the paired-code DPO dataset.
- The `digitalbazaar/forge` security team and others who triaged Doruk's CVE disclosures.

— Doruk Tan Ozturk & Mehmet Efe Akça, May 2026
