# Codex GPT-5.5 Round 1 Critique

## Verdict
Technical Depth would not earn full marks as written. The probe work is real, unusually well-instrumented, and mostly honest on metrics, but the submitted `VIDEO_SCRIPT.md`, `WRITEUP.md`, and `README.md` still sell the old single-tier "token turns red while Gemma writes code" product. The new two-tier architecture is the stated winning angle, yet the public writeup does not explain `src/scan.py -> gemmaforge.leads/v1 -> pwnkit --seed-findings -> Ollama Gemma 4 27B`, and pwnkit PR #371 is only partially end-to-end: seed leads are parsed and passed through, Ollama runtime exists, `/live` exists, but seed findings are explicitly TODO for worklist injection and the Hunt lane is explicitly TODO/placeholder. As written, a technical judge will give strong credit for the probe, then subtract heavily for architecture mismatch and possible overclaim risk.

## Goal-by-goal scoring (G3.1 .. G3.6 in detail; G1/G2 only if a technical flaw hurts them)

| Goal | Score | Technical critique |
|---|---|---|
| G3.1 | partial | The metrics and reproduction trail are real: `WRITEUP.md` says "Gemma 4 E2B (layer 17, 1,198 CyberSecEval pairs)" and README has `build_dataset.py -> extract_activations -> train_probe.py`, but the top-level claim "before the first risky token is finalized" is not proven by the shipped sample-level probe trained on complete-snippet last-token activations. |
| G3.2 | met | The writeup leads with the OOD number and discloses the main metric traps: "Honest headline: 0.907 cross-language" and "length baseline collapses to chance (0.514) while the probe still hits 0.843"; this is the strongest technical section. |
| G3.3 | unmet | The writeup still says "one Gemma instance can drive both the probe and a normal IDE assistant flow"; it does not make the new load-bearing argument that E2B/9B/27B model sizes are an architecture, nor does it contrast closed models vs Llama/Qwen on hidden states, function calling, context, license, and local deployment. |
| G3.4 | unmet | Current architecture is the old stream UI: "`Gemma 4` unmodified ... `The probe` ... per generated token"; a reader cannot trace repo scanning, ranked leads, `pwnkit review --seed-findings --runtime ollama`, 27B verifier tool use, certified findings, and `/live`. |
| G3.5 | partial | Probe limitations are unusually candid, e.g. "Train-inference distribution gap" and "Surface-form sensitivity"; Tier-2 limitations are missing, and the only pwnkit mention is future work: "VS Code extension + pwnkit confidence-filter + W&B telemetry." |
| G3.6 | partial | `src/scan.py`, `docs/leads-schema.md`, `docs/events.md`, and tests make the repo close to judge-ready, but README's quick start runs `src.stream_with_probe`, not `python -m src.scan`; PR #371 is not linked prominently; `https://gemmaforge.doruk.ch` failed DNS in my check, while the HF Space URL returned HTTP 200. |
| G1/G2 technical blocker | partial | The video money shot is technically obsolete: it shows "Gemma writes `return db.query(...)`, the meter swings hard right" instead of the required whole-repo scan -> lead queue -> agent verdict pipeline. |

## Claim audit

