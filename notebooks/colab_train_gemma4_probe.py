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
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # GemmaForge Value-Head Probe Training
#
# Colab-friendly token-level probe training for the rebuilt `scripts/build_dataset.py`
# schema. The base Gemma model is frozen; only a linear value head is trained on a
# selected decoder layer, following the core Obalcells pattern without LoRA complexity.

# %%
from pathlib import Path

REPO_URL = "https://github.com/peaktwilight/gemmaforge.git"
BRANCH = "main"
WORKDIR = Path("/content/gemmaforge")

MODEL_ID = "google/gemma-4-E2B-it"
HF_REPO_ID = "peaktwilight/gemmaforge-gemma4-probe"
HF_PRIVATE_REPO = False
PUSH_TO_HUB = True

DATASET_PATH = None
BUILT_DATASET_PATH = WORKDIR / "data" / "dataset.jsonl"
BUILD_MAX_ROWS = None
BUILD_LANGS = []
BUILD_CWES = []

MAX_LENGTH = 1024
POSITIVE_TOKEN_FIELDS = ("evidence", "vulnerable_line", "sink", "source")
NEGATIVE_TOKEN_FIELDS = ("sanitizer",)
SAFE_ROW_NEGATIVE_MODE = "all_tokens"  # "all_tokens" or "last_token"
POS_WEIGHT = 8.0
NEG_WEIGHT = 1.0

PROBE_LAYER = None
PROBE_LAYER_FRACTION = 0.25
TRAIN_BATCH_SIZE = 2
EVAL_BATCH_SIZE = 2
NUM_EPOCHS = 2
LEARNING_RATE = 3e-3
SPAN_MAX_LOSS_WEIGHT = 0.5
GRADIENT_ACCUMULATION_STEPS = 1
MAX_TRAIN_STEPS = None
EVAL_FRACTION = 0.2
RANDOM_SEED = 7
THRESHOLD = 0.5

INSTALL_TRANSFORMERS_FROM_GIT = False

# %% [markdown]
# ## Install
#
# Installs `torch`, `torchvision`, and `torchaudio` from the same PyTorch
# nightly CUDA 12.1 wheel index so compiled torchvision ops match torch. If
# torch or torchvision were already imported in this runtime, restart Colab
# once after this cell finishes, then rerun from the top.

# %%
import importlib
import os
import subprocess
import sys


def run(cmd, cwd=None, env=None, display_cmd=None):
    shown = display_cmd if display_cmd is not None else cmd
    print(f"$ {' '.join(map(str, shown))}")
    return subprocess.run(cmd, cwd=cwd, env=env, check=True)


PYTORCH_INDEX_URL = "https://download.pytorch.org/whl/nightly/cu121"
torch_stack_already_loaded = any(
    name == "torch" or name.startswith(("torch.", "torchvision", "torchaudio"))
    for name in sys.modules
)

os.environ["USE_TORCHVISION"] = "1"
os.environ.pop("TRANSFORMERS_NO_TORCHVISION", None)

run([
    sys.executable,
    "-m",
    "pip",
    "install",
    "-q",
    "-U",
    "--pre",
    "--index-url",
    PYTORCH_INDEX_URL,
    "torch",
    "torchvision",
    "torchaudio",
])
packages = [
    "accelerate>=0.34",
    "datasets>=2.20",
    "huggingface_hub>=0.24",
    "numpy>=1.26",
    "scikit-learn>=1.5",
    "tqdm>=4.65",
]
transformers_pkg = "git+https://github.com/huggingface/transformers.git" if INSTALL_TRANSFORMERS_FROM_GIT else "transformers>=5.8.1"
run([sys.executable, "-m", "pip", "install", "-q", "-U", transformers_pkg, *packages])
if torch_stack_already_loaded:
    print("Restart the Colab runtime now so Python loads the newly installed torch/torchvision wheels.")
else:
    torch = importlib.import_module("torch")
    torchvision = importlib.import_module("torchvision")

    print(f"torch={torch.__version__} torchvision={torchvision.__version__} cuda={torch.version.cuda}")

