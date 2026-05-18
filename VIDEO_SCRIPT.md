# Video script — GemmaForge (target: 2:50, hard limit 3:00)

## Team
- **Doruk Tan Ozturk** — security researcher, disclosed CVE-2026-33896 and other CVE-grade npm bugs. Builder of pwnkit (Tier 2). Opens with the CVE hook, voiceovers the demo.
- **Mehmet Efe Akça** — MSc Data Science at ETH Zürich. Built the probe (Tier 1). Carries the interpretability bridge.

## Format
- Talking head + screen-share, alternating
- Doruk on camera for hook + demo voiceover
- Efe on camera for the interpretability bridge
- Both on camera at the close
- Subtitles burned in (judges may watch muted)

---

## Beat 1 — Hook (0:00–0:18)

*B-roll behind the opening line: the actual CVE-2026-33896 advisory page on GitHub, ~2s, then the `node-forge` repo's `package.json` showing it's used as a dependency by widely-deployed crypto stacks.*

**Visual:** Doruk on camera, sitting at desk. Code editor barely visible behind him.

**Doruk (to camera):**
> "Two months ago I published CVE-2026-33896 in `node-forge` — a crypto library that ships inside a lot of the JavaScript stack you've used today. I find bugs like this for a living. But here's what bothers me: an AI assistant could have written that exact pattern this morning, and nobody would have caught it before it shipped."

**Cut to:** title card. White on black:

```
   GemmaForge
   Two Gemmas, one laptop.
   Local repo-wide vulnerability auditing.
```

---

## Beat 2 — The twist (0:18–0:35)

*Visual: quick montage — Copilot autocompleting an Express handler, a developer tab-accepting the suggestion, a CVE detail page. Speed up 2x.*

**Doruk (voiceover):**
> "Every IDE has an AI in it now. They write a lot of the code that ships. The standard answer is: scan it afterwards. With Snyk. With Semgrep. With something cloud-bound that costs $200 a seat. Maintainers of open packages — the people whose bugs *I* keep finding — usually don't have that."

*Cut to Doruk on camera, leaning in.*

**Doruk:**
> "So we built something different. A two-tier auditor that runs entirely on your laptop. Small Gemma reads your whole repo and triages it. Big Gemma verifies the hits. Same model family, no cloud, free."

---

## Beat 3 — The bridge (0:35–1:05)

**Visual:** Efe on camera. Whiteboard or simple diagram visible behind him.

**Efe (to camera):**
> "I'm Efe — I do MSc Data Science at ETH, one of my courses is Reliable and Trustworthy AI. Last year there was a result from ETH and Anthropic's MATS program: a tiny linear classifier on a model's hidden states can detect hallucinations in real time. AUC around 0.9. We adapted that — same probe shape, different signal. We trained it on Gemma 4 E2B's hidden states to predict *vulnerability likelihood* and *which CWE class* the code looks like."

**Visual cut:** simple diagram appears next to him.

```
Gemma 4 E2B hidden state ── linear probe ── risk score + CWE
   (~1,500 numbers)         (~10 KB)
```

**Efe:**
> "The probe is smaller than a JPEG. Inference is one extra dot product per chunk. Cross-language AUC zero-point-nine-oh-seven — train on Python, evaluate on JavaScript, still works. The signal lives in the hidden state. We ship two variants — `weak-probe` on a small Gemma for laptops, `strong-probe` on a larger Gemma for workstations. Same scan tool, same lead schema."

---

## Beat 4 — The demo (1:05–2:15) — THE MONEY SHOT

*Beat 4 has three crisp sub-cuts. Total ~70 seconds, hard cap.*

### 4a — Tier 1: scan the whole repo (1:05–1:30)

**Visual:** terminal, dark background, large font. A clean example Express app open on the side.

```
$ python -m src.scan ./example-app \
      --events live.ndjson \
      --top-k 5 > leads.jsonl
```

**Doruk (voiceover):**
> "Tier one — `weak-probe`. A small Gemma, two billion parameters, runs on a 2018 laptop. It reads every file. One forward pass per chunk."

*Numbers tick: `files: ⟨N⟩ · chunks: ⟨M⟩ · elapsed: ⟨T⟩ · leads: ⟨K⟩` — replaced at recording time with the real `src/scan.py` counts on the demo repo.*

