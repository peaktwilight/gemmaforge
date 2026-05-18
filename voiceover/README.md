# Voiceover scripts — one per scene

16 files, one per scene of `VIDEO_SCRIPT.md`. Each file is **mic-ready**: open it, read the line, hit target duration. Nothing else.

## Recording order

The natural order is 01 → 16, but speakers can record in any order and the editor stitches.

| Scene | File | Speaker | Target |
|---:|---|---|---:|
| 01 | [`01-hook-cve.md`](01-hook-cve.md) | Doruk (voiceover) | 10s |
| 02 | [`02-ai-just-wrote-it.md`](02-ai-just-wrote-it.md) | Doruk (voiceover) | 10s |
| 03 | [`03-stakes-priced-out.md`](03-stakes-priced-out.md) | Doruk (voiceover) | 10s |
| 04 | [`04-the-question-silence.md`](04-the-question-silence.md) | — (silence) | 8s |
| 05 | [`05-title-efe-intro.md`](05-title-efe-intro.md) | Efe (to camera) | 12s |
| 06 | [`06-tier1-live-demo.md`](06-tier1-live-demo.md) | Efe (voiceover) | 15s |
| 07 | [`07-tier1-auc-headline.md`](07-tier1-auc-headline.md) | Efe (voiceover) | 10s |
| 08 | [`08-tier1-structural-finding.md`](08-tier1-structural-finding.md) | Efe (voiceover) | 10s |
| 09 | [`09-tier1-robustness.md`](09-tier1-robustness.md) | Efe (voiceover) | 10s |
| 10 | [`10-bridge-doruk-takes-mic.md`](10-bridge-doruk-takes-mic.md) | Doruk (to camera) | 10s |
| 11 | [`11-tier2-command-handoff.md`](11-tier2-command-handoff.md) | Doruk (voiceover) | 15s |
| 12 | [`12-tier2-dashboard.md`](12-tier2-dashboard.md) | Doruk (voiceover) | 15s |
| 13 | [`13-tier2-real-run.md`](13-tier2-real-run.md) | Doruk (voiceover) | 10s |
| 14 | [`14-why-gemma-family.md`](14-why-gemma-family.md) | Efe (voiceover) | 10s |
| 15 | [`15-author-grounded-data.md`](15-author-grounded-data.md) | Doruk (voiceover) | 10s |
| 16 | [`16-close.md`](16-close.md) | Doruk + Efe (in unison) | 5s |
| | **Total** | | **2:50** |

## How to use each file

Each scene file has:

1. **Header** — scene number, target seconds, who reads it, position in the video.
2. **What's on screen while you read** — one sentence so you know the tone.
3. **The line** — in a blockquote, with inline `[bracketed]` cues for the speaker and the editor (legend below). Read at the pace that lands inside the target window; if you can't, shorten the *line* (not the on-screen caption — that's in `VIDEO_SCRIPT.md` and the editor needs it intact).
4. **Tone** — one sentence on delivery (eye-line, mood) where the inline cues don't capture it.

## Inline cue legend

The same `[brackets]` work for both speaker and editor — read them as performance / cut directions, not aloud.

**Speaker cues (timing + delivery):**
- `[pause]` — short breath, ≈ 0.3 s
- `[beat]` — longer pause, ≈ 0.7 s
- `[stress]` — emphasise the next word
- `[slow]` / `[normal]` — tempo shift, applies until reset
- `[flat]` — deliver matter-of-fact, no lift
- `[soft]` — drop the volume one notch

**Editor cues (visuals + sync):**
- `[caption-in: …]` — burned-in caption fades in *now*
- `[caption-out]` — caption fades out
- `[cursor-click]` — mouse-click on screen
- `[badge-land]` — small badge animates onto frame
- `[type-in: "…"]` — text appears typewriter-style
- `[zoom-in]` / `[zoom-out]` — push or pull on the live frame
- `[cut]` — hard cut at this exact word

Backticks are literal — read what's inside as the word(s) on the page.

## Recording tips

- Read each line **twice in a row** — one safety take.
- Leave **2 seconds of room tone** at the end of every clip so the editor can crossfade.
- Camera scenes (05, 10, 16): eye-line into the lens, not the monitor.
- For ad-lib tightening, the editor prefers a slightly faster read to a clipped one — pace, don't rush.
