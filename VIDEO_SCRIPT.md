# Video script — GemmaForge (target: 2:50, hard limit 3:00)

## Team
- **Doruk Tan Ozturk** — security researcher, disclosed CVE-2026-33896 and other CVE-grade npm bugs. Builder of pwnkit (Tier 2). Opens with the CVE hook, voiceovers the demo.
- **Mehmet Efe Akça** — MSc Data Science at ETH Zürich. Built the probe (Tier 1). Carries the interpretability bridge.

## Format
- Talking head + screen-share, alternating
- Doruk on camera for hook + demo voiceover
- Efe on camera for the interpretability bridge
- Both on camera at the close
- Subtitles burned in (judges may watch muted) — every beat must read on mute

## Tracks targeted
- Main · Impact, Safety & Trust · Special Tech / Ollama

---

## Beat 1 — Hook (0:00–0:18)

*B-roll behind the opening line: the real CVE-2026-33896 advisory page on GitHub (2s), then a Copilot autocompletion finishing an Express handler — the suggestion contains a textbook injection. Burned-in caption: `AI tools now ship ~100M lines of code/day. Most of it is unaudited.`*

**Visual:** Doruk on camera, sitting at desk. Code editor barely visible behind him.

**Doruk (to camera):**
> "Two months ago I published CVE-2026-33896 in `node-forge` — a crypto library that ships inside a lot of the JavaScript stack you've used today. I find bugs like this for a living. But here's what bothers me: an AI assistant could have written that exact pattern this morning, and nobody would have caught it before it shipped."

**Cut to:** title card. White on black:

```
   GemmaForge
   Small Gemma finds. Big Gemma hunts.
   Local repo-wide vulnerability auditing.
```

---

## Beat 2 — The twist (0:18–0:35)

*Visual: quick montage — Copilot autocompleting an Express handler, a developer tab-accepting the suggestion, Snyk's pricing page ($25/dev/mo highlighted), the CVE detail page. Speed up 2x. Caption on Snyk frame: `Solo maintainers priced out.`*

**Doruk (voiceover):**
> "Every IDE has an AI in it now. They write a lot of the code that ships. The standard answer is: scan it afterwards. With Snyk. With Semgrep. With something cloud-bound that costs hundreds of dollars a seat. Maintainers of open packages — the people whose bugs *I* keep finding — usually don't have that."

*Cut to Doruk on camera, leaning in.*

**Doruk:**
> "So we built something different. A two-tier auditor that runs entirely on your laptop. Small Gemma reads your whole repo and triages it. Big Gemma verifies the hits. Same model family, no cloud, free."

---

## Beat 3 — The bridge (0:35–1:05)

**Visual:** Efe on camera. Whiteboard or simple diagram visible behind him.

**Efe (to camera):**
> "I'm Efe — MSc Data Science at ETH, one of my courses is Reliable and Trustworthy AI. There's a result from ETH and Anthropic's MATS program: a tiny linear classifier on a model's hidden states can detect hallucinations. AUC around 0.9. We adapted that — same probe shape, different signal. We trained it on Gemma 4 hidden states to predict *vulnerability likelihood* and *which CWE class* the code looks like."

**Visual cut:** simple diagram appears next to him, then a second slide with the receipts.

```
Gemma 4 hidden state ── linear probe ── risk score + CWE
   (~1,500 numbers)         (~10 KB)
```

```
   weak-probe  · Gemma 4 E2B · layer 17 · AUC 0.907 cross-lang (Py→JS)
   strong-probe · Gemma 4 E4B · layer 10 · 0.969 group_repo
   <1 ms/token overhead · 0.9726 per-CWE macro
```

**Efe:**
> "The probe is smaller than a JPEG. Cross-language AUC zero-point-nine-oh-seven — train on Python, evaluate on JavaScript, still works. Here's the interpretability finding we didn't expect: in the small Gemma the vuln direction lives at layer seventeen; in the bigger Gemma it shows up at layer ten. The signal moves earlier as the model gets larger. And under a comment-plus-reindent adversarial attack, max-pool aggregation cuts the drop twenty-two-fold versus last-token."