> "Five suspect spans, ranked. Each one tagged with the CWE class the probe thinks it is."

### 4b — The /live dashboard (1:30–1:55)

**Visual:** cut to the pwnkit `/live` dashboard. Three lanes, headers burned-in as on-screen text:

```
   ┌─ Lane 1 · Probe ─┐  ┌─ Lane 2 · Leads ─┐  ┌─ Lane 3 · Hunt ─┐
```

*Lane 1 streams probe.alarm events as they arrive. Lane 2 stacks the leads with file + line range + CWE. Lane 3 streams agent findings live (pwnkit#372 wired this up). Clicking a finding highlights the originating probe lead in Lane 2.*

**Doruk (voiceover):**
> "The same scan in pictures. Left lane: the probe firing on internal hidden states. Middle lane: the leads that crossed threshold. Right lane: the big-Gemma agent's verdicts as they land. Click any verdict — it lights up the probe lead that produced it. Two Gemmas, one screen, full provenance."

### 4c — Tier 2: big Gemma audits the same repo (1:55–2:15)

**Visual:** cut back to the terminal, a *second* pane this time:

```
$ pwnkit review ./example-app \
      --seed-findings leads.jsonl \
      --seed-only \
      --runtime ollama
```

**Doruk (voiceover):**
> "Tier two. The leads become my pwnkit agent's worklist. With `--runtime ollama`, the agent loop drives **Gemma 4 27B** — same family, bigger sibling — running locally through Ollama with native streaming function calls. For every lead, it reads the file, greps for call sites, and writes a verdict. Confirmed bugs surface; false positives get rejected."

*Cut to one of the agent's findings rendered as a card, with the matching lead visible underneath:*

```
   ▶ src/router.js:38–52  CWE-89 (SQL injection)
     verdict: confirmed
     evidence: req.params.id interpolated into a tagged-template SQL string,
               no parameterised execute, no input validation upstream
     mitigation: use db.prepare(...) with bound parameters

   ── matched probe lead ──
   confidence 0.93 · top_cwe CWE-89 · rank 0
```

**Doruk:**
> "The agent's verdict matches the probe's top lead. Two Gemmas — small and large, same family — agreeing on where the bug is. End to end on one laptop, in about a minute."

---

## Beat 5 — Why this matters (2:15–2:40)

**Visual:** Efe and Doruk both on camera, side by side at the desk.

**Efe:**
> "Both tiers run on the same laptop. Nothing leaves the device. Probe runs on basically anything. The 27B verifier needs a real GPU or an M-series Mac with thirty-two gigs — same hardware that runs Stable Diffusion."

**Doruk:**
> "And that's the part we care about. The people most exposed to AI-generated vulnerabilities — solo maintainers of packages with millions of installs, students, developers in places where Snyk pricing isn't an option — are the people who can't pipe their code through a cloud API to find out. With two Gemmas locally, they don't have to."

---

## Beat 6 — Close (2:40–2:50)

**Visual:** title card.

```
   GemmaForge
   Local. Free. Apache-2.0.
   github.com/peaktwilight/gemmaforge
```

**Doruk and Efe (together, voiceover):**
> "Every developer should have a senior security engineer that runs on their laptop, on every commit, for free. We just built one. It's open. Go audit something."

---

## Production notes
- Record 4K, export 1080p with high bitrate — judges' screens vary
- All demo runs use locally-running Gemma 4 (E2B for Tier 1, 27B via Ollama for Tier 2) so on-screen rendering is fluid
- Background music: subtle synth, low under voiceover; drop out during 4a/4b/4c so the typing + dashboard motion are the audio
- Cut zero "uhh"s — script is ~370 words, fits comfortably inside 2:50 at a calm pace
- B-roll: CVE-2026-33896 advisory page (2s) behind the opening line
- Both faces on camera before 1:05 — judges reward visible humans early
- Burned-in subtitles for the lane headers (Lane 1/2/3) and the agent verdict card — judges may watch muted
- **Verification step:** Lane 3 is live-wired in pwnkit#372 — record a real run of `pwnkit review` against the demo repo so the agent's verdicts actually stream into the Hunt lane. If the agent rejects a probe lead (false-positive), show it — that demonstrates Tier 2 doing its job.
