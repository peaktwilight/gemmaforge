"""Token-level eval orchestration for the new probe path.

Mirrors `protocol.py` but operates on per-token probe scores and the
char-range spans from `data/dataset.jsonl`. Reports metrics at the three
paper-defined aggregation levels:

  all       every token in every example (out-of-span tokens have label=0)
  span      tokens inside annotated spans (positive or negative)
  span_max  one decision per span: max(probs[start:end+1])

Token-level scores have to come from somewhere — see
`scripts/run_token_eval.py` for the expected on-disk format. The eval
side here is tokenizer-agnostic; the caller supplies token offsets.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Iterable, Optional, Sequence

import numpy as np

from .baselines import Baseline, BroadcastProbeBaseline
from .metrics import (
    ClfMetrics,
    bootstrap_auc_ci,
    calibration_metrics,
    compute_clf_metrics,
)
from .splits import Split, make_splits
from .token_data import TokenSpan, parse_spans, token_labels_array


@dataclass
class TokenSplitReport:
    split_name: str
    n_train_examples: int
    n_test_examples: int
    note: str
    # Per-aggregation-level metric dicts. Each contains: auc, ci_lo, ci_hi,
    # accuracy, precision, recall, f1, recall_at_fpr_*, brier, ece, n_total, n_pos.
    all_metrics: dict[str, float] = field(default_factory=dict)
    span_metrics: dict[str, float] = field(default_factory=dict)
    span_max_metrics: dict[str, float] = field(default_factory=dict)
    baseline_aucs: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FullTokenReport:
    dataset_path: str
    n_examples: int
    n_pos_examples: int
    splits: list[TokenSplitReport]

    def to_dict(self) -> dict:
        return {
            "dataset_path": self.dataset_path,
            "n_examples": self.n_examples,
            "n_pos_examples": self.n_pos_examples,
            "splits": [s.to_dict() for s in self.splits],
        }


def _level_metrics(
    labels: np.ndarray,
    probs: np.ndarray,
    bootstrap_n: int,
) -> dict[str, float]:
    """Pack ClfMetrics + bootstrap CI + calibration into a flat dict."""
    if len(labels) == 0:
        return {"n_total": 0, "n_pos": 0}
    preds = (probs >= 0.5).astype(int)
    clf = compute_clf_metrics(preds, labels, probs)
    _, lo, hi = bootstrap_auc_ci(labels, probs, n_iter=bootstrap_n)
    cal = calibration_metrics(labels, probs)
    return {
        "auc": clf.auc,
        "auc_ci_lo": lo,
        "auc_ci_hi": hi,
        "accuracy": clf.accuracy,
        "precision": clf.precision,
        "recall": clf.recall,
        "f1": clf.f1,
        "recall_at_fpr_0.05": clf.recall_at_fpr.get("recall_at_fpr_0.05", float("nan")),
        "recall_at_fpr_0.10": clf.recall_at_fpr.get("recall_at_fpr_0.10", float("nan")),
        "brier": cal["brier"],
        "ece": cal["ece"],
        "n_total": clf.n_total,
        "n_pos": clf.n_pos,
    }


def _collect_for_indices(
    indices: Iterable[int],
    rows: list[dict],
    token_probs: list[np.ndarray],
    token_offsets: list[list[tuple[int, int]]] | None,
    token_spans: list[list[tuple[int, int, int]]],
    *,
    pad_negatives_for_span_max: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[tuple[int, float]]]:
    """Stack per-example token scores and labels.

    Returns:
      all_probs   (T,)  all tokens, every example concatenated
      all_labels  (T,)
      in_span     (T,)  boolean — token sits inside any annotated span
      _           reserved
      span_max_pairs  list of (label, max_prob) per annotated span

    On `data/dataset.jsonl`, every annotated span is positive (no
    sanitizer entries; negative examples have empty token_labels). To
    make `span_max` a meaningful binary classifier on that corpus, we
    add one synthetic *whole-file* negative span per negative example
    when `pad_negatives_for_span_max=True`. This matches the streaming-UI
    operational metric: "for a safe file, the max token score should
    stay low; for a vulnerable file, the max should rise inside the
    evidence span". Disable the pad on datasets that already include
    negative spans (e.g. paper-style sanitizer-annotated data).
    """
    all_probs_chunks: list[np.ndarray] = []
    all_labels_chunks: list[np.ndarray] = []
    in_span_chunks: list[np.ndarray] = []
    span_max_pairs: list[tuple[int, float]] = []
    for i in indices:
        probs = token_probs[i]
        spans = token_spans[i]
        labels, mask = token_labels_array(len(probs), spans)
        all_probs_chunks.append(probs)
        all_labels_chunks.append(labels)
        in_span_chunks.append(mask)
        for start, end, lbl in spans:
            end_c = min(end, len(probs) - 1)
            if end_c < start:
                continue
            span_max_pairs.append((int(lbl), float(np.max(probs[start : end_c + 1]))))
        if (
            pad_negatives_for_span_max
            and int(rows[i].get("label", 0)) == 0
            and len(probs) > 0
            and not spans
        ):
            span_max_pairs.append((0, float(np.max(probs))))
    if not all_probs_chunks:
        return (
            np.empty(0, dtype=float),
            np.empty(0, dtype=int),
            np.empty(0, dtype=bool),
            np.empty(0, dtype=int),
            span_max_pairs,
        )
    return (
        np.concatenate(all_probs_chunks),
        np.concatenate(all_labels_chunks),
        np.concatenate(in_span_chunks),
        np.empty(0, dtype=int),
        span_max_pairs,
    )


def evaluate_token_split(
    rows: list[dict],
    token_probs: list[np.ndarray],
    token_spans: list[list[tuple[int, int, int]]],
    split: Split,
    *,
    bootstrap_n: int = 1000,
    baselines: Optional[list[Baseline]] = None,
    sample_X: Optional[np.ndarray] = None,
) -> TokenSplitReport:
    """Evaluate one split at token level.

    `token_probs[i]` is the per-token probability array for row `i`.
    `token_spans[i]` is the row's char-spans already mapped to token
    indices (see `token_data.char_spans_to_token_spans`).

    The probe scores are evaluated as-is — no refit at token level (a
    fixed token-probe is the deployment artifact; refitting per split
    requires per-token activations, which slots in cleanly above this
    layer once #17 lands).

    Baselines are scored at the *example* level and broadcast to every
    token in each test row. That's the right comparison for the streaming
    UI: the old sample-level probe outputs a single decision per file,
    and we want to know what AUC that single decision achieves when
    treated as a token-level signal.
    """
    te = split.test_idx
    all_p, all_y, mask, _, span_max = _collect_for_indices(
        te.tolist(), rows, token_probs, None, token_spans
    )
    all_m = _level_metrics(all_y, all_p, bootstrap_n)
    span_p = all_p[mask]
    span_y = all_y[mask]
    span_m = _level_metrics(span_y, span_p, bootstrap_n)
    if span_max:
        sm_labels = np.array([p[0] for p in span_max], dtype=int)
        sm_probs = np.array([p[1] for p in span_max], dtype=float)
        span_max_m = _level_metrics(sm_labels, sm_probs, bootstrap_n)
    else:
        span_max_m = {"n_total": 0, "n_pos": 0}

    # Baselines: score each test row at example level, broadcast.
    baseline_aucs: dict[str, dict[str, float]] = {}
    if baselines:
        from sklearn.metrics import roc_auc_score
        rows_te = [rows[i] for i in te.tolist()]
        for bl in baselines:
            try:
                if isinstance(bl, BroadcastProbeBaseline) and sample_X is not None:
                    ex_scores = bl.score(rows_te, X=sample_X[te])
                else:
                    ex_scores = bl.score(rows_te)
            except Exception as e:  # noqa: BLE001
                baseline_aucs[bl.name] = {"error": str(e)}
                continue
            # Broadcast: every token in row i gets ex_scores[i].
            broad_probs = []
            for j, i in enumerate(te.tolist()):
                broad_probs.append(np.full_like(token_probs[i], ex_scores[j], dtype=float))
            broad_arr = np.concatenate(broad_probs) if broad_probs else np.empty(0)
            level: dict[str, float] = {}
            try:
                if len(np.unique(all_y)) >= 2:
                    level["all_auc"] = float(roc_auc_score(all_y, broad_arr))
                else:
                    level["all_auc"] = float("nan")
                if len(np.unique(span_y)) >= 2 and len(span_y) > 0:
                    level["span_auc"] = float(roc_auc_score(span_y, broad_arr[mask]))
                else:
                    level["span_auc"] = float("nan")
                # span_max baseline: one prediction per span = ex_score of its
                # parent example. Rebuild aligned with span_max ordering.
                ex_score_by_te_idx = dict(zip(te.tolist(), ex_scores))
                sm_baseline_probs = []
                for i in te.tolist():
                    for _ in token_spans[i]:
                        sm_baseline_probs.append(ex_score_by_te_idx[i])
                if span_max and len(np.unique([p[0] for p in span_max])) >= 2:
                    sm_b = np.array(sm_baseline_probs, dtype=float)
                    sm_lbl = np.array([p[0] for p in span_max], dtype=int)
                    level["span_max_auc"] = float(roc_auc_score(sm_lbl, sm_b))
                else:
                    level["span_max_auc"] = float("nan")
            except Exception as e:  # noqa: BLE001
                level["error"] = str(e)
            baseline_aucs[bl.name] = level

    return TokenSplitReport(
        split_name=split.name,
        n_train_examples=int(len(split.train_idx)),
        n_test_examples=int(len(te)),
        note=split.note,
        all_metrics=all_m,
        span_metrics=span_m,
        span_max_metrics=span_max_m,
        baseline_aucs=baseline_aucs,
    )


def full_token_report(
    rows: list[dict],
    token_probs: list[np.ndarray],
    token_spans: list[list[tuple[int, int, int]]],
    *,
    dataset_path: str,
    include: tuple[str, ...] = ("random", "group_repo", "heldout_cwe", "heldout_lang", "heldout_source"),
    seed: int = 7,
    bootstrap_n: int = 1000,
    baselines: Optional[list[Baseline]] = None,
    sample_X: Optional[np.ndarray] = None,
) -> FullTokenReport:
    """Run the canonical split bundle on token-level data.

    Splits are still produced at the *example* level (one row in
    `data/dataset.jsonl` = one example). Token-level evaluation then
    slices the per-row probs / spans by example index.
    """
    y = np.array([int(r.get("label", 0)) for r in rows], dtype=np.int8)
    splits = make_splits(rows, y, include=include, seed=seed)
    reports = [
        evaluate_token_split(
            rows, token_probs, token_spans, sp,
            bootstrap_n=bootstrap_n, baselines=baselines, sample_X=sample_X,
        )
        for sp in splits
    ]
    return FullTokenReport(
        dataset_path=dataset_path,
        n_examples=len(rows),
        n_pos_examples=int(y.sum()),
        splits=reports,
    )
