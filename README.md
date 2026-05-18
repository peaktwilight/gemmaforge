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

- **Model:** `gemma4:8b` (8B params, 2560-dim hidden states, 131k context, native function-calling)
- **Probe:** a 2560-input linear classifier (~10KB) on the hidden state at each generated token
- **Training data:** patched/vulnerable function pairs from GHSA advisories, BigVul, and the author's CVE corpus
- **Inference:** < 1 ms per token of overhead. Runs on the same M1/M2/M3 laptop as Gemma 4 itself.

## Tracks targeted

- **Main Track** — Best overall: a novel safety mechanism applied to the headline model of the hackathon.
- **Impact / Safety & Trust** — Direct hit: "Pioneer frameworks for transparency and reliability, ensuring AI remains grounded and explainable." The probe peers *inside* the model — that's the most literal interpretation of explainability we could think of.
- **Special Tech / Ollama** — Local-only, no cloud. The model runs on Ollama. The probe runs on the developer's laptop. Zero data leaves the device.

## Team

**Doruk Tan Ozturk** — [@peaktwilight](https://github.com/peaktwilight) · [doruk.ch](https://doruk.ch) · security researcher. Discovered CVE-2026-33896 (`node-forge`) and three other CVEs in widely-used npm packages. The vulnerable functions from those disclosures are part of this probe's training set.

**Mehmet Efe Akça** — MSc Data Science @ **ETH Zürich** · TA for *Mathematics of Signals, Networks, and Learning*. Coursework: *Reliable and Trustworthy AI: interpretability & verifiability*, *Probabilistic AI*, *Large-Scale AI*. Brings the interpretability-research side of the project — the linear-probe technique adopted here sits directly in his area of study.

Together: a security researcher who knows what danger looks like in source code + an interpretability researcher who knows how to read what neural networks are thinking. The whole point of GemmaForge is that those two skills only become useful when you put them together.

## License

Apache-2.0.