| Claim a judge might challenge | Where evidenced | Verdict |
|---|---|---|
| "Live demo: https://gemmaforge.doruk.ch" | `WRITEUP.md`; `curl -I -L https://gemmaforge.doruk.ch` failed DNS from this environment. | unverified / high-risk |
| HF Space `peaktwilight/gemmaforge` works | `README.md`; HTTP 200 from `https://huggingface.co/spaces/peaktwilight/gemmaforge`. | verified |
| Doruk has "10+ CVE-grade vulnerabilities" and "200M+ combined monthly downloads" | `WRITEUP.md`, `README.md`; not evidenced in repo except repeated prose. | unverified unless external proof is linked |
| `CVE-2026-33896` in `node-forge`, 33M weekly downloads | `WRITEUP.md`, `README.md`, `LINKEDIN.md`; advisory link is generic and no local proof of npm download count. | weak |
| "AI coding assistants ship ~100M lines of code per day" | `WRITEUP.md`; no citation. | unverified |
| "Every major assistant emits SQLi/path traversal/command injection/etc. as steady-state behavior" | `WRITEUP.md`; no citation or benchmark reference. | weak |
| "Can detect before the first risky token is finalized" | `WRITEUP.md`, `VIDEO_SCRIPT.md`; `src.stream_with_probe.py` streams scores, but sample-level training is last-token complete snippets and token-level path is weaker/not successor-shipped. | overclaimed |
| Sample-level path ships; token-level path is successor | `WRITEUP.md`; `data/probe.npz`, `src/train_probe.py`, `data/probe_spanmax_card.json`, `scripts/train_value_head.py`. | verified |
| Token-level: token AUC 0.768 / example AUC 0.700 at layer 8 | `data/probe_spanmax_card.json`. | verified |
| Obeso et al. hallucination probe paper exists and reports AUC around/>0.9 | arXiv `2509.03531`, README/WRITEUP citation. | verified |
| Linear classifier on Gemma layer 17, 1,536 weights, <10 KB | `data/probe_v2_card.json`, `data/probe.npz`, `integrations/pwnkit/adapter.py`; hidden dim 1536. | verified |
| "sub-ms per token" / "<1 ms overhead" | Repeated in `WRITEUP.md`, `README.md`, `RESULTS.md`; no benchmark artifact found. | weak |
| 1,198 CyberSecEval pairs | `data/pairs_v2.jsonl`, `data/eval/report.md`, `RESULTS.md`. | verified |
| Random stratified AUC 0.963 / accuracy 92.1% | `data/probe_v2_card.json`, `data/eval/report.md`; note `data/probe_card.json` has older 0.960/92.0. | verified but stale duplicate risk |
| Group-by-repo AUC 0.958 / accuracy 91.6% | `data/eval/report.md`, `data/probe_strict.json`. | verified |
| Held-out CWE 0.92-0.96 / 83-91% | `data/eval/report.md`, `data/probe_strict.json`. | verified |
| Cross-language Py->JS AUC 0.907 / accuracy 81.9% | `data/eval/report.md`, `data/probe_strict.json`. | verified |
| 4-layer ensemble AUC 0.976 random | `data/probe_ensemble.json`. | verified |
| MLP head AUC 0.919 cross-lang | `data/probe_mlp_ablation.json` / summarized in `RESULTS.md`. | verified |
| MLP x ensemble AUC 0.940 Py->JS | `data/probe_mlp_ensemble_xlang.json`. | verified |
| Per-CWE macro AUC 0.9726, top-1 routing 94.7% | `data/probe_per_cwe_card.json` verifies macro AUC; top-1 routing is asserted in `RESULTS.md` but not present in the JSON card I inspected. | weak for top-1 routing |
| "Near-zero off-diagonal confusion matrix" | `RESULTS.md` says approximate/reconstructed confusion, not exact. | weak / should not overstate |
| "Author-grounded training data ... Doruk personally found CVEs" | `WRITEUP.md`, `README.md`; `RESULTS.md` says `pairs_v1` has `doruk-cve-corpus` n=1 and the main `pairs_v2` source is CyberSecEval/CyberSecEval-leadup. | weak / likely overclaimed for shipped metrics |
| "Runs locally, no network" | `src/stream_with_probe.py`, `integrations/pwnkit/adapter.py` use local HF model load after weights are present; Ollama runtime local in pwnkit. | mostly verified, but setup may download models |
| Architecture: "Ollama for chat/tool-calling, HF transformers + MPS for activation hook" | `README.md`, `src.stream_with_probe.py`, pwnkit `runtime/ollama.ts`. | verified for components, not integrated in writeup |
| Per generated token read hidden state and emit risk | `src/stream_with_probe.py`. | verified |
| SSE page colors tokens green/yellow/red | `web/index.html`, `src.stream_with_probe.py`. | verified |
| Dataset "~1,200 CyberSecEval + SVEN + ~55 natural-language safe examples" | `WRITEUP.md`; main metrics are on `pairs_v2` CyberSecEval only; README dataset table lists SVEN separately. | misleading unless scoped |
| Activation capture at layers 25/50/75/100% | `src/extract_activations.py`, `RESULTS.md`. | verified |
| End-to-end training ~90s on M1 Max once cached | `WRITEUP.md`; not evidenced by timing artifact. | weak |
| Demo unsafe mean risk lifts ~10 pts | `WRITEUP.md`; screenshots/recording artifacts exist, but no clear metric file. | weak |
| "GPT-5/Claude do not expose raw hidden states" | General platform fact; no repo evidence. | plausible but uncited |
| "Gemma native function calling + 131k context" | `README.md`; pwnkit Ollama runtime supports tools; context length not locally evidenced. | weak unless linked to Gemma docs |
| "Apache-2.0-equivalent license" / code Apache-2.0 | Repo `LICENSE` supports project license; model license claim needs exact Gemma license wording. | weak wording |
| "E2B does >20 tok/s on Apple Silicon" | `WRITEUP.md`, `README.md`; no benchmark file. | weak |
| Length baseline 0.883 unmatched vs probe 0.907 | `WRITEUP.md`, `README.md`; source likely `data/eval_length_matched.json` only contains matched numbers, not unmatched 0.883. | weak unless artifact located |
| Length-matched 230 pairs, length baseline 0.514, probe 0.843, delta 0.329 | `data/eval_length_matched.json`. | verified |
| Regex baseline beats on CWE-328, 0.991 vs 0.944 | `WRITEUP.md`, `README.md`; not found in files skimmed. | weak |
| T1-T5 adversarial suite, T3 delta -0.089, max-pool flattens to <=0.005 | `data/adversarial_full_suite.json`. | verified |
| "Streaming UI ships max-pool" | `src/stream_with_probe.py` defaults to max-pool. | verified |
| Coverage: Python/JS strong, C/C++ less, Rust/Zig noisy | `WRITEUP.md`; `docs/coverage.md`/README say Rust/Go/Ruby/PHP not in dataset, not "noisy"; C/C++ activations not extracted. | partially wrong |
| LoRA 30 SFT steps, 64 examples, 39s MPS, CE 2.30 | `data/lora_adapter/train_status.json`, `RESULTS.md`. | verified |
| LoRA base=3, LoRA=0 vulnerable patterns on 5 prompts | `data/lora_eval.json`. | verified but tiny n |
| "Full DPO LoRA supports --max_steps 500" | `scripts/train_lora.py`, `RESULTS.md`. | verified as code capability, not result |
| "Tracked as 13 open GitHub issues" | `WRITEUP.md`, `README.md`; not verified. | unverified |
| "Code, probe weights, training-data manifest: Apache-2.0, all in repo" | `LICENSE`, `data/`, `README.md`; training-data manifest is not obvious by that name. | mostly verified |
| "Training set uses only public CVE disclosures; embargoed excluded" | `WRITEUP.md`; no manifest proving exclusion. | weak |
| pwnkit PR #371 merged 2026-05-18 | GitHub PR #371 page; `git ls-remote` main at `21b8fa6`, PR head `7f582ab`. | verified merged; exact 17:10 UTC timestamp not independently verified here |
| PR #371 adds `--seed-findings <path|->` parser | `/tmp/pwnkit-pr371-check/packages/cli/src/commands/review.ts`, `packages/core/src/seed-findings.ts`. | verified |
| PR #371 injects seed findings into the agent's worklist before semgrep | pwnkit `packages/cli/src/commands/run.ts` says TODO and "core ignores it." | false / must not pitch |
| PR #371 adds `--runtime ollama`, defaults to `gemma4:27b`, calls `/api/chat` with `tools[]` | pwnkit `packages/core/src/runtime/index.ts`, `runtime/ollama.ts`. | verified |
| PR #371 supports streaming Ollama tool-calls | pwnkit `runtime/ollama.ts` says "Streaming is intentionally NOT supported in v1." | false / must not pitch |
| PR #371 `/live` dashboard has three lanes | pwnkit `packages/dashboard/src/App.tsx`, `live-page.tsx`. | verified for route/UI |
| PR #371 Hunt lane shows agent-produced findings live | pwnkit `live-page.tsx` says Hunt is placeholder/TODO. | false / must not pitch |

