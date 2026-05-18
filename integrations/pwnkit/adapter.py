"""GemmaForge → pwnkit adapter.

Wraps the GemmaForge linear probes as a *confidence filter* over findings
emitted by pwnkit (https://github.com/PwnKit-Labs/pwnkit).

Public API:

    from integrations.pwnkit.adapter import GemmaForgeFilter

    gf = GemmaForgeFilter()                # lazy: nothing heavy happens yet
    out = gf.score_finding({
        "claim":   "SQL injection at line 42 of router.js",
        "snippet": "...source code...",
        "cwe":     "CWE-89",
        "confidence": "high",
    })
    # out == finding | {
    #     "gemmaforge_confidence": 0.83,         # float in [0, 1]
    #     "gemmaforge_cwe_match":  1.0 | 0.5 | 0.0 | None,
    #     "gemmaforge_layer":      17,
    #     "gemmaforge_top_cwe":    "CWE-89" | None,
    # }

Design notes
------------
- The probe is a single (w, b) logistic regression over Gemma 4 layer-17
  hidden states at the last input token (see src/train_probe.py).
- The per-CWE probe is K=5 stacked one-vs-rest heads for the top 5 CWEs
  in the training set: CWE-78, CWE-338, CWE-95, CWE-94, CWE-328.
- The Gemma 4 LM is heavy (>1GB) so it is loaded lazily on the FIRST
  call to ``score_finding``. Probes are tiny (.npz, ~tens of KB) and
  eager-loaded in ``__init__``.
- torch / transformers are imported INSIDE the lazy method so simply
  importing this module costs nothing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + float(np.exp(-x)))
    e = float(np.exp(x))
    return e / (1.0 + e)


class GemmaForgeFilter:
    """Score pwnkit findings with GemmaForge's vulnerability probes."""

    def __init__(
        self,
        probe_path: str = "data/probe.npz",
        per_cwe_probe_path: str = "data/probe_per_cwe.npz",
        model_id: str = "google/gemma-4-E2B-it",
        max_tokens: int = 512,
    ) -> None:
        self.probe_path = Path(probe_path)
        self.per_cwe_probe_path = Path(per_cwe_probe_path)
        self.model_id = model_id
        self.max_tokens = max_tokens

        # Eager-load the tiny probes so we fail fast on bad paths.
        bp = np.load(self.probe_path)
        self._w = bp["w"].astype(np.float32)
        self._b = float(bp["b"])
        self._layer = int(bp["layer"])

        if self.per_cwe_probe_path.exists():
            pc = np.load(self.per_cwe_probe_path, allow_pickle=False)
            self._cwes = [str(c) for c in pc["cwes"]]
            self._W_cwe = pc["W"].astype(np.float32)  # (K, dim)
            self._b_cwe = pc["b"].astype(np.float32)  # (K,)
            assert int(pc["layer"]) == self._layer, (
                "binary and per-CWE probes were trained on different layers; "
                f"binary={self._layer} per-cwe={int(pc['layer'])}"
            )
        else:
            self._cwes = []
            self._W_cwe = None
            self._b_cwe = None

        # Heavy state — populated by _ensure_model on first call.
        self._model = None
        self._tokenizer = None
        self._device = None

    # ---------------- lazy LM load ---------------- #

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        import torch  # local import: keeps module import cheap
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        dtype = torch.float16 if device != "cpu" else torch.float32
        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id, dtype=dtype, attn_implementation="eager"
        )
        model.to(device)
        model.eval()

        self._tokenizer = tokenizer
        self._model = model
        self._device = device

    # ---------------- core: snippet → hidden state ---------------- #

    def _hidden_state(self, snippet: str) -> np.ndarray:
        """Run the LM on the snippet, return layer-N last-token hidden state."""
        import torch

        self._ensure_model()
        ids = self._tokenizer.encode(
            snippet, return_tensors="pt", truncation=True, max_length=self.max_tokens
        ).to(self._device)
        with torch.inference_mode():
            out = self._model(ids, output_hidden_states=True, use_cache=False)
        # hidden_states[0] is the embedding output; layer L -> index L+1.
        h = out.hidden_states[self._layer + 1][0, -1, :]
        return h.detach().to("cpu").float().numpy()

    # ---------------- public ---------------- #

    def score_finding(self, finding: dict) -> dict:
        """Score a pwnkit finding.

        Returns ``finding`` merged with:
          - ``gemmaforge_confidence`` (float in [0, 1])
          - ``gemmaforge_cwe_match``  (1.0 | 0.5 | 0.0 | None)
          - ``gemmaforge_top_cwe``    (str | None) — argmax CWE head
          - ``gemmaforge_layer``      (int)        — which layer was probed
        """
        snippet = finding.get("snippet") or ""
        if not snippet.strip():
            raise ValueError("finding['snippet'] must be a non-empty string")

        h = self._hidden_state(snippet)
        confidence = _sigmoid(float(np.dot(self._w, h) + self._b))

        cwe_match: Optional[float] = None
        top_cwe: Optional[str] = None
        claimed = finding.get("cwe")
        if claimed and self._W_cwe is not None:
            if claimed in self._cwes:
                logits = self._W_cwe @ h + self._b_cwe  # (K,)
                order = np.argsort(-logits)  # descending
                top1 = self._cwes[int(order[0])]
                top2 = self._cwes[int(order[1])] if len(order) > 1 else None
                top_cwe = top1
                if claimed == top1:
                    cwe_match = 1.0
                elif claimed == top2:
                    cwe_match = 0.5
                else:
                    cwe_match = 0.0
            # claimed CWE outside the 5 trained heads → leave as None

        return {
            **finding,
            "gemmaforge_confidence": confidence,
            "gemmaforge_cwe_match": cwe_match,
            "gemmaforge_top_cwe": top_cwe,
            "gemmaforge_layer": self._layer,
        }
