"""Tier 2 cascade — strong-probe re-scoring of Tier 1 leads.

Reads ``gemmaforge.leads/v1`` ND-JSON on stdin (or ``--in``), re-scores each
record with the strong probe (Gemma 4 E4B + ``data/probe_strong.npz``,
layer 10 by default), and emits ``gemmaforge.scored/v1`` ND-JSON with a
``cascade.decision`` field that the Tier 3 verifier (pwnkit) filters on.

Spec: ``docs/pipeline-contract.md``.

Usage::

    python -m src.cascade < leads.jsonl > scored.jsonl
    python -m src.cascade --in leads.jsonl --out scored.jsonl --model google/gemma-4-E4B-it
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch


SCHEMA_IN = "gemmaforge.leads/v1"
SCHEMA_OUT = "gemmaforge.scored/v1"

DEFAULT_MODEL = "google/gemma-4-E4B-it"
DEFAULT_PROBE = Path("data/probe_strong.npz")

PROMOTE_THRESHOLD = 0.85
DROP_THRESHOLD = 0.30


class StrongProbe:
    """Gemma 4 E4B + linear probe head. Scores snippets with the same
    sigmoid(w·h + b) head as the weak probe, just on the larger backbone."""

    def __init__(self, model_id: str, probe_path: Path):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        npz = np.load(probe_path)
        self.w = npz["w"].astype(np.float32)
        self.b = float(npz["b"])
        self.layer = int(npz["layer"])
        self.model_id = model_id

        if torch.cuda.is_available():
            self.device, self.dtype = "cuda", torch.bfloat16
        elif torch.backends.mps.is_available():
            self.device, self.dtype = "mps", torch.float16
        else:
            self.device, self.dtype = "cpu", torch.float32

        print(
            f"[cascade] loading {model_id} on {self.device} ({self.dtype})...",
            file=sys.stderr,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = (
            AutoModelForCausalLM.from_pretrained(
                model_id, dtype=self.dtype, attn_implementation="eager"
            )
            .to(self.device)
            .eval()
        )
        print(
            f"[cascade] probe layer={self.layer}  dim={self.w.shape[0]}  b={self.b:.4f}",
            file=sys.stderr,
        )

    @torch.inference_mode()
    def score(self, snippet: str) -> float:
        ids = self.tokenizer.encode(
            snippet, return_tensors="pt", truncation=True, max_length=512
        ).to(self.device)
        out = self.model(ids, output_hidden_states=True, use_cache=False)
        h = out.hidden_states[self.layer + 1][0, -1, :].detach().to("cpu").float().numpy()
        logit = float(self.w @ h + self.b)
        return float(1.0 / (1.0 + np.exp(-logit)))


def decide(strong_conf: float) -> tuple[str, str]:
    if strong_conf >= PROMOTE_THRESHOLD:
        return ("promote", f"strong_confidence>={PROMOTE_THRESHOLD}")
    if strong_conf < DROP_THRESHOLD:
        return ("drop", f"strong_confidence<{DROP_THRESHOLD}")
    return ("defer", f"strong_confidence in [{DROP_THRESHOLD}, {PROMOTE_THRESHOLD})")


def score_one(lead: dict, probe: StrongProbe) -> dict:
    """Take a leads/v1 record, return scored/v1 with Tier 2 appended."""
    strong_conf = probe.score(lead["snippet"])

    weak_score = {
        "tier": 1,
        "model_id": lead.get("model_id", "google/gemma-4-E2B-it"),
        "probe": "weak",
        "layer": lead.get("gemmaforge_layer"),
        "confidence": lead.get("gemmaforge_confidence"),
        "top_cwe": lead.get("gemmaforge_top_cwe"),
        "ts": lead.get("ts", time.time()),
    }
    strong_score = {
        "tier": 2,
        "model_id": probe.model_id,
        "probe": "strong",
        "layer": probe.layer,
        "confidence": strong_conf,
        "ts": time.time(),
    }
    decision, reason = decide(strong_conf)

    return {
        "schema": SCHEMA_OUT,
        "file": lead["file"],
        "start_line": lead["start_line"],
        "end_line": lead["end_line"],
        "snippet": lead["snippet"],
        "scores": [weak_score, strong_score],
        "cascade": {"stage": 2, "decision": decision, "reason": reason},
        "rank": lead.get("rank"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in", dest="in_path", default="-", help="leads/v1 ND-JSON path or '-' for stdin")
    ap.add_argument("--out", default="-", help="scored/v1 ND-JSON path or '-' for stdout")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--probe", default=str(DEFAULT_PROBE), type=Path)
    args = ap.parse_args()

    probe = StrongProbe(args.model, args.probe)

    src = sys.stdin if args.in_path == "-" else Path(args.in_path).open("r", encoding="utf-8")
    dst = sys.stdout if args.out == "-" else Path(args.out).open("w", encoding="utf-8")

    counts = {"in": 0, "promote": 0, "defer": 0, "drop": 0, "skipped": 0}
    for line in src:
        line = line.strip()
        if not line:
            continue
        try:
            lead = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[cascade] skip malformed line: {e}", file=sys.stderr)
            counts["skipped"] += 1
            continue
        if lead.get("schema") != SCHEMA_IN:
            print(f"[cascade] skip non-{SCHEMA_IN} record (saw {lead.get('schema')})", file=sys.stderr)
            counts["skipped"] += 1
            continue
        counts["in"] += 1
        scored = score_one(lead, probe)
        dst.write(json.dumps(scored, ensure_ascii=False) + "\n")
        dst.flush()
        counts[scored["cascade"]["decision"]] += 1

    print(
        f"[cascade] in={counts['in']}  promote={counts['promote']}  "
        f"defer={counts['defer']}  drop={counts['drop']}  skipped={counts['skipped']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
