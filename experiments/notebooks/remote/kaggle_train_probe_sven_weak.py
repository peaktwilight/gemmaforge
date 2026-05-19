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
# # GemmaForge Weak Probe on SVEN (Kaggle)
#
# Trains the linear value-head probe on `google/gemma-4-E2B-it` (~2B effective
# params — the "weak" base in the weak-vs-strong head-to-head landed in
# 15ab29a / 4926024) using the SVEN position-paired training set
# (`data/pairs_sven_train.jsonl`, 1,254 rows: 627 pos / 627 neg, 9 CWEs,
# C / C++ / Python). Output: `peaktwilight/gemmaforge-weak-sven-probe` — a
# clean SVEN-only counterpart to the merged-dataset weak probe at
# `peaktwilight/gemmaforge-gemma4-probe`.
#
# ## Kaggle submission flow
#
# 1. **Attach this notebook to the competition**: open the notebook editor,
#    File -> Add or upload data -> Competitions -> "Gemma 4 Good Hackathon".
# 2. **Set secrets** (Add-ons -> Secrets):
#    - `HF_TOKEN`: write-scoped HF token (needed for the Hub push; E2B itself
#      is ungated so download works without one).
#    - `GITHUB_TOKEN`: `repo:read` while `peaktwilight/gemmaforge` is private.
#      The clone cell exits cleanly with instructions if missing.
#    - `WANDB_API_KEY`: optional, forwarded into `src.train_probe`.
# 3. **Accelerator**: Settings -> GPU T4 (x1 is fine; x2 is also OK). CPU/TPU
#    won't work — bf16 needs CUDA. E2B is ~4 GB in bf16 so a single T4 fits it
#    with headroom.
# 4. **Run All**. Expect ~15-25 min wall clock on T4 (download 2-4 min +
#    extraction 8-15 min + probe fit + push).

# %%
# ## Settings
import os
from pathlib import Path

MODEL_ID = "google/gemma-4-E2B-it"
REPO_URL = "https://github.com/peaktwilight/gemmaforge.git"
REPO_BRANCH = "main"
WORKDIR = Path("/kaggle/working/gemmaforge")

OUT_REPO_ID = "peaktwilight/gemmaforge-weak-sven-probe"
OUT_REPO_PRIVATE = False
PUSH_TO_HUB = True

# SVEN training set: position-paired (POSITIVE = code up to vuln end,
# NEGATIVE = same code truncated >=50 chars BEFORE the first edit). Built by
# scripts/build_dataset_sven.py from `bstee615/sven`.
TRAIN_JSONL_REL = Path("data") / "pairs_sven_train.jsonl"

ACTS_DIR = Path("/kaggle/working/activations_weak_sven")
PROBE_PATH = Path("/kaggle/working/probe_weak_sven.npz")
PROBE_CARD_PATH = Path("/kaggle/working/probe_weak_sven_card.json")
EVAL_PATH = Path("/kaggle/working/eval_weak_sven.json")
BUNDLE_DIR = Path("/kaggle/working/bundle_weak_sven")

RANDOM_SEED = 7
MAX_LENGTH = 512  # mirrors src/extract_activations.py


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
print(f"train_data={TRAIN_JSONL_REL}")

# %% [markdown]
# ## Bootstrap
#
# Kaggle base images ship transformers ~4.42 which doesn't know the `gemma4`
# arch, so we force-upgrade JUST transformers with `--no-deps` (keeps the
# pinned torch/CUDA wheels). The P100 detection branch mirrors
# `kaggle_train_lora_dpo.py` — Kaggle's stock torch wheel ships sm_70+ only,
# so when Kaggle rolls a P100 (sm_60) the model init crashes with
# "no kernel image available". Swap in a cu118 wheel that still has sm_60.

# %%
import sys
import subprocess

