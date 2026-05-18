# Video script — GemmaForge (target: 2:50, hard limit 3:00)

## Team
- **Doruk Tan Ozturk** — security researcher, 4 published CVEs in npm. Opens with the CVE hook, voiceovers the demo.
- **Mehmet Efe Akça** — MSc Data Science at ETH Zürich, coursework in Reliable and Trustworthy AI. Carries the interpretability bridge.

## Format
- Talking head + screen-share, alternating
- Doruk on camera for hook + demo voiceover
- Efe on camera for the interpretability bridge
- Both on camera at the close
- Subtitles burned in (judges may watch muted)

---

## Beat 1 — Hook (0:00–0:18)

*B-roll behind opening line: the actual CVE-2026-33896 advisory page on GitHub, ~2s, then the npm download counter ticking up on node-forge.*

**Visual:** Doruk on camera, sitting at desk. Code editor barely visible behind him.

**Doruk (to camera):**
> "Two months ago I published CVE-2026-33896 — a certificate-forgery bug in node-forge, an npm package with 33 million weekly downloads. I find bugs like that for a living. But here is what bothers me: an AI assistant could have written that exact pattern this morning, and nobody would have caught it until it shipped."

**Cut to:** title card. White on black:

```
   GemmaForge
   Real-time vulnerability detection
   inside Gemma 4
```

---

## Beat 2 — The twist (0:18–0:35)

*Visual: quick montage — Copilot autocompleting an Express handler, a developer tab-accepting the suggestion, a CVE detail page. Speed up 2x.*

**Doruk (voiceover):**
> "Every IDE has an AI in it now. They ship hundreds of millions of lines a day, and a non-trivial slice is vulnerable. The standard answer is: scan it afterwards. But by then the model has already shown the developer something insecure — and most of them paste before the scanner ever runs."

*Cut to Doruk on camera, leaning in.*

**Doruk:**
> "So we asked a different question. What if the model itself could tell you it is about to write vulnerable code — before the first risky token?"

---

## Beat 3 — The bridge (0:35–1:05)

**Visual:** Efe on camera. Whiteboard or simple diagram visible behind him.

**Efe (to camera):**
> "I am Efe — I do MSc Data Science at ETH, and one of my courses is Reliable and Trustworthy AI. Last year there was a result from ETH and Anthropic's MATS program: a tiny linear classifier, trained on a model's hidden states, can detect hallucinations in real time at near-zero cost. AUC around 0.9. We adapted that idea — same probe, different signal. Instead of hallucinations, we trained it on vulnerability likelihood, on Gemma 4's hidden states."

**Visual cut:** simple diagram appears next to him.

```
Gemma 4 hidden state ── linear probe ── risk score
  (2,560 numbers)       (~10 KB)        (0..1)
```

**Efe:**
> "Twenty-five hundred numbers in, one risk score out. The probe is smaller than a JPEG. It runs in the same forward pass as the model — you pay nothing for it."

---

## Beat 4 — The demo (1:05–2:15) — THE MONEY SHOT

**Visual:** Full-screen screen capture of the GemmaForge web UI on a clean dark background. Cursor poised over the preset list. No talking head.

**Doruk (voiceover):**
> "One click. SQL injection preset. Gemma 4 is going to write an Express handler."

*Click. Tokens stream in. Boilerplate is green. Risk meter on the right stays low.*

> "Watch the meter."

*The moment Gemma writes ``return db.query(`SELECT * FROM users WHERE id=${id}`)``, the meter swings hard right, the tokens light up red, peak-risk jumps to 91%.*

> "There. The probe fired the moment Gemma decided to interpolate a user-controlled id into a SQL string — before the closing backtick was even emitted. It does not see the SQL. It sees the shape of Gemma's internal state that produces this kind of SQL."

*Cut. Click second preset: path traversal.*

> "Path traversal."

*Tokens stream. The moment `fs.readFileSync('/var/data/' + filename` appears, red.*

*Cut. Click third: weak randomness.*

> "Math.random instead of crypto.randomBytes."

*Red.*

*Cut. Type custom prompt: "Now write the SAME endpoint safely with parameterized queries."*

> "And when we ask Gemma to write the same endpoint safely —"

*Tokens stream. Green throughout. Peak risk: 8%.*

> "Eight percent. Same model, same prompt skeleton, different internal state. The probe sees it."

---

## Beat 5 — Why this matters (2:15–2:40)

**Visual:** Efe and Doruk both on camera, side by side at the desk.

**Efe:**
> "This runs entirely on the laptop. Gemma 4 local, probe local. Nothing leaves the device."

**Doruk:**
> "And that is the part we care about. The people most exposed to AI-generated vulnerabilities — solo maintainers, students, developers in regions where a Snyk seat is a month of rent — are the people who cannot pipe pre-disclosure code through a cloud API. With Gemma 4, they do not have to. The whole thing fits on a thumb drive."

---

## Beat 6 — Close (2:40–2:50)

**Visual:** title card.

```
   GemmaForge
   Local. Free. Apache-2.0.
   github.com/peaktwilight/gemmaforge
```

**Doruk and Efe (together, voiceover):**
> "Thanks for watching."

---

## Production notes
- Record 4K, export 1080p with high bitrate — judges' screens will vary
- All demo runs use the local Gemma 4 model so on-screen rendering is fluid
- Background music: subtle synth, low under voiceover, drop out during demo so the typing/probe-flash is the audio
- Cut zero "uhh" — script is ~330 words, fits cleanly inside 2:50 at a calm pace
- B-roll: CVE-2026-33896 advisory page (2s) + node-forge npm download counter behind the opening line
- Both faces on camera before 1:05 — judges reward visible humans early
