# Scene 06 — Tier 1, live: the probe colours every token

**Speaker:** Efe (voiceover) · **Target:** 15s · **Position:** 0:50–1:05

**On screen while you read:** screen-recording of the HF Space (`peaktwilight/gemma4ge`) or `python -m src.stream_with_probe --serve`. Gemma 4 is streaming an Express handler; tokens fade green → yellow → red as the probe scores them. A red cluster flares around `${req.params.id}`. Top-right caption sticks for the whole 15s: *"< 1 ms / token overhead · Gemma 4 E2B · sample-level linear probe · layer 17"*.

## Line

> "Watch this. As Gemma writes, every token gets a colour. Green when it's safe. Yellow when it's getting iffy. Red when it's about to ship a bug. Live. On a laptop. No cloud."
