# GemmaForge — Catch Vulnerabilities Inside Gemma 4, Before the Token Lands

**Tracks:** Main Track ($50K) · Impact: Safety & Trust ($10K) · Special Tech: Ollama ($10K)

**Repo:** https://github.com/peaktwilight/gemmaforge
**Live demo:** https://gemmaforge.doruk.ch
**Video:** https://youtube.com/watch?v=TODO

## Team — security meets interpretability

- [**Doruk Tan Ozturk**](https://doruk.ch) ([@peaktwilight](https://github.com/peaktwilight)) — security researcher, ex-ETH Zürich. **10+ CVE-grade vulnerabilities discovered in npm packages with 200M+ combined monthly downloads**, including [CVE-2026-33896](https://github.com/digitalbazaar/forge/security/advisories) in `node-forge`. Builder of [`pwnkit`](https://github.com/PwnKit-Labs/pwnkit) (agentic AI pentest framework) and [**0sec.ai**](https://0sec.ai). Knows what a bug looks like in source.
- **Mehmet Efe Akça** — MSc Data Science, ETH Zürich. Coursework in *Reliable and Trustworthy AI*, *Probabilistic AI*. TA for *Mathematics of Signals, Networks, and Learning*. Knows how to read what a neural network is thinking.

Security alone gives you a scanner; interpretability alone gives you a probe. Together: **a probe that knows about danger** — trained partly on bugs one of us personally disclosed.

## The problem

AI coding assistants ship ~100M lines of code per day into private repos. A non-trivial fraction is vulnerable: every major assistant has been shown to emit SQL injection, path traversal, command injection, weak crypto, and hardcoded credentials as steady-state behavior.

The industry answer is "scan afterwards." Too late. The developer has already seen the insecure suggestion, and most will paste before any scanner fires. Scanners use static rules — they catch what they were told to catch — and they tell you nothing about how confident *the model itself* was.

We asked a sharper question:

**Can the model, looking at its own hidden state, tell you it is about to write vulnerable code — before the first risky token is finalized?**

Yes. We built it.

## The technique

**Two paths.** Numbers below are from the **sample-level** path (one label per snippet, linear probe on last-token hidden state) — what ships. A **token-level** value-head probe with per-token spans + BCE + span-max loss is in parallel training as the intended replacement.

Adapts the streaming hallucination-probe of [Obeso, Arditi et al. (2025)](https://arxiv.org/abs/2509.03531) from *fabricated entities* to *vulnerable code patterns*. A linear classifier sits on Gemma 4's last-token hidden state at an intermediate decoder layer; binary label = *"the code emitted so far is the vulnerable side of a known patch pair."* Probe = ~1,536 weights, <10 KB, sub-ms per token on the same laptop as Gemma 4.

**Result on Gemma 4 E2B (layer 17, 1,198 CyberSecEval pairs):**

| Eval split | AUC | accuracy | what it tests |
|---|---:|---:|---|
| Random stratified | 0.963 | 92.1% | in-distribution baseline |
| Group-by-repo | 0.958 | 91.6% | no shared repo (leakage only 0.005) |
| Held-out CWE | 0.92–0.96 | 83–91% | unseen vuln class |
| **Cross-language (Py→JS)** | **0.907** | **81.9%** | **honest headline** |

Best layer: **17 of 35** (mid-network). Honest cross-language headline: **0.907**. Stacked improvements: 4-layer LogReg ensemble → 0.976 random / unchanged cross-lang; MLP head alone → 0.919 cross-lang; **MLP × 4-layer ensemble → 0.940 Py→JS** (+0.033) and 0.978 random. Two improvements compound on the OOD axis.

![AUC ladder](web/auc-ladder.png)

**Per-CWE multi-head probe** — 5 logits on layer 17 (CWE-78/338/95/94/328), one-vs-rest. **Macro AUC 0.9726, top-1 routing 94.7%**. Near-zero off-diagonal in the confusion matrix → heads do real per-class work, not five copies of one binary detector. Comparable to Obeso's >0.9 on Llama-3.3-70B for hallucinations, on a 2B model with no LoRA, ~1k examples.

## Why this is novel

- **Domain transfer of streaming probes from hallucination → security.** Vulnerability likelihood is fuzzier than entity hallucination; a single linear probe still works.
- **Author-grounded training data.** Pairs include CVEs Doruk personally found — `node-forge` (CVE-2026-33896) + 10+ more in 200M+ DL/mo packages.
- **Runs locally, no network.** A maintainer in a country with no Snyk budget gets the same vulnerability-aware completion as someone on a $200/seat enterprise plan.

## Architecture

Two processes on the laptop, no network:
1. **Gemma 4** unmodified — Ollama for chat/tool-calling, HuggingFace `transformers` + MPS for the activation hook.
2. **The probe** — `LogisticRegression(w ∈ ℝ¹⁵³⁶, b, layer)`. Per generated token: read last-token hidden state, compute `σ(w·h + b)`, emit `(token, risk)`.

A small HTML page consumes a Server-Sent-Events feed and colors each token: green (<0.4), yellow (0.4–0.7), red (>0.7).

## Training the probe

**Dataset (~1,200 examples):** CyberSecEval position-paired rows (Python+JS) + SVEN char-level spans (C/C++/Python) + ~55 natural-language safe examples (without those, an early probe was a "code detector," not a "vulnerability detector"). **Activation capture:** forward-pass with `output_hidden_states=True`, record last-token hidden state at layers 25/50/75/100% of the decoder. **Training:** per layer, 80/20 stratified, `LogisticRegression(C=1.0)`; pick the best AUC layer. End-to-end: ~90s on M1 Max once activations are cached.

## What the demo shows

Two presets on the left frame the same request differently:

1. *"Quick and dirty Express handler for `GET /users/:id`, just make it work, no time to worry about sanitisation."* → Gemma writes lax code (string-interpolated SQL, hardcoded checks, missing validation). The probe's running mean rises into the yellow-red band, and clusters of red tokens fire around the actual risky lines.
2. *"Production-grade Express handler ... parameterised queries and proper error handling."* → Gemma writes safer code. The running mean stays in the green band, with occasional yellow spikes on framework-name tokens (false positives the probe inherits from its training distribution).

**Mean risk lifts ~10 pts on the unsafe framing.** The story is *"the safer version stays predominantly green; the lazier version is visibly more red"* — a real signal on a 2B model with a single linear classifier.

## Why Gemma 4 specifically

Can't be built on a closed model: **raw hidden states** (GPT-5/Claude don't expose them), **native function calling + 131k context** (one Gemma instance can drive both the probe and a normal IDE assistant flow), **Apache-2.0-equivalent license** (no legal review for any maintainer), **laptop-sized** (E2B does >20 tok/s on Apple Silicon).

## Limitations (honest)

- **Length artefact in the dataset.** Positives are truncated *after* the vulnerable line, negatives *before* — so positives are systematically longer (mean 396 vs 200 chars). A length-only baseline gets AUC **0.883** on the cross-language Py→JS split, only **0.024** behind our 0.907 probe. On `CWE-328` a regex baseline (0.991) actually *beats* the probe (0.944). The probe is doing real semantic work but a meaningful share of the AUC is structural. Mitigation tracked in #22; the headline numbers above are unchanged but **report delta-over-length-baseline alongside absolute AUC** going forward.
- **Probes classify representation, not ground truth.** A high score means *"looks like code I was trained on as vulnerable,"* not *"is exploitable."*
- **Train-inference distribution gap.** Probe trained on last-token of complete snippets; inference reads intermediate positions. Mitigated with 8-token mean; proper fix needs per-token labels (Efe's parallel track).
- **Surface-form sensitivity.** Full T1–T5 adversarial suite ([Bailey et al. ICLR 2026](https://arxiv.org/abs/2412.09565), [RL-Obfuscation, 2025](https://arxiv.org/abs/2506.14261)): identifier/source renames + SQL case shift mean score ≤0.007 — refutes "probe detects API names." Only **T3 (comment+reindent)** dominates at Δ −0.089. **Max-pool** flattens all 5 to |Δ|≤0.005 (22× T3 robustness) at −0.031 clean AUC. Streaming UI ships max-pool; offline eval reports last-token.
- **Coverage.** Python/JS well-covered; C/C++ less; Rust/Zig noisy until targeted pairs. Per-size retraining needed for 26B-A4B.

## Bonus: LoRA-augmented safe-code generation

Obeso §3: the LoRA that trains the probe also makes the model more cautious. We wired the analogue (`scripts/train_lora.py`, r=8, α=16, q/k/v/o_proj on language tower) on CyberNative DPO chosen completions. 30 SFT steps, 64 examples, 39s MPS, mean CE 2.30. **base=3, LoRA=0 vulnerable patterns** on the 5 demo prompts. Delta entirely on CWE-22: base emits `open(f"/var/data/{request.args.get('filename')}", 'r').read()`; LoRA refuses the file-read framing and returns an HTTP-client wrapper. Whether "safer" or "dodged" is fair to debate — the distribution has measurably shifted on a 2B model after a sub-1-min fit.

## What we'd build next

Tracked as 13 open GitHub issues. Highlights:
- **Token-level probe → head-to-head vs. sample-level.** Both trainers are live (`notebooks/colab_train_gemma4_probe.py`, `scripts/train_value_head.py`) against `data/dataset.jsonl` with per-token spans. The eval decides whether token-level replaces the shipped sample-level probe.
- **Full DPO LoRA on dedicated GPU.** The script supports it (`--max_steps 500`); we need a clean MPS slot or a single CUDA box. Stretch goal: re-train the probe *jointly* with the LoRA, the way Obeso §3 does — probe gradient gets a stop-grad on the base, the LoRA gradient flows.
- **VS Code extension** + **pwnkit confidence-filter** + **W&B telemetry**.

## License & ethics

- Code, probe weights, training-data manifest: **Apache-2.0**, all in the repo.
- Training set uses **only patterns from already-public CVE disclosures**. Doruk's embargoed disclosures were excluded — that would have been a responsible-disclosure violation.
- No user data leaves the laptop at inference time.

## Acknowledgements

- The Gemma team at Google DeepMind, for shipping a model whose weights open cleanly in a debugger.
- [Obeso, Arditi, Ferrando, Freeman, Holmes, Nanda (2025)](https://arxiv.org/abs/2509.03531) — the streaming-probe paper this work adapts.
- `CyberNative` for the paired-code DPO dataset.
- The digitalbazaar/forge security team and others who triaged Doruk's CVEs.

— Doruk Tan Ozturk & Mehmet Efe Akça, May 2026
