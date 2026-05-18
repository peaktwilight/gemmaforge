"""Causal attention pool probe for vulnerability detection.

Implements the "Attention Probes" technique from
https://learnmechinterp.com/ and Kelp et al. arXiv 2510.09694.

Background
----------
The existing GemmaForge probe consumes the *last-token* hidden state h and
applies a learned linear head::

    risk = sigma(w . h + b)

Mean-pool over a fixed window is a band-aid: it weights every token equally.
The principled fix is an attention pool: given a rolling buffer of recent
hidden states ``H \\in R^{K x D}`` (one row per token position),

    a = softmax(H @ Wq)            # [K, n_heads]   per-head attention weights
    V = H @ Wv                     # [K, D]         transformed values
    h_agg = sum_k a_k * V_k        # [D]            aggregated representation
    logit = head(h_agg)            # [1]

The query is *learned* (not derived from the current token), so this is a
"learned probe direction" attention rather than self-attention. We use 8
heads following the original Attention Probes paper; per-head pooled
representations are concatenated head-wise via averaging into the same D
before the final head -- a minimal multi-head variant that keeps the head
weights light.

Save format
-----------
The linear probe lives at ``data/probe.npz`` with keys ``{w, b, layer}``.
Attention probes need more weights, so we serialize to a separate file
``data/probe_attention.npz`` with keys ``{Wq, Wv, head_w, head_b, layer}``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


N_HEADS_DEFAULT = 8


class AttentionProbe(nn.Module):
    """Causal attention pool probe.

    Parameters
    ----------
    d_model : int
        Hidden-state dimensionality D (e.g. 1536 for Gemma 3 4B residual).
    n_heads : int, default 8
        Number of query heads. Each head produces its own scalar attention
        weight over the buffer; the head outputs are averaged before the
        final classifier head.
    """

    def __init__(self, d_model: int, n_heads: int = N_HEADS_DEFAULT) -> None:
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        # Query: D -> n_heads scalar scores per token, no bias (paper)
        self.Wq = nn.Linear(d_model, n_heads, bias=False)
        # Value: D -> D, no bias (paper)
        self.Wv = nn.Linear(d_model, d_model, bias=False)
        # Final classifier on the pooled representation
        self.head = nn.Linear(d_model, 1)

    def forward(self, H: torch.Tensor) -> torch.Tensor:
        """Compute risk logits from a buffer of hidden states.

        Parameters
        ----------
        H : tensor of shape ``[B, K, D]``
            Batched rolling buffers. ``K`` may vary across batches if you
            pre-pad; this implementation assumes a fixed K per batch.

        Returns
        -------
        logits : tensor of shape ``[B, 1]``
        """
        if H.dim() != 3:
            raise ValueError(f"expected [B, K, D], got {tuple(H.shape)}")
        B, K, D = H.shape
        if D != self.d_model:
            raise ValueError(f"d_model mismatch: probe={self.d_model}, input={D}")

        # Per-head attention scores: [B, K, n_heads]
        scores = self.Wq(H)
        attn = F.softmax(scores, dim=1)  # softmax over token positions K

        # Values: [B, K, D]
        V = self.Wv(H)

        # Pool per head, then average over heads.
        # attn:  [B, K, H] -> [B, H, K]
        # V:     [B, K, D]
        # pooled per head: [B, H, D]
        pooled = torch.einsum("bkh,bkd->bhd", attn, V)
        # Average across heads -> [B, D]
        h_agg = pooled.mean(dim=1)

        return self.head(h_agg)

    # -- serialization -------------------------------------------------

    def save(self, path: str | Path, layer: int) -> None:
        """Save weights as a single ``.npz`` (independent of the linear probe)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            Wq=self.Wq.weight.detach().cpu().numpy().astype(np.float32),
            Wv=self.Wv.weight.detach().cpu().numpy().astype(np.float32),
            head_w=self.head.weight.detach().cpu().numpy().astype(np.float32),
            head_b=self.head.bias.detach().cpu().numpy().astype(np.float32),
            layer=np.int32(layer),
            n_heads=np.int32(self.n_heads),
        )

    @classmethod
    def load(cls, path: str | Path) -> tuple["AttentionProbe", int]:
        """Load an attention probe from a ``.npz`` file.

        Returns
        -------
        (probe, layer) : the reconstructed module and the layer index it was
            trained on (matching the layer field of the existing probe.npz).
        """
        npz = np.load(path)
        Wq = npz["Wq"]
        Wv = npz["Wv"]
        head_w = npz["head_w"]
        head_b = npz["head_b"]
        layer = int(npz["layer"])
        n_heads = int(npz["n_heads"]) if "n_heads" in npz.files else N_HEADS_DEFAULT

        d_model = Wv.shape[0]
        probe = cls(d_model=d_model, n_heads=n_heads)
        with torch.no_grad():
            probe.Wq.weight.copy_(torch.from_numpy(Wq))
            probe.Wv.weight.copy_(torch.from_numpy(Wv))
            probe.head.weight.copy_(torch.from_numpy(head_w))
            probe.head.bias.copy_(torch.from_numpy(head_b))
        probe.eval()
        return probe, layer


__all__ = ["AttentionProbe", "N_HEADS_DEFAULT"]
