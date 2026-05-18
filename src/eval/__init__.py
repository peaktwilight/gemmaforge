"""Evaluation framework for GemmaForge vulnerability-detection probes.

Adapted from the hallucination-probes paper methodology (Obeso et al. 2025,
arxiv.org/abs/2509.03531). The paper evaluates probes at three aggregation
levels — all-token, in-span-token, and span-max. For vulnerability probes we
add leakage-aware splits (paired safe/vulnerable variants share repos), a
per-CWE and per-language breakdown, regex baselines, and bootstrap CIs.

Public API:
    metrics.compute_clf_metrics(preds, labels, probs) -> dict
    metrics.bootstrap_auc_ci(labels, probs, n=1000) -> (lo, hi)
    metrics.calibration_metrics(labels, probs) -> dict
    splits.make_splits(rows, y, names=...) -> list[Split]
    baselines.RegexBaseline().score(rows) -> np.ndarray
    protocol.evaluate_split(X, y, rows, split, probe=None) -> SplitReport
    protocol.full_report(X, y, rows, probe=None) -> FullReport
    report.render_markdown(report) -> str
"""
from . import metrics, splits, baselines, protocol, report, probe_io  # noqa: F401

__all__ = ["metrics", "splits", "baselines", "protocol", "report", "probe_io"]
