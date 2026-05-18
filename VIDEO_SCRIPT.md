# Video script — GemmaForge (target: 2:50, hard limit 3:00)

**16 scenes** · each scene = one screen, one idea, one spoken line, one on-screen caption. Subtitles burned in — every scene reads on mute.

## Team
- **Doruk Tan Ozturk** — security researcher, disclosed CVE-2026-33896 and other CVE-grade npm bugs. Builder of pwnkit (Tier 2). On camera: scenes 01, 02, 03, 10, 11, 13, 15, 16.
- **Mehmet Efe Akça** — MSc Data Science at ETH Zürich. Built the probe (Tier 1). On camera: scenes 05, 06, 07, 08, 09, 14, 16.

## Format
- 16 distinct scenes, average ~10s each (range 5–15s).
- Talking head ↔ screen-share alternates; never two talking-head scenes back-to-back.
- Every scene has three layers: **(a)** visual, **(b)** burned-in caption that survives on mute, **(c)** the spoken line.
- Persistent lower-third for all 16 scenes: `gemmaforge · github.com/peaktwilight/gemmaforge`.

## Tracks targeted
- Main · Impact / Safety & Trust · Special Tech / Ollama

---

## Scene 01 — Hook: a real CVE (0:00–0:10, 10s)

**Visual:** slow zoom into the GitHub Security Advisory for CVE-2026-33896 (the node-forge bug). Cursor lingers on "node-forge" and the red "Critical" badge.

**Burned-in caption (top-left, persists 10s):**
```
CVE-2026-33896 · node-forge · Critical
Disclosed March 2026
```

**Doruk (voiceover):**
> "Two months ago I disclosed a critical bug in `node-forge` — a crypto library used across the JavaScript stack."

---

## Scene 02 — Hook: AI just wrote it again (0:10–0:20, 10s)

**Visual:** IDE screen-recording. Copilot autocompletes an Express handler, ending in the unsafe pattern `db.query(\`SELECT * FROM users WHERE id=${req.params.id}\`)`. Developer tab-accepts.

**Burned-in caption (centre, fades in halfway):**
```
AI tools now ship ~100M lines of code per day.
Almost none of it is audited before it ships.
```

**Doruk (voiceover):**
> "An AI assistant could have written that exact pattern this morning. Nobody would have caught it before it shipped."

---

## Scene 03 — Stakes: the scan happens too late, somewhere else (0:20–0:30, 10s)

**Visual:** split screen at 1.5× speed. Left: Snyk pricing page, `$25 / developer / month` highlighted. Right: a SAST dashboard showing "Scan started 3 hours ago…".

**Burned-in caption (bottom):**
```
Cloud-bound · subscription-gated · runs after the fact
Solo maintainers + air-gapped enterprises priced out.
```

**Doruk (voiceover):**
> "The standard answer is to scan in the cloud, after the fact. A lot of devs can't afford it. A lot of orgs can't legally use it."

---

## Scene 04 — The question (0:30–0:38, 8s)

**Visual:** hard cut to a black card. White text appears phrase-by-phrase, typewriter-style. No music yet — silence + a single low pad note.

**On-screen text (sequential reveal, no other caption):**
```
What if the model itself
       could tell you
              which parts of your repo
                     it would file CVEs against?
```

*No spoken line.* The question lands on text alone.

---

## Scene 05 — Title card + Efe intro (0:38–0:50, 12s)

**Visual:** logo card (large), Efe appears on camera in the lower-right third, soft-focus library/desk background.

**Burned-in title (centre):**
```
   GemmaForge
   Small Gemma finds.  Big Gemma hunts.
```

**Burned-in lower-third (sticky 12s):**
```
Mehmet Efe Akça · MSc Data Science, ETH Zürich
```

**Efe (to camera):**
> "We trained a fifteen-hundred-weight linear probe on Gemma 4's hidden states. It tells you which tokens the model is about to write look like the inside of a known CVE."

---

## Scene 06 — Probe in action: small Gemma walks a real repo (0:50–1:05, 15s)

