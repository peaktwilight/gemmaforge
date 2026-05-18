# Iteration Goals — Hackathon Submission Alignment (v2, two-tier framing)

This file defines what "good enough to ship" means for the submission. The write/critique/refine loop runs until every goal in §1–§3 is met, or remaining gaps are explicitly accepted in §4.

## §0 — The pitch, locked

GemmaForge is a **two-tier, fully-local vulnerability auditing pipeline** built on the Gemma 4 family:

1. **Tier 1 — Small Gemma probe (`Gemma 4 E2B`, ~2B params).** A linear probe on the model's hidden state at layer 17 scores every chunk of a repo for vulnerability likelihood and the most likely CWE class. One forward pass per chunk, runs on any laptop. Output: ranked leads JSONL (`gemmaforge.leads/v1` schema).
   - Shipped: `src/scan.py`, `data/probe.npz`, `data/probe_per_cwe.npz`.
   - Headline number: **AUC 0.907 cross-language (Py→JS)**, **macro AUC 0.9726** across 5 CWE heads.

2. **Tier 2 — Big Gemma agent verifier (`Gemma 4 27B` via Ollama).** Takes the JSONL leads, drives an agentic tool loop (`pwnkit review --seed-findings leads.jsonl --runtime ollama`) to certify each lead with tool use (`read_file`, `grep_repo`, etc.). Outputs structured per-finding verdicts.
   - Shipped: **pwnkit PR #371 — merged 2026-05-18 17:10 UTC.** Adds `--seed-findings <path|->` (consumes our `gemmaforge.leads/v1` JSONL), `--runtime ollama` (drives `Gemma 4:27b` via `/api/chat` with `tools[]`), and a `/live` dashboard view (Probe / Lead / Hunt lanes via SSE).
   - **The consumer-side code is in `0sec-labs/pwnkit`. We will reference it in the writeup. The video can show the live dashboard.**

3. **Live dashboard.** SSE-driven `/live` route in the pwnkit dashboard, fed by `gemmaforge.events/v1` ND-JSON from `src/scan.py --events …` and `src/stream_with_probe.py --events …`. Three lanes: probe scoring tokens (left), leads emerging (middle), agent hunt (right). Click-to-highlight provenance from lead → originating `probe.alarm`.

4. **Local-only, free, Apache-2.0.** Nothing leaves the laptop. User picks model size by hardware: probe alone on a 2018 MacBook, full 27B verifier on an RTX 4090 or M-series Mac with 32GB+.

5. **Author-grounded.** Training data includes the patterns from CVEs Doruk personally disclosed, including `CVE-2026-33896` (`node-forge`, 33M weekly downloads).

## §1 — Impact & Vision (40 pts) goals

The video + writeup must, by themselves, make a non-technical judge feel:

