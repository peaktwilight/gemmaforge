"""Train a token-level value-head probe on a frozen Gemma layer, locally.

Local equivalent of `notebooks/colab_train_gemma4_probe.py`. Reads
`data/dataset.jsonl` (the SVEN-diff dataset built by `scripts/build_dataset.py`),
loads the base model frozen, trains a single linear value head on one decoder
layer with BCE + span-max loss, and writes the probe + card to disk.

Run on macOS (MPS), Linux (CUDA), or CPU:
    uv run scripts/train_value_head.py
    uv run scripts/train_value_head.py --model google/gemma-3-4b-it --epochs 1
    uv run scripts/train_value_head.py --max-rows 200 --max-length 512   # smoke
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = REPO_ROOT / "data" / "dataset.jsonl"
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "value_head_probe"

POSITIVE_TOKEN_FIELDS = ("evidence", "vulnerable_line", "sink", "source")
NEGATIVE_TOKEN_FIELDS = ("sanitizer",)


def pick_device(prefer_cpu: bool) -> torch.device:
    if prefer_cpu:
        return torch.device("cpu")
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def pick_dtype(device: torch.device) -> torch.dtype:
    if device.type == "cuda":
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    if device.type == "mps":
        return torch.float16
    return torch.float32


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_decoder_layers(model) -> list:
    inner = model
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
    raise ValueError(f"Could not find decoder layers for {type(model)}")


def validate_row(row: dict, idx: int) -> dict:
    missing = [k for k in ("code", "label", "token_labels") if k not in row]
    if missing:
        raise ValueError(f"Row {idx} missing keys: {missing}")
    if int(row["label"]) not in (0, 1):
        raise ValueError(f"Row {idx} has non-binary label: {row['label']!r}")
    if not isinstance(row["token_labels"], dict):
        raise ValueError(f"Row {idx} token_labels must be a dict")
    return row


def merge_token_spans(indices: list[int]) -> list[list[int]]:
    indices = sorted(set(indices))
    if not indices:
        return []
    spans, start, prev = [], indices[0], indices[0]
    for idx in indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            spans.append([start, prev])
            start = prev = idx
    spans.append([start, prev])
    return spans


def token_indices_for_char_span(offsets, start: int, end: int) -> list[int]:
    out = []
    for token_idx, (ts, te) in enumerate(offsets):
        if ts == te or te <= start or ts >= end:
            continue
        out.append(token_idx)
    return out


def apply_token_labels(row, labels, weights, offsets, pos_weight, neg_weight):
    code_len = len(row["code"])
    pos_indices, neg_indices = [], []

    def apply(fields, label, weight, sink):
        skipped = 0
        for field in fields:
            for span in row["token_labels"].get(field, []) or []:
                if not isinstance(span, (list, tuple)) or len(span) != 2:
                    skipped += 1
                    continue
                s, e = int(span[0]), int(span[1])
                if not (0 <= s < e <= code_len):
                    skipped += 1
                    continue
                tok_idx = token_indices_for_char_span(offsets, s, e)
                if not tok_idx:
                    skipped += 1
                    continue
                for i in tok_idx:
                    labels[i] = label
                    weights[i] = weight
                sink.extend(tok_idx)
        return skipped

    skipped = apply(NEGATIVE_TOKEN_FIELDS, 0.0, neg_weight, neg_indices)
    skipped += apply(POSITIVE_TOKEN_FIELDS, 1.0, pos_weight, pos_indices)
    # Positives override negatives if overlapping.
    for i in pos_indices:
        labels[i] = 1.0
        weights[i] = pos_weight
    return merge_token_spans(pos_indices), merge_token_spans(neg_indices), skipped


def row_group_key(row: dict) -> str:
    key = f"{row.get('_file_name') or ''}:{row.get('_func_name') or ''}"
    if key != ":":
        return key
    return hashlib.sha1(row["code"].encode("utf-8", errors="ignore")).hexdigest()


def split_rows(rows: list[dict], eval_fraction: float, seed: int) -> tuple[list, list]:
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row_group_key(row), []).append(row)
    keys = list(groups)
    random.Random(seed).shuffle(keys)
    n_eval = max(1, int(len(keys) * eval_fraction))
    eval_keys = set(keys[:n_eval])
    train_rows, eval_rows = [], []
    for k, grp in groups.items():
        (eval_rows if k in eval_keys else train_rows).extend(grp)
    return train_rows, eval_rows


class VulnerabilityTokenDataset(Dataset):
    def __init__(self, rows, tokenizer, max_length, pos_weight, neg_weight, safe_row_mode):
        self.items = []
        self.stats = {"positive_rows": 0, "safe_rows": 0, "skipped_rows": 0, "skipped_spans": 0}
        pad_id = tokenizer.pad_token_id
        for row in tqdm(rows, desc="Tokenizing"):
            enc = tokenizer(str(row["code"]), truncation=True, max_length=max_length,
                            return_offsets_mapping=True)
            offsets = enc.pop("offset_mapping")
            input_ids = enc["input_ids"]
            attention_mask = enc["attention_mask"]
            labels = [-100.0] * len(input_ids)
            weights = [0.0] * len(input_ids)
            pos_spans, neg_spans, skipped = apply_token_labels(
                row, labels, weights, offsets, pos_weight, neg_weight,
            )
            self.stats["skipped_spans"] += skipped

            if int(row["label"]) == 1:
                self.stats["positive_rows"] += 1
                if not pos_spans:
                    self.stats["skipped_rows"] += 1
                    continue
            else:
                self.stats["safe_rows"] += 1
                valid = [i for i, m in enumerate(attention_mask) if m == 1 and input_ids[i] != pad_id]
                if safe_row_mode == "last_token":
                    valid = valid[-1:]
                for i in valid:
                    labels[i] = 0.0
                    weights[i] = neg_weight
                neg_spans.extend(merge_token_spans(valid))

            if not any(lab != -100.0 for lab in labels):
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


def make_collate(pad_id: int):
    def collate(batch):
        max_len = max(len(b["input_ids"]) for b in batch)
        out = {
            "input_ids": torch.full((len(batch), max_len), pad_id, dtype=torch.long),
            "attention_mask": torch.zeros((len(batch), max_len), dtype=torch.long),
            "labels": torch.full((len(batch), max_len), -100.0, dtype=torch.float32),
            "weights": torch.zeros((len(batch), max_len), dtype=torch.float32),
            "pos_spans": [],
            "neg_spans": [],
        }
        for i, b in enumerate(batch):
            n = len(b["input_ids"])
            out["input_ids"][i, :n] = b["input_ids"]
            out["attention_mask"][i, :n] = b["attention_mask"]
            out["labels"][i, :n] = b["labels"]
            out["weights"][i, :n] = b["weights"]
            out["pos_spans"].append(b["pos_spans"])
            out["neg_spans"].append(b["neg_spans"])
        return out
    return collate


class ValueHead(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.value_head = nn.Linear(hidden_size, 1)
        nn.init.normal_(self.value_head.weight, mean=0.0, std=0.01)
        nn.init.zeros_(self.value_head.bias)

    def forward(self, hidden):
        return self.value_head(hidden).squeeze(-1)


def probe_bce_loss(logits, labels, weights):
    valid = labels != -100.0
    if not valid.any():
        return logits.sum() * 0.0
    loss = F.binary_cross_entropy_with_logits(
        logits[valid].float(), labels[valid].float(),
        weight=weights[valid].float(), reduction="sum",
    )
    return loss / weights[valid].float().sum().clamp_min(1.0)


def span_max_loss(logits, pos_spans, neg_spans):
    losses = []
    for b in range(logits.shape[0]):
        for s, e in pos_spans[b]:
            if e < logits.shape[1]:
                losses.append(F.binary_cross_entropy_with_logits(
                    logits[b, s:e + 1].max(), logits.new_tensor(1.0)))
        for s, e in neg_spans[b]:
            if e < logits.shape[1]:
                losses.append(F.binary_cross_entropy_with_logits(
                    logits[b, s:e + 1].max(), logits.new_tensor(0.0)))
    return torch.stack(losses).mean() if losses else logits.sum() * 0.0


@torch.no_grad()
def get_hidden(model, batch, device, probe_layer):
    out = model(
        input_ids=batch["input_ids"].to(device),
        attention_mask=batch["attention_mask"].to(device),
        output_hidden_states=True,
        use_cache=False,
    )
    return out.hidden_states[probe_layer + 1].detach().to(device).float()


def evaluate(model, head, loader, device, probe_layer, threshold):
    head.eval()
    tok_probs, tok_preds, tok_labels = [], [], []
    span_probs, span_preds, span_labels = [], [], []
    losses = []
    with torch.no_grad():
        for batch in tqdm(loader, desc="Evaluating"):
            logits = head(get_hidden(model, batch, device, probe_layer))
            labels = batch["labels"].to(device)
            weights = batch["weights"].to(device)
            losses.append(float(probe_bce_loss(logits, labels, weights).cpu()))
            probs = torch.sigmoid(logits).float().cpu()
            preds = (probs >= threshold).float()
            valid = batch["labels"] != -100.0
            tok_probs.extend(probs[valid].numpy().tolist())
            tok_preds.extend(preds[valid].numpy().tolist())
            tok_labels.extend(batch["labels"][valid].numpy().tolist())
            for b in range(probs.shape[0]):
                for s, e in batch["pos_spans"][b]:
                    if e < probs.shape[1]:
                        p = float(probs[b, s:e + 1].max())
                        span_probs.append(p); span_preds.append(float(p >= threshold)); span_labels.append(1.0)
                for s, e in batch["neg_spans"][b]:
                    if e < probs.shape[1]:
                        p = float(probs[b, s:e + 1].max())
                        span_probs.append(p); span_preds.append(float(p >= threshold)); span_labels.append(0.0)

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

    result = {"probe_loss": float(np.mean(losses)) if losses else None, "threshold": threshold}
    result.update(metrics("token", tok_labels, tok_preds, tok_probs))
    result.update(metrics("span_max", span_labels, span_preds, span_probs))
    return result


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--model", default="google/gemma-4-E2B-it")
    ap.add_argument("--hf-token", default=None, help="HF access token (or use HF_TOKEN env).")
    ap.add_argument("--cpu", action="store_true", help="Force CPU even if CUDA/MPS available.")
    ap.add_argument("--max-rows", type=int, default=None, help="Cap rows loaded from the dataset.")
    ap.add_argument("--max-length", type=int, default=1024)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--train-batch-size", type=int, default=2)
    ap.add_argument("--eval-batch-size", type=int, default=2)
    ap.add_argument("--learning-rate", type=float, default=3e-3)
    ap.add_argument("--gradient-accumulation-steps", type=int, default=1)
    ap.add_argument("--max-train-steps", type=int, default=None)
    ap.add_argument("--eval-fraction", type=float, default=0.2)
    ap.add_argument("--probe-layer", type=int, default=None,
                    help="Absolute decoder layer index (0-based). Overrides --probe-layer-fraction.")
    ap.add_argument("--probe-layer-fraction", type=float, default=0.25)
    ap.add_argument("--pos-weight", type=float, default=8.0)
    ap.add_argument("--neg-weight", type=float, default=1.0)
    ap.add_argument("--span-max-loss-weight", type=float, default=0.5)
    ap.add_argument("--safe-row-mode", choices=("all_tokens", "last_token"), default="all_tokens")
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=7)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    seed_everything(args.seed)

    device = pick_device(args.cpu)
    dtype = pick_dtype(device)
    print(f"[train] device={device} dtype={dtype} torch={torch.__version__}", file=sys.stderr)

    import os
    hf_token = args.hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HF_WRITE_TOKEN")

    if not args.dataset.exists():
        print(f"[train] dataset not found: {args.dataset}\n"
              f"        build it first with: uv run scripts/build_dataset.py", file=sys.stderr)
        return 1

    tokenizer = AutoTokenizer.from_pretrained(args.model, token=hf_token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    if not getattr(tokenizer, "is_fast", False):
        raise RuntimeError("A fast tokenizer is required for character-offset labels.")

    model_kwargs = {"torch_dtype": dtype, "attn_implementation": "eager"}
    if device.type == "cuda":
        model_kwargs["device_map"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(args.model, token=hf_token, **model_kwargs)
    if device.type != "cuda":
        model = model.to(device)
    model.eval()
    if hasattr(model.config, "use_cache"):
        model.config.use_cache = False
    for p in model.parameters():
        p.requires_grad_(False)
    print(f"[train] loaded {args.model} on {device}", file=sys.stderr)

    decoder_layers = get_decoder_layers(model)
    n_layers = len(decoder_layers)
    if args.probe_layer is None:
        probe_layer = int(n_layers * args.probe_layer_fraction)
    else:
        probe_layer = int(args.probe_layer)
    probe_layer = min(max(probe_layer, 0), n_layers - 1)
    print(f"[train] decoder_layers={n_layers} probe_layer={probe_layer}", file=sys.stderr)
    hidden_size = getattr(model.config, "hidden_size", None) or model.get_input_embeddings().weight.shape[1]

    rows: list[dict] = []
    with args.dataset.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            rows.append(validate_row(json.loads(line), i))
            if args.max_rows is not None and len(rows) >= args.max_rows:
                break
    print(f"[train] loaded {len(rows)} rows from {args.dataset}", file=sys.stderr)

    train_rows, eval_rows = split_rows(rows, args.eval_fraction, args.seed)
    train_ds = VulnerabilityTokenDataset(
        train_rows, tokenizer, args.max_length, args.pos_weight, args.neg_weight, args.safe_row_mode,
    )
    eval_ds = VulnerabilityTokenDataset(
        eval_rows, tokenizer, args.max_length, args.pos_weight, args.neg_weight, args.safe_row_mode,
    )
    print(f"[train] rows total={len(rows)} train={len(train_rows)} eval={len(eval_rows)}", file=sys.stderr)
    print(f"[train] train items={len(train_ds)} stats={train_ds.stats}", file=sys.stderr)
    print(f"[train] eval  items={len(eval_ds)} stats={eval_ds.stats}", file=sys.stderr)
    if not train_ds or not eval_ds:
        print("[train] empty train/eval dataset after tokenization", file=sys.stderr)
        return 1

    collate = make_collate(tokenizer.pad_token_id)
    train_loader = DataLoader(train_ds, batch_size=args.train_batch_size, shuffle=True, collate_fn=collate)
    eval_loader = DataLoader(eval_ds, batch_size=args.eval_batch_size, shuffle=False, collate_fn=collate)

    head = ValueHead(hidden_size).to(device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=args.learning_rate)
    global_step = 0
    started = time.time()

    for epoch in range(args.epochs):
        head.train()
        pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{args.epochs}")
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(pbar):
            hidden = get_hidden(model, batch, device, probe_layer)
            logits = head(hidden)
            labels = batch["labels"].to(device)
            weights = batch["weights"].to(device)
            bce = probe_bce_loss(logits, labels, weights)
            smax = span_max_loss(logits, batch["pos_spans"], batch["neg_spans"])
            loss = bce + args.span_max_loss_weight * smax
            (loss / args.gradient_accumulation_steps).backward()
            if (step + 1) % args.gradient_accumulation_steps == 0:
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1
            pbar.set_postfix(loss=float(loss.detach().cpu()),
                             bce=float(bce.detach().cpu()),
                             span=float(smax.detach().cpu()))
            if args.max_train_steps is not None and global_step >= args.max_train_steps:
                break
        if args.max_train_steps is not None and global_step >= args.max_train_steps:
            break

    train_minutes = (time.time() - started) / 60.0
    print(f"[train] training done in {train_minutes:.1f} min, steps={global_step}", file=sys.stderr)

    eval_metrics = evaluate(model, head, eval_loader, device, probe_layer, args.threshold)
    print(json.dumps(eval_metrics, indent=2))

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(head.state_dict(), out_dir / "probe_head.bin")
    w = head.value_head.weight.detach().float().cpu().numpy()[0]
    b = float(head.value_head.bias.detach().float().cpu().numpy()[0])
    np.savez_compressed(
        out_dir / "probe.npz",
        w=w.astype(np.float32),
        b=np.float32(b),
        layer=np.int32(probe_layer),
        model_id=args.model,
        max_length=np.int32(args.max_length),
    )
    probe_config = {
        "format": "gemmaforge_value_head_v1",
        "model_id": args.model,
        "layer_idx": probe_layer,
        "num_layers": n_layers,
        "hidden_size": hidden_size,
        "max_length": args.max_length,
        "threshold": args.threshold,
        "positive_token_fields": list(POSITIVE_TOKEN_FIELDS),
        "negative_token_fields": list(NEGATIVE_TOKEN_FIELDS),
    }
    (out_dir / "probe_config.json").write_text(json.dumps(probe_config, indent=2))

    probe_card = {
        **probe_config,
        "dataset_path": str(args.dataset),
        "dataset_rows": len(rows),
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "train_items": len(train_ds),
        "eval_items": len(eval_ds),
        "train_stats": train_ds.stats,
        "eval_stats": eval_ds.stats,
        "training": {
            "epochs": args.epochs,
            "steps": global_step,
            "learning_rate": args.learning_rate,
            "span_max_loss_weight": args.span_max_loss_weight,
            "pos_weight": args.pos_weight,
            "neg_weight": args.neg_weight,
            "minutes": round(train_minutes, 2),
            "device": str(device),
            "dtype": str(dtype),
        },
        "metrics": eval_metrics,
    }
    (out_dir / "probe_card.json").write_text(json.dumps(probe_card, indent=2))
    (out_dir / "eval_results.json").write_text(json.dumps(eval_metrics, indent=2))

    print(f"[train] saved probe to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