## The 5 highest-leverage edits

1. `WRITEUP.md` / title + problem + technique: replace the old "before the token lands" single-tier framing with "small Gemma finds repo-wide leads; big Gemma verifies them locally." Keep token streaming as a demo mode, not the product thesis.
2. `WRITEUP.md` / Architecture: add the exact trace required by G3.4: `repo -> src/scan.py chunks -> Gemma E2B hidden state layer 17 -> binary/per-CWE probes -> gemmaforge.leads/v1 -> pwnkit review --seed-findings leads.jsonl --runtime ollama -> Gemma 4 27B tool loop -> verdicts`; explicitly say the pwnkit worklist injection is not landed if you cannot update pwnkit.
3. `WRITEUP.md` / Why Gemma 4 specifically: rewrite around model-size-tier-as-architecture. The current "one Gemma instance can drive both..." line fights the two-tier story and is not enough for the Ollama prize.
4. `VIDEO_SCRIPT.md` / demo beat: replace the token-overlay preset demo with the `/live` three-lane scan replay only if the Hunt lane is honestly labeled as a replay/placeholder; otherwise show terminal proof: `gemmaforge scan` emits leads, then pwnkit loads them and Ollama can run independently.
5. `README.md` / quick start + pwnkit link: add a judge path that works without ambiguity: `python -m src.scan examples/... --output leads.jsonl --events events.ndjson`, schema link, pwnkit PR #371 link, and a blunt note that pwnkit currently parses/passes seed leads but worklist injection is TODO.

