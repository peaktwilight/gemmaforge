"""Smoke test the UI by writing a fake probe (random + sign-shifted), so we
can spin the web demo before the real probe is trained.

A real probe takes ~10-20 minutes to extract+train. This script writes a
sensible 2560-dim fake to data/probe.npz in ~1 second, so we can verify
the streaming UI + server end-to-end without blocking on training.

Sign convention: positive risk = vulnerable.
"""
import numpy as np
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

# 2560 matches Gemma 4 8B; E2B is smaller (probably 1152 or 1536).
# We'll write something that matches the most likely E2B dim and let the
# real probe overwrite. Will fix once we see the actual hidden state shape.
DIM = 1152

rng = np.random.default_rng(7)
w = rng.normal(0, 0.01, size=DIM).astype(np.float32)
b = np.float32(-0.5)

np.savez_compressed(OUT / "probe.npz", w=w, b=b, layer=np.int32(12))

card = {
    "best_layer": 12,
    "best_auc": 0.5,
    "best_acc": 0.5,
    "all_layers": [],
    "pos_rate": 0.5,
    "note": "FAKE probe for UI smoke test only — real probe will overwrite.",
}
(OUT / "probe_card.json").write_text(json.dumps(card, indent=2))
print(f"wrote fake probe to {OUT / 'probe.npz'}")