# %% [markdown]
# ## Auth

# %%
from huggingface_hub import login


def get_optional_secret(name):
    value = os.environ.get(name)
    if value:
        return value
    try:
        from google.colab import userdata  # type: ignore

        value = userdata.get(name)
        if value:
            os.environ[name] = value
            return value
    except Exception:
        pass
    return None


HF_TOKEN = get_optional_secret("HF_WRITE_TOKEN") or get_optional_secret("HF_TOKEN")
if HF_TOKEN:
    login(token=HF_TOKEN)
    print("Logged in to Hugging Face Hub.")
else:
    print("No HF token found; gated model access or upload may fail.")

# %% [markdown]
# ## Clone And Build Dataset

# %%
github_token = get_optional_secret("GITHUB_TOKEN")
repo_url = REPO_URL
if github_token and REPO_URL.startswith("https://github.com/"):
    repo_url = REPO_URL.replace("https://", f"https://x-access-token:{github_token}@")

if WORKDIR.exists():
    run(["git", "fetch", "origin"], cwd=WORKDIR)
    run(["git", "checkout", BRANCH], cwd=WORKDIR)
    run(["git", "pull", "--ff-only", "origin", BRANCH], cwd=WORKDIR)
else:
    run(["git", "clone", "--branch", BRANCH, repo_url, str(WORKDIR)], display_cmd=["git", "clone", "--branch", BRANCH, REPO_URL, str(WORKDIR)])

os.chdir(WORKDIR)

if DATASET_PATH is None:
    build_cmd = [sys.executable, "scripts/build_dataset.py", "--out", str(BUILT_DATASET_PATH), "--seed", str(RANDOM_SEED)]
    if BUILD_MAX_ROWS is not None:
        build_cmd += ["--max-rows", str(BUILD_MAX_ROWS)]
    for lang in BUILD_LANGS:
        build_cmd += ["--lang", lang]
    for cwe in BUILD_CWES:
        build_cmd += ["--cwe", cwe]
    run(build_cmd, cwd=WORKDIR)
    dataset_path = BUILT_DATASET_PATH
else:
    dataset_path = Path(DATASET_PATH)

print(f"Dataset: {dataset_path}")

# %% [markdown]
# ## Imports And Model

# %%
import gc
import hashlib
import json
import os
import random
import time

os.environ["USE_TORCHVISION"] = "1"
os.environ.pop("TRANSFORMERS_NO_TORCHVISION", None)

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def pick_dtype():
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32


seed_everything(RANDOM_SEED)
torch_dtype = pick_dtype()
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} dtype={torch_dtype}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
if not getattr(tokenizer, "is_fast", False):
    raise RuntimeError("A fast tokenizer is required for character offset labels.")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN,
    torch_dtype=torch_dtype,
    device_map="auto",
    attn_implementation="eager",
)
model.eval()
if hasattr(model.config, "use_cache"):
    model.config.use_cache = False
for param in model.parameters():
    param.requires_grad_(False)

device = next(model.parameters()).device
print(f"Loaded {MODEL_ID} on {device}")

# %% [markdown]
# ## Token Dataset

# %%
def get_decoder_layers(m):
    inner = m
    for attr in ("model", "transformer", "language_model"):
        if hasattr(inner, attr):
            inner = getattr(inner, attr)
            if hasattr(inner, "layers") or hasattr(inner, "h"):
                break
    if hasattr(inner, "layers"):
        return list(inner.layers)
    if hasattr(inner, "h"):
        return list(inner.h)
    if hasattr(inner, "model") and hasattr(inner.model, "layers"):
        return list(inner.model.layers)
    raise ValueError(f"Could not find decoder layers for {type(m)}")


def choose_probe_layer(m):
    n_layers = len(get_decoder_layers(m))
    layer = int(n_layers * PROBE_LAYER_FRACTION) if PROBE_LAYER is None else int(PROBE_LAYER)
    layer = min(max(layer, 0), n_layers - 1)
    print(f"Decoder layers: {n_layers}; probe layer: {layer}")
    return layer, n_layers


