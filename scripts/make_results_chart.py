"""Build the AUC ladder chart for the GemmaForge writeup.

Reads probe result JSON files from data/ and renders a single horizontal bar
chart (1200x600 PNG) that compares every probe variant against the random
baseline. Output is written to web/auc-ladder.png so it can be embedded into
WRITEUP.md / RESULTS.md.

Run:
    python scripts/make_results_chart.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = ROOT / "web"


def load_json(path: Path):
    """Best-effort JSON load. Warn and return None when the file is missing."""

    if not path.exists():
        print(f"[warn] {path.relative_to(ROOT)} not found - using fallback value", file=sys.stderr)
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[warn] failed to read {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        return None


def auc_color(auc: float) -> str:
    """Map an AUC value to a band-aware bar color."""

    if auc < 0.85:
        return "#9aa0a6"  # grey -- random / weak
    if auc < 0.93:
        return "#f4c430"  # yellow -- decent
    if auc < 0.97:
        return "#9ccc65"  # light green -- strong
    return "#2e7d32"  # strong green -- best in class


def pull_numbers() -> dict[str, float]:
    """Resolve the AUC for every label, falling back to the spec values."""

    fallbacks = {
        "random_baseline": 0.500,
        "length_feature": 0.55,
        "py_to_js": 0.907,
        "maxpool_full": 0.932,
        "logreg_l17": 0.963,
        "mlp_128_64": 0.965,
        "mlp_64": 0.970,
        "ensemble": 0.976,
        "per_cwe_macro": 0.973,
    }

    resolved = dict(fallbacks)

    card = load_json(DATA / "probe_card.json")
    if card and "best_auc" in card:
        resolved["logreg_l17"] = float(card["best_auc"])

    per_cwe = load_json(DATA / "probe_per_cwe_card.json")
    if per_cwe and "macro_auc" in per_cwe:
        resolved["per_cwe_macro"] = float(per_cwe["macro_auc"])

    ensemble = load_json(DATA / "probe_ensemble.json")
    if ensemble:
        best_method = ensemble.get("best_method")
        for row in ensemble.get("results", []):
            if row.get("method") == best_method:
                resolved["ensemble"] = float(row["auc"])
                break

    mlp = load_json(DATA / "probe_mlp_ablation.json")
    if mlp:
        for row in mlp.get("rows", []):
            if row.get("split") != "random_stratified":
                continue
            if row.get("variant") == "mlp_64":
                resolved["mlp_64"] = float(row["auc"])
            elif row.get("variant") == "mlp_128_64":
                resolved["mlp_128_64"] = float(row["auc"])
            elif row.get("variant") == "logreg":
                resolved["logreg_l17"] = float(row["auc"])
            if row.get("split", "").startswith("heldout_lang::test=javascript") and row.get("variant") == "logreg":
                resolved["py_to_js"] = float(row["auc"])

    maxpool = load_json(DATA / "eval_maxpool_full.json")
    if maxpool and "subset_max_pool_auc" in maxpool:
        resolved["maxpool_full"] = float(maxpool["subset_max_pool_auc"])

    return resolved


def main() -> int:
    aucs = pull_numbers()

    # Spec order: top -> bottom on the chart.
    rows = [
        ("Per-CWE macro (random)", aucs["per_cwe_macro"]),
        ("4-layer ensemble (random)", aucs["ensemble"]),
        ("MLP(64,) L17 (random)", aucs["mlp_64"]),
        ("MLP(128,64) L17 (random)", aucs["mlp_128_64"]),
        ("LogReg L17 (random split)", aucs["logreg_l17"]),
        ("Max-pool aggregation (full held-out)", aucs["maxpool_full"]),
        ("LogReg L17 (cross-language Py→JS)", aucs["py_to_js"]),
        ("Length-of-input feature", aucs["length_feature"]),
        ("Random baseline (50/50)", aucs["random_baseline"]),
    ]

    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]
    colors = [auc_color(v) for v in values]

    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)

    y_pos = list(range(len(labels)))
    bars = ax.barh(y_pos, values, color=colors, edgecolor="#1f2933", linewidth=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()  # first row stays on top
    ax.set_xlim(0.5, 1.0)
    ax.set_xlabel("ROC-AUC", fontsize=11)

    # Reference lines for 0.5 random and 0.9 "useful" thresholds.
    ax.axvline(0.5, color="#9aa0a6", linewidth=1.0, linestyle="--", alpha=0.7)
    ax.axvline(0.9, color="#1f2933", linewidth=0.7, linestyle=":", alpha=0.4)

    # Annotate each bar with its AUC.
    for bar, value in zip(bars, values):
        ax.text(
            value + 0.004,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.3f}",
            va="center",
            ha="left",
            fontsize=9,
            color="#1f2933",
        )

    ax.set_title(
        "GemmaForge probe variants — AUC ladder",
        fontsize=14,
        fontweight="bold",
        pad=14,
        loc="left",
    )

    # Legend for color bands.
    legend_handles = [
        Patch(facecolor="#9aa0a6", edgecolor="#1f2933", label="<0.85 (random / weak)"),
        Patch(facecolor="#f4c430", edgecolor="#1f2933", label="0.85-0.93 (decent)"),
        Patch(facecolor="#9ccc65", edgecolor="#1f2933", label="0.93-0.97 (strong)"),
        Patch(facecolor="#2e7d32", edgecolor="#1f2933", label=">0.97 (best in class)"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower right",
        fontsize=8,
        frameon=True,
        framealpha=0.95,
        title="ROC-AUC band",
        title_fontsize=8,
    )

    ax.grid(axis="x", linestyle=":", alpha=0.35)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    footnote = (
        "Gemma 4 E2B layer 17, ~1k pairs, 80/20 stratified unless noted. "
        "Cross-language Py→JS is the OOD stress test."
    )
    fig.text(
        0.01,
        0.015,
        footnote,
        fontsize=8.5,
        color="#3c4858",
        style="italic",
    )

    fig.tight_layout(rect=(0, 0.05, 1, 1))

    WEB.mkdir(parents=True, exist_ok=True)
    out = WEB / "auc-ladder.png"
    fig.savefig(out, dpi=100, bbox_inches=None, facecolor="white")
    plt.close(fig)

    print(f"[ok] wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
