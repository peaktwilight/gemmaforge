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

# %% [markdown]
# # GemmaForge Strong-Probe on Gemma 4 31B (Colab)
#
# Linear probe on the dense variant `google/gemma-4-31B-it` (~31B
# params). Targets Colab on a single fat GPU (RTX 6000 Pro 96GB or
# similar — full bf16 weights are ~62GB, so an 80GB A100 is tight).
#
# Flow:
# 1. Install deps (transformers >= 4.49 for `gemma4`, torchao >= 0.16 for PEFT).
# 2. Auth (Colab Secrets: `HF_TOKEN`, optional `GITHUB_TOKEN`/`WANDB_API_KEY`).
# 3. Clone gemmaforge into `/content/gemmaforge`.
# 4. Read `num_hidden_layers` from the config — pick 25/50/75/100% layers.
# 5. Extract hidden states (last-token, bf16, device_map="auto") for each
#    candidate layer via `src.extract_activations.extract`.
# 6. Fit logistic regression with `src.train_probe.main` (group-aware split).
# 7. Five-split AUC matrix (random / group / held-out-CWE / held-out-lang / held-out-source).
# 8. Bundle + push to `peaktwilight/gemmaforge-31b-probe`.

# %%

# %%
# ## Settings
import os
from pathlib import Path

MODEL_ID = "google/gemma-4-31B-it"
REPO_URL = "https://github.com/peaktwilight/gemmaforge.git"
REPO_BRANCH = "main"
WORKDIR = Path("/content/gemmaforge")

OUT_REPO_ID = "peaktwilight/gemmaforge-31b-probe"
OUT_REPO_PRIVATE = False
PUSH_TO_HUB = True

ACTS_DIR = Path("/content/activations_31b")
PROBE_PATH = Path("/content/probe_31b.npz")
PROBE_CARD_PATH = Path("/content/probe_31b_card.json")
EVAL_PATH = Path("/content/eval_31b.json")
BUNDLE_DIR = Path("/content/bundle_31b")

RANDOM_SEED = 7
MAX_LENGTH = 512  # mirrors src/extract_activations.py

# E2B fallback numbers for the comparison table (overwritten from the clone if present).
E2B_BASELINE = {
    "num_layers": 35, "best_layer": 17, "random_stratified_auc": 0.960,
    "group_repo_auc": None, "heldout_cwe_worst_auc": None, "heldout_lang_worst_auc": None,
}


def get_secret(name):
    """Colab userdata first, then env var. Returns None if absent."""
    val = os.environ.get(name)
    if val:
        return val
    try:
        from google.colab import userdata  # type: ignore
        val = userdata.get(name)
        if val:
            os.environ[name] = val
            return val
    except Exception:
        pass
    return None


HF_TOKEN = get_secret("HF_WRITE_TOKEN") or get_secret("HF_TOKEN")
GITHUB_TOKEN = get_secret("GITHUB_TOKEN")
WANDB_API_KEY = get_secret("WANDB_API_KEY")
print(f"HF_TOKEN set: {bool(HF_TOKEN)}  GITHUB_TOKEN set: {bool(GITHUB_TOKEN)}  WANDB set: {bool(WANDB_API_KEY)}")
print(f"model={MODEL_ID}  out_repo={OUT_REPO_ID}")

# %% [markdown]
# ## Install
#
# Colab's base image usually ships a recent torch (sm_70+) and a recent-enough
# transformers, but the `gemma4` arch and the `Gemma4ClippableLinear` wrapper
# only appear in `transformers >= 4.49`. `--upgrade --no-deps` keeps torch
# pinned so we don't accidentally swap CUDA wheels. `torchao>=0.16` is
# required by recent `peft` versions.

# %%
import subprocess
import sys

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "--upgrade", "--no-deps", "transformers>=4.49"],
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "peft", "accelerate>=0.34", "datasets>=2.20",
     "huggingface_hub>=0.24", "scikit-learn>=1.5",
     "numpy>=1.26", "wandb>=0.17", "tqdm>=4.65",
     "torchao>=0.16"],
    check=True,
)

import transformers
print(f"transformers={transformers.__version__}")