---

## Beat 4 — The demo (1:05–2:15) — THE MONEY SHOT

*Beat 4 has three crisp sub-cuts. Total ~70 seconds, hard cap. Every cut has a burned-in caption naming the tier and the action — readable on mute.*

### 4a — Tier 1: scan the whole repo (1:05–1:30)

**Visual:** terminal, dark background, large font. A clean Express example app open on the side. Caption: `Tier 1 · weak-probe · laptop-class`.

```
$ python -m src.scan ./examples/vuln-express-app \
      --events live.ndjson \
      --top-k 5 > leads.jsonl
```

**Doruk (voiceover):**
> "Tier one — `weak-probe`. Gemma 4 E2B, runs on a 2018 laptop. It reads every file. One forward pass per chunk."

*Numbers tick on screen: `files · chunks · elapsed · leads` — replaced at recording time with the real `src/scan.py` counts.*

> "Five suspect spans, ranked. Each one tagged with the CWE class the probe thinks it is. Sub-millisecond overhead per token."

### 4b — The 4-panel dashboard (1:30–1:55)

**Visual:** cut to the live HF Space at `peaktwilight/gemma4ge`. Browser chrome visible for half a beat — judges should see this is a real Space. Then full-screen the dashboard. Caption: `huggingface.co/spaces/peaktwilight/gemma4ge`.

```
   ┌─ Stream ─┐  ┌─ Scan ─┐  ┌─ Leads ─┐  ┌─ Hand-off ─┐
```

*Panel 1 streams Gemma tokens. Panel 2 ticks scan progress (files / chunks / elapsed). Panel 3 stacks ranked leads with file + line range + CWE. Panel 4 shows the pwnkit hand-off card with live links to the merged PRs #371 and #372.*

**Doruk (voiceover):**
> "The same scan, in pictures, served from a Hugging Face Space. Left to right: Gemma streaming, scan progress, ranked leads, and the hand-off to Tier two. Clicking the hand-off card opens the two pwnkit pull requests we merged this week — three-seventy-one wires the lead schema, three-seventy-two wires the live event stream. Open source, both sides."

### 4c — Tier 2: big Gemma audits the same repo (1:55–2:15)

**Visual:** cut back to terminal, a *second* pane. Caption: `Tier 2 · Gemma 4 27B via Ollama · same laptop`.

```
$ pwnkit-cli review examples/vuln-express-app \
      --seed-findings examples/leads.jsonl \
      --runtime ollama --model gemma4:latest
```

**Doruk (voiceover):**
> "Tier two. The leads become my pwnkit agent's worklist. With `--runtime ollama`, the agent loop drives Gemma 4 27B locally — same family, bigger sibling. We ran this end-to-end today: six seeded leads, six attack plans, five minutes of real local Gemma inference. The plumbing works — repo to probe to agent to verdict, no cloud."

*Cut to the agent's run summary rendered on screen, side by side with the dashboard's Hand-off panel updating:*

```
   loaded 6 seed lead(s) · totalAttacks: 6 · runtime: ollama (gemma4:latest)
   elapsed ~5 min · all-local · zero network egress
```

**Doruk:**
> "Two Gemmas — small and large, same family — agreeing on where to look. End to end on one laptop."

---

## Beat 5 — Why this matters (2:15–2:40)

**Visual:** Efe and Doruk both on camera, side by side at the desk. Caption strip across the bottom: `40 pts Impact · 30 pts Story · 30 pts Tech`.

**Efe:**
> "Both tiers run on the same laptop. Nothing leaves the device. The probe runs on basically anything. The 27B verifier needs a real GPU or an M-series Mac with thirty-two gigs — same hardware that runs Stable Diffusion. Training data includes Doruk's disclosed CVEs in `node-forge` and ten other npm packages with two hundred million downloads a month — author-grounded, not synthetic."

