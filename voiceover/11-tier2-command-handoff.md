# Scene 11 — Tier 2, the command: handoff

**Speaker:** Doruk (voiceover) · **Target:** 15s · **Position:** 1:45–2:00

**On screen while you read:** terminal recording, type-on at human speed, no autocomplete noise. First a small block:

```
$ python -m src.scan repo/ > leads.jsonl
```

then the bigger one:

```
$ pwnkit-cli review repo/ \
      --seed-findings leads.jsonl \
      --runtime ollama \
      --model gemma4:27b
```

Right-side caption sticks for all 15s: *"Ollama · /api/chat · native function-calling · 0sec-labs/pwnkit #371 + #372 (both merged 2026-05-18) · Local · no API keys · no network"*.

## Line

> "[stress] Two commands. [beat — first command finishes typing on screen] The probe walks the repo and writes the leads. [type-in: `pwnkit-cli review repo/ ...`] [pause] Pwnkit picks them up and drives a local Gemma 4 27B through tool-calls — [pause] read files, [pause] grep call sites, [pause] verify."

## Tone

Densest line of the video — viewer's eye is also reading commands on screen. Pace yourself with the on-screen typing; don't outrun the keystrokes. The closing list ("read files / grep call sites / verify") gets a small beat between each item.
