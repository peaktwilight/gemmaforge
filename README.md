# GemmaForge

**Real-time vulnerability detection inside Gemma 4 — see when AI is about to write insecure code, before it does.**

GemmaForge is a Gemma 4 safety layer that watches the model's *hidden states* while it generates code, and raises an alarm token-by-token when the activations look like a known vulnerability pattern. No external scanner. No after-the-fact lint. The detection happens **inside the model**, in real time, as the first risky token is forming.

We achieve this with a **linear probe** trained on Gemma 4's internal representations of ~1000 known vulnerable / safe code pairs drawn from real CVEs — including [CVE-2026-33896](https://github.com/digitalbazaar/forge/security/advisories) (`node-forge`, 33M weekly downloads), which the author of this project disclosed in March 2026.

## The story

In 2026, every IDE has an AI in it. Most of the code those AIs generate ships. Almost none of it is checked for security before it does.

Existing safety tools (Snyk, Semgrep, CodeQL) run *after* the code is written. By then, the model has already shown you something insecure and many devs will copy it. The damage is done.

GemmaForge asks a different question: **what if the model itself could tell you, mid-generation, that the next 50 tokens it's about to emit look exactly like the kind of code a CVE gets filed against?**

Recent research [(Obeso, Arditi et al., 2025)](https://arxiv.org/abs/2509.03531) shows linear probes on hidden states can detect hallucinated entities in real time, with AUC > 0.9, at near-zero inference cost. We adapt the same technique to a different signal — **vulnerability likelihood** — using Gemma 4 as the target model and a labeled dataset built from real CVE disclosures.

## What this is, technically

```
Prompt: "function getUserById(id) {"
   ↓
Gemma 4 generates: "  const q = `SELECT * FROM users WHERE id=${id}`"
                    ─────────────────────────────────────────────────
                                          ▲
                              probe score: 0.94 → red highlight
                              ("SQL injection imminent")
```

- **Model:** `gemma4:8b` (8B params, 1536-dim hidden states, 131k context, native function-calling)
- **Probe:** a 1,536-input linear classifier (~10KB) on the hidden state at decoder layer 8 (of 35). **AUC 0.846** on held-out 80/20.
- **Training data:** 1,056 examples — paired vulnerable/patched code (CyberNative DPO + the author's CVE corpus) + ~55 natural-language safe negatives so the probe doesn't fire on Gemma's chat preamble
- **Inference:** < 1 ms per token of overhead on top of normal forward pass. Runs on the same M1/M2/M3 laptop as Gemma 4 itself.

## Tracks targeted

- **Main Track** — Best overall: a novel safety mechanism applied to the headline model of the hackathon.
- **Impact / Safety & Trust** — Direct hit: "Pioneer frameworks for transparency and reliability, ensuring AI remains grounded and explainable." The probe peers *inside* the model — that's the most literal interpretation of explainability we could think of.
- **Special Tech / Ollama** — Local-only, no cloud. The model runs on Ollama. The probe runs on the developer's laptop. Zero data leaves the device.

## Team

**Doruk Tan Ozturk** — [@peaktwilight](https://github.com/peaktwilight) · [doruk.ch](https://doruk.ch) · security researcher, ex-ETH Zürich, building [0sec.ai](https://0sec.ai). **10+ CVE-grade vulnerabilities discovered in npm packages with 200M+ combined monthly downloads**, including CVE-2026-33896 in `node-forge`. The vulnerable functions from those disclosures are part of this probe's training set.

**Mehmet Efe Akça** — MSc Data Science @ **ETH Zürich** · TA for *Mathematics of Signals, Networks, and Learning*. Coursework: *Reliable and Trustworthy AI: interpretability & verifiability*, *Probabilistic AI*, *Large-Scale AI*. Brings the interpretability-research side of the project — the linear-probe technique adopted here sits directly in his area of study.

Together: a security researcher who knows what danger looks like in source code + an interpretability researcher who knows how to read what neural networks are thinking. The whole point of GemmaForge is that those two skills only become useful when you put them together.

## Quick start

```bash
git clone https://github.com/peaktwilight/gemmaforge
cd gemmaforge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 1. build the vulnerable/safe pair dataset (uses CyberNative DPO + seed CVEs)
python scripts/build_dataset.py
# 2. extract Gemma 4 hidden states  (~10 min on M1 Max, ~5 min on a 3090)
python -m src.extract_activations
# 3. train the linear probe  (~90 seconds)
python -m src.train_probe
# 4. run the streaming demo with web UI
python -m src.stream_with_probe --serve
# then open http://localhost:8787/
```

The streaming web UI uses the Server-Sent-Events feed at `/stream?prompt=…`. The CLI mode (`--prompt "…"`) renders the same risk-coloured stream in your terminal with ANSI colour codes.

## Repository layout

```
src/
  extract_activations.py  ── forward-pass Gemma 4 over the labelled dataset,
                              capture per-layer hidden state at the last token.
  train_probe.py          ── per-layer logistic-regression probe, pick best
                              AUC, export (w, b, layer) to data/probe.npz.
  stream_with_probe.py    ── token-by-token streaming inference with the
                              trained probe + an HTTP/SSE server for the UI.

hfspace/
  app.py                  ── HuggingFace Spaces deployment (Gradio + ZeroGPU).
  requirements.txt
  README.md               ── space metadata.

web/
  index.html              ── single-file streaming UI (vanilla JS + SSE).
  cover.svg               ── submission cover image.

scripts/
  build_dataset.py        ── assemble vulnerable/safe code pairs from
                              CyberNative DPO + a hand-curated seed set
                              covering CWE-22/78/79/89/94/295/327/330/352/
                              502/798/918/1333.
  smoke_probe.py          ── write a placeholder probe so the UI is
                              demo-able while real training is in flight.

WRITEUP.md                ── Kaggle submission writeup (~1400 words).
VIDEO_SCRIPT.md           ── 2:50 video script for the two-person team.
LINKEDIN.md               ── launch post.
```

## License

Apache-2.0.