import torch
assert torch.cuda.is_available(), "Need CUDA. Runtime -> Change runtime type -> GPU."
n_gpu = torch.cuda.device_count()
print(f"torch={torch.__version__}  cuda={torch.version.cuda}  n_gpu={n_gpu}")
for i in range(n_gpu):
    p = torch.cuda.get_device_properties(i)
    cc = torch.cuda.get_device_capability(i)
    print(f"  gpu[{i}]={p.name}  mem={p.total_memory / 1e9:.1f} GB  cc=sm_{cc[0]}{cc[1]}")
print(f"bf16_ok={torch.cuda.is_bf16_supported()}  supported_archs={torch.cuda.get_arch_list()}")
subprocess.run(["nvidia-smi"], check=False)

# Quick sanity: gemma4 must be in CONFIG_MAPPING.
from transformers.models.auto.configuration_auto import CONFIG_MAPPING
assert "gemma4" in CONFIG_MAPPING, "transformers too old — gemma4 missing from CONFIG_MAPPING"
print("gemma4 arch present in transformers registry")

# %% [markdown]
# ## Hugging Face login
#
# Gemma 4 31B is gated. Accept the license on the model page with the
# same HF account whose token you set as `HF_TOKEN` in Colab Secrets.

# %%
from huggingface_hub import login

if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN missing. In Colab: left sidebar -> key icon -> Add new secret "
        "with name HF_TOKEN (write-scoped HF token, needed for gated model + Hub push)."
    )
login(token=HF_TOKEN)
print("Logged in to Hugging Face Hub.")

# %% [markdown]
# ## Clone gemmaforge

# %%
clone_url = REPO_URL
if GITHUB_TOKEN and REPO_URL.startswith("https://github.com/"):
    clone_url = REPO_URL.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@")

if WORKDIR.exists():
    print(f"Refreshing clone at {WORKDIR} ...")
    for git_args in (["fetch", "origin"], ["checkout", REPO_BRANCH], ["pull", "--ff-only", "origin", REPO_BRANCH]):
        subprocess.run(["git", *git_args], cwd=WORKDIR, check=True)
else:
    print(f"Cloning {REPO_URL} -> {WORKDIR} ...")
    subprocess.run(
        ["git", "clone", "--branch", REPO_BRANCH, clone_url, str(WORKDIR)],
        check=True,
    )