def validate_row(row, idx):
    missing = [key for key in ("code", "label", "token_labels") if key not in row]
    if missing:
        raise ValueError(f"Row {idx} missing keys: {missing}")
    if int(row["label"]) not in (0, 1):
        raise ValueError(f"Row {idx} has non-binary label: {row['label']!r}")
    if not isinstance(row["token_labels"], dict):
        raise ValueError(f"Row {idx} token_labels must be a dict")
    return row


def merge_token_spans(indices):
    indices = sorted(set(indices))
    if not indices:
        return []
    spans = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            spans.append([start, prev])
            start = prev = idx
    spans.append([start, prev])
    return spans


def token_indices_for_char_span(offsets, start, end):
    out = []
    for token_idx, (token_start, token_end) in enumerate(offsets):
        if token_start == token_end:
            continue
        if token_end <= start or token_start >= end:
            continue
        out.append(token_idx)
    return out


def apply_token_labels(row, labels, weights, offsets):
    code_len = len(row["code"])
    pos_indices, neg_indices = [], []

    def apply(fields, label, weight):
        target = pos_indices if label == 1.0 else neg_indices
        skipped = 0
        for field in fields:
            for span in row["token_labels"].get(field, []) or []:
                if not isinstance(span, (list, tuple)) or len(span) != 2:
                    skipped += 1
                    continue
                start, end = int(span[0]), int(span[1])
                if not (0 <= start < end <= code_len):
                    skipped += 1
                    continue
                token_indices = token_indices_for_char_span(offsets, start, end)
                if not token_indices:
                    skipped += 1
                    continue
                for token_idx in token_indices:
                    labels[token_idx] = label
                    weights[token_idx] = weight
                target.extend(token_indices)
        return skipped

    skipped = apply(NEGATIVE_TOKEN_FIELDS, 0.0, NEG_WEIGHT)
    skipped += apply(POSITIVE_TOKEN_FIELDS, 1.0, POS_WEIGHT)
    for token_idx in pos_indices:
        labels[token_idx] = 1.0
        weights[token_idx] = POS_WEIGHT
    return merge_token_spans(pos_indices), merge_token_spans(neg_indices), skipped


def row_group_key(row):
    key = f"{row.get('_file_name') or ''}:{row.get('_func_name') or ''}"
    if key != ":":
        return key
    return hashlib.sha1(row["code"].encode("utf-8", errors="ignore")).hexdigest()


def split_rows(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row_group_key(row), []).append(row)
    keys = list(groups)
    random.Random(RANDOM_SEED).shuffle(keys)
    n_eval = max(1, int(len(keys) * EVAL_FRACTION))
    eval_keys = set(keys[:n_eval])
    train_rows, eval_rows = [], []
    for key, group_rows in groups.items():
        (eval_rows if key in eval_keys else train_rows).extend(group_rows)
    return train_rows, eval_rows


class VulnerabilityTokenDataset(Dataset):
    def __init__(self, rows, tokenizer, max_length):
        self.items = []
        self.stats = {"positive_rows": 0, "safe_rows": 0, "skipped_rows": 0, "skipped_spans": 0}
        for row in tqdm(rows, desc="Tokenizing"):
            encoded = tokenizer(str(row["code"]), truncation=True, max_length=max_length, return_offsets_mapping=True)
            offsets = encoded.pop("offset_mapping")
            input_ids = encoded["input_ids"]
            attention_mask = encoded["attention_mask"]
            labels = [-100.0] * len(input_ids)
            weights = [0.0] * len(input_ids)
            pos_spans, neg_spans, skipped = apply_token_labels(row, labels, weights, offsets)
            self.stats["skipped_spans"] += skipped

            if int(row["label"]) == 1:
                self.stats["positive_rows"] += 1
                if not pos_spans:
                    self.stats["skipped_rows"] += 1
                    continue
            else:
                self.stats["safe_rows"] += 1
                valid = [i for i, mask in enumerate(attention_mask) if mask == 1 and input_ids[i] != tokenizer.pad_token_id]
                if SAFE_ROW_NEGATIVE_MODE == "last_token":
                    valid = valid[-1:]
                for token_idx in valid:
                    labels[token_idx] = 0.0
                    weights[token_idx] = NEG_WEIGHT
                neg_spans.extend(merge_token_spans(valid))

            if not any(label != -100.0 for label in labels):
                self.stats["skipped_rows"] += 1
                continue
            self.items.append({
                "input_ids": torch.tensor(input_ids, dtype=torch.long),
                "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
                "labels": torch.tensor(labels, dtype=torch.float32),
                "weights": torch.tensor(weights, dtype=torch.float32),
                "pos_spans": pos_spans,
                "neg_spans": neg_spans,
            })

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        return self.items[idx]


