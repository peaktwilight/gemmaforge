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
| Random stratified | 0.963 | 92.1% | in-distribution, baseline (paired-leakage warning ↓) |
| Group-by-repo | 0.958 | 91.6% | no shared repo across train/test — leakage was real but only 0.005 |
| Held-out CWE-78 | 0.924 | 84.8% | unseen vuln class |
| Held-out CWE-338 | 0.923 | 82.9% | unseen vuln class |
| **Cross-language (Python→JS)** | **0.907** | **81.9%** | **realistic transfer headline** |

Best layer: **17 of 35** (mid-network). Multi-layer concat (8+17+26+34) → 0.958, doesn't beat single-layer 17. We report the **cross-language 0.907** as the headline because it's the most demanding split that excludes the same-source / same-language leakage that random/group splits don't.

Obeso et al. reached AUC > 0.9 on Llama-3.3-70B for hallucinations; we hit 0.846 on a 2B Gemma 4 with no tuning, no LoRA, ~1k examples. The obvious next steps from §3 of that paper — LoRA-augmented probes, more data, per-CWE heads — should close the gap.

## Why this is novel

- **Domain transfer of streaming probes from hallucination → security.** Entity hallucination is sharply defined. Vulnerability likelihood is a property of code patterns, not single tokens. A single linear probe still works.
- **Author-grounded training data.** The training pairs include pre-disclosure and post-patch versions of CVEs Doruk personally found — `node-forge` (CVE-2026-33896), three more npm CVEs, plus hand-curated synthetic seeds. The probe learned what danger looks like from real bugs he disclosed.
- **Runs locally, no network.** The maintainer in a country with no Snyk budget, the researcher who refuses to send pre-disclosure code to a third-party API — both get the same vulnerability-aware completion as someone on a $200/seat enterprise plan.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ developer's laptop  —  no network required                       │
│                                                                  │
│  ┌──────────────┐   hidden states    ┌─────────────────────┐     │
│  │  Gemma 4     │ ───────────────►   │ linear vuln probe   │     │
│  │  via Ollama  │  (1536-D vector)   │ (~10 KB, sigmoid)   │     │
│  │  + MLX hook  │                    └────────┬────────────┘     │
│  │  for hidden  │   token + risk             │ risk score        │
│  │  states      │ ─────────────────►  ┌──────▼──────────────┐    │
│  └──────────────┘                     │  streaming UI       │    │
│                                       │  green/yellow/red   │    │
│                                       └─────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

Two processes on the user's machine:

1. **Gemma 4**, unmodified — via Ollama for chat and tool-calling, via HuggingFace `transformers` with MPS for the activation hook.
2. **The probe** — a trained `LogisticRegression` exported as `(w ∈ ℝ¹⁵³⁶, b ∈ ℝ, layer)`. Each generated token: read the last-token hidden state at the chosen layer, compute `σ(w·h + b)`, emit `(token, risk)`.

A small HTML page consumes a Server-Sent-Events feed and colors each token: green (<0.4), yellow (0.4–0.7), red (>0.7).

## Training the probe

1. **Dataset.** ~1,050 examples:
   - Doruk's published CVE corpus (`node-forge`, `picomatch`, two more).
   - `CyberNative/Code_Vulnerability_Security_DPO` — paired vulnerable/patched code across Python, JS, C, Java, 1:1 balanced.
   - Hand-written seeds covering CWE-22, 78, 79, 89, 94, 295, 327, 330, 352, 502, 798, 918, 1333.
   - **~55 natural-language safe examples** (chat greetings, markdown, JSON, prose). Without these, an early probe scored every chat sentence as vulnerable — it was a "code detector," not a "vulnerability detector." Adding non-code negatives forced the actual signal.
2. **Activation capture.** Forward-pass each example through Gemma 4 with `output_hidden_states=True`. Record the last-token hidden state at layers 25%, 50%, 75%, 100%.
3. **Probe training.** Per layer: 80/20 stratified split, `sklearn.linear_model.LogisticRegression(C=1.0)`. Pick the layer with best held-out AUC. Save `(w, b, layer)` as a 10 KB `.npz`.

End-to-end training: ~90 seconds on an M1 Max once activations are cached. Fast enough to iterate the dataset interactively.

## What the demo shows

Two presets on the left frame the same request differently:

1. *"Quick and dirty Express handler for `GET /users/:id`, just make it work, no time to worry about sanitisation."* → Gemma writes lax code (string-interpolated SQL, hardcoded checks, missing validation). The probe's running mean rises into the yellow-red band, and clusters of red tokens fire around the actual risky lines.
2. *"Production-grade Express handler ... parameterised queries and proper error handling."* → Gemma writes safer code. The running mean stays in the green band, with occasional yellow spikes on framework-name tokens (false positives the probe inherits from its training distribution).

Across runs, **mean risk lifts ~10 percentage points** on the unsafe framing vs. the safe one. The story is *"the safer version stays predominantly green; the lazier version is visibly more red"* — a real signal on a 2B model with a single linear classifier.

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

## What we'd build next

- **Per-CWE heads.** Multi-head output (CWE-89 vs CWE-22 vs CWE-78 …) so the UI names the bug class.
- **Token-level training data at scale.** SVEN (ETH SRI, char-level vuln spans) + CyberSecEval (line-level, 8 languages) integrated; we built the loaders. Need a full per-token training run with the span-max loss from Obeso §3 to close the AUC gap toward 0.9.
- **LoRA-augmented Gemma.** Obeso §3 reports the same LoRA used to train a hallucination probe also makes the model *more cautious* on its own — generations become "more conservative in making specific factual claims." The cybersecurity analogue is "model writes safer code by default." We have the training script wired (see `scripts/train_lora.py`) and partial results in the repo.
- **W&B telemetry on training runs.** Probe and LoRA training would log per-step loss/AUC to wandb so reruns are auditable.
- **VS Code extension.** The streaming layer is already SSE; an editor plugin is a week of polish.
- **Hook into pwnkit.** Doruk's pentest framework drives Gemma 4 through CVE-hunting workflows. Adding the probe as a confidence filter — "Gemma claims this is SQLi *and* the activations match the SQLi training pattern" — closes the loop.

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