**Visual:** screen-recording of the GemmaForge dashboard. Bottom-left corner shows a terminal running `python -m src.scan examples/vuln-express-app > leads.jsonl`. The dashboard's **Scan** panel fills in real time — files tick by, each rendered as a strip of chunk-tiles that turn yellow / red as the probe scores them. The **Leads** panel populates simultaneously with ranked rows landing one after another, each carrying a CWE badge: `CWE-78 · 0.94`, `CWE-89 · 0.91`, `CWE-338 · 0.89`.

**Burned-in caption (top-right, sticky 15s):**
```
python -m src.scan examples/vuln-express-app  →  leads.jsonl
ranked CWE candidates · Gemma 4 E2B probe · laptop-class
```

**Efe (voiceover):**
> "Point the little Gemma at a real repo. It walks through it chunk by chunk, scoring every span. The risky ones bubble up over here — ranked, and already labelled with the kind of bug they look like."

---

## Scene 07 — Tier 1, the honest headline AUC (1:05–1:15, 10s)

**Visual:** numbers card. The AUC ladder image (`web/auc-ladder.png`) is the background at 30% opacity; one number in the foreground.

**Burned-in text (large, centred):**
```
AUC 0.907   Python → JavaScript
            (train Python, evaluate JavaScript)

0.940 stacked (MLP × 4-layer ensemble)
0.9726 per-CWE macro (78 · 338 · 95 · 94 · 328)
```

**Efe (voiceover):**
> "Cross-language AUC nine-oh-seven. Honest number — train on Python, test on JavaScript."

---

## Scene 08 — Tier 1, structural finding: L17 → L10 (1:15–1:25, 10s)

**Visual:** two side-by-side decoder stacks (slide-deck render). Left: Gemma 4 E2B, 35 layers, L17 highlighted (49% depth). Right: Gemma 4 E4B, 42 layers, **L10** highlighted (24% depth). Red arrow drops 17→10 between them.

**Burned-in caption (bottom):**
```
strong-probe (E4B): best layer drops from L17 / 35 → L10 / 42
The linear vulnerability direction lives EARLIER in the bigger model.
```

**Efe (voiceover):**
> "When we re-trained on the bigger Gemma, the best layer moved from mid-network down into the bottom quarter. Bigger models know what's risky sooner."

---

## Scene 09 — Tier 1, robustness: 22× T3 (1:25–1:35, 10s)

**Visual:** before/after of the same snippet — left, clean source; right, the T3 attack (comments inserted between every statement, indentation perturbed). Beneath both, a sparkline of per-token probe scores.

**Burned-in caption:**
```
Adversarial T1–T5 suite
T3 (comment + reindent), last-token:   Δ −0.087
T3 (comment + reindent), max-pool:     Δ −0.004    ← 22× more robust
```

**Efe (voiceover):**
> "Full T1 through T5 adversarial suite. Max-pool aggregation flattens the worst attack twenty-two times over."

---

## Scene 10 — Tier 2 bridge: Doruk takes back the mic (1:35–1:45, 10s)

**Visual:** cut to Doruk on camera. Soft-focus terminal behind him with `pwnkit-cli --help` output dimly visible.

**Burned-in lower-third (sticky 10s):**
```
Doruk Tan Ozturk · pwnkit · 0sec.ai
```

**Doruk (to camera):**
> "The probe tells you *where* to look. But you still want to *prove* it. That's where the bigger Gemma comes in."

---

## Scene 11 — Handoff: leads flow into pwnkit (1:45–2:00, 15s)

**Visual:** same terminal from Scene 06, still next to the dashboard. The `leads.jsonl` filename pulses briefly to call it out, then the next command types on, character by character:

```bash
$ pwnkit-cli review examples/vuln-express-app \
      --seed-findings leads.jsonl \
      --runtime ollama \
      --model gemma4:27b
```

**Burned-in caption (right side, sticky 15s):**
```
pwnkit consumes gemmaforge.leads/v1
Ollama  /api/chat  +  tools[]   ·   Gemma 4 27B locally
0sec-labs/pwnkit  #371 + #372  (merged)
```