req_file = WORKDIR / "requirements.txt"
if req_file.exists():
    print(f"Installing {req_file} ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)], check=True)

if str(WORKDIR) not in sys.path:
    sys.path.insert(0, str(WORKDIR))

dataset_path = WORKDIR / "data" / "dataset.jsonl"
assert dataset_path.exists(), f"missing {dataset_path}"
n_rows = sum(1 for line in dataset_path.read_text().splitlines() if line.strip())
print(f"Dataset: {dataset_path}  rows={n_rows}")

if WANDB_API_KEY:
    os.environ["WANDB_API_KEY"] = WANDB_API_KEY
    print("wandb logging enabled for train_probe stage.")

# %% [markdown]
# ## Probe layer selection
#
# We probe at 25/50/75/100% of the decoder depth, matching
# `src/extract_activations.py`. Pre-reading the config (no weights yet) so
# the chosen indices print BEFORE the slow weight download starts.

# %%
from transformers import AutoConfig

print("Fetching model config (no weights yet) ...")
cfg = AutoConfig.from_pretrained(MODEL_ID, token=HF_TOKEN, trust_remote_code=False)
text_cfg = getattr(cfg, "text_config", cfg)  # Gemma 4 multimodal nests text under text_config
n_layers = int(getattr(text_cfg, "num_hidden_layers", 0)) or int(getattr(cfg, "num_hidden_layers", 0))
hidden_size = int(getattr(text_cfg, "hidden_size", 0)) or int(getattr(cfg, "hidden_size", 0))
n_experts = (getattr(text_cfg, "num_experts", None)
             or getattr(text_cfg, "num_local_experts", None)
             or getattr(cfg, "num_experts", None))
print(f"model layers={n_layers}  hidden_size={hidden_size}  experts={n_experts}")
assert n_layers > 0, f"could not detect layer count from {type(cfg).__name__}"

LAYER_CANDIDATES = sorted({n_layers // 4, n_layers // 2, (3 * n_layers) // 4, n_layers - 1})
print(f"Probe layer candidates (25/50/75/100% of {n_layers}): {LAYER_CANDIDATES}")

# %% [markdown]
# ## Extract activations
#
# `src.extract_activations.extract` was written for a single small GPU and
# calls `model.to(device)`, which doesn't fit 31B. We monkey-patch
# `AutoModelForCausalLM.from_pretrained` to inject `device_map="auto"` and
# `torch_dtype=bf16`, and stub out `.to()` for sharded models so accelerate's
# device-map invariants stay intact. The patches are scoped to the extract
# call — everything else in `src/` is untouched.

# %%
import time
import gc
import transformers as _tx
from src import extract_activations as ea

ACTS_DIR.mkdir(parents=True, exist_ok=True)
existing = sorted(ACTS_DIR.glob("activations_layer*.npz"))
expected = {f"activations_layer{li:02d}.npz" for li in LAYER_CANDIDATES}
if existing and {p.name for p in existing} >= expected:
    print(f"Cached activations found in {ACTS_DIR}: {[p.name for p in existing]}; skipping extraction.")
else:
    print(f"Extracting activations for {len(LAYER_CANDIDATES)} layers -> {ACTS_DIR}")
    _orig_from_pretrained = _tx.AutoModelForCausalLM.from_pretrained

    def _patched_from_pretrained(model_id, *args, **kwargs):
        kwargs.setdefault("device_map", "auto")
        kwargs["torch_dtype"] = torch.bfloat16
        kwargs.pop("dtype", None)  # extract_activations.py passes dtype= (transformers >=4.43 alias)
        kwargs.setdefault("token", HF_TOKEN)
        kwargs.setdefault("attn_implementation", "eager")
        return _orig_from_pretrained(model_id, *args, **kwargs)

    _tx.AutoModelForCausalLM.from_pretrained = _patched_from_pretrained

    import torch.nn as _nn
    _orig_to = _nn.Module.to

    def _patched_to(self, *a, **kw):
        # No-op when accelerate has sharded the model across devices.
        if hasattr(self, "hf_device_map") and len(getattr(self, "hf_device_map", {})) > 1:
            return self
        return _orig_to(self, *a, **kw)

    _nn.Module.to = _patched_to
    try:
        t0 = time.time()
        ea.extract(
            model_id=MODEL_ID,
            jsonl_path=dataset_path,
            out_dir=ACTS_DIR,
            layer_indices=LAYER_CANDIDATES,
        )
        print(f"Extraction finished in {(time.time() - t0) / 60:.1f} min")
    finally:
        _tx.AutoModelForCausalLM.from_pretrained = _orig_from_pretrained
        _nn.Module.to = _orig_to

import numpy as np
for p in sorted(ACTS_DIR.glob("activations_layer*.npz")):
    z = np.load(p)
    print(f"  {p.name}  X={z['X'].shape}  y_pos={int(z['y'].sum())}")

gc.collect(); torch.cuda.empty_cache()

# %% [markdown]
# ## Train the linear probe
#
# `src.train_probe.main()` reads each `activations_layer*.npz`, fits logistic
# regression with a group-aware split (`--pairs` enables that), and writes
# the best layer's `(w, b, layer)` to `PROBE_PATH`.

# %%
from src import train_probe as train_probe_mod
import json

train_probe_argv = [
    "train_probe", "--acts-dir", str(ACTS_DIR), "--out", str(PROBE_PATH),
    "--card", str(PROBE_CARD_PATH), "--pairs", str(dataset_path),
]
if WANDB_API_KEY:
    train_probe_argv += ["--wandb-project", "gemmaforge-31b-probe"]

_prev_argv, sys.argv = sys.argv, train_probe_argv
try:
    t0 = time.time()
    train_probe_mod.main()
    print(f"Probe training finished in {time.time() - t0:.1f}s")
finally:
    sys.argv = _prev_argv

probe_card = json.loads(PROBE_CARD_PATH.read_text())
print("--- probe_card.json ---")
print(json.dumps(probe_card, indent=2))
best_layer = int(probe_card["best_layer"])
print(f"\nBest layer: {best_layer}  AUC={probe_card['best_auc']:.3f}  ACC={probe_card['best_acc']:.3f}")

# %% [markdown]
# ## Five-split AUC matrix
#
# `scripts/eval_splits.py` hardcodes E2B-specific paths, so this section
# inlines the same logic parameterised by `best_layer`. Group key is
# `(_file_name, _func_name)` — the dataset.jsonl analog of E2B's
# `_origin_repo`.

# %%
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
    "n_experts": n_experts,
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

# %% [markdown]
# ## Compare against E2B baseline (from the clone, if present)

# %%
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
    for key, label in [("group_repo_auc", "group_repo"),
                       ("heldout_cwe_worst_auc", "heldout_cwe"),
                       ("heldout_lang_worst_auc", "heldout_lang")]:
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

worst_31b = worst["auc"] if worst else float("nan")
g_repo = E2B_BASELINE.get("group_repo_auc")
w_cwe = E2B_BASELINE.get("heldout_cwe_worst_auc")
print("\n--- comparison ---")
print(f"               E2B ({E2B_BASELINE['num_layers']}L)              31B ({n_layers}L)")
print(f"best layer     {E2B_BASELINE['best_layer']:<22d} {best_layer}")
print(f"random AUC     {E2B_BASELINE['random_stratified_auc']:<22.3f} {random_baseline['auc']:.3f}")
print(f"group AUC      {('%.3f' % g_repo) if g_repo else 'n/a':<22s} {group_repo['auc']:.3f}")
print(f"worst-cwe AUC  {('%.3f' % w_cwe) if w_cwe else 'n/a':<22s} {worst_31b:.3f}")

# %%

# %% [markdown]
# ## Bundle and push to the Hub

# %%
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
- gemma-4-31b
- linear-probe
- security
- vulnerability-detection
---

# GemmaForge Strong Probe — Gemma 4 31B (Colab)

Frozen `{MODEL_ID}` with a logistic-regression probe on the last-token
hidden state of decoder layer **{best_layer}** (of {n_layers}). Dense
companion to [`peaktwilight/gemmaforge-gemma4-probe`](https://huggingface.co/peaktwilight/gemmaforge-gemma4-probe)
(E2B) and [`peaktwilight/gemmaforge-26b-probe`](https://huggingface.co/peaktwilight/gemmaforge-26b-probe)
(26B-A4B MoE).

## Files
- `probe_31b.npz` — `(w, b, layer)`; `sigmoid(w @ activation + b)` = risk.
- `probe_31b_card.json` — per-layer AUC/ACC from `src.train_probe`.
- `eval_31b.json` — five-split AUC matrix.

## Headline

| Split | E2B ({E2B_BASELINE['num_layers']}L, L{E2B_BASELINE['best_layer']}) | 31B ({n_layers}L, L{best_layer}) |
|---|---:|---:|
| Random stratified (leaky) | {_fmt(E2B_BASELINE['random_stratified_auc'])} | {_fmt(random_baseline['auc'])} |
| Group split (file / func) | {_fmt(E2B_BASELINE.get('group_repo_auc'))} | {_fmt(group_repo['auc'])} |
| Held-out CWE (worst)      | {_fmt(E2B_BASELINE.get('heldout_cwe_worst_auc'))} | {_fmt(worst_31b)} |
| Held-out lang (worst)     | {_fmt(E2B_BASELINE.get('heldout_lang_worst_auc'))} | see `eval_31b.json` |

Layer candidates: {LAYER_CANDIDATES} (25/50/75/100% of {n_layers}).

## Reproduce

```python
from huggingface_hub import hf_hub_download
import numpy as np
npz = np.load(hf_hub_download("{OUT_REPO_ID}", "probe_31b.npz"))
w, b, layer = npz["w"], float(npz["b"]), int(npz["layer"])
# risk = sigmoid(w @ hidden_states[layer + 1][0, -1, :] + b)
```

Pipeline: <https://github.com/peaktwilight/gemmaforge>.
"""

(BUNDLE_DIR / "README.md").write_text(readme)
print("Bundle contents:")
for p in sorted(BUNDLE_DIR.iterdir()):
    print(f"  {p.name}  ({p.stat().st_size} bytes)")

if PUSH_TO_HUB:
    api = HfApi(token=HF_TOKEN)
    api.create_repo(repo_id=OUT_REPO_ID, repo_type="model", private=OUT_REPO_PRIVATE, exist_ok=True)
    api.upload_folder(
        repo_id=OUT_REPO_ID, repo_type="model", folder_path=str(BUNDLE_DIR),
        commit_message=(
            f"Upload Gemma 4 31B linear probe "
            f"(layer {best_layer}/{n_layers}, random_AUC={random_baseline['auc']:.3f})"
        ),
    )
    print(f"\nUploaded to https://huggingface.co/{OUT_REPO_ID}")
else:
    print("PUSH_TO_HUB=False, skipping Hub upload.")
print(f"Local artifacts at {BUNDLE_DIR}/")
