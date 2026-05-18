# GemmaForge — Catch Vulnerabilities Inside Gemma 4, Before the Token Lands

**Tracks:** Main Track ($50K) · Impact: Safety & Trust ($10K) · Special Tech: Ollama ($10K)

**Repo:** https://github.com/peaktwilight/gemmaforge
**Live demo:** https://gemmaforge.doruk.ch
**Video:** https://youtube.com/watch?v=TODO

## Team — security meets interpretability

- [**Doruk Tan Ozturk**](https://doruk.ch) ([@peaktwilight](https://github.com/peaktwilight)) — security researcher, ex-ETH Zürich. **10+ CVE-grade vulnerabilities discovered in npm packages with 200M+ combined monthly downloads**, including [CVE-2026-33896](https://github.com/digitalbazaar/forge/security/advisories) in `node-forge`. Builder of [`pwnkit`](https://github.com/PwnKit-Labs/pwnkit) (agentic AI pentest framework) and [**0sec.ai**](https://0sec.ai). Knows what a bug looks like in source.
- **Mehmet Efe Akça** — MSc Data Science, ETH Zürich. Coursework in *Reliable and Trustworthy AI*, *Probabilistic AI*, *Large-Scale AI*. TA for *Mathematics of Signals, Networks, and Learning*. Knows how to read what a neural network is thinking.

Security alone gives you a scanner. Interpretability alone gives you a probe. Together you get **a probe that knows about danger** — trained partly on bugs one of us personally disclosed.

## The problem

AI coding assistants ship ~100M lines of code per day into private repos. A non-trivial fraction is vulnerable: every major assistant has been shown to emit SQL injection, path traversal, command injection, weak crypto, and hardcoded credentials as steady-state behavior.

The industry answer is "scan afterwards." Too late. The developer has already seen the insecure suggestion, and most will paste before any scanner fires. Scanners use static rules — they catch what they were told to catch — and they tell you nothing about how confident *the model itself* was.

We asked a sharper question:

**Can the model, looking at its own hidden state, tell you it is about to write vulnerable code — before the first risky token is finalized?**

Yes. We built it.

## The technique

We adapt the streaming hallucination-probe of [Obeso, Arditi et al. (2025)](https://arxiv.org/abs/2509.03531) (arXiv 2509.03531) from *fabricated entities* to *vulnerable code patterns*. A single linear classifier sits on Gemma 4's last-token hidden state at an intermediate decoder layer. The binary label is *"the code emitted so far is the vulnerable side of a known patch pair."*

The probe is roughly 1,536 weights — under 10 KB — and scores a token in well under a millisecond on the same Apple Silicon laptop that is running Gemma 4.

**Result on Gemma 4 E2B (this submission):** the probe reaches **AUC 0.846** on a stratified 80/20 held-out split of the 1,056-example dataset. Of the four candidate layers (8, 17, 26, 34 — i.e. 25/50/75/100% of the 35-layer decoder), the **earliest layer wins** — consistent with the interpretability finding that mid-network features are often more linearly separable than the final residual stream.

| layer | AUC   | accuracy |
|-------|-------|----------|
| **8** | **0.846** | **73.6%** |
| 17    | 0.823 | 75.0%    |
| 26    | 0.839 | 78.3%    |
| 34    | 0.800 | 72.6%    |

The Obeso paper showed streaming probes work for hallucinated entities at AUC > 0.9 on Llama-3.3-70B; we hit 0.832 on a 2B Gemma 4 with zero hyper-parameter tuning, no LoRA augmentation, and a 1,000-example dataset. With the obvious next steps from that paper — LoRA-augmented probes, more data, per-CWE heads — we expect to close most of that gap.

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
   - **~55 natural-language / non-code "safe" examples** (chat greetings, markdown documentation, README prose, JSON, comments). Without these, an early version of the probe scored every chat-style sentence as vulnerable because it had never seen one — the probe was effectively a "code detector," not a "vulnerability detector." Including non-code negatives forced the probe to learn the actual signal.
2. **Activation capture.** Forward-pass each example through Gemma 4 with `output_hidden_states=True`. Record the last-token hidden state at layers 25%, 50%, 75%, 100%.
3. **Probe training.** Per layer: 80/20 stratified split, `sklearn.linear_model.LogisticRegression(C=1.0)`. Pick the layer with best held-out AUC. Save `(w, b, layer)` as a 10 KB `.npz`.

End-to-end training: ~90 seconds on an M1 Max once activations are cached. Fast enough to iterate the dataset interactively.

## What the demo shows

Click a preset on the left — e.g. *"Write an Express handler for GET /users/:id that returns the user row from MySQL."* Gemma 4 streams code. As tokens land:

- Framework boilerplate stays green.
- The instant Gemma starts writing `` `SELECT * FROM users WHERE id=${id}` ``, the probe flips red **mid-line**. The risk meter pegs at the exact moment Gemma decides to interpolate user-controlled `id` into a SQL string.
- Ask Gemma to write the same handler "safely." The query renders as `db.query("SELECT … WHERE id=?", [id])` and the probe scores near zero.

The developer sees Gemma's internal state betray the unsafe pattern *before* they paste a single character.

## Why Gemma 4 specifically

This project can't be built on a closed model:

- **Raw hidden states.** GPT-5 and Claude don't expose them. Open weights are the only option.
- **Function calling + long context.** Gemma 4 ships native function calling and a 131k window, so the same model running the probe can also drive a normal IDE assistant flow without a cloud round-trip.
- **Permissive license.** Gemma 4's terms are Apache-2.0-equivalent in practice — any maintainer in any country runs it without legal review.
- **Laptop-sized.** Gemma 4 E2B (~2B params) does >20 tok/s on Apple Silicon. 26B-A4B handles the harder cases without leaving the device.

## Limitations (honest)

- **Probes are not ground-truth classifiers, they classify representation.** A high score means *"this looks, on the inside, like code I was trained on as vulnerable,"* not *"this is exploitable."* Expect false positives on lookalike-but-safe patterns.
- **Per-size retraining.** A probe trained on E2B does not drop into 26B-A4B unchanged. ~10 min of compute per size.
- **Uneven cross-language coverage.** Python and JS are well represented. C/C++ less so. Rust and Zig score noisily until we collect targeted pairs.

Tractable with time and data, not blockers on the technique.

## What we'd build next

- **Per-CWE heads.** Multi-head output (CWE-89 vs CWE-22 vs CWE-78 …) so the UI names the bug class.
- **LoRA-augmented probes.** Obeso et al. §3 reports clear AUC gains from a small joint adapter.
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
