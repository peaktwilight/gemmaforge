# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# In[1]:
# # GemmaForge Probe Replication on Gemma 4 26B-A4B (Kaggle)
#
# Replicates the linear value-head probe pipeline on the larger MoE variant
# `google/gemma-4-26B-A4B-it` (~26B total params, ~4B active). The E2B
# baseline lands AUC ~0.96 on layer 17 of 35 under the leaky random split
# and drops into 0.6-0.8 under held-out CWE / language splits. This notebook
# reproduces the same five-split AUC matrix on 26B and ships the artifact
# bundle to `peaktwilight/gemmaforge-26b-probe`. Advances issue #8 on
# `peaktwilight/gemmaforge` ("MoE variant probe sweep").
#
# ## Kaggle submission flow
#
# 1. **Attach the competition**: File -> Add or upload data -> "Gemma 4
#    Good Hackathon".
# 2. **Set secrets** (Add-ons -> Secrets):
#    - `HF_TOKEN`: write-scoped HF token (gated model + push-to-hub).
#    - `GITHUB_TOKEN`: `repo:read` while `peaktwilight/gemmaforge` is
#      private. Notebook exits cleanly at cell 5 if missing.
#    - `WANDB_API_KEY`: optional, forwarded into `src.train_probe`.
# 3. **Accelerator**: Settings -> GPU T4 x2. CPU/TPU won't work; MoE active
#    path is ~4B params so two T4s fit it at bf16 with `device_map="auto"`.
# 4. **Run All**. Expect ~45-60 min wall clock on T4 x2 (download 10-15 min
#    + extraction 20-30 min + probe fit + push).

# In[2]:
# ## Settings
import os
from pathlib import Path

MODEL_ID = "google/gemma-4-26B-A4B-it"
REPO_URL = "https://github.com/peaktwilight/gemmaforge.git"
REPO_BRANCH = "main"
WORKDIR = Path("/kaggle/working/gemmaforge")

OUT_REPO_ID = "peaktwilight/gemmaforge-26b-probe"
OUT_REPO_PRIVATE = False

ACTS_DIR = Path("/kaggle/working/activations_26b")
PROBE_PATH = Path("/kaggle/working/probe_26b.npz")
PROBE_CARD_PATH = Path("/kaggle/working/probe_26b_card.json")
EVAL_PATH = Path("/kaggle/working/eval_26b.json")
BUNDLE_DIR = Path("/kaggle/working/bundle_26b")

RANDOM_SEED = 7
MAX_LENGTH = 512  # mirrors src/extract_activations.py

# E2B baseline numbers for the model-card comparison. Re-read from the
# clone in cell 10; these are fallbacks if the files have moved.
E2B_BASELINE = {
    "num_layers": 35, "best_layer": 17, "random_stratified_auc": 0.960,
    "group_repo_auc": None, "heldout_cwe_worst_auc": None, "heldout_lang_worst_auc": None,
}


def _get_secret(name):
    """Try Kaggle Secrets first; fall back to env var when run outside Kaggle."""
    val = os.environ.get(name)
    if val:
        return val
    try:
        from kaggle_secrets import UserSecretsClient  # type: ignore
        val = UserSecretsClient().get_secret(name)
        if val:
            os.environ[name] = val
            return val
    except Exception:
        pass
    return None


HF_TOKEN = _get_secret("HF_TOKEN") or _get_secret("HF_WRITE_TOKEN")
GITHUB_TOKEN = _get_secret("GITHUB_TOKEN")
WANDB_API_KEY = _get_secret("WANDB_API_KEY")
print(f"HF_TOKEN set: {bool(HF_TOKEN)}  GITHUB_TOKEN set: {bool(GITHUB_TOKEN)}  WANDB set: {bool(WANDB_API_KEY)}")
print(f"model={MODEL_ID}  out_repo={OUT_REPO_ID}")

# In[3]:
# ## Bootstrap
import sys
import subprocess

PIP_BASE = [
    "transformers>=4.45", "peft>=0.12", "accelerate>=0.34",
    "datasets>=2.20", "huggingface_hub>=0.24", "scikit-learn>=1.5",
    "numpy>=1.26", "wandb>=0.17", "tqdm>=4.65",
]
print("Installing base packages...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-warn-script-location", *PIP_BASE], check=True)

