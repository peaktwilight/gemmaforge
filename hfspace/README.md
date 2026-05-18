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

- **Panel 1 · Probe stream** — colour-graded per-token risk feed. *Empty on this hosted Space* (free CPU tier can't host Gemma 4); the local pipeline runs `src/stream_with_probe.py --serve` on `:8787` and Panel 1 wires up automatically.
- **Panel 2 · Scan progress** — `scan.start` / `scan.file` / `probe.score` / `scan.lead` / `scan.end` events from a **real `src/scan.py` run** against `examples/vuln-express-app`. The bytes you see were emitted by an actual Gemma 4 E2B forward pass — captured into `examples/events.ndjson`, replayed at 6× original speed.
- **Panel 3 · Ranked leads** — `gemmaforge.leads/v1` records from that same real run. 14 chunks scored, 14 leads emitted; the probe correctly identifies CWE-78 (cmd injection in `ping.js`, `users.js`), CWE-338 (weak RNG in `token.js`), and CWE-95 (eval-class) at confidence 1.000, while dying off on boilerplate at 0.05–0.18.
- **Panel 4 · pwnkit handoff** — a **real `pwnkit review` run** consuming the same leads. 6 seeds ingested from gemmaforge, 3 critical/high findings drafted by the Gemma 4 8B agent over Ollama in one tool-calling turn (Command Injection · Path Traversal · SQL Injection), 5-minute wall clock. Captured into `examples/pwnkit-events.ndjson` via `scripts/build_pwnkit_replay.py` (pulled out of pwnkit's SQLite pipeline_events table), replayed here.

Every byte on Panels 2–4 came out of genuine pipeline runs — no hand-crafted data. Recordings live in this Space at `examples/events.ndjson` (probe scan), `examples/leads.jsonl` (probe output, valid `gemmaforge.leads/v1`), and `examples/pwnkit-events.ndjson` (pwnkit agent timeline). Replay logic in `dashboard/server.py:replay_events_file()` + `pwnkit_stream()`.

Built for the [Gemma 4 Good Hackathon](https://kaggle.com/competitions/gemma-4-good-hackathon) by [Doruk Tan Ozturk](https://doruk.ch) and Mehmet Efe Akça.

[GitHub repo](https://github.com/peaktwilight/gemmaforge) · [Kaggle writeup](https://kaggle.com/competitions/gemma-4-good-hackathon/writeups) · [pwnkit](https://github.com/0sec-labs/pwnkit)