def collate_batch(batch):
    max_len = max(len(item["input_ids"]) for item in batch)
    pad_id = tokenizer.pad_token_id
    out = {
        "input_ids": torch.full((len(batch), max_len), pad_id, dtype=torch.long),
        "attention_mask": torch.zeros((len(batch), max_len), dtype=torch.long),
        "labels": torch.full((len(batch), max_len), -100.0, dtype=torch.float32),
        "weights": torch.zeros((len(batch), max_len), dtype=torch.float32),
        "pos_spans": [],
        "neg_spans": [],
    }
    for i, item in enumerate(batch):
        n = len(item["input_ids"])
        out["input_ids"][i, :n] = item["input_ids"]
        out["attention_mask"][i, :n] = item["attention_mask"]
        out["labels"][i, :n] = item["labels"]
        out["weights"][i, :n] = item["weights"]
        out["pos_spans"].append(item["pos_spans"])
        out["neg_spans"].append(item["neg_spans"])
    return out


rows = [validate_row(json.loads(line), i) for i, line in enumerate(dataset_path.read_text().splitlines()) if line.strip()]
train_rows, eval_rows = split_rows(rows)
train_dataset = VulnerabilityTokenDataset(train_rows, tokenizer, MAX_LENGTH)
eval_dataset = VulnerabilityTokenDataset(eval_rows, tokenizer, MAX_LENGTH)
print(f"Rows total={len(rows)} train={len(train_rows)} eval={len(eval_rows)}")
print(f"Train items={len(train_dataset)} stats={train_dataset.stats}")
print(f"Eval items={len(eval_dataset)} stats={eval_dataset.stats}")
if not train_dataset or not eval_dataset:
    raise RuntimeError("Empty train/eval dataset after tokenization")

train_loader = DataLoader(train_dataset, batch_size=TRAIN_BATCH_SIZE, shuffle=True, collate_fn=collate_batch)
eval_loader = DataLoader(eval_dataset, batch_size=EVAL_BATCH_SIZE, shuffle=False, collate_fn=collate_batch)
probe_layer, num_layers = choose_probe_layer(model)
hidden_size = getattr(model.config, "hidden_size", None) or model.get_input_embeddings().weight.shape[1]

# %% [markdown]
# ## Train

