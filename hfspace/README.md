---
title: GemmaForge
emoji: 🔥
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: true
license: apache-2.0
short_description: Live dashboard for the two-Gemma vulnerability pipeline
---

# GemmaForge — live dashboard

Four-panel dashboard for the GemmaForge two-Gemma vulnerability pipeline.

- **Panel 1 · Probe stream** — colour-graded per-token risk feed (replays a canned demo here; live mode runs against the local streaming probe server on `:8787`).
- **Panel 2 · Scan progress** — `scan.file` / `probe.score` / `scan.end` events as `src/scan.py` walks the repo.
- **Panel 3 · Ranked leads** — `gemmaforge.leads/v1` records with file:line, CWE, snippet preview, and probe confidence.
- **Panel 4 · pwnkit handoff** — synthetic `queued → exploit → report` cycle illustrating the Tier 3 verifier handoff (pwnkit `--seed-findings` consuming our leads JSONL).

This hosted Space replays `examples/leads.jsonl` so judges can see the layout end-to-end without bringing up a backend. For the live pipeline, clone the repo and follow `dashboard/README.md`.

Built for the [Gemma 4 Good Hackathon](https://kaggle.com/competitions/gemma-4-good-hackathon) by [Doruk Tan Ozturk](https://doruk.ch) and Mehmet Efe Akça.

[GitHub repo](https://github.com/peaktwilight/gemmaforge) · [Kaggle writeup](https://kaggle.com/competitions/gemma-4-good-hackathon/writeups) · [pwnkit](https://github.com/0sec-labs/pwnkit)
