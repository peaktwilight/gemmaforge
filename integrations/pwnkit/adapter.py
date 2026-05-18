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
  hidden states (see src/train_probe.py). Repo scanning scores every token
  position in overlapping token windows, then reports max + robust top-k
  confidence for the chunk.
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


def _sigmoid_array(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid for a vector of logits."""
    out = np.empty_like(x, dtype=np.float64)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    e = np.exp(x[~pos])
    out[~pos] = e / (1.0 + e)
    return out


def _topk_mean(values: np.ndarray, *, min_k: int = 3, frac: float = 0.02) -> float:
    """Robust high-risk aggregate for per-token probe scores.

    Raw max keeps recall high but can be driven by one unstable token. This
    aggregate is useful for reporting and ranking diagnostics because it asks
    whether the top of the score distribution is consistently high.
    """
    if values.size == 0:
        return 0.0
    k = min(values.size, max(min_k, int(np.ceil(values.size * frac))))
    if k <= 1:
        return float(values.max())
    top = np.partition(values, values.size - k)[values.size - k:]
    return float(top.mean())


def _token_windows(input_ids: list[int], max_tokens: int, stride: int) -> list[tuple[int, list[int]]]:
    """Return overlapping token windows as (global_start_token, token_ids)."""
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if stride <= 0:
        raise ValueError("stride must be positive")
    if len(input_ids) <= max_tokens:
        return [(0, input_ids)]

    windows: list[tuple[int, list[int]]] = []
    start = 0
    while start < len(input_ids):
        end = min(start + max_tokens, len(input_ids))
        windows.append((start, input_ids[start:end]))
        if end == len(input_ids):
            break
        start += stride
    return windows


class GemmaForgeFilter:
    """Score pwnkit findings with GemmaForge's vulnerability probes."""

    # Per-CWE probe file to use when no explicit ``per_cwe_probe_path`` is
    # passed. Each scan profile pins its own per-CWE head so the binary probe
    # and per-CWE probe agree on the source layer / model.
    _PER_CWE_BY_PROFILE = {
        "weak-probe": "data/probe_per_cwe.npz",
        "strong-probe": "data/probe_strong_per_cwe.npz",
    }

    def __init__(
        self,
        probe_path: str = "data/probe.npz",
        per_cwe_probe_path: Optional[str] = None,
        model_id: str = "google/gemma-4-E2B-it",
        max_tokens: int = 512,
        token_stride: Optional[int] = None,
        scan_profile: str = "weak-probe",
    ) -> None:
        self.probe_path = Path(probe_path)
        if per_cwe_probe_path is None:
            per_cwe_probe_path = self._PER_CWE_BY_PROFILE.get(
                scan_profile, "data/probe_per_cwe.npz"
            )
        self.per_cwe_probe_path = Path(per_cwe_probe_path)
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.token_stride = token_stride or max(1, max_tokens // 2)
        self.scan_profile = scan_profile

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
            assert self._W_cwe.shape[1] == self._w.shape[0], (
                "binary and per-CWE probe dimensions differ; "
                f"binary={self._w.shape[0]} per-cwe={self._W_cwe.shape[1]}"
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

    def _hidden_states_for_ids(self, input_ids: list[int]) -> np.ndarray:
        """Run the LM on token ids and return layer-N hidden states for every token."""
        import torch

        self._ensure_model()
        ids = torch.tensor([input_ids], dtype=torch.long, device=self._device)
        with torch.inference_mode():
            out = self._model(ids, output_hidden_states=True, use_cache=False)
        # hidden_states[0] is the embedding output; layer L -> index L+1.
        h = out.hidden_states[self._layer + 1][0, :, :]
        mat = h.detach().to("cpu").float().numpy()
        if mat.shape[-1] != self._w.shape[0]:
            raise ValueError(
                f"probe dim {self._w.shape[0]} != hidden dim {mat.shape[-1]} "
                f"for model {self.model_id} layer {self._layer}. "
                "Use a probe trained on this model/profile."
            )
        return mat

    def _score_snippet_tokens(self, snippet: str) -> dict:
        """Score a snippet using all token positions across sliding token windows."""
        self._ensure_model()
        input_ids = self._tokenizer.encode(snippet, add_special_tokens=True)
        windows = _token_windows(input_ids, self.max_tokens, self.token_stride)

        # Store one score per original token. Overlapped tokens keep the max
        # score seen across windows so robust aggregation does not double-count.
        per_token = np.full(len(input_ids), -np.inf, dtype=np.float64)
        h_at_max: Optional[np.ndarray] = None
        max_prob = -1.0

        for start, ids in windows:
            h = self._hidden_states_for_ids(ids)
            probs = _sigmoid_array(h @ self._w + self._b)
            end = start + len(ids)
            per_token[start:end] = np.maximum(per_token[start:end], probs)

            idx = int(np.argmax(probs))
            p = float(probs[idx])
            if p > max_prob:
                max_prob = p
                h_at_max = h[idx]

        valid_scores = per_token[np.isfinite(per_token)]
        if valid_scores.size == 0 or h_at_max is None:
            raise ValueError("snippet produced no tokens")

        top_cwe: Optional[str] = None
        top_cwe_score: Optional[float] = None
        cwe_ranking: list[str] = []
        if self._W_cwe is not None and self._b_cwe is not None:
            logits = self._W_cwe @ h_at_max + self._b_cwe
            order = np.argsort(-logits)
            cwe_ranking = [self._cwes[int(i)] for i in order.tolist()]
            top_idx = int(order[0])
            top_cwe = self._cwes[top_idx]
            top_cwe_score = _sigmoid(float(logits[top_idx]))

        return {
            "gemmaforge_confidence": float(max_prob),
            "gemmaforge_confidence_robust": _topk_mean(valid_scores),
            "gemmaforge_top_cwe": top_cwe,
            "gemmaforge_top_cwe_score": top_cwe_score,
            "gemmaforge_cwe_ranking": cwe_ranking,
            "gemmaforge_layer": self._layer,
            "model_id": self.model_id,
            "scan_profile": self.scan_profile,
            "scoring_mode": "token-window-max",
            "token_count": int(len(input_ids)),
            "windows_scored": int(len(windows)),
            "max_tokens": int(self.max_tokens),
            "token_stride": int(self.token_stride),
        }

    # ---------------- public ---------------- #

    def score_snippet(self, snippet: str) -> dict:
        """Score a raw snippet with no external CWE claim.

        This is the scan-friendly API used by ``src/scan.py``. The per-CWE
        head's argmax is always surfaced as ``gemmaforge_top_cwe`` when the
        per-CWE probe is loaded — there is no claim to compare against here,
        so ``gemmaforge_cwe_match`` is intentionally omitted from the output.
        """
        if not snippet.strip():
            raise ValueError("snippet must be a non-empty string")
        return self._score_snippet_tokens(snippet)

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

        scored = self._score_snippet_tokens(snippet)

        cwe_match: Optional[float] = None
        top_cwe: Optional[str] = scored.get("gemmaforge_top_cwe")
        claimed = finding.get("cwe")
        if claimed and self._W_cwe is not None:
            if claimed in self._cwes:
                ranking = scored.get("gemmaforge_cwe_ranking") or []
                top1 = ranking[0] if len(ranking) >= 1 else top_cwe
                top2 = ranking[1] if len(ranking) >= 2 else None
                if claimed == top1:
                    cwe_match = 1.0
                elif claimed == top2:
                    cwe_match = 0.5
                else:
                    cwe_match = 0.0
            # claimed CWE outside the 5 trained heads → leave as None

        return {
            **finding,
            **scored,
            "gemmaforge_cwe_match": cwe_match,
            "gemmaforge_top_cwe": top_cwe,
        }