**Doruk (voiceover):**
> "Now we hand those leads to pwnkit. One command. It picks up where the probe left off — and fires up the big Gemma, right here on the laptop, to actually go and prove every one of them."

---

## Scene 12 — Big Gemma at work: pwnkit drives the agent (2:00–2:15, 15s)

**Visual:** the dashboard's **Hand-off to pwnkit** panel fills in real time. Tool-call cards land one after another:
- `read_file src/users.js`
- `grep -n "db.query"`
- `read_file src/ping.js`
- `verify — string interpolation reaches sink`

Then a verdict card lands with a green stroke: `CWE-89 · CONFIRMED · sql-injection at users.js:31`. Mouse hovers a row in the Leads panel and clicks; the matching investigation card glows.

**Burned-in caption (bottom, sticky 15s):**
```
Gemma 4 27B  via  Ollama   ·   live tool-calls
click-to-highlight  lead → investigation provenance
```

**Doruk (voiceover):**
> "And now you watch the big Gemma go to work. It opens the actual file. Greps the call sites. Builds a case. Every lead the probe found is something it can dig into and verify — right here, on the same laptop."

---

## Scene 13 — The real run (2:15–2:25, 10s)

**Visual:** terminal output, clean monospace, key lines highlighted with a yellow stroke as they appear:

```
$ pwnkit-cli review examples/vuln-express-app \
      --seed-findings examples/leads.jsonl \
      --runtime ollama --model gemma4:latest

[review] loaded 6 seed lead(s) from examples/leads.jsonl
…
{ "totalAttacks": 6, "durationMs": 289969, "semgrepFindings": 6 }
```

**Burned-in caption (top, sticky 10s):**
```
6 leads → 6 investigations   ·   ~5 minutes
local Gemma 4 inference   ·   zero network   ·   receipts in stdout
```

**Doruk (voiceover):**
> "And this isn't a mockup. We ran the whole thing today — small Gemma, big Gemma, six leads, six investigations. Five minutes of real local inference. The whole pipeline never touched a cloud."

**Burned-in caption (top):**
```
6 leads → 6 attacks · ~5 minutes · local · zero network
Real run.  Today.  On a laptop.
```

**Doruk (voiceover):**
> "This isn't a render. Six seeded leads, six investigations, five minutes of local Gemma 4 inference. Nothing left the machine."

---

## Scene 14 — Why Gemma specifically (2:25–2:35, 10s)

**Visual:** three model tiles animate left-to-right onto the screen:

```
┌──────────┐    ┌──────────┐    ┌──────────────────┐
│  E2B 2B  │ →  │  E4B 4B  │ →  │  Gemma 4 27B     │
│  probe   │    │  probe+  │    │  agentic verifier│
│  laptop  │    │  workstn │    │  workstation     │
└──────────┘    └──────────┘    └──────────────────┘
```

**Burned-in caption:**
```
Same family · same tokenizer · same tool schema · one license
Raw hidden states for Tier 1.   Native function-calling for Tier 2.
Only Gemma 4 gives you both.
```

**Efe (voiceover):**
> "Three Gemmas in one family. Hidden states for the probe, function-calling for the agent. Mix Llama with Qwen and the two halves don't speak the same language."

---

## Scene 15 — Why us: author-grounded training data (2:35–2:45, 10s)

**Visual:** scrolling reel of GitHub Security Advisory cards — CVE-2026-33896 first, then a quick stack of ~5 more advisory titles authored by Doruk. A small badge lands at the end: `200M+ monthly downloads across affected packages`.

**Burned-in caption:**
```
Training pairs include CVEs Doruk personally disclosed.
node-forge · plus ~10 more in npm packages totalling 200M+ DL/mo.
```

**Doruk (voiceover):**
> "The probe was trained partly on bugs we ourselves found and disclosed. That's why it knows what danger smells like."

---

## Scene 16 — Close (2:45–2:50, 5s)

**Visual:** both Doruk and Efe on camera, split screen. End card behind them.

