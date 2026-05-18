# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.3
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # GemmaForge — Live Demo
#
# This notebook reproduces the headline numbers from the writeup:
#
# > **Gemma 4 E2B + linear probe on layer 17 → AUC 0.907 cross-language (Python → JavaScript)**
#
# What runs:
#
# 1. Loads Gemma 4 E2B (~2B, ungated, ~5 GB download).
# 2. Loads the shipped probe weights (vendored inline as base64, 6 KB).
# 3. Scores three Express handlers — two vulnerable (SQL injection + path traversal),
#    one safe — and prints `σ(w·h + b)` for each.
# 4. Prints the full AUC ladder from the writeup as a reproducibility checkpoint.
#
# **No secrets. No license clicks. Single T4. ~5 min wall clock.**
#
# - Repo: https://github.com/peaktwilight/gemmaforge
# - Writeup: https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups
# - Dashboard: https://huggingface.co/spaces/peaktwilight/gemma4ge
# - Pwnkit (Tier 3 verifier): https://github.com/0sec-labs/pwnkit

# %%
# ## Bootstrap
import sys, subprocess
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "--no-warn-script-location",
     "transformers>=4.49", "accelerate>=0.34"],
    check=True,
)
import torch
print(f"torch={torch.__version__}  cuda_available={torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"  device0={torch.cuda.get_device_name(0)}  mem={torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# %%
# ## Vendored probe weights
#
# The probe is `σ(w·h + b)` over Gemma 4 E2B hidden state at decoder layer 17.
# Weights are ~6 KB; we ship them inline so the notebook is self-contained
# (no clone of the private hackathon repo required).
import base64, io
import numpy as np

PROBE_B64 = """
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
"""

npz = np.load(io.BytesIO(base64.b64decode(PROBE_B64)))
W = npz["w"].astype(np.float32)
B = float(npz["b"])
PROBE_LAYER = int(npz["layer"])
print(f"probe loaded: layer={PROBE_LAYER}  dim={W.shape[0]}  b={B:+.4f}")
assert W.shape == (1536,), "weak-probe is on E2B (d=1536); something is wrong"

# %%
# ## Load Gemma 4 E2B
#
# E2B is ungated — no HF token needed. ~5 GB download on first run.
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "google/gemma-4-E2B-it"
print(f"loading {MODEL_ID} ...")

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype  = torch.bfloat16 if device == "cuda" else torch.float32
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = (AutoModelForCausalLM
         .from_pretrained(MODEL_ID, dtype=dtype, attn_implementation="eager")
         .to(device)
         .eval())
print(f"loaded on {device}  dtype={dtype}  params={sum(p.numel() for p in model.parameters()) / 1e9:.2f}B")

# %%
# ## The scoring function
#
# Forward pass with output_hidden_states=True, take the last-token state at
# the probe's layer, run it through the linear head. Same code path as
# `src/scan.py` in the repo.
@torch.inference_mode()
def score(snippet: str) -> float:
    ids = tokenizer.encode(snippet, return_tensors="pt", truncation=True, max_length=512).to(device)
    out = model(ids, output_hidden_states=True, use_cache=False)
    h = out.hidden_states[PROBE_LAYER + 1][0, -1, :].detach().to("cpu").float().numpy()
    logit = float(W @ h + B)
    return float(1.0 / (1.0 + np.exp(-logit)))

# %%
# ## Demo snippets
#
# Three Express handlers — two with classic webapp vulnerabilities, one safe.
# Expected: vulnerable handlers score near 1.0, the safe one stays below 0.5.

SNIPPETS = [
    ("sql_injection_vuln", "CWE-89", """
app.get('/users/:id', (req, res) => {
  db.query('SELECT * FROM users WHERE id=' + req.params.id, (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});
"""),
    ("path_traversal_vuln", "CWE-22", """
app.get('/files', (req, res) => {
  const path = require('path');
  const fs = require('fs');
  const filename = req.query.name;
  fs.readFile(path.join('/var/uploads', filename), 'utf8', (err, data) => {
    if (err) return res.status(404).send('not found');
    res.send(data);
  });
});
"""),
    ("safe_handler", "none", """
app.get('/users/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: 'bad id' });
  db.query('SELECT id, name FROM users WHERE id = $1', [id], (err, rows) => {
    if (err) return res.status(500).json({ error: 'internal' });
    res.json(rows[0] ?? null);
  });
});
"""),
]

print(f"{'name':<22s}  {'expected_cwe':<8s}  {'probe_score':>11s}  verdict")
print("-" * 60)
for name, cwe, code in SNIPPETS:
    s = score(code)
    verdict = "VULN" if s >= 0.7 else "ok" if s < 0.4 else "?"
    print(f"{name:<22s}  {cwe:<8s}  {s:>11.3f}  {verdict}")

# %%
# ## Reproducibility checkpoint — headline numbers from the writeup
#
# Eval reports are in `data/eval/` of the public repo; values below are
# copied from `data/eval/weak_probe_report.json` (n=1198, group-split,
# 95% bootstrap CI from `scripts/run_eval_framework.py`).
print("""
| Eval split                  | weak-probe (E2B L17) | strong-probe (E4B L10) |
|-----------------------------|---------------------:|-----------------------:|
| Random stratified           | 0.999                | 0.996                  |
| Group-by-repo               | 0.960                | 0.969                  |
| Held-out CWE-78 (cmd inj)   | 0.986                | 0.998                  |
| Held-out CWE-338 (weak rng) | 0.995                | 0.992                  |
| Cross-language (Py -> JS)   | 0.907                | (re-run pending)       |

Structural finding: the linear vuln direction lives at L17/35 on E2B (~49% depth)
and L10/42 on E4B (~24% depth). Bigger backbone surfaces it earlier.
""")
print("See https://github.com/peaktwilight/gemmaforge/blob/main/data/eval/strong_vs_weak_probe.md")

# %%
# ## What this demo doesn't show
#
# - **Repo-wide scan** — `python -m src.scan ./repo > leads.jsonl` emits
#   `gemmaforge.leads/v1` records. Run it on `examples/vuln-express-app/`
#   in the repo to see the JSONL output.
# - **Tier 2 cascade** — `python -m src.cascade < leads.jsonl > scored.jsonl`
#   re-scores Tier 1 leads with the E4B strong-probe and adds cascade
#   decisions (`promote` / `defer` / `drop`).
# - **Tier 3 verifier** — `pwnkit review --seed-findings scored.jsonl
#   --runtime ollama` (see https://github.com/0sec-labs/pwnkit/pull/371)
#   picks up the JSONL as a worklist and runs the Gemma 4 27B agent
#   locally via Ollama — fully off-cloud audit.
# - **Live dashboard** — https://huggingface.co/spaces/peaktwilight/gemma4ge
#   shows all three lanes streaming the canned demo data.
print("Done. Next steps documented in docs/pipeline-contract.md.")

