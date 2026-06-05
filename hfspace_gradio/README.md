---
title: GemmaForge — Repo Scan
emoji: 🔎
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: 5.25.0
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-a10g
short_description: Paste a public GitHub repo, get ranked vulnerability leads.
---

# GemmaForge — public-repo vulnerability scan

Gradio + ZeroGPU Space for the GemmaForge two-tier vulnerability pipeline. Paste a
public GitHub repo URL, the Space shallow-clones it, runs the shipped linear + per-CWE
probes over Gemma 4 E2B activations, and returns ranked leads in the
`gemmaforge.leads/v1` schema.

## What it does

1. Validates the URL (only `github.com/owner/repo` form is accepted) and shallow-clones
   the repo into a tempdir on the Space.
2. Walks the source files matching the requested languages (default: `py,js`).
3. Scores each sliding-window chunk with the GemmaForge linear probe on layer 17 of
   `google/gemma-4-E2B-it`, plus the per-CWE one-vs-rest heads for CWE-78/338/95/94/328.
4. Ranks the leads by `confidence × (1 + 0.5 if top_cwe else 0)` and returns the top-K.

## Limits

Each scan is capped to fit the 120s ZeroGPU (H200-backed) window:

- 100 MB shallow clone
- 400 source files considered
- 800 probe forward passes by default (slider goes up to 2000)
- 105s wall-clock budget — partial results returned if hit
- 256 KB max per file

For full-repo scans, clone the [GemmaForge repo](https://github.com/peaktwilight/gemmaforge)
and run `python -m src.scan` locally — the same probe, same schema, no caps.

## Related

- Tier 2 verifier — [`pwnkit`](https://0sec.ai/pwnkit) consumes the
  same `gemmaforge.leads/v1` JSONL via `--seed-findings`, drives Gemma 4 27B as an
  agent that reads files and corroborates each lead.
- Dashboard Space — [`peaktwilight/gemmaforge`](https://huggingface.co/spaces/peaktwilight/gemmaforge)
  shows the four-panel pipeline view (probe stream / scan progress / leads / pwnkit handoff).

Built for the [Gemma 4 Good Hackathon](https://kaggle.com/competitions/gemma-4-good-hackathon)
by [Doruk Tan Ozturk](https://doruk.ch) and Mehmet Efe Akça.