**Burned-in end card:**
```
   GemmaForge — Two Gemmas, one laptop.

   Repo:    github.com/peaktwilight/gemmaforge
   Live:    huggingface.co/spaces/peaktwilight/gemma4ge
   pwnkit:  github.com/0sec-labs/pwnkit  (PR #371, #372)

   Tracks:  Main · Safety & Trust · Ollama
```

**Doruk + Efe (in unison, to camera):**
> "Local. Open. Verifiable."

---

## Timing summary

| # | Scene | Start | Duration |
|---|---|---:|---:|
| 01 | Hook: CVE | 0:00 | 10s |
| 02 | Hook: AI just wrote it again | 0:10 | 10s |
| 03 | Stakes: priced out / cloud-bound | 0:20 | 10s |
| 04 | The question (black card) | 0:30 | 8s |
| 05 | Title + Efe intro | 0:38 | 12s |
| 06 | Tier 1 live (streaming probe) | 0:50 | 15s |
| 07 | Tier 1 numbers (AUC 0.907) | 1:05 | 10s |
| 08 | Tier 1 structural (L17→L10) | 1:15 | 10s |
| 09 | Tier 1 robustness (22× T3) | 1:25 | 10s |
| 10 | Bridge: Doruk takes mic | 1:35 | 10s |
| 11 | Tier 2 command (handoff) | 1:45 | 15s |
| 12 | Tier 2 dashboard (4 panels) | 2:00 | 15s |
| 13 | Tier 2 real run (today's output) | 2:15 | 10s |
| 14 | Why Gemma (model family) | 2:25 | 10s |
| 15 | Why us (CVE-grounded data) | 2:35 | 10s |
| 16 | Close | 2:45 | 5s |
| | **Total** | | **2:50** |

10-second buffer to the 3:00 hard limit.

---

## Shot list (B-roll + screen-capture)

| # | Asset | Source |
|---|---|---|
| 01 | CVE-2026-33896 advisory page | `github.com/digitalbazaar/forge/security/advisories` |
| 02 | Copilot autocomplete writing `db.query(\`… ${id}\`)` | Record in VS Code on a clean Express scaffold |
| 03a | Snyk pricing page (`$25/dev/mo` highlighted) | `snyk.io/plans` |
| 03b | "Cloud SAST 3h ago" mock | Mock screenshot, generic SAST UI |
| 06 | Streaming probe demo | `python -m src.stream_with_probe --serve` OR the HF Space directly |
| 07 | AUC ladder background | `web/auc-ladder.png` (already in repo) |
| 08 | E2B / E4B decoder-stack diagram (L17 → L10) | Render new — Keynote/Figma, two columns of blocks + red arrow |
| 09 | T3 before/after + sparkline | Render new from `data/adversarial_full_suite.json` |
| 11 | Terminal: scan + pwnkit review | Record in iTerm, clean prompt (`PS1='$ '`), font ≥ 18pt |
| 12 | 4-panel dashboard, live | `huggingface.co/spaces/peaktwilight/gemma4ge` (Docker SDK build) |
| 13 | Terminal: real E2E output | Replay `/tmp/e2e-ollama.log` from today's run |
| 14 | Three-tile model-family diagram | Render new — Keynote/Figma |
| 15 | GHSA advisory reel | Pull from Doruk's GitHub security advisory list |
| 16 | End card | Render new — repo + HF + pwnkit URLs + 3-track lower-third |

---

## Notes for the editor

- **Subtitles on by default.** Median consumption is YouTube on mute; every scene's caption is load-bearing.
- **No music under spoken lines.** Soft pad only under scene 04 (the question lands on text alone) and scene 16 (close).
- **Pacing rule:** if a scene runs long, shorten the *spoken* line first — never the on-screen caption. Caption survives mute; voiceover doesn't.
- **Hard cuts between scenes 01→02, 03→04, 04→05, 09→10, 13→14, 15→16.** Everywhere else, 200–400 ms crossfade.
- **Lower-third URL persists all 16 scenes.** It's the one thing a paused screenshot must always carry.