import torch
print(f"torch={torch.__version__}  cuda_available={torch.cuda.is_available()}")
assert torch.cuda.is_available(), "This notebook needs CUDA. Settings -> Accelerator -> GPU T4 x2."
n_gpu = torch.cuda.device_count()
print(f"n_gpu={n_gpu}  device0={torch.cuda.get_device_name(0)}  bf16_ok={torch.cuda.is_bf16_supported()}")
for i in range(n_gpu):
    props = torch.cuda.get_device_properties(i)
    print(f"  gpu[{i}]={props.name}  mem={props.total_memory / 1e9:.1f} GB")
subprocess.run(["nvidia-smi"], check=False)

# In[4]:
# ## Hugging Face login
#
# 26B-A4B is gated. Accept the license on the model page with the same
# account whose token you've set as `HF_TOKEN`.
from huggingface_hub import login

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN not found. Add it under Add-ons -> Secrets with label 'HF_TOKEN' (write-scoped: gates download + push).")
login(token=HF_TOKEN)
print("Logged in to Hugging Face Hub.")

# In[5]:
# ## Clone gemmaforge
#
# Repo is currently PRIVATE during the hackathon embargo. Require a
# `GITHUB_TOKEN` secret; otherwise exit cleanly with instructions.
if not GITHUB_TOKEN:
    print("=" * 64)
    print("ERROR: GITHUB_TOKEN secret is not set.")
    print("=" * 64)
    print("`peaktwilight/gemmaforge` is private during the hackathon embargo.")
    print("Fix: Add-ons -> Secrets -> add 'GITHUB_TOKEN' with `repo:read`")
    print("OR temporarily flip the repo to public, then re-run this cell.")
    raise SystemExit(0)

clone_url = REPO_URL.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@")
if WORKDIR.exists():
    print(f"Refreshing clone at {WORKDIR} ...")
    for git_args in (["fetch", "origin"], ["checkout", REPO_BRANCH], ["pull", "--ff-only", "origin", REPO_BRANCH]):
        subprocess.run(["git", *git_args], cwd=WORKDIR, check=True)
else:
    print(f"Cloning {REPO_URL} -> {WORKDIR} ...")
    subprocess.run(["git", "clone", "--branch", REPO_BRANCH, clone_url, str(WORKDIR)], check=True)

