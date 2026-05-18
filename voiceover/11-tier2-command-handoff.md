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

> "Two commands. The probe walks the repo and writes the leads. Pwnkit picks them up and drives a local Gemma 4 27B through tool-calls — read files, grep call sites, verify."

## Pacing

*This is the dense one — three concrete things in the second half of the line ("read files, grep call sites, verify") and the viewer's eye is also tracking commands on screen. Read deliberately. "Two commands" is the opening hook — pause briefly after it so the first command finishes typing. The list at the end ("read files, grep call sites, verify") gets a small beat between each.*
