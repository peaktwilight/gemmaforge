# Scene 11 — Handoff: leads flow into pwnkit

**Speaker:** Doruk (voiceover) · **Target:** 15s · **Position:** 1:45–2:00

**On screen while you read:** the same terminal from Scene 06. The `leads.jsonl` file from the probe is briefly highlighted, then the next command types on, character by character:

```
$ pwnkit-cli review examples/vuln-express-app \
      --seed-findings leads.jsonl \
      --runtime ollama \
      --model gemma4:latest
```

Right-side caption sticks for the full 15 s: *"pwnkit consumes gemmaforge.leads/v1 · Ollama /api/chat with tools[] · Gemma 4 8B locally · 0sec-labs/pwnkit #371 + #372 (merged)"*.

## Line

> "Now we hand those leads to pwnkit. One command. It picks up where the probe left off — and fires up the big Gemma, right here on the laptop, to actually go and prove every one of them."
