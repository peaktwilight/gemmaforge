# Causal Attention Pool Probe — Implementation Notes

References:
[learnmechinterp.com — Attention Probes](https://learnmechinterp.com/) and
Kelp et al., *Attention Probes for Concept Detection in LLMs*,
arXiv:2510.09694.

## Motivation

GemmaForge's deployed probe is a single learned direction over the last-token
residual stream at layer 17:

```
risk = sigma(w . h_last + b)
```

This works (test AUC 0.963) but it discards every token in the buffer
*except* the last. The `eval_maxpool` script adds a fixed-window max-pool on
top, which improves adversarial robustness ~22x at the cost of being a
hand-tuned post-hoc band-aid. An **attention probe** is the principled
replacement: it *learns* which positions in a rolling buffer matter.

## Architecture

Given a buffer of recent hidden states `H \in R^{K x D}`:

```
scores = H @ Wq                # [K, n_heads]
attn   = softmax(scores, dim=0)
V      = H @ Wv                # [K, D]
h_agg  = mean_heads( sum_k attn_k * V_k )   # [D]
logit  = head_w . h_agg + head_b
```

Following the Attention Probes paper, we use `n_heads = 8`, `Wq: D -> 8`,
`Wv: D -> D`, no bias on Wq/Wv. With D = 1536 and 8 heads the probe has
~2.36M parameters — small enough to ship next to a 4B model.

Implementation: `src/attention_probe.py` (`AttentionProbe` nn.Module). Save
format: `data/probe_attention.npz` with keys
`{Wq, Wv, head_w, head_b, layer, n_heads}` (separate from `probe.npz` which
stays the linear-probe contract).

## Why we cannot fully evaluate this yet

The activation cache under `data/activations_v2/activations_layer*.npz`
contains exactly one vector per sample: the **last-token** hidden state
extracted by `src/extract_activations.py`. The per-token extraction path
(`src/extract_token_activations.py`) that would produce the
`[N, K, D]` tensor an attention probe actually needs is gated behind
GitHub issue #17.

The toy training script (`scripts/train_attention_probe.py`) fakes the
buffer by repeating `h_last` K times. Mathematically this is a degenerate
case: a constant H makes `softmax(H @ Wq)` uniform regardless of Wq, so

```
h_agg = mean_heads( (1/K) * sum_k Wv h_last ) = Wv h_last
```

The probe collapses to a linear classifier with effective weight
`head_w^T Wv`. We measured this empirically: toy AUC at layer 17 = 0.959 vs
the linear probe's 0.963 — same number, off by SGD noise. Layer trend
matches too (08: 0.93, 17: 0.96, 26: 0.94, 34: 0.89).

## Migration plan (once issue #17 lands)

1. `extract_token_activations.py` writes `activations_token_layer17.npz`
   with key `H` of shape `[N, K, D]` and `y` of shape `[N]`. Pick K = 32
   or K = 64 (the streaming UI's effective window).
2. Replace `_fake_buffer(h, k)` in `scripts/train_attention_probe.py` with
   a direct load of `H` — no shape changes needed downstream; the module
   already accepts `[B, K, D]`.
3. Re-train across all four cached layers; report AUC + the adversarial
   eval from `scripts/adversarial_test.py`.
4. If attention pool beats both raw last-token and the max-pool baseline
   on the SLODA adversarial set, swap it into `src/stream_with_probe.py`
   behind a `--probe-kind=attention` flag.

## Honest expectation

Attention probes are most useful when the relevant signal is **diffuse
across positions** — e.g. a vulnerability cue that surfaces several tokens
*before* the sink. If the signal is already concentrated at the last
token (which a single direction at 0.963 AUC suggests it largely is on
this dataset), the upside is modest. The bigger win is likely robustness
under adversarial obfuscation, where max-pool already gave 22x gains
(`a71c998` in the log); attention pool should subsume that with a learned
weighting. Real evaluation gated on issue #17.
