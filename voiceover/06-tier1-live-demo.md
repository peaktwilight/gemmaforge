# Scene 06 — Probe in action: small Gemma walks a real repo

**Speaker:** Efe (voiceover) · **Target:** 15s · **Position:** 0:50–1:05

**On screen while you read:** the GemmaForge dashboard. Bottom-left, a terminal runs `python -m src.scan examples/vuln-express-app > leads.jsonl`. The dashboard's **Scan** panel fills in real time — files tick across, each one shown as a strip of chunk-tiles that turn yellow / red as the probe scores them. As the scan progresses, the **Leads** panel populates with ranked rows; the top entry lands with a badge `CWE-78 · 0.94`, then `CWE-89 · 0.91`, then `CWE-338 · 0.89`. Top-right caption sticks: *"python -m src.scan examples/vuln-express-app → leads.jsonl · ranked CWE candidates · Gemma 4 E2B"*.

## Line

> "Point the little Gemma at a real repo. It walks through it chunk by chunk, scoring every span. The risky ones bubble up over here — ranked, and already labelled with the kind of bug they look like."
