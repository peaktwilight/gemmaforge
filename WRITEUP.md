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

We adapt the streaming hallucination-probe of [Obeso, Arditi et al. (2025)](https://arxiv.org/abs/2509.03531) (arXiv 2509.03531) from *fabricated entities* to *vulnerable code patterns*. A single linear classifier sits on Gemma 4's last-token hidden state at an intermediate decoder layer. The binary label is *"the code emitted so far is the vulnerable side of a known patch pair."*

The probe is roughly 1,536 weights — under 10 KB — and scores a token in well under a millisecond on the same Apple Silicon laptop that is running Gemma 4.

**Result on Gemma 4 E2B (layer 17, 1,198 CyberSecEval pairs):**

| Eval split | AUC | accuracy | what it tests |
|---|---:|---:|---|
| Random stratified | 0.963 | 92.1% | in-distribution baseline |
| Group-by-repo | 0.958 | 91.6% | no shared repo (leakage only 0.005) |
| Held-out CWE | 0.92–0.96 | 83–91% | unseen vuln class |
| **Cross-language (Py→JS)** | **0.907** | **81.9%** | **honest headline** |

Best layer: **17 of 35** (mid-network). Multi-layer concat doesn't beat it. **0.907 cross-language** is the honest headline.

**Per-CWE multi-head probe** — 5 logits (CWE-78 / 338 / 95 / 94 / 328) on the same layer 17, trained one-vs-rest. **Macro AUC 0.9726, top-1 routing 94.7%**. The off-diagonal of the confusion matrix is near-zero, which means the heads are doing real per-class work — not five copies of a binary "danger" detector. Comparable to Obeso's >0.9 on Llama-3.3-70B for hallucinations, on a 2B Gemma 4 with no tuning, no LoRA, ~1k examples.

## Why this is novel

- **Domain transfer of streaming probes from hallucination → security.** Entity hallucination is sharply defined. Vulnerability likelihood is a property of code patterns, not single tokens. A single linear probe still works.
- **Author-grounded training data.** Training pairs include patterns from CVEs Doruk personally found — `node-forge` (CVE-2026-33896) plus 10+ more in 200M+ DL/mo npm packages. The probe learned what danger looks like from real bugs he disclosed.
- **Runs locally, no network.** The maintainer in a country with no Snyk budget, the researcher who refuses to send pre-disclosure code to a third-party API — both get the same vulnerability-aware completion as someone on a $200/seat enterprise plan.

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

This project can't be built on a closed model:

- **Raw hidden states.** Closed models don't expose them. Open weights are the only option.
- **Native function calling + 131k context.** The same Gemma 4 instance can drive a normal IDE assistant flow alongside the probe, without a cloud round-trip.
- **Permissive license.** Apache-2.0-equivalent terms; any maintainer in any country runs it without legal review.
- **Laptop-sized.** E2B (~2B) does >20 tok/s on Apple Silicon. 26B-A4B covers harder cases locally.

## Limitations (honest)

- **Probes classify representation, not ground truth.** A high score means *"this looks, on the inside, like code I was trained on as vulnerable,"* not *"this is exploitable."* Expect false positives on lookalike-but-safe patterns.
- **Train-inference distribution gap on streaming.** The probe was trained on the last-token activation of *complete* snippets but at inference reads every *intermediate* position. We mitigate with an 8-token sliding-window mean; a proper fix needs per-token labels — a real project, not a hackathon weekend.
- **Per-size retraining.** A probe trained on E2B does not drop into 26B-A4B unchanged. ~10 min of compute per size.
- **Uneven cross-language coverage.** Python and JS are well represented. C/C++ less so. Rust and Zig score noisily until we collect targeted pairs.

Tractable with time and data, not blockers on the technique.

## Bonus: LoRA-augmented safe-code generation

Obeso §3 reports the LoRA that trains the probe also makes the model itself more cautious. We wired the analogue: `scripts/train_lora.py` fine-tunes Gemma 4 E2B (r=8, α=16, q/k/v/o_proj on the language tower only) on CyberNative DPO chosen completions. Primary path: `trl.DPOTrainer`; SFT fallback.

**Result.** 30 SFT steps, 64 examples, 39s on MPS, mean CE 2.30. `scripts/eval_lora.py` regex-scores base vs base+LoRA on the 5 demo prompts: total **base=3, LoRA=0 vulnerable patterns**. The delta is entirely on CWE-22 (path traversal): base emits `open(f"/var/data/{request.args.get('filename')}", 'r').read()`; LoRA refuses the file-read framing and returns an HTTP-client wrapper instead. Whether that's "safer" or "dodged" is fair to debate, but the model's generation distribution has measurably shifted on a 2B model after a sub-1-min adapter fit. A full DPO run via `trl` is the obvious next step.

## What we'd build next

Tracked as 13 open GitHub issues. Highlights:
- **Token-level span-max training** — SVEN + CyberSecEval data integrated; trainer written; per-token run pending.
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