**Doruk:**
> "And that's the part we care about. The people most exposed to AI-generated vulnerabilities — solo maintainers of packages with millions of installs, students, developers in places where Snyk pricing isn't an option — are the ones who can't pipe their code through a cloud API to find out. With two Gemmas locally, they don't have to."

---

## Beat 6 — Close (2:40–2:50)

**Visual:** title card.

```
   GemmaForge
   Local. Free. Apache-2.0.
   github.com/peaktwilight/gemmaforge
   huggingface.co/spaces/peaktwilight/gemma4ge
```

**Doruk and Efe (together, voiceover):**
> "Every developer should have a senior security engineer that runs on their laptop, on every commit, for free. We just built one. It's open. Go audit something."

---

## Production notes
- Record 4K, export 1080p high bitrate — judges' screens vary
- All demo runs use locally-running Gemma 4 (E2B/E4B for Tier 1, 27B via Ollama for Tier 2) so on-screen rendering is fluid
- Background music: subtle synth, low under voiceover; drop out during 4a/4b/4c so typing + dashboard motion are the audio
- Cut zero "uhh"s — script is ~430 words, fits comfortably inside 2:50 at a calm pace
- Both faces on camera before 1:05 — judges reward visible humans early
- **Subtitled-on-mute:** burned-in captions on every beat. Lane/panel headers, tier labels, the AUC numbers in Beat 3, the run-summary numbers in 4c, and the tracks strip in Beat 5 must all be legible without audio.
- **Verification step:** the 4c terminal capture must be a real run of `pwnkit-cli review examples/vuln-express-app --seed-findings examples/leads.jsonl --runtime ollama --model gemma4:latest`. The "loaded 6 seed lead(s)" and "totalAttacks: 6" lines are real output from today's E2E — show them.
- Pwnkit PR links to surface in 4b: [0sec-labs/pwnkit#371](https://github.com/0sec-labs/pwnkit/pull/371) and [0sec-labs/pwnkit#372](https://github.com/0sec-labs/pwnkit/pull/372). Both merged.

---

## Shot list (B-roll + screen-capture)

| Time | Source | Shot |
|------|--------|------|
| 0:00–0:06 | GitHub | CVE-2026-33896 advisory page on `digitalbazaar/forge`, scroll the description |
| 0:06–0:12 | VS Code | Copilot ghost-text completing a vulnerable Express handler, dev hits Tab |
| 0:12–0:18 | After Effects | Title card: "GemmaForge — Small Gemma finds. Big Gemma hunts." |
| 0:18–0:28 | Web | Montage: Copilot completion, Snyk pricing page ($25/dev/mo highlight), CVE detail page — 2x speed |
| 0:28–0:35 | Doruk cam | Lean-in to camera, two-Gemma pitch |
| 0:35–0:50 | Efe cam | Talking head + on-screen diagram of probe shape |
| 0:50–1:05 | Efe cam | Slide with AUC 0.907 / layer 17→10 / 22× robustness numbers burned in |
| 1:05–1:30 | Terminal | `python -m src.scan ./examples/vuln-express-app --events live.ndjson --top-k 5 > leads.jsonl` running, file/chunk counters incrementing, final 5 ranked leads |
| 1:30–1:55 | Browser | HF Space `peaktwilight/gemma4ge` 4-panel dashboard — Stream / Scan / Leads / Hand-off. Cursor clicks Hand-off card; PR #371 and #372 tabs flash open |
| 1:55–2:15 | Terminal (split) | `pwnkit-cli review ... --runtime ollama --model gemma4:latest` running side-by-side with dashboard Hand-off panel updating; final "loaded 6 seed lead(s) · totalAttacks: 6" summary card |
| 2:15–2:40 | Doruk + Efe cam | Two-shot at desk; lower-third with the three judging tracks |
| 2:40–2:50 | After Effects | Closing title card with repo URL + HF Space URL |

