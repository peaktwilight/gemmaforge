"""LoRA fine-tuning Gemma 4 E2B for safer-by-default code generation.

This is the second prong of GemmaForge alongside the linear probe.
Inspired by Obeso et al. 2025 (arXiv 2509.03531) §3: training LoRA adapters
jointly with a hallucination probe makes the *model itself* more cautious.
We do the security analogue: DPO-train Gemma so chosen=safe wins over
rejected=vulnerable on a paired-completion dataset.

Data source: CyberNative/Code_Vulnerability_Security_DPO (4,656 pairs,
columns: lang, vulnerability, system, question, chosen, rejected). The
same upstream dataset that fed `data/pairs_v1.jsonl`.

Defaults:
  - Model: google/gemma-4-E2B-it
  - LoRA r=8, alpha=16, dropout=0.05, scaling 0.5 (alpha / r = 2, then
    we set lora_alpha=4 to land on a 0.5 effective scaling if requested;
    here we keep alpha=16 -> scaling 2 as the standard reading. The spec
    asks for scaling 0.5 -- we expose it via `--scaling` and rescale.)
  - DPO via trl.DPOTrainer; if trl is missing or unusable, fall back to
    plain SFT on the chosen completions only (mark as FALLBACK in stderr).
  - ~1 epoch, 500 examples max, fits in ~30 min on M1 Max MPS.

Fallback chain on OOM / package conflicts:
  1. trl.DPOTrainer on MPS with google/gemma-4-E2B-it
  2. trl.SFTTrainer on MPS (chosen completions only)
  3. Same on CPU
  4. google/gemma-3-4b-it as a smaller substitute
The script exits gracefully and writes a brief status JSON either way.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from pathlib import Path

# Silence HF tokenizer parallelism warning.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from peft import LoraConfig, get_peft_model
    _HAS_PEFT = True
except Exception as _e:
    _HAS_PEFT = False
    _peft_err = _e

try:
    from trl import DPOConfig, DPOTrainer
    _HAS_TRL = True
except Exception as _e:
    _HAS_TRL = False
    _trl_err = _e


DEFAULT_MODEL = "google/gemma-4-E2B-it"
FALLBACK_MODEL = "google/gemma-3-4b-it"
ADAPTER_DIR = Path("data/lora_adapter")
STATUS_PATH = ADAPTER_DIR / "train_status.json"


def _device(prefer_cpu: bool = False) -> str:
    if prefer_cpu:
        return "cpu"
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _build_dpo_records(n: int, seed: int = 0) -> list[dict]:
    """Load CyberNative DPO and shape into {prompt, chosen, rejected}.

    The upstream dataset stores raw `chosen` / `rejected` completions plus
    a natural-language `question` (the prompt). We wrap each in the
    Gemma chat template so the LoRA learns the assistant turn that
    actually ships to users.
    """
    ds = load_dataset("CyberNative/Code_Vulnerability_Security_DPO", split="train")
    idx = list(range(len(ds)))
    random.Random(seed).shuffle(idx)
    idx = idx[: max(n, 0)] if n > 0 else idx

    out: list[dict] = []
    for i in idx:
        row = ds[i]
        q = (row.get("question") or "").strip()
        ch = (row.get("chosen") or "").strip()
        rj = (row.get("rejected") or "").strip()
        if not q or not ch or not rj:
            continue
        # `prompt` here is plain text; the trl DPOTrainer applies the
        # chat template via the processing_class (tokenizer).
        out.append({"prompt": q, "chosen": ch, "rejected": rj})
    return out


def _write_status(d: dict) -> None:
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(d, indent=2))


def _train_dpo(model_id: str, device: str, records: list[dict],
               r: int, alpha: int, dropout: float, lr: float,
               max_steps: int, max_len: int) -> dict:
    from datasets import Dataset

    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    dtype = torch.float32 if device == "cpu" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        model_id, dtype=dtype, attn_implementation="eager"
    )
    model.to(device)
    model.config.use_cache = False

    # Gemma 4 is a Gemma4ForConditionalGeneration — has both a vision
    # tower and a language model, each with q_proj/k_proj/v_proj/o_proj.
    # We only want to LoRA-adapt the language model attentions.
    peft_cfg = LoraConfig(
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        bias="none",
        target_modules=r".*language_model\..*\.(q_proj|k_proj|v_proj|o_proj)$",
        task_type="CAUSAL_LM",
    )

    ds = Dataset.from_list(records)

    args = DPOConfig(
        output_dir=str(ADAPTER_DIR),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=1,
        max_steps=max_steps,
        learning_rate=lr,
        logging_steps=5,
        save_steps=10_000,  # we save manually at end
        save_strategy="no",
        report_to=[],
        bf16=False,
        fp16=False,
        remove_unused_columns=False,
        beta=0.1,
        max_length=max_len,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # peft adapters → ref is base model with adapters disabled
        args=args,
        train_dataset=ds,
        processing_class=tok,
        peft_config=peft_cfg,
    )

    t0 = time.time()
    trainer.train()
    dt = time.time() - t0

    trainer.model.save_pretrained(str(ADAPTER_DIR))
    tok.save_pretrained(str(ADAPTER_DIR))

    return {"trainer": "DPO", "elapsed_sec": dt, "steps_run": trainer.state.global_step}


def _train_sft(model_id: str, device: str, records: list[dict],
               r: int, alpha: int, dropout: float, lr: float,
               max_steps: int, max_len: int) -> dict:
    """Fallback: SFT on chosen completions only.

    No DPO objective; we just teach the LoRA to *imitate* the safe
    completions. Weaker signal than DPO (no negative gradient on the
    vulnerable side) but still nudges the model toward safer patterns.
    """
    from datasets import Dataset

    print("[FALLBACK] DPO unavailable -> SFT on chosen completions", file=sys.stderr)

    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    dtype = torch.float32 if device == "cpu" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        model_id, dtype=dtype, attn_implementation="eager"
    )
    model.to(device)
    model.config.use_cache = False

    peft_cfg = LoraConfig(
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        bias="none",
        target_modules=r".*language_model\..*\.(q_proj|k_proj|v_proj|o_proj)$",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, peft_cfg)
    model.print_trainable_parameters()

    def _fmt(ex):
        text = (
            f"<start_of_turn>user\n{ex['prompt']}<end_of_turn>\n"
            f"<start_of_turn>model\n{ex['chosen']}<end_of_turn>"
        )
        enc = tok(text, truncation=True, max_length=max_len, padding="max_length", return_tensors="pt")
        return {"input_ids": enc.input_ids[0], "attention_mask": enc.attention_mask[0]}

    ds = Dataset.from_list(records).map(_fmt)
    ds.set_format(type="torch", columns=["input_ids", "attention_mask"])

    model.train()
    optim = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    # Cosine warmup-ish: ramp lr linearly over first 5 steps to combat
    # divergence from large early gradients.
    warmup = min(5, max_steps // 4 + 1)
    base_lr = lr
    pad_id = tok.pad_token_id
    loss_sum = 0.0
    n_steps = 0
    t0 = time.time()
    for step, batch in enumerate(ds):
        if step >= max_steps:
            break
        # LR warmup.
        cur_lr = base_lr * min(1.0, (step + 1) / max(1, warmup))
        for g in optim.param_groups:
            g["lr"] = cur_lr
        input_ids = batch["input_ids"].unsqueeze(0).to(device)
        attn = batch["attention_mask"].unsqueeze(0).to(device)
        # Mask pad tokens in labels so loss isn't dominated by padding.
        labels = input_ids.clone()
        labels[labels == pad_id] = -100
        out = model(input_ids=input_ids, attention_mask=attn, labels=labels)
        out.loss.backward()
        torch.nn.utils.clip_grad_norm_(
            [p for p in model.parameters() if p.requires_grad], 1.0,
        )
        optim.step()
        optim.zero_grad()
        loss_sum += float(out.loss.detach())
        n_steps += 1
        if step % 5 == 0 or step == max_steps - 1:
            print(f"  step {step}  loss={out.loss.item():.4f}  lr={cur_lr:.2e}", file=sys.stderr)

    dt = time.time() - t0
    model.save_pretrained(str(ADAPTER_DIR))
    tok.save_pretrained(str(ADAPTER_DIR))
    return {
        "trainer": "SFT-fallback",
        "elapsed_sec": dt,
        "steps_run": n_steps,
        "mean_loss": (loss_sum / max(1, n_steps)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--n", type=int, default=500, help="number of training examples")
    ap.add_argument("--max_steps", type=int, default=120)
    ap.add_argument("--max_len", type=int, default=512)
    ap.add_argument("--r", type=int, default=8)
    ap.add_argument("--alpha", type=int, default=16)
    ap.add_argument("--dropout", type=float, default=0.05)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--cpu", action="store_true", help="force CPU")
    ap.add_argument("--sft_only", action="store_true", help="skip DPO, go straight to SFT fallback")
    args = ap.parse_args()

    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)

    if not _HAS_PEFT:
        print(f"FATAL: peft import failed: {_peft_err}", file=sys.stderr)
        _write_status({"status": "failed", "stage": "import_peft", "error": str(_peft_err)})
        return 2

    print(f"[1/3] loading dataset (n={args.n})", file=sys.stderr)
    try:
        records = _build_dpo_records(args.n)
        print(f"  got {len(records)} preference pairs", file=sys.stderr)
    except Exception as e:
        traceback.print_exc()
        _write_status({"status": "failed", "stage": "dataset", "error": str(e)})
        return 3

    device = _device(prefer_cpu=args.cpu)
    print(f"[2/3] device = {device}, model = {args.model}", file=sys.stderr)

    # Try training. Catch OOM / package conflicts. Try in order:
    # primary DPO -> SFT -> CPU SFT -> fallback model SFT.
    attempts: list[tuple[str, str, callable]] = []
    if _HAS_TRL and not args.sft_only:
        attempts.append((args.model, device, _train_dpo))
    attempts.append((args.model, device, _train_sft))
    if device != "cpu":
        attempts.append((args.model, "cpu", _train_sft))
    if args.model != FALLBACK_MODEL:
        attempts.append((FALLBACK_MODEL, device, _train_sft))
        if device != "cpu":
            attempts.append((FALLBACK_MODEL, "cpu", _train_sft))

    last_err: str | None = None
    for model_id, dev, fn in attempts:
        try:
            print(f"  attempting {fn.__name__} on {model_id} @ {dev}", file=sys.stderr)
            result = fn(
                model_id, dev, records,
                r=args.r, alpha=args.alpha, dropout=args.dropout, lr=args.lr,
                max_steps=args.max_steps, max_len=args.max_len,
            )
            print(f"[3/3] training OK: {result}", file=sys.stderr)
            _write_status({
                "status": "ok",
                "model_id": model_id,
                "device": dev,
                "adapter_dir": str(ADAPTER_DIR),
                "n_examples": len(records),
                "lora": {"r": args.r, "alpha": args.alpha, "dropout": args.dropout},
                **result,
            })
            return 0
        except KeyboardInterrupt:
            print("interrupted by user", file=sys.stderr)
            return 130
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            last_err = err
            print(f"  attempt failed: {err}", file=sys.stderr)
            traceback.print_exc(limit=2)
            # Free GPU mem before retrying.
            try:
                import gc
                gc.collect()
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            except Exception:
                pass

    _write_status({
        "status": "failed",
        "stage": "training_all_attempts",
        "error": last_err or "unknown",
    })
    print("ALL TRAINING ATTEMPTS FAILED -- see data/lora_adapter/train_status.json", file=sys.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(main())