gpu_check = subprocess.run(
    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
    capture_output=True, text=True, check=False,
)
gpu_name = gpu_check.stdout.strip()
print(f"detected gpu: {gpu_name!r}")
if "P100" in gpu_name:
    print("P100 detected -> reinstalling torch 2.5.1+cu118 + matching torchvision (sm_60)")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-q", "--no-warn-script-location",
        "--force-reinstall", "--no-deps",
        "--index-url", "https://download.pytorch.org/whl/cu118",
        "torch==2.5.1", "torchvision==0.20.1",
    ], check=True)

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "--no-warn-script-location",
     "--upgrade", "--no-deps", "transformers>=4.49"],
    check=True,
)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "--no-warn-script-location",
     "peft", "accelerate>=0.34", "datasets>=2.20",
     "huggingface_hub>=0.24", "scikit-learn>=1.5",
     "numpy>=1.26", "wandb>=0.17", "tqdm>=4.65"],
    check=True,
)

import transformers
print(f"transformers={transformers.__version__}")

import torch
assert torch.cuda.is_available(), "Need CUDA. Settings -> Accelerator -> GPU T4."
n_gpu = torch.cuda.device_count()
print(f"torch={torch.__version__}  cuda={torch.version.cuda}  n_gpu={n_gpu}")
for i in range(n_gpu):
    p = torch.cuda.get_device_properties(i)
    cc = torch.cuda.get_device_capability(i)
    print(f"  gpu[{i}]={p.name}  mem={p.total_memory / 1e9:.1f} GB  cc=sm_{cc[0]}{cc[1]}")
print(f"bf16_ok={torch.cuda.is_bf16_supported()}  supported_archs={torch.cuda.get_arch_list()}")
subprocess.run(["nvidia-smi"], check=False)

from transformers.models.auto.configuration_auto import CONFIG_MAPPING
assert "gemma4" in CONFIG_MAPPING, "transformers too old — gemma4 missing from CONFIG_MAPPING"
print("gemma4 arch present in transformers registry")

# %% [markdown]
# ## Hugging Face login
#
# `google/gemma-4-E2B-it` is ungated, so the token is only needed for the
# final push-to-hub. We still log in if a token is set so the same client
# handles both download (faster, authenticated mirror) and push.

# %%
if HF_TOKEN:
    from huggingface_hub import login
    login(token=HF_TOKEN)
    print("Logged in to Hugging Face Hub.")
else:
    print("No HF_TOKEN — download will still work (E2B is ungated). "
          "Push-to-hub will be skipped at the end.")

# %% [markdown]
# ## Clone gemmaforge
#
# Repo is currently PRIVATE during the hackathon embargo. We require a
# `GITHUB_TOKEN` secret; otherwise the cell exits cleanly with instructions.

# %%
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

dataset_path = WORKDIR / TRAIN_JSONL_REL
assert dataset_path.exists(), f"missing {dataset_path} — should be in the repo"
import json as _json
n_rows = 0
pos = 0
with dataset_path.open() as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        n_rows += 1
        if _json.loads(line).get("label") == 1:
            pos += 1
print(f"Dataset: {dataset_path}  rows={n_rows}  pos={pos}  neg={n_rows - pos}")

if WANDB_API_KEY:
    os.environ["WANDB_API_KEY"] = WANDB_API_KEY
    print("wandb logging enabled for train_probe stage.")

# %% [markdown]
# ## Probe layer selection
#
# E2B is small (~30 decoder layers); we still probe at 25/50/75/100% of the
# depth so the layer card has the same shape as the 26B / 31B notebooks for
# the head-to-head comparison. Pre-reading the config (no weights yet) so
# the chosen indices print BEFORE the slow weight download starts.

# %%
from transformers import AutoConfig

