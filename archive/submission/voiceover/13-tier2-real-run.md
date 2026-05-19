# Scene 13 — The real run

**Speaker:** Doruk (voiceover) · **Target:** 10s · **Position:** 2:15–2:25

**On screen while you read:** terminal output, clean monospace, key lines highlighted with a yellow stroke as they appear:

```
$ pwnkit-cli review examples/vuln-express-app \
      --seed-findings examples/leads.jsonl \
      --runtime ollama --model gemma4:latest

[review] loaded 6 seed lead(s) from examples/leads.jsonl
…
{ "totalAttacks": 6, "durationMs": 289969, "semgrepFindings": 6 }
```

Top caption: *"6 leads → 6 investigations · ~5 minutes of local Gemma 4 inference · zero network · receipts in stdout"*.

## Line

> "And this isn't a mockup. We ran the whole thing today — small Gemma, big Gemma, six leads, six investigations. Five minutes of real local inference. The whole pipeline never touched a cloud."
