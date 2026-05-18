# Codex GPT-5.5 Round 2 Critique

## Verdict
ONE MORE ROUND. The rewrite is much stronger and the core Technical Depth story is now legible: E2B probe -> ranked leads -> pwnkit/Ollama verifier, with honest metric reporting and a real Gemma-4-specific argument. But there is still one technical-honesty risk: the artifacts still claim or strongly imply that pwnkit currently verifies each GemmaForge lead as a seeded worklist item, while the same artifacts admit seed-findings worklist injection is still pwnkit#368 TODO. Fix that contradiction everywhere, and this becomes defensible.

## Round-1 claim audit re-check
- `gemmaforge.doruk.ch` live demo: removed; HF Space is now the linked demo.
- HF Space works: still presented; Round 1 already verified.
- Doruk "10+ CVE-grade" / "200M+ downloads": numeric download claims removed; "additional CVE-grade vulnerabilities" remains external but acceptably biographical.
- `CVE-2026-33896`, `node-forge`, 33M weekly downloads: 33M claim removed; CVE claim remains as team/background evidence, acceptable if the advisory page is shown.
- "AI assistants ship ~100M LOC/day": removed.
- "Every major assistant emits vulnerabilities": softened to "public benchmarks show"; still uncited, but no longer a dangerous quantified claim.
- "Detect before the first risky token is finalized": removed/hedged; sample-level vs token-level split is now explicit in WRITEUP.md:40-42 and README.md:41-45.
- Token-level path is successor, not shipped production probe: now correctly stated.
- Sub-ms / `<1 ms` overhead: still present in WRITEUP.md:40 and README.md:16 without a benchmark artifact; low-risk polish, but still weak.
- Per-CWE macro AUC 0.9726: verified in `data/probe_per_cwe_card.json`.
- Per-CWE top-1 routing 94.7%: still asserted in README.md:276 and RESULTS.md:76, but not in `data/probe_per_cwe_card.json`; either cite the generating artifact or remove.
- "Near-zero off-diagonal confusion": walked back to "off-diagonal mass ... small" in WRITEUP.md:57; acceptable.
- Author-grounded / author-informed training data: improved, but still weak. README.md:39 and README.md:68 say the training set includes the `node-forge` patch; the canonical metric table says `pairs_v2` is CyberSecEval-only. Needs a manifest/source row if kept.
- Dataset scope: fixed. Canonical metrics are now scoped to `pairs_v2`; SVEN/token-level data is separated.
- Runs locally, no network: properly scoped to inference; setup/model download caveat is implicit but acceptable.
- Architecture components: now clear, but the integration still overstates current seeded verification in several places.
- End-to-end training ~90s: still appears in README.md:199 without timing artifact; polish-level weak metric.
- Demo unsafe mean risk lifts ~10 points: still in WRITEUP.md:144 without an obvious metric file; acceptable only as demo observation.
- GPT/Claude hidden-state contrast: plausible and now part of a coherent Gemma-specific argument; citation polish only.
- Gemma native function calling + 131k context: still uncited, but load-bearing argument is clear.
- Apache wording: fixed. It now distinguishes project Apache-2.0 from Gemma Terms of Use.
- E2B laptop performance: ">20 tok/s" removed; "2018 laptop" remains in script/README but is not a central metric.
- Length baseline: length-matched 0.514 vs probe 0.843 verified; unmatched 0.883 still needs a source artifact if kept.
- Regex baseline 0.991 vs 0.944: still claimed in WRITEUP.md:150 and README.md:79 without an artifact located in this pass; because it is framed as a limitation, risk is low but it still needs a cite.
- T1-T5 adversarial suite / T3 max-pool mitigation: verified against `data/adversarial_full_suite.json`.
- Coverage wording: fixed; README.md:78 and WRITEUP.md:154 now match "not in dataset / no activation pass" rather than "noisy."
- "Tracked as 13 open issues": removed.
- Training set public/embargo exclusion: still asserted; acceptable ethics statement, but stronger with manifest link.
- pwnkit PR #371 merged: verified.
- PR #371 seed parser: verified.
- PR #371 seed worklist injection: still TODO and now disclosed, but contradicted by headline/demo wording. This is the remaining blocker.
- PR #371 Ollama streaming tool-calls: fixed; artifacts now say batched/non-streaming.
- PR #371 `/live` Hunt lane: fixed in the explicit notes; remaining issue is not Lane 3, it is terminal/per-lead verifier wording.