# %%
class ValueHead(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.value_head = nn.Linear(hidden_size, 1)
        nn.init.normal_(self.value_head.weight, mean=0.0, std=0.01)
        nn.init.zeros_(self.value_head.bias)

    def forward(self, hidden):
        return self.value_head(hidden).squeeze(-1)


@torch.no_grad()
def get_hidden(batch):
    outputs = model(
        input_ids=batch["input_ids"].to(device),
        attention_mask=batch["attention_mask"].to(device),
        output_hidden_states=True,
        use_cache=False,
    )
    return outputs.hidden_states[probe_layer + 1].detach().to(device).float()


def probe_bce_loss(logits, labels, weights):
    valid = labels != -100.0
    if not valid.any():
        return logits.sum() * 0.0
    loss = F.binary_cross_entropy_with_logits(logits[valid].float(), labels[valid].float(), weight=weights[valid].float(), reduction="sum")
    return loss / weights[valid].float().sum().clamp_min(1.0)


def span_max_loss(logits, pos_spans, neg_spans):
    losses = []
    for batch_idx in range(logits.shape[0]):
        for start, end in pos_spans[batch_idx]:
            if end < logits.shape[1]:
                losses.append(F.binary_cross_entropy_with_logits(logits[batch_idx, start:end + 1].max(), logits.new_tensor(1.0)))
        for start, end in neg_spans[batch_idx]:
            if end < logits.shape[1]:
                losses.append(F.binary_cross_entropy_with_logits(logits[batch_idx, start:end + 1].max(), logits.new_tensor(0.0)))
    return torch.stack(losses).mean() if losses else logits.sum() * 0.0


head = ValueHead(hidden_size).to(device)
optimizer = torch.optim.AdamW(head.parameters(), lr=LEARNING_RATE)
global_step = 0
started = time.time()

for epoch in range(NUM_EPOCHS):
    head.train()
    pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{NUM_EPOCHS}")
    optimizer.zero_grad(set_to_none=True)
    for step, batch in enumerate(pbar):
        hidden = get_hidden(batch)
        logits = head(hidden)
        labels = batch["labels"].to(device)
        weights = batch["weights"].to(device)
        bce = probe_bce_loss(logits, labels, weights)
        smax = span_max_loss(logits, batch["pos_spans"], batch["neg_spans"])
        loss = bce + SPAN_MAX_LOSS_WEIGHT * smax
        (loss / GRADIENT_ACCUMULATION_STEPS).backward()
        if (step + 1) % GRADIENT_ACCUMULATION_STEPS == 0:
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            global_step += 1
        pbar.set_postfix(loss=float(loss.detach().cpu()), bce=float(bce.detach().cpu()), span=float(smax.detach().cpu()))
        if MAX_TRAIN_STEPS is not None and global_step >= MAX_TRAIN_STEPS:
            break
    if MAX_TRAIN_STEPS is not None and global_step >= MAX_TRAIN_STEPS:
        break

print(f"Training finished in {(time.time() - started) / 60:.1f} min, steps={global_step}")

# %% [markdown]
# ## Evaluate

# %%
@torch.no_grad()
def evaluate_loader(loader):
    head.eval()
    token_probs, token_preds, token_labels = [], [], []
    span_probs, span_preds, span_labels = [], [], []
    losses = []
    for batch in tqdm(loader, desc="Evaluating"):
        logits = head(get_hidden(batch))
        labels = batch["labels"].to(device)
        weights = batch["weights"].to(device)
        losses.append(float(probe_bce_loss(logits, labels, weights).cpu()))
        probs = torch.sigmoid(logits).float().cpu()
        preds = (probs >= THRESHOLD).float()
        valid = batch["labels"] != -100.0
        token_probs.extend(probs[valid].numpy().tolist())
        token_preds.extend(preds[valid].numpy().tolist())
        token_labels.extend(batch["labels"][valid].numpy().tolist())
        for batch_idx in range(probs.shape[0]):
            for start, end in batch["pos_spans"][batch_idx]:
                if end < probs.shape[1]:
                    p = float(probs[batch_idx, start:end + 1].max())
                    span_probs.append(p); span_preds.append(float(p >= THRESHOLD)); span_labels.append(1.0)
            for start, end in batch["neg_spans"][batch_idx]:
                if end < probs.shape[1]:
                    p = float(probs[batch_idx, start:end + 1].max())
                    span_probs.append(p); span_preds.append(float(p >= THRESHOLD)); span_labels.append(0.0)

    def metrics(prefix, labels, preds, probs):
        out = {f"{prefix}_count": len(labels)}
        if labels:
            out[f"{prefix}_accuracy"] = float(accuracy_score(labels, preds))
            out[f"{prefix}_precision"] = float(precision_score(labels, preds, zero_division=0))
            out[f"{prefix}_recall"] = float(recall_score(labels, preds, zero_division=0))
            out[f"{prefix}_f1"] = float(f1_score(labels, preds, zero_division=0))
            out[f"{prefix}_pos_rate"] = float(np.mean(labels))
            if len(set(labels)) > 1:
                out[f"{prefix}_auc"] = float(roc_auc_score(labels, probs))
        return out

    result = {"probe_loss": float(np.mean(losses)) if losses else None, "threshold": THRESHOLD}
    result.update(metrics("token", token_labels, token_preds, token_probs))
    result.update(metrics("span_max", span_labels, span_preds, span_probs))
    return result


eval_metrics = evaluate_loader(eval_loader)
print(json.dumps(eval_metrics, indent=2))

# %% [markdown]
# ## Save And Upload

# %%
probe_dir = WORKDIR / "data" / "gemma4_value_head_probe"
probe_dir.mkdir(parents=True, exist_ok=True)

torch.save(head.state_dict(), probe_dir / "probe_head.bin")
w = head.value_head.weight.detach().float().cpu().numpy()[0]
b = float(head.value_head.bias.detach().float().cpu().numpy()[0])
np.savez_compressed(probe_dir / "probe.npz", w=w.astype(np.float32), b=np.float32(b), layer=np.int32(probe_layer), model_id=MODEL_ID, max_length=np.int32(MAX_LENGTH))

probe_config = {
    "format": "gemmaforge_value_head_v1",
    "model_id": MODEL_ID,
    "layer_idx": probe_layer,
    "num_layers": num_layers,
    "hidden_size": hidden_size,
    "max_length": MAX_LENGTH,
    "threshold": THRESHOLD,
    "positive_token_fields": list(POSITIVE_TOKEN_FIELDS),
    "negative_token_fields": list(NEGATIVE_TOKEN_FIELDS),
}
(probe_dir / "probe_config.json").write_text(json.dumps(probe_config, indent=2))

probe_card = {
    **probe_config,
    "dataset_path": str(dataset_path),
    "dataset_rows": len(rows),
    "train_rows": len(train_rows),
    "eval_rows": len(eval_rows),
    "train_items": len(train_dataset),
    "eval_items": len(eval_dataset),
    "train_stats": train_dataset.stats,
    "eval_stats": eval_dataset.stats,
    "training": {"epochs": NUM_EPOCHS, "steps": global_step, "learning_rate": LEARNING_RATE, "span_max_loss_weight": SPAN_MAX_LOSS_WEIGHT, "pos_weight": POS_WEIGHT, "neg_weight": NEG_WEIGHT},
    "metrics": eval_metrics,
}
(probe_dir / "probe_card.json").write_text(json.dumps(probe_card, indent=2))
(probe_dir / "eval_results.json").write_text(json.dumps(eval_metrics, indent=2))

readme = f"""---
library_name: transformers
tags:
- gemma
- gemma-4
- value-head
- token-classification
- security
---

# GemmaForge Gemma 4 Value-Head Probe

Frozen `{MODEL_ID}` with a trained linear value head on decoder layer `{probe_layer}`.

```json
{json.dumps(eval_metrics, indent=2)}
```
"""
(probe_dir / "README.md").write_text(readme)

print(f"Saved {probe_dir}")
print(sorted(path.name for path in probe_dir.iterdir()))

if PUSH_TO_HUB:
    from huggingface_hub import HfApi

    if not HF_TOKEN:
        raise RuntimeError("PUSH_TO_HUB=True but no HF token was found.")
    api = HfApi(token=HF_TOKEN)
    api.create_repo(repo_id=HF_REPO_ID, repo_type="model", private=HF_PRIVATE_REPO, exist_ok=True)
    api.upload_folder(repo_id=HF_REPO_ID, repo_type="model", folder_path=str(probe_dir), commit_message=f"Upload GemmaForge value-head probe trained on {MODEL_ID}")
    print(f"Uploaded to https://huggingface.co/{HF_REPO_ID}")
else:
    print("PUSH_TO_HUB=False, skipping upload.")

# %%
# del model
# gc.collect()