- **G1.1 The problem is urgent and real.** Stakes named concretely (CVE-2026-33896, 200M+ DL/mo across Doruk's CVEs, AI-generated code shipping daily). Solo maintainers + air-gapped enterprises named as specific victim classes.
- **G1.2 The solution is genuinely new.** Not "another linter." The framing must land in ≤30s: *small Gemma triages the whole repo cheap; big Gemma verifies the hits deep; all local.* The model-size-tier-as-architecture idea is the headline.
- **G1.3 The change-the-world line is in there.** One sentence a viewer could quote. Candidate: *"What if every developer had a senior security engineer they could run on their laptop, on every commit, for free?"*
- **G1.4 Track-fit is unambiguous.** Safety & Trust = literal hidden-state introspection + auditable agent reasoning. Ollama = the agent runtime is Ollama, the probe also runs locally. Main = a novel architecture using two unique Gemma 4 features in one product.
- **G1.5 Positive change is tangible.** Solo maintainer / no-Snyk-budget / air-gapped enterprise story is specific, not generic "democratization."

## §2 — Video Pitch & Storytelling (30 pts) goals

- **G2.1 Cold-open hook ≤ 15s.** Doruk's CVE record opens the credibility. Specific stat ("200M+ DL/mo") earns the next 2:45.
- **G2.2 Narrative arc with the new climax.** Hook → problem → two-tier idea → demo (whole-repo scan → agent verify → certify) → why-it-matters → close. The climax is *not* a single red token; it is the agent producing a certified finding.
- **G2.3 Money-shot demo: the full pipeline visible at once.** The `/live` dashboard's three-lane view is the canonical money shot — probe firing on the left, leads stacking in the middle, agent producing verdicts on the right. The viewer must feel "the small model and the big model are working together."
- **G2.4 Both humans visible before 1:05.** Authority signal early. Doruk (security) does the hook + demo voiceover; Efe (interpretability) does the bridge ("here's why a tiny linear probe can detect this").
- **G2.5 Under 3:00, comfortably.** Target 2:50. Cut the two-tier demo to ≤70s if it threatens to overrun.
- **G2.6 Subtitle-friendly.** Every key line readable without audio. Risk score / CWE labels burned into the dashboard view.
- **G2.7 Close is memorable.** One sentence + URL on screen. No "thanks for watching."

## §3 — Technical Depth & Execution (30 pts) goals

The writeup + repo must convince a technical judge:

- **G3.1 The technique is real and reproducible.** Linear probe on hidden states, named layer (17), named metrics (AUC 0.963 in-dist / 0.907 cross-lang / macro 0.9726 across CWEs). Reproducible from the repo (`build_dataset.py` → `extract_activations.py` → `train_probe.py`).
- **G3.2 The numbers are honest.** Cross-language AUC is the headline, not random-split. Length-baseline collapse documented (0.514 on length-matched eval, probe holds 0.843). Adversarial T1–T5 suite mentioned, max-pool mitigation called out.
- **G3.3 Gemma 4 is load-bearing in TWO ways.** *(NEW for v2.)* The writeup must say *why this can't be built on Claude/GPT/Llama*: (a) **raw hidden states** for the probe, (b) **native function calling + 131k context** for the agent, (c) **model-size family** (E2B/9B/27B) maps to cheap-triage→deep-verify tiering, (d) **Apache-2.0** so no legal review, (e) **laptop-sized** so the whole pipeline is offline. Closed models miss on (a) and (e); open non-Gemma models (Llama, Qwen) hit (a) but miss the function-calling+context combo or the license cleanliness.
- **G3.4 Architecture is legible.** A reader who is not in interpretability research can trace: repo → `src/scan.py` chunks → Gemma E2B forward pass → hidden state @ layer 17 → linear probe `σ(w·h+b)` + per-CWE head → ranked leads JSONL (`gemmaforge.leads/v1`) → `pwnkit review --seed-findings --runtime ollama` → Gemma 4:27b tool loop → certified findings + SSE events → `/live` dashboard.
- **G3.5 Limitations are disclosed without killing the pitch.** Length artefact (refuted on length-matched eval), T3 (comment+reindent) vulnerability (mitigated by max-pool), train-inference distribution gap, coverage (Py/JS strong, C/C++ weaker, Rust/Zig noisy). One sentence on Tier-2 limitations (agent is bounded by tool design + Gemma 4 27B's tool-following quality).
- **G3.6 Repo is judge-ready.** README quick-start works, `python -m src.scan` runs against a sample repo end-to-end, HF Space demo URL works, link to `0sec-labs/pwnkit#371` is prominent so the judges can verify the agent side.

## §4 — Accepted gaps

(empty so far — every gap discovered in critique rounds either gets fixed or moved here with a one-line reason)

## §5 — Stop conditions for the iteration loop

Stop when:
1. Both critique agents (Claude-B and Codex GPT-5.5) return critiques where every remaining item is (a) already addressed, (b) trivial wording polish, or (c) explicitly listed in §4 above.
2. AND a manual re-score against §1–§3 has every goal marked "met."

Do NOT stop when:
- Artifacts are "fine" but a goal in §1–§3 is unmet.
- Critics still find a substantive problem.
- Only one of the two critics is satisfied.

## §6 — Out of scope for this loop

- Recording the actual video (downstream).
- Final HF Space deploy.
- LinkedIn copy.
- New experiments / probe retraining.
- Building anything new on the pwnkit side (PR #371 already merged; do not pitch beyond what landed).

This loop is purely about the **written artifacts that get submitted** — `WRITEUP.md`, `VIDEO_SCRIPT.md`, `README.md`. If a critic suggests "run another experiment" or "build another feature," we either point at an existing result/feature or move it to §4 as an accepted gap.