## Round-1 risk flag check
- SeedFindings worklist injection is TODO: disclosed in WRITEUP.md:82, WRITEUP.md:156, README.md:139, but not fully honored by README.md:5, README.md:136, VIDEO_SCRIPT.md:107-127, and WRITEUP.md:18/70/135.
- Streaming Ollama tool-calls are not in v1: now honest. WRITEUP.md:80 and README.md:137 say batched/non-streaming; WRITEUP.md:155 says verdicts arrive batched.
- Lane 3 Hunt is placeholder: now honest. VIDEO_SCRIPT.md:97 and VIDEO_SCRIPT.md:166 explicitly say not to fake it; WRITEUP.md:81/124 and README.md:138 label it placeholder.
- "Before first risky token" overclaim: removed as product thesis and replaced with sample-level metrics plus token-level candidate disclosure.
- Author-grounded training data: partially addressed, but "training set includes node-forge patch" still needs a concrete data-manifest pointer.

## Goal-by-goal re-scoring (G3.1 .. G3.6)
- G3.1: met, improved from partial. Layer, model, dataset size, sample-level path, and reproduction path are now named.
- G3.2: met, unchanged/stronger. Cross-language AUC is the headline and the length/adversarial caveats are prominent.
- G3.3: met, improved from unmet. The new "model-size family is the architecture" section is exactly the right Gemma-4-specific argument.
- G3.4: partial, improved from unmet. The trace is legible, but it still draws a straight line from `--seed-findings --seed-only` to "structured per-lead verdicts" even though worklist injection is not shipped.
- G3.5: partial, improved from partial. Limitations are now strong, but they are undercut by higher-level per-lead verifier claims.
- G3.6: partial, improved from partial. README is much more judge-ready, but `--seed-only` is described as relying solely on `--seed-findings` in README.md:136, which is exactly the unshipped behavior.

## New issues introduced by the rewrite (if any)
- README.md:136 says `--seed-only` "skips semgrep prioritisation, relies solely on `--seed-findings`." Under the stated pwnkit#368 TODO, this is false and should be removed or rewritten.
- VIDEO_SCRIPT.md:107-127 shows `pwnkit review --seed-findings leads.jsonl --seed-only --runtime ollama`, then says the agent "writes a verdict per lead" and closes with "Cold repo to verified finding." That is still pitching unshipped seed-worklist behavior.
- WRITEUP.md:18 says Tier 2 "verify each lead"; WRITEUP.md:70 says pwnkit "consumes this format directly ... and runs its agentic verification loop"; WRITEUP.md:135 says "structured per-lead audit verdicts." These lines conflict with WRITEUP.md:82/156.
- README.md:5 says Tier 2 "verifies each lead"; README.md:114-122 diagram implies leads flow directly to structured per-lead verdicts. Same contradiction.
- WRITEUP.md:84 says "Nothing in the demo or this writeup depends on un-shipped code," but the scripted `--seed-only` per-lead verification demo does depend on pwnkit#368.
- pwnkit#368/#370 are described as "follow-up commit on the same merged PR/thread" in several places. Since the PR is already merged, "follow-up issue/PR" would be cleaner and less confusing than "same PR."

## Trivial polish remaining
- Replace all "verify each lead," "per-lead verdicts," and "seed-only relies solely on seed-findings" wording with: "pwnkit parses the leads today; the Ollama agent can run locally on the same repo; promoting leads to the primary worklist is pwnkit#368."
- Either add the artifact for top-1 routing accuracy 94.7% or delete that sentence.
- Either cite the unmatched length baseline 0.883 and regex CWE-328 0.991/0.944 artifacts, or leave only the verified length-matched and adversarial results.
- Add a concrete manifest/source pointer for "training set includes the node-forge CVE patch," or soften it to "team expertise and public CVE patterns informed the dataset design."
- Remove "2018 laptop" if no timing/hardware artifact is available; "probe-only path runs on laptop-class hardware" is enough.

## Final stop recommendation
- ONE MORE ROUND — fix the remaining Tier-2 seeded-verification overclaim. After that, Technical Depth is ship-ready.
