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
    # Closes #25. Same one-pair-per-example shape as span_max, but for
    # positive examples the max is taken over each annotated span dilated by
    # `proximity_window` tokens on each side; negatives keep whole-file max.
    # AUC + standard clf metrics; F1 at threshold=0.5 doubles as the
    # detection-window operational number described in #25.
    dilated_span_max_metrics: dict[str, float] = field(default_factory=dict)
    # Per-token AUC where the ground-truth positive mask is dilated by
    # `proximity_window` tokens on each side. Rewards firing in the ±W halo
    # around labelled spans, which is what soft-label training (#26) is
    # trying to teach.
    proximal_all_metrics: dict[str, float] = field(default_factory=dict)
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
    proximity_window: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[tuple[int, float]], list[tuple[int, float]]]:
    """Stack per-example token scores and labels.

    Returns:
      all_probs   (T,)  all tokens, every example concatenated
      all_labels  (T,)
      in_span     (T,)  boolean — token sits inside any annotated span
      _           reserved
      span_max_pairs  list of (label, max_prob) per annotated span

    span_max is computed as one pair per example: (example-level label,
    max prob over all tokens in that example). This matches both the
    streaming-UI operational rule ("file is risky iff any token's prob
    is high") and `src/train_probe_spanmax.py`'s `ex_AUC` reporting.

    The previous behaviour emitted one pair per char-range span for
    positives (max over ~2 span tokens) and one whole-file-max pair for
    negatives — an asymmetry that inverted AUC for noisy real probes
    because negative-file max-over-many-tokens easily beat positive
    max-over-few-tokens. The fix is symmetric per-example aggregation.

    `pad_negatives_for_span_max` is retained for API compatibility but
    is now a no-op (negatives are always represented, exactly once).
    """
    del pad_negatives_for_span_max  # no-op; kept for backward compat
    all_probs_chunks: list[np.ndarray] = []
    all_labels_chunks: list[np.ndarray] = []
    in_span_chunks: list[np.ndarray] = []
    span_max_pairs: list[tuple[int, float]] = []
    dilated_pairs: list[tuple[int, float]] = []
    for i in indices:
        probs = token_probs[i]
        spans = token_spans[i]
        labels, mask = token_labels_array(len(probs), spans)
        all_probs_chunks.append(probs)
        all_labels_chunks.append(labels)
        in_span_chunks.append(mask)
        if len(probs) > 0:
            ex_label = int(rows[i].get("label", int(any(lbl == 1 for _, _, lbl in spans))))
            whole_file_max = float(np.max(probs))
            span_max_pairs.append((ex_label, whole_file_max))

            # Dilated span_max (#25): positives → max over each annotated
            # positive span dilated by ±proximity_window; negatives → whole
            # file (symmetric with span_max for negatives, where there are
            # no spans to dilate around).
            if ex_label == 1 and proximity_window >= 0:
                pos_spans = [(s, e) for (s, e, lbl) in spans if lbl == 1]
                if pos_spans:
                    n_tok = len(probs)
                    di_mask = np.zeros(n_tok, dtype=bool)
                    for s, e in pos_spans:
                        s2 = max(0, s - proximity_window)
                        e2 = min(n_tok - 1, e + proximity_window)
                        if e2 >= s2:
                            di_mask[s2 : e2 + 1] = True
                    score = float(probs[di_mask].max()) if di_mask.any() else whole_file_max
                else:
                    # Positive example but no mapped spans (rare, e.g. truncation).
                    score = whole_file_max
            else:
                score = whole_file_max
            dilated_pairs.append((ex_label, score))
    if not all_probs_chunks:
        return (
            np.empty(0, dtype=float),
            np.empty(0, dtype=int),
            np.empty(0, dtype=bool),
            np.empty(0, dtype=int),
            span_max_pairs,
            dilated_pairs,
        )
    return (
        np.concatenate(all_probs_chunks),
        np.concatenate(all_labels_chunks),
        np.concatenate(in_span_chunks),
        np.empty(0, dtype=int),
        span_max_pairs,
        dilated_pairs,
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
    proximity_window: int = 0,
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
    all_p, all_y, mask, _, span_max, dilated_max = _collect_for_indices(
        te.tolist(), rows, token_probs, None, token_spans,
        proximity_window=proximity_window,
    )
    all_m = _level_metrics(all_y, all_p, bootstrap_n)
    span_p = all_p[mask]
    span_y = all_y[mask]
    span_m = _level_metrics(span_y, span_p, bootstrap_n)

    # proximal_all: same per-token AUC as `all`, but with the positive mask
    # dilated by ±proximity_window. Tokens in the halo around a labelled
    # span count as positive too, so the probe is not punished for firing
    # 5-10 tokens away from the diff anchor. Closes the eval half of #25
    # in a way that's symmetric across positives and negatives.
    if proximity_window > 0:
        proximal_y = np.zeros_like(all_y)
        offset = 0
        for i in te.tolist():
            n_tok = len(token_probs[i])
            row_spans = token_spans[i]
            if n_tok > 0 and row_spans:
                local = np.zeros(n_tok, dtype=np.int8)
                for s, e, lbl in row_spans:
                    if lbl != 1:
                        continue
                    s2 = max(0, s - proximity_window)
                    e2 = min(n_tok - 1, e + proximity_window)
                    if e2 >= s2:
                        local[s2 : e2 + 1] = 1
                proximal_y[offset : offset + n_tok] = local
            offset += n_tok
        proximal_m = _level_metrics(proximal_y, all_p, bootstrap_n)
        proximal_m["proximity_window"] = int(proximity_window)
    else:
        proximal_m = {"n_total": 0, "n_pos": 0}
    if span_max:
        sm_labels = np.array([p[0] for p in span_max], dtype=int)
        sm_probs = np.array([p[1] for p in span_max], dtype=float)
        span_max_m = _level_metrics(sm_labels, sm_probs, bootstrap_n)
    else:
        span_max_m = {"n_total": 0, "n_pos": 0}
    if dilated_max and proximity_window > 0:
        dm_labels = np.array([p[0] for p in dilated_max], dtype=int)
        dm_probs = np.array([p[1] for p in dilated_max], dtype=float)
        dilated_m = _level_metrics(dm_labels, dm_probs, bootstrap_n)
        dilated_m["proximity_window"] = int(proximity_window)
    else:
        dilated_m = {"n_total": 0, "n_pos": 0}

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
                # span_max baseline: one prediction per example = ex_score.
                # Aligned with span_max_pairs which is also one-per-example
                # (skipping empty-token rows, in the same iteration order).
                if span_max and len(np.unique([p[0] for p in span_max])) >= 2:
                    sm_baseline_probs = [
                        ex_scores[j]
                        for j, i in enumerate(te.tolist())
                        if len(token_probs[i]) > 0
                    ]
                    sm_b = np.array(sm_baseline_probs, dtype=float)
                    sm_lbl = np.array([p[0] for p in span_max], dtype=int)
                    level["span_max_auc"] = float(roc_auc_score(sm_lbl, sm_b))
                    # Baseline broadcast-prob is constant across tokens, so
                    # dilation doesn't change its score per example. Re-use
                    # the same alignment.
                    if proximity_window > 0:
                        level["dilated_span_max_auc"] = float(roc_auc_score(sm_lbl, sm_b))
                    else:
                        level["dilated_span_max_auc"] = float("nan")
                else:
                    level["span_max_auc"] = float("nan")
                    level["dilated_span_max_auc"] = float("nan")
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
        dilated_span_max_metrics=dilated_m,
        proximal_all_metrics=proximal_m,
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
    proximity_window: int = 0,
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
            proximity_window=proximity_window,
        )
        for sp in splits
    ]
    return FullTokenReport(
        dataset_path=dataset_path,
        n_examples=len(rows),
        n_pos_examples=int(y.sum()),
        splits=reports,
    )