print("Fetching model config (no weights yet) ...")
cfg = AutoConfig.from_pretrained(MODEL_ID, token=HF_TOKEN, trust_remote_code=False)
text_cfg = getattr(cfg, "text_config", cfg)  # Gemma 4 multimodal nests text under text_config
n_layers = int(getattr(text_cfg, "num_hidden_layers", 0)) or int(getattr(cfg, "num_hidden_layers", 0))
hidden_size = int(getattr(text_cfg, "hidden_size", 0)) or int(getattr(cfg, "hidden_size", 0))
print(f"model layers={n_layers}  hidden_size={hidden_size}")
assert n_layers > 0, f"could not detect layer count from {type(cfg).__name__}"

LAYER_CANDIDATES = sorted({n_layers // 4, n_layers // 2, (3 * n_layers) // 4, n_layers - 1})
print(f"Probe layer candidates (25/50/75/100% of {n_layers}): {LAYER_CANDIDATES}")

# %% [markdown]
# ## Extract activations
#
# E2B fits on a single T4 in bf16, but we still patch
# `AutoModelForCausalLM.from_pretrained` to inject `device_map="auto"` +
# `torch_dtype=bf16` so the notebook tolerates whatever Kaggle assigns
# (T4 / P100 / V100 / A100). The patches are scoped to the extract call
# — everything else in `src/` is untouched.

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
        if HF_TOKEN:
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
# regression with a group-aware split (`--pairs` enables that — closes the
# issue #18 sibling leak), and writes the best layer's `(w, b, layer)` to
# `PROBE_PATH`.

# %%
from src import train_probe as train_probe_mod
import json

train_probe_argv = [
    "train_probe", "--acts-dir", str(ACTS_DIR), "--out", str(PROBE_PATH),
    "--card", str(PROBE_CARD_PATH), "--pairs", str(dataset_path),
]
if WANDB_API_KEY:
    train_probe_argv += ["--wandb-project", "gemmaforge-weak-sven-probe"]

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
# Same shape as `scripts/eval_splits.py` and the 31B notebook, parameterised
# by `best_layer`. Group key is `(_file_name, _func_name)` so paired
# POSITIVE / NEGATIVE truncations from the same SVEN function can't land in
# both train and test.

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

# Propagate each pair's positive CWE down onto its paired negative — the
# SVEN-before-leadup rows are emitted without a `cwe` field, so we copy it
# over from the sibling positive sharing the same (_file_name, _func_name).
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

# (e) held-out source — SVEN-only set is dominated by SVEN-before / -leadup,
# so this split is usually single-class on one side; the guard below skips
# any split where AUC isn't defined.
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
    "dataset": str(TRAIN_JSONL_REL), "n_rows": len(rows),
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
# ## Held-out evaluation on `dataset_sven_heldout.jsonl`
#
# The 272-row held-out file is single-class (all `is_completion_vulnerable =
# true`), so AUC isn't defined on it. We still extract activations and report
# the probe's mean risk score — a sanity check that the weak probe assigns
# high risk to held-out SVEN vulnerable completions.

# %%
heldout_path = WORKDIR / "data" / "dataset_sven_heldout.jsonl"
if heldout_path.exists():
    heldout_rows = [json.loads(line) for line in heldout_path.read_text().splitlines() if line.strip()]
    labels = [r.get("label") for r in heldout_rows]
    n_pos_h = sum(1 for L in labels if L == 1)
    n_neg_h = sum(1 for L in labels if L == 0)
    print(f"heldout rows={len(heldout_rows)}  pos={n_pos_h}  neg={n_neg_h}")

    HELDOUT_ACTS = Path("/kaggle/working/activations_weak_sven_heldout")
    HELDOUT_ACTS.mkdir(parents=True, exist_ok=True)
    if not (HELDOUT_ACTS / f"activations_layer{best_layer:02d}.npz").exists():
        _orig_from_pretrained = _tx.AutoModelForCausalLM.from_pretrained

        def _patched_from_pretrained(model_id, *args, **kwargs):
            kwargs.setdefault("device_map", "auto")
            kwargs["torch_dtype"] = torch.bfloat16
            kwargs.pop("dtype", None)
            if HF_TOKEN:
                kwargs.setdefault("token", HF_TOKEN)
            kwargs.setdefault("attn_implementation", "eager")
            return _orig_from_pretrained(model_id, *args, **kwargs)

        _tx.AutoModelForCausalLM.from_pretrained = _patched_from_pretrained
        import torch.nn as _nn
        _orig_to = _nn.Module.to

        def _patched_to(self, *a, **kw):
            if hasattr(self, "hf_device_map") and len(getattr(self, "hf_device_map", {})) > 1:
                return self
            return _orig_to(self, *a, **kw)

        _nn.Module.to = _patched_to
        try:
            ea.extract(
                model_id=MODEL_ID,
                jsonl_path=heldout_path,
                out_dir=HELDOUT_ACTS,
                layer_indices=[best_layer],
            )
        finally:
            _tx.AutoModelForCausalLM.from_pretrained = _orig_from_pretrained
            _nn.Module.to = _orig_to

    z_h = np.load(HELDOUT_ACTS / f"activations_layer{best_layer:02d}.npz")
    Xh, yh = z_h["X"], z_h["y"].astype(int)

    # Refit on ALL of pairs_sven_train for the heldout scoring (no held-out
    # within train — we want the strongest probe applied to the truly unseen
    # set).
    clf_full = LogisticRegression(max_iter=1000, C=1.0).fit(X, y)
    risks = clf_full.predict_proba(Xh)[:, 1]
    heldout_summary = {
        "n": int(len(Xh)),
        "n_pos": int(yh.sum()),
        "mean_risk_pos": float(risks[yh == 1].mean()) if int(yh.sum()) > 0 else None,
        "mean_risk_neg": float(risks[yh == 0].mean()) if int((yh == 0).sum()) > 0 else None,
        "frac_flagged_at_0.5": float((risks >= 0.5).mean()),
    }
    print("heldout summary:", json.dumps(heldout_summary, indent=2))
    # Append to eval JSON so the bundle carries this signal too.
    eval_blob = json.loads(EVAL_PATH.read_text())
    eval_blob["heldout_sven"] = heldout_summary
    EVAL_PATH.write_text(json.dumps(eval_blob, indent=2))
    gc.collect(); torch.cuda.empty_cache()
else:
    print(f"warning: {heldout_path} not found — skipping held-out sanity check")
    heldout_summary = None

# %% [markdown]
# ## Build artifact bundle and push to the Hub

# %%
import shutil

BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
for src in (PROBE_PATH, PROBE_CARD_PATH, EVAL_PATH):
    shutil.copyfile(src, BUNDLE_DIR / src.name)


def _fmt(value):
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


worst_auc = worst["auc"] if worst else float("nan")
heldout_line = (
    f"Mean risk pos: {_fmt(heldout_summary['mean_risk_pos']) if heldout_summary else 'n/a'}, "
    f"flagged @ 0.5: {_fmt(heldout_summary['frac_flagged_at_0.5']) if heldout_summary else 'n/a'}"
)

readme = f"""---
library_name: numpy
base_model: {MODEL_ID}
tags:
- gemma
- gemma-4-e2b
- linear-probe
- security
- vulnerability-detection
- sven
datasets:
- bstee615/sven
---

# GemmaForge Weak Probe — Gemma 4 E2B on SVEN

Frozen `{MODEL_ID}` with a logistic-regression probe on the last-token
hidden state of decoder layer **{best_layer}** (of {n_layers}). Trained on
the SVEN position-paired training set
([`scripts/build_dataset_sven.py`](https://github.com/peaktwilight/gemmaforge/blob/main/scripts/build_dataset_sven.py)).
Companion to the strong-probe (Gemma 4 31B) head-to-head at
[`peaktwilight/gemmaforge-31b-probe`](https://huggingface.co/peaktwilight/gemmaforge-31b-probe).

## Files
- `probe_weak_sven.npz` — `(w, b, layer)`; `sigmoid(w @ activation + b)` = risk.
- `probe_weak_sven_card.json` — per-layer AUC/ACC from `src.train_probe`.
- `eval_weak_sven.json` — five-split AUC matrix + held-out SVEN sanity check.

## Headline

| Split | AUC | ACC |
|---|---:|---:|
| Random stratified (leaky)   | {_fmt(random_baseline['auc'])} | {_fmt(random_baseline['acc'])} |
| Group split (file / func)   | {_fmt(group_repo['auc'])} | {_fmt(group_repo['acc'])} |
| Held-out CWE (worst)        | {_fmt(worst_auc)} | — |
| Held-out lang (worst credible) | see `eval_weak_sven.json` | — |

Held-out `dataset_sven_heldout.jsonl` (272 vulnerable completions, single-class):
{heldout_line}

Training data: `data/pairs_sven_train.jsonl` ({len(rows)} rows, balanced).
Layer candidates: {LAYER_CANDIDATES} (25/50/75/100% of {n_layers}).

## Reproduce

```python
from huggingface_hub import hf_hub_download
import numpy as np
npz = np.load(hf_hub_download("{OUT_REPO_ID}", "probe_weak_sven.npz"))
w, b, layer = npz["w"], float(npz["b"]), int(npz["layer"])
# risk = sigmoid(w @ hidden_states[layer + 1][0, -1, :] + b)
```

Pipeline: <https://github.com/peaktwilight/gemmaforge>.
Notebook: `notebooks/kaggle_train_probe_sven_weak.ipynb`.
"""

(BUNDLE_DIR / "README.md").write_text(readme)
print("Bundle contents:")
for p in sorted(BUNDLE_DIR.iterdir()):
    print(f"  {p.name}  ({p.stat().st_size} bytes)")

if PUSH_TO_HUB and HF_TOKEN:
    from huggingface_hub import HfApi
    api = HfApi(token=HF_TOKEN)
    api.create_repo(repo_id=OUT_REPO_ID, repo_type="model", private=OUT_REPO_PRIVATE, exist_ok=True)
    api.upload_folder(
        repo_id=OUT_REPO_ID, repo_type="model", folder_path=str(BUNDLE_DIR),
        commit_message=(
            f"Upload Gemma 4 E2B weak probe on SVEN "
            f"(layer {best_layer}/{n_layers}, random_AUC={random_baseline['auc']:.3f})"
        ),
    )
    print(f"\nUploaded to https://huggingface.co/{OUT_REPO_ID}")
elif PUSH_TO_HUB:
    print("PUSH_TO_HUB=True but no HF_TOKEN — skipping Hub upload.")
else:
    print("PUSH_TO_HUB=False — skipping Hub upload.")
print(f"Local artifacts at {BUNDLE_DIR}/  (also visible in Kaggle's Output tab).")

# %% [markdown]
# ## How To Run (recap)
#
# 1. Kaggle -> Import Notebook -> `notebooks/kaggle_train_probe_sven_weak.ipynb`.
# 2. Attach "Gemma 4 Good Hackathon" under Add or upload data.
# 3. Settings -> Accelerator -> **GPU T4** (x1 fine; x2 also works). CPU/TPU
#    won't work.
# 4. Secrets: `HF_TOKEN` (write-scoped, for push-to-hub), `GITHUB_TOKEN`
#    (`repo:read` while gemmaforge is private), optional `WANDB_API_KEY`.
# 5. Run All. Wall clock on T4 ~15-25 min (download 2-4 + extraction 8-15
#    + probe+eval 2-3 + push 1).
# 6. Output: `peaktwilight/gemmaforge-weak-sven-probe` on the Hub +
#    `/kaggle/working/bundle_weak_sven/` locally + the five-split AUC table
#    and SVEN held-out summary printed inline.
print("Done. See https://huggingface.co/" + OUT_REPO_ID)
