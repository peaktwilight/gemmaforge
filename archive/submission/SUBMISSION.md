# Submission Checklist — Gemma 4 Good Hackathon

**Deadline:** 2026-05-18 23:59 UTC
**Status:** drafting

## Required artefacts

- [ ] **Kaggle Writeup** (≤1500 words) — `WRITEUP.md` content pasted into a new Kaggle Writeup. Tracks: **Main Track** · **Impact: Safety & Trust** · **Special Tech: Ollama**.
- [ ] **Public Code Repository** — pushed to `https://github.com/peaktwilight/gemmaforge` (flip to public at T-15 min, see runbook)
- [ ] **Public Video** (≤3 min, YouTube, no login required) — unlisted → public on submission day, link pasted into writeup. Placeholder: `https://youtube.com/watch?v=TODO` — replace before clicking Submit.
- [ ] **Live Demo URL** — HuggingFace Space at `https://huggingface.co/spaces/peaktwilight/gemmaforge` (CPU-basic, must read `RUNNING` at T-30 min)
- [ ] **Cover image + media gallery** — primary: `web/cover.svg`; PNG fallback if Kaggle rejects SVG: `web/screenshot-demo.png` (or `web/auc-ladder.png`, `web/demo-grid.png`)

## Order of operations on submission day

1. **Test probe locally one more time** (`python -m src.stream_with_probe --serve`)
2. **Push code to GitHub** (`git push origin main`)
3. **Deploy to HuggingFace Space** (`bash scripts/deploy_hf.sh`)
4. **Record video** (Doruk + Efe, see `VIDEO_SCRIPT.md`)
5. **Edit + upload to YouTube** (unlisted, then public)
6. **Paste writeup into Kaggle**, attach video link + repo link + HF Space link + cover image
7. **Submit on Kaggle** with the "Submit" button (top right of writeup)
8. **Post LinkedIn announcement** (see `LINKEDIN.md`) — paste Kaggle link in first comment

## Submission text snippets

### Kaggle writeup title
GemmaForge — Two Gemmas, One Laptop: Local Repo-Wide Vulnerability Auditing

### Subtitle
Small Gemma (E2B) plus a linear probe on its hidden state triages a whole repo in one forward pass; big Gemma (8B, `gemma4:latest` via Ollama) verifies each lead with tool use. End-to-end local. Built by a security researcher (Doruk) and an ETH interpretability researcher (Efe).

### Tags
gemma, gemma-4, ollama, security, ai-safety, interpretability, linear-probe, vulnerability-detection, agentic-verification, local-first

## Backup plan (if X fails)

- **HF Space not deploying:** submit the GitHub repo URL as "Live Demo" with `bash scripts/setup.sh && python -m src.stream_with_probe --serve` instructions in the README. Kaggle accepts "files for the demo." Attach a 30-second GIF of the working UI.
- **Video not ready by deadline:** YouTube allows upload + immediate publish. We have screen-share recordings of the demo as raw fallback B-roll. Even a single-shot Loom is acceptable if needed.
- **Probe regression on demo day:** the shipped `data/probe.npz` is layer 17, **AUC 0.963 in-dist / 0.907 cross-language**. If a later commit regresses, `git log -- data/probe.npz` will identify the last known good commit; `git checkout <sha> -- data/probe.npz`. Backup: `data/probe_v2.npz` is a stable copy.
