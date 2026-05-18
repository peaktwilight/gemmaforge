# Gemma 4 Good Hackathon — Evaluation Criteria & Tracks

**Submission deadline:** 2026-05-18 23:59 UTC

## Judging philosophy

> "Your project will be judged primarily on your video demo. This is your chance to create something exciting, compelling, and with the potential to be seen by millions. Your video should tell a story, demonstrate the real-world impact of your product, and leave the judges inspired."

> "While the video is the star of the show, all projects must be backed by real, functional technology. The accompanying writeup and code repository will be used by our judges to verify that your product is not just a concept but a working proof-of-concept built on Gemma 4."

## Evaluation criteria (100 points total)

| Criterion | Points | What judges look for |
|---|---:|---|
| **Impact & Vision** | 40 | As demonstrated in the video: how clearly and compellingly does the project address a significant real-world problem? Is the vision inspiring? Does the solution have tangible potential for positive change? |
| **Video Pitch & Storytelling** | 30 | How exciting, engaging, and well-produced is the video? Does it tell a powerful story that captures the viewer's imagination? |
| **Technical Depth & Execution** | 30 | As verified by the repo and writeup: how innovative is the use of Gemma 4's unique features? Is the technology real, functional, well-engineered — not faked for the demo? |

**Implication for GemmaForge:** the video carries 70 points (Impact & Vision + Video). The writeup/code carry 30 points (Technical Depth) but also *back up* the Impact & Vision score — judges will check the repo to verify the demo isn't faked.

## Prize structure

### Main Track — Best Overall
*(Implicit from problem statement — top prize tier.)*

- **Fourth Prize:** $10,000

### Impact Track — $50,000 total

Awards for projects driving impact in five areas:

| Track | Brief | Prize |
|---|---|---:|
| **Health & Sciences** | Bridge the gap between humans and data. Tools that accelerate discovery or democratize knowledge. | $10,000 |
| **Global Resilience** | Systems of tomorrow — offline, edge-based disaster response to long-range climate mitigation — that anticipate, mitigate, and respond to pressing challenges. | $10,000 |
| **Future of Education** | Reimagine the learning journey. Multi-tool agents that adapt to the individual and empower the educator through seamless integration. | $10,000 |
| **Digital Equity & Inclusivity** | Break down barriers through linguistic diversity, intuitive interfaces, tools that help close the AI skills gap. | $10,000 |
| **Safety & Trust** | Pioneer frameworks for transparency and reliability, ensuring AI remains grounded and explainable. | **$10,000** ← GemmaForge's primary impact track |

### Special Technology Track — $50,000 total

Five prizes for outstanding technical achievement using specific tools/frameworks. **Projects are eligible to win both a Main Track Prize and a Special Technology Prize.**

| Tech | Brief | Prize |
|---|---|---:|
| **Cactus** | Best local-first mobile/wearable app that intelligently routes tasks between models. | $10,000 |
| **LiteRT** | Most compelling use case built using Google AI Edge's LiteRT implementation of Gemma 4. | $10,000 |
| **llama.cpp** | Best innovative implementation of Gemma 4 on resource-constrained hardware. | $10,000 |
| **Ollama** | Best project that utilizes and showcases Gemma 4 running locally via Ollama. | **$10,000** ← GemmaForge's primary tech track |
| **Unsloth** | Best fine-tuned Gemma 4 model created using Unsloth, optimized for a specific impactful task. | $10,000 |

## GemmaForge's targeted prize stack

1. **Main Track** — best overall (novel safety mechanism applied to the headline model)
2. **Impact: Safety & Trust** — literal probe-into-the-model implementation of "transparency and reliability, ensuring AI remains grounded and explainable"
3. **Special Tech: Ollama** — local-only, Gemma 4 via Ollama, zero data leaves device

**Potential stretch tracks to consider:**
- *Digital Equity & Inclusivity* — solo maintainers / no-Snyk-budget devs argument is already in our writeup
- *Unsloth* — only if we ship the LoRA path with Unsloth tooling (we currently use vanilla PEFT)
- *llama.cpp* — only if we port the probe to GGUF runtime (not currently shipped)

## What this means for the iteration loop

Every refinement pass should score the artifact against:

1. **Impact & Vision (40 pts)** — does the *video* make a non-technical judge feel the problem is real and urgent, and that this solution is meaningfully a step toward fixing it?
2. **Video Pitch & Storytelling (30 pts)** — does the video have narrative arc, an emotional hook, a money-shot demo, and a memorable close?
3. **Technical Depth & Execution (30 pts)** — does the writeup + repo prove the demo is real, the technique is novel, and the engineering is rigorous?

A great writeup with a mediocre video caps the project at ~60 points. A great video with a faked demo gets disqualified on repo review. We need both to be excellent.
