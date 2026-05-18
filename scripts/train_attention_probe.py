"""Train the AttentionProbe -- TOY / DEGENERATE proof-of-concept.

NOTE: This is a degenerate run -- the attention probe collapses to a linear
probe when the input buffer is constant. Real per-position activations are
needed for a meaningful run.

What this script does
---------------------
The activations cached in ``data/activations_v2/activations_layer*.npz``
contain only the *last-token* hidden state ``h \\in R^{D}`` for each sample
(see ``src/extract_activations.py``). A real attention pool needs a buffer
of per-position hidden states ``H \\in R^{K x D}``. The per-token
extraction path that would produce that (Efe's ``extract_token_activations``)
is blocked on GitHub issue #17.

As a hackathon stop-gap we fake the buffer by repeating the last-token
activation K times: ``H = h.unsqueeze(1).expand(B, K, D)``. With a constant
buffer, ``softmax(H @ Wq) = 1/K`` for every position regardless of Wq, and
``mean_k V_k = Wv @ h`` -- the head therefore collapses to
``sigma(head_w . (Wv h) + head_b)`` which is mathematically equivalent to a
linear probe with effective weight ``head_w^T Wv``. We expect AUC to come
out near the linear-probe baseline; any small gap is optimization noise.

This script exists to (a) exercise the AttentionProbe module on real
activation tensors so the end-to-end path is plumbed, and (b) produce a
``data/probe_attention.npz`` that downstream code can already load. Replace
the constant-buffer fake with real per-token activations once issue #17
lands.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split

# Make `src/` importable when run from the repo root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.attention_probe import AttentionProbe  # noqa: E402


def _fake_buffer(h: torch.Tensor, k: int) -> torch.Tensor:
    """Repeat the last-token activation K times to fake a buffer.

    h: [B, D] -> [B, K, D]. With constant H the attention pool degenerates to
    a linear probe (see module docstring).
    """
    return h.unsqueeze(1).expand(-1, k, -1).contiguous()


def train_one_layer(
    X: np.ndarray,
    y: np.ndarray,
    layer: int,
    *,
    k: int = 8,
    n_heads: int = 8,
    lr: float = 1e-3,
    epochs: int = 50,
    batch_size: int = 64,
    seed: int = 7,
    device: str = "cpu",
) -> dict:
    """Fit an AttentionProbe on one layer's last-token activations."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    Xtr_t = torch.from_numpy(Xtr).float().to(device)
    Xte_t = torch.from_numpy(Xte).float().to(device)
    ytr_t = torch.from_numpy(ytr).float().to(device)
    yte_t = torch.from_numpy(yte).float().to(device)

    d_model = X.shape[1]
    probe = AttentionProbe(d_model=d_model, n_heads=n_heads).to(device)
    opt = torch.optim.Adam(probe.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    n_train = Xtr_t.shape[0]
    for epoch in range(epochs):
        probe.train()
        perm = torch.randperm(n_train, device=device)
        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, n_train, batch_size):
            idx = perm[start : start + batch_size]
            h = Xtr_t[idx]                       # [b, D]
            H = _fake_buffer(h, k)               # [b, K, D]
            logits = probe(H).squeeze(-1)        # [b]
            loss = loss_fn(logits, ytr_t[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            epoch_loss += float(loss.detach().cpu())
            n_batches += 1
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(
                f"[train_attn] layer {layer:02d}  epoch {epoch+1:02d}/{epochs}  "
                f"loss={epoch_loss / max(n_batches, 1):.4f}",
                file=sys.stderr,
            )

    probe.eval()
    with torch.no_grad():
        H_test = _fake_buffer(Xte_t, k)
        logits = probe(H_test).squeeze(-1)
        probs = torch.sigmoid(logits).cpu().numpy()
    yhat_cls = (probs >= 0.5).astype(np.int64)
    auc = float(roc_auc_score(yte, probs))
    acc = float(accuracy_score(yte, yhat_cls))

    return {
        "layer": layer,
        "auc": auc,
        "acc": acc,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "pos_rate": float(y.mean()),
        "probe": probe,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--acts",
        default="data/activations_v2/activations_layer17.npz",
        help="Path to an activations_layer*.npz file (last-token H).",
    )
    ap.add_argument("--out", default="data/probe_attention.npz")
    ap.add_argument("--card", default="data/probe_attention_card.json")
    ap.add_argument("--k", type=int, default=8, help="Buffer length K.")
    ap.add_argument("--n-heads", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    acts_path = Path(args.acts)
    if not acts_path.exists():
        print(f"[train_attn] activations not found: {acts_path}", file=sys.stderr)
        sys.exit(1)

    layer = int(acts_path.stem.split("layer")[-1])
    npz = np.load(acts_path)
    X, y = npz["X"], npz["y"]
    print(
        f"[train_attn] layer {layer:02d}  X={X.shape}  y_pos={int(y.sum())}  "
        f"(DEGENERATE / TOY -- buffer = last-token repeated K={args.k} times)",
        file=sys.stderr,
    )

    result = train_one_layer(
        X,
        y,
        layer=layer,
        k=args.k,
        n_heads=args.n_heads,
        lr=args.lr,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        device=args.device,
    )

    print(
        f"[train_attn] layer {layer:02d}  AUC={result['auc']:.3f}  ACC={result['acc']:.3f}",
        file=sys.stderr,
    )

    probe: AttentionProbe = result["probe"]
    probe.save(args.out, layer=layer)

    card = {
        "kind": "attention_probe_toy",
        "layer": layer,
        "auc": result["auc"],
        "acc": result["acc"],
        "n_train": result["n_train"],
        "n_test": result["n_test"],
        "pos_rate": result["pos_rate"],
        "k": args.k,
        "n_heads": args.n_heads,
        "lr": args.lr,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "note": (
            "Degenerate run: buffer = last-token repeated K times. With a "
            "constant buffer the attention pool reduces to a linear probe. "
            "Replace _fake_buffer with real per-token activations once issue "
            "#17 (per-token extraction) lands."
        ),
    }
    Path(args.card).write_text(json.dumps(card, indent=2))
    print(f"[train_attn] saved {args.out} + {args.card}", file=sys.stderr)


if __name__ == "__main__":
    main()
