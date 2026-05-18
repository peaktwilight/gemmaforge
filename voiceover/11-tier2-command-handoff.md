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

> "Two commands. First, the little Gemma walks your repo and writes down everything suspicious. Then the big Gemma picks up that list — running right here, on your laptop — and starts hunting. Reads files. Greps. Verifies."
