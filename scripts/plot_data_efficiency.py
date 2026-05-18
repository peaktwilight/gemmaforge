"""Render the data efficiency curve as a 2-line PNG.

Reads ``data/data_efficiency.json`` (produced by
``scripts/data_efficiency_curve.py``) and writes ``web/data-efficiency-curve.png``
at 1200x600. Two lines: held-out AUC for the random 80/20 split and for the
Python->JavaScript cross-language split, both as a function of training-set
fraction (log x-axis). Error bars are 95% CIs (1.96 * SE over the 5 seeds).

Run:
    python scripts/plot_data_efficiency.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
IN_JSON = ROOT / "data" / "data_efficiency.json"
OUT_PNG = ROOT / "web" / "data-efficiency-curve.png"


def _series(points: list[dict], key_prefix: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Pull (fraction, n_train, auc_mean, auc_ci) for a regime, dropping NaNs."""
    fracs, ns, means, cis = [], [], [], []
    for p in points:
        mean = p.get(f"{key_prefix}_auc_mean")
        if mean is None or not np.isfinite(mean):
            continue
        fracs.append(p["fraction"])
        ns.append(p.get(f"{key_prefix}_n_train", 0))
        means.append(mean)
        cis.append(p.get(f"{key_prefix}_auc_ci", 0.0))
    return (
        np.asarray(fracs, dtype=np.float64),
        np.asarray(ns, dtype=np.int64),
        np.asarray(means, dtype=np.float64),
        np.asarray(cis, dtype=np.float64),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-json", default=str(IN_JSON))
    ap.add_argument("--out", default=str(OUT_PNG))
    args = ap.parse_args()

    in_path = Path(args.in_json)
    if not in_path.exists():
        sys.exit(
            f"[plot] missing {in_path}; run scripts/data_efficiency_curve.py first"
        )
    payload = json.loads(in_path.read_text())
    points = payload["points"]
    if not points:
        sys.exit("[plot] no points in data_efficiency.json")

    rf, rn, rm, rci = _series(points, "random")
    xf, xn, xm, xci = _series(points, "xlang")

    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)

    # Color choices match the rest of the writeup: dark green for the
    # strong leaky baseline, amber-orange for the harder xlang split.
    ax.errorbar(
        rf, rm, yerr=rci,
        marker="o", markersize=8, linewidth=2.2,
        capsize=4, capthick=1.2,
        color="#2e7d32", ecolor="#2e7d32",
        label=f"Random 80/20  (test n={payload.get('random_test_size', '?')})",
    )
    ax.errorbar(
        xf, xm, yerr=xci,
        marker="s", markersize=8, linewidth=2.2,
        capsize=4, capthick=1.2,
        color="#ef6c00", ecolor="#ef6c00",
        label=f"Cross-language Py->JS  (test=JavaScript)",
    )

    # AUC=0.9 sightline to make the threshold crossings legible at a glance.
    ax.axhline(0.9, linestyle="--", linewidth=1.0, color="#9aa0a6", alpha=0.7)
    ax.text(
        0.052, 0.902, "AUC = 0.9",
        fontsize=9, color="#5f6368", va="bottom",
    )

    ax.set_xscale("log")
    # Annotate every fraction with its absolute training size for the random
    # regime (xlang totals are listed in the legend block below).
    xticks = sorted(set(rf.tolist() + xf.tolist()))
    ax.set_xticks(xticks)
    ax.set_xticklabels([f"{f:g}" for f in xticks])
    ax.set_xlim(min(xticks) * 0.85, max(xticks) * 1.15)

    # Y-axis: keep it tight around the data so the shape is readable, but
    # always include the 0.9 sightline.
    y_lo = min(0.78, float(np.nanmin([rm.min() - rci.max(), xm.min() - xci.max()])))
    y_hi = min(1.0, float(np.nanmax([rm.max() + rci.max(), xm.max() + xci.max()])) + 0.02)
    ax.set_ylim(y_lo, y_hi)

    ax.set_xlabel("Training-set fraction (log scale)", fontsize=12)
    ax.set_ylabel("Held-out AUC", fontsize=12)
    ax.set_title(
        "Data efficiency: held-out AUC vs training set size.",
        fontsize=14, pad=14,
    )

    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="lower right", fontsize=10, frameon=True)

    # Annotate each point with its n_train so reviewers don't have to
    # do mental arithmetic from the fraction axis.
    for f, n, m in zip(rf, rn, rm):
        ax.annotate(
            f"n={n}", xy=(f, m), xytext=(0, 10), textcoords="offset points",
            fontsize=8, color="#2e7d32", ha="center",
        )
    for f, n, m in zip(xf, xn, xm):
        ax.annotate(
            f"n={n}", xy=(f, m), xytext=(0, -14), textcoords="offset points",
            fontsize=8, color="#ef6c00", ha="center",
        )

    fig.text(
        0.01, 0.01,
        f"estimator: {payload.get('estimator', 'LogReg')}  "
        f"  seeds={len(payload.get('seeds', []))}  "
        f"  error bars = 95% CI",
        fontsize=8, color="#5f6368",
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    # Force a 1200x600 raster regardless of layout tweaks.
    fig.set_size_inches(12, 6)
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    print(f"[plot] wrote {out_path.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