req_file = WORKDIR / "requirements.txt"
if req_file.exists():
    print(f"Installing {req_file} ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)], check=True)

if str(WORKDIR) not in sys.path:
    sys.path.insert(0, str(WORKDIR))

dataset_path = WORKDIR / "data" / "dataset.jsonl"
assert dataset_path.exists(), f"missing {dataset_path} — should be in the repo"
n_rows = sum(1 for line in dataset_path.read_text().splitlines() if line.strip())
print(f"Dataset: {dataset_path}  rows={n_rows}")

if WANDB_API_KEY:
    os.environ["WANDB_API_KEY"] = WANDB_API_KEY
    print("wandb logging enabled for train_probe stage.")

# In[6]:
# ## Probe layer selection
#
# E2B has 35 layers; baseline lands on layer 17 (~49%). For 26B-A4B we
# read `num_hidden_layers` and pick 25/50/75/100% layers, matching
# `src/extract_activations.py:69-70`. We pre-read the config (no weights
# yet) so the chosen indices print BEFORE the slow download starts.
from transformers import AutoConfig

print("Fetching model config (no weights yet) ...")
cfg = AutoConfig.from_pretrained(MODEL_ID, token=HF_TOKEN, trust_remote_code=False)
text_cfg = getattr(cfg, "text_config", cfg)  # Gemma 4 multimodal nests text under text_config
n_layers = int(getattr(text_cfg, "num_hidden_layers", 0)) or int(getattr(cfg, "num_hidden_layers", 0))
hidden_size = int(getattr(text_cfg, "hidden_size", 0)) or int(getattr(cfg, "hidden_size", 0))
n_experts = getattr(text_cfg, "num_experts", None) or getattr(text_cfg, "num_local_experts", None) or getattr(cfg, "num_experts", None)
print(f"model layers={n_layers}  hidden_size={hidden_size}  experts={n_experts}")
assert n_layers > 0, f"could not detect layer count from {type(cfg).__name__}"

LAYER_CANDIDATES = sorted({n_layers // 4, n_layers // 2, (3 * n_layers) // 4, n_layers - 1})
print(f"Probe layer candidates (25/50/75/100% of {n_layers}): {LAYER_CANDIDATES}")

# In[7]:
# ## Extract activations
#
# Calls the canonical `src.extract_activations.extract(...)`. The function
# uses `model.to(device)` which won't fit 26B on a single T4, so we
# monkey-patch `AutoModelForCausalLM.from_pretrained` to inject
# `device_map="auto"` (sharding across the two T4s) plus `torch_dtype=
# bfloat16` for the duration of the call. The patch only affects the
# extract invocation; everything else in src/ is untouched.
import time, gc
import transformers
from src import extract_activations as ea

ACTS_DIR.mkdir(parents=True, exist_ok=True)
existing = sorted(ACTS_DIR.glob("activations_layer*.npz"))
expected = {f"activations_layer{li:02d}.npz" for li in LAYER_CANDIDATES}
if existing and {p.name for p in existing} >= expected:
    print(f"Found cached activations in {ACTS_DIR}: {[p.name for p in existing]}; skipping extraction.")
else:
    print(f"Extracting activations for {len(LAYER_CANDIDATES)} layers -> {ACTS_DIR}")
    _orig_from_pretrained = transformers.AutoModelForCausalLM.from_pretrained

    def _patched_from_pretrained(model_id, *args, **kwargs):
        kwargs.setdefault("device_map", "auto")
        kwargs["torch_dtype"] = torch.bfloat16
        kwargs.pop("dtype", None)  # extract_activations.py passes dtype= (transformers >=4.43 alias)
        kwargs.setdefault("token", HF_TOKEN)
        return _orig_from_pretrained(model_id, *args, **kwargs)

    transformers.AutoModelForCausalLM.from_pretrained = _patched_from_pretrained
    # Also neutralise `model.to(device)` for sharded models — calling .to()
    # on a device_map model is a no-op in recent transformers but raises in
    # accelerate's BigModelMixin in some versions.
    import torch.nn as _nn
    _orig_to = _nn.Module.to
    def _patched_to(self, *a, **kw):
        if hasattr(self, "hf_device_map") and len(getattr(self, "hf_device_map", {})) > 1:
            return self
        return _orig_to(self, *a, **kw)
    _nn.Module.to = _patched_to
    try:
        t0 = time.time()
        ea.extract(model_id=MODEL_ID, jsonl_path=dataset_path, out_dir=ACTS_DIR, layer_indices=LAYER_CANDIDATES)
        print(f"Extraction finished in {(time.time() - t0) / 60:.1f} min")
    finally:
        transformers.AutoModelForCausalLM.from_pretrained = _orig_from_pretrained
        _nn.Module.to = _orig_to

import numpy as np
for p in sorted(ACTS_DIR.glob("activations_layer*.npz")):
    z = np.load(p)
    print(f"  {p.name}  X={z['X'].shape}  y_pos={int(z['y'].sum())}")

gc.collect(); torch.cuda.empty_cache()

# In[8]:
# ## Train the linear probe
#
# Calls `src.train_probe.main()` with argv patched to write into
# /kaggle/working/. The `--pairs` flag turns on the group-aware split
# (issue #18) so the train-time leak the E2B baseline suffered doesn't
# repeat here.
from src import train_probe as train_probe_mod
import json

train_probe_argv = [
    "train_probe", "--acts-dir", str(ACTS_DIR), "--out", str(PROBE_PATH),
    "--card", str(PROBE_CARD_PATH), "--pairs", str(dataset_path),
]
if WANDB_API_KEY:
    train_probe_argv += ["--wandb-project", "gemmaforge-26b-probe"]

prev_argv, sys.argv = sys.argv, train_probe_argv
try:
    t0 = time.time()
    train_probe_mod.main()
    print(f"Probe training finished in {time.time() - t0:.1f}s")
finally:
    sys.argv = prev_argv

probe_card = json.loads(PROBE_CARD_PATH.read_text())
print("--- probe_card.json ---")
print(json.dumps(probe_card, indent=2))
best_layer = int(probe_card["best_layer"])
print(f"\nBest layer: {best_layer}  AUC={probe_card['best_auc']:.3f}  ACC={probe_card['best_acc']:.3f}")

# In[9]:
# ## Five-split AUC matrix
#
# `scripts/eval_splits.py` hardcodes E2B paths (layer 17, activations_v2/,
# pairs.jsonl), so we inline the same logic parameterised by `best_layer`.
# Group key is `(_file_name, _func_name)` — the dataset.jsonl analog of
# E2B's `_origin_repo`.
from collections import Counter
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split


def fit_eval(X, y, tr, te):
    if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
        return float("nan"), float("nan"), len(tr), len(te)
    clf = LogisticRegression(max_iter=1000, C=1.0).fit(X[tr], y[tr])
    prob = clf.predict_proba(X[te])[:, 1]
    pred = clf.predict(X[te])
    return float(roc_auc_score(y[te], prob)), float(accuracy_score(y[te], pred)), len(tr), len(te)


def add(split_name, tr, te):
    auc, acc, ntr, nte = fit_eval(X, y, tr, te)
    results.append({"split": split_name, "auc": auc, "acc": acc, "n_train": ntr, "n_test": nte})


z = np.load(ACTS_DIR / f"activations_layer{best_layer:02d}.npz")
X, y = z["X"], z["y"].astype(int)
rows = [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]
assert len(rows) == len(X), f"row count mismatch: jsonl={len(rows)} npz={len(X)}"

# Propagate each pair's positive CWE down onto its paired negative.
file_cwe = {
    (r.get("_file_name"), r.get("_func_name")): r["cwe"]
    for r in rows if r["label"] == 1 and r.get("cwe")
}
for r in rows:
    key = (r.get("_file_name"), r.get("_func_name"))
    r["_paired_cwe"] = r.get("cwe") if (r["label"] == 1 or r.get("cwe")) else file_cwe.get(key)

print(f"loaded X={X.shape}  y_pos={int(y.sum())}  rows={len(rows)}")
results = []

# (a) random stratified
idx = np.arange(len(y))
tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=RANDOM_SEED)
add("random_stratified", tr, te)

# (b) group split on (_file_name, _func_name)
groups = np.array([f"{r.get('_file_name') or ''}:{r.get('_func_name') or ''}" or str(i) for i, r in enumerate(rows)])
(tr, te), = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_SEED).split(X, y, groups=groups)
add("group_file_func", tr, te)

# (c) held-out CWE, top-5 by positive frequency
cwe_arr = np.array([r["_paired_cwe"] for r in rows], dtype=object)
pos_cwes = [r["_paired_cwe"] for r in rows if r["label"] == 1 and r["_paired_cwe"]]
for cwe, _ in Counter(pos_cwes).most_common(5):
    add(f"heldout_cwe::{cwe}", np.where(cwe_arr != cwe)[0], np.where(cwe_arr == cwe)[0])

# (d) held-out language
lang_arr = np.array([r.get("lang") or "" for r in rows])
for held in sorted({lang for lang in lang_arr if lang}):
    te = np.where(lang_arr == held)[0]; tr = np.where(lang_arr != held)[0]
    if len(te) >= 10 and len(tr) >= 10:
        add(f"heldout_lang::test={held}", tr, te)

# (e) held-out source — usually single-class on dataset.jsonl, skipped if so.
src_arr = np.array([r.get("source") or "" for r in rows])
for held in sorted({s for s in src_arr if s}):
    te = np.where(src_arr == held)[0]; tr = np.where(src_arr != held)[0]
    if len(te) >= 10 and len(tr) >= 10:
        auc, *_ = fit_eval(X, y, tr, te)
        if not np.isnan(auc):
            add(f"heldout_source::test={held}", tr, te)

print("\n" + "=" * 70)
print(f"{'split':<36s}  {'auc':>6s}  {'acc':>6s}  {'n_tr':>5s}  {'n_te':>5s}")
print("-" * 70)
for r in results:
    auc_str = "n/a" if np.isnan(r["auc"]) else f"{r['auc']:.3f}"
    acc_str = "n/a" if np.isnan(r["acc"]) else f"{r['acc']:.3f}"
    print(f"{r['split']:<36s}  {auc_str:>6s}  {acc_str:>6s}  {r['n_train']:>5d}  {r['n_test']:>5d}")
print("=" * 70)

random_baseline = next(r for r in results if r["split"] == "random_stratified")
group_repo = next(r for r in results if r["split"] == "group_file_func")
credible = [r for r in results if r["split"].startswith(("heldout_cwe::", "heldout_lang::"))]
worst = min(credible, key=lambda r: float("inf") if np.isnan(r["auc"]) else r["auc"]) if credible else None

EVAL_PATH.write_text(json.dumps({
    "model_id": MODEL_ID, "num_layers": n_layers, "hidden_size": hidden_size,
    "best_layer": best_layer, "layer_candidates": LAYER_CANDIDATES,
    "all_layers": probe_card.get("all_layers"), "splits": results,
    "headline": {
        "random_stratified_auc": random_baseline["auc"],
        "group_file_func_auc": group_repo["auc"],
        "worst_credible_split": worst["split"] if worst else None,
        "worst_credible_auc": worst["auc"] if worst else None,
    },
}, indent=2))
print(f"\nSaved {EVAL_PATH}")

# In[10]:
# ## Compare against E2B baseline
#
# Best-effort: parse `data/probe_card.json` + `data/eval_splits.md` from
# the clone. Fallbacks at top of notebook if either is missing.
import re

e2b_card_path = WORKDIR / "data" / "probe_card.json"
e2b_splits_path = WORKDIR / "data" / "eval_splits.md"

if e2b_card_path.exists():
    e2b_card = json.loads(e2b_card_path.read_text())
    E2B_BASELINE["best_layer"] = int(e2b_card["best_layer"])
    E2B_BASELINE["random_stratified_auc"] = float(e2b_card["best_auc"])
    if e2b_card.get("all_layers"):
        E2B_BASELINE["num_layers"] = max(int(lyr["layer"]) for lyr in e2b_card["all_layers"]) + 1
    print(f"E2B card: layers={E2B_BASELINE['num_layers']}  best_layer={E2B_BASELINE['best_layer']}  AUC={E2B_BASELINE['random_stratified_auc']:.3f}")
else:
    print(f"warning: {e2b_card_path} not found, using hardcoded baseline")

if e2b_splits_path.exists():
    md = e2b_splits_path.read_text()
    # Cells look like `| \`heldout_cwe::CWE-79\` | 0.812 | 0.760 | 800 | 240 |`
    for key, label in [("group_repo_auc", "group_repo"), ("heldout_cwe_worst_auc", "heldout_cwe"), ("heldout_lang_worst_auc", "heldout_lang")]:
        candidates = []
        for line in md.splitlines():
            if f"`{label}" in line:
                for part in (p.strip() for p in line.split("|")):
                    if re.fullmatch(r"\d\.\d{3}", part):
                        candidates.append(float(part)); break
        if candidates:
            E2B_BASELINE[key] = min(candidates) if key.endswith("worst_auc") else candidates[0]
    print(f"E2B splits: group_repo={E2B_BASELINE['group_repo_auc']}  worst_cwe={E2B_BASELINE['heldout_cwe_worst_auc']}  worst_lang={E2B_BASELINE['heldout_lang_worst_auc']}")
else:
    print(f"warning: {e2b_splits_path} not found")

worst_26b = worst["auc"] if worst else float("nan")
g_repo = E2B_BASELINE.get("group_repo_auc")
w_cwe = E2B_BASELINE.get("heldout_cwe_worst_auc")
print("\n--- comparison ---")
print(f"               E2B ({E2B_BASELINE['num_layers']}L)              26B-A4B ({n_layers}L)")
print(f"best layer     {E2B_BASELINE['best_layer']:<22d} {best_layer}")
print(f"random AUC     {E2B_BASELINE['random_stratified_auc']:<22.3f} {random_baseline['auc']:.3f}")
print(f"group AUC      {('%.3f' % g_repo) if g_repo else 'n/a':<22s} {group_repo['auc']:.3f}")
print(f"worst-cwe AUC  {('%.3f' % w_cwe) if w_cwe else 'n/a':<22s} {worst_26b:.3f}")

# In[11]:
# ## Build artifact bundle and push to the Hub
#
# Contents: probe_26b.npz + probe_26b_card.json + eval_26b.json + README.md.
from huggingface_hub import HfApi
import shutil


def _fmt(value):
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
for src in (PROBE_PATH, PROBE_CARD_PATH, EVAL_PATH):
    shutil.copyfile(src, BUNDLE_DIR / src.name)

readme = f"""---
library_name: numpy
base_model: {MODEL_ID}
tags:
- gemma
- gemma-4-26b-a4b
- moe
- linear-probe
- security
- vulnerability-detection
---

# GemmaForge Linear Probe — Gemma 4 26B-A4B

Frozen `{MODEL_ID}` with a logistic-regression probe on the last-token
hidden state of decoder layer **{best_layer}** (of {n_layers}). MoE
companion to [`peaktwilight/gemmaforge-gemma4-probe`](https://huggingface.co/peaktwilight/gemmaforge-gemma4-probe)
(E2B). Same dataset + code path, different base. Advances issue #8.

## Files
- `probe_26b.npz` — `(w, b, layer)`; `sigmoid(w @ activation + b)` = risk.
- `probe_26b_card.json` — per-layer AUC/ACC from `src.train_probe`.
- `eval_26b.json` — five-split AUC matrix.

## Headline

| Split | E2B ({E2B_BASELINE['num_layers']}L, L{E2B_BASELINE['best_layer']}) | 26B-A4B ({n_layers}L, L{best_layer}) |
|---|---:|---:|
| Random stratified (leaky) | {_fmt(E2B_BASELINE['random_stratified_auc'])} | {_fmt(random_baseline['auc'])} |
| Group split (file / func) | {_fmt(E2B_BASELINE.get('group_repo_auc'))} | {_fmt(group_repo['auc'])} |
| Held-out CWE (worst)      | {_fmt(E2B_BASELINE.get('heldout_cwe_worst_auc'))} | {_fmt(worst_26b)} |
| Held-out lang (worst)     | {_fmt(E2B_BASELINE.get('heldout_lang_worst_auc'))} | see `eval_26b.json` |

Layer candidates: {LAYER_CANDIDATES} (25/50/75/100% of {n_layers}).

## Reproduce

```python
from huggingface_hub import hf_hub_download
import numpy as np
npz = np.load(hf_hub_download("{OUT_REPO_ID}", "probe_26b.npz"))
w, b, layer = npz["w"], float(npz["b"]), int(npz["layer"])
# risk = sigmoid(w @ hidden_states[layer + 1][0, -1, :] + b)
```

Pipeline: <https://github.com/peaktwilight/gemmaforge>.
"""

(BUNDLE_DIR / "README.md").write_text(readme)
print("Bundle contents:")
for p in sorted(BUNDLE_DIR.iterdir()):
    print(f"  {p.name}  ({p.stat().st_size} bytes)")

api = HfApi(token=HF_TOKEN)
api.create_repo(repo_id=OUT_REPO_ID, repo_type="model", private=OUT_REPO_PRIVATE, exist_ok=True)
api.upload_folder(
    repo_id=OUT_REPO_ID, repo_type="model", folder_path=str(BUNDLE_DIR),
    commit_message=f"Upload Gemma 4 26B-A4B linear probe (layer {best_layer}/{n_layers}, random_AUC={random_baseline['auc']:.3f})",
)
print(f"\nUploaded to https://huggingface.co/{OUT_REPO_ID}")
print(f"Local artifacts still at {BUNDLE_DIR}/ (Kaggle Output tab).")

# In[12]:
# ## How To Run (recap)
#
# 1. Kaggle -> Import Notebook -> `notebooks/kaggle_train_probe_26b.ipynb`.
# 2. Attach "Gemma 4 Good Hackathon" under Add or upload data.
# 3. Settings -> Accelerator -> **GPU T4 x2**. CPU/TPU won't work.
# 4. Secrets: `HF_TOKEN` (write-scoped), `GITHUB_TOKEN` (`repo:read` while
#    gemmaforge is private), optional `WANDB_API_KEY`.
# 5. Accept the Gemma 4 26B-A4B license on HF with the same account.
# 6. Run All. Wall clock on T4 x2 ~45-60 min (download 10-15 + extraction
#    20-30 + probe+eval 3-5 + push 1).
# 7. Output: `peaktwilight/gemmaforge-26b-probe` on the Hub +
#    `/kaggle/working/bundle_26b/` locally + a printed E2B-vs-26B table.
print("Done. See https://huggingface.co/" + OUT_REPO_ID)