## Risk flags

- The most dangerous overclaim is Tier 2. Do not say "pwnkit consumes GemmaForge leads and certifies each lead" unless the core actually injects seeds into the agent worklist. Current pwnkit main says the core ignores `seedFindings`.
- Do not show or describe the `/live` Hunt lane as real agent output. The pwnkit component itself says the Hunt lane is a placeholder and "the wiring lands in a follow-up."
- Do not claim streaming Ollama tool-calls. PR #371's runtime is explicitly non-streaming.
- The "author-grounded training data" story needs narrowing. The metrics are on CyberSecEval `pairs_v2`, while the only explicit `doruk-cve-corpus` count I saw is one row in deprecated `pairs_v1`.
- The writeup's "before first risky token" line is too strong for a sample-level probe trained on complete snippets. Safer: "the streaming demo scores intermediate hidden states, but the shipped validated metrics are sample-level; token-level training is in progress."
- Several public credibility numbers need citations or removal: 100M AI-generated LOC/day, 200M+ package downloads/month, 33M weekly `node-forge`, >20 tok/s, sub-ms overhead, 90s training, regex 0.991 vs 0.944.
- `gemmaforge.doruk.ch` failed from this environment. If it is not live tonight, remove it from `WRITEUP.md` or replace with the HF Space URL that returned HTTP 200.
- README and writeup disagree with the new goals: README still targets `gemma4:8b`/E2B single-flow "in-IDE token-level overlay"; the v2 goal is E2B probe plus 27B verifier.
- Coverage wording is sloppy: "Rust/Zig noisy" is not evidenced; repo docs say Rust/Go/Ruby/PHP are not in the dataset yet and C/C++ activations are not extracted.
- `data/probe_card.json` and `data/probe_v2_card.json` disagree on best AUC (0.960 vs 0.963). Cite `data/probe_v2_card.json` or `data/eval/report.md` consistently and explain stale artifacts if asked.
