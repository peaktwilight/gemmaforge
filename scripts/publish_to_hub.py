#!/usr/bin/env python3
"""Publish the GemmaForge probe artifacts and labeled dataset to the Hugging Face Hub.

This script populates two repos so external researchers can pull our work directly:

    # 1. shipped probes (model repo)
    from huggingface_hub import snapshot_download
    snapshot_download("peaktwilight/gemmaforge-probe")

    # 2. labeled vuln/safe pairs (dataset repo)
    from datasets import load_dataset
    load_dataset("peaktwilight/gemmaforge-data")

Requires `HF_TOKEN` (or `HF_WRITE_TOKEN`) in env with **write** access to both repos.
Run with `--dry-run` first to preview the upload plan without touching the Hub.

The script is idempotent — re-running updates existing repos in place via
`HfApi.upload_file` / `HfApi.upload_folder`.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

PROBE_REPO_ID = "peaktwilight/gemmaforge-probe"
DATA_REPO_ID = "peaktwilight/gemmaforge-data"

# (local_path_relative_to_DATA_DIR, path_in_repo)
PROBE_FILES: list[tuple[str, str]] = [
    ("probe.npz", "probe.npz"),
    ("probe_per_cwe.npz", "probe_per_cwe.npz"),
    ("probe_ensemble.npz", "probe_ensemble.npz"),
    ("probe_spanmax.npz", "probe_spanmax.npz"),
    # Companion JSON cards make AUC numbers reproducible without re-running eval.
    ("probe_card.json", "probe_card.json"),
    ("probe_per_cwe_card.json", "probe_per_cwe_card.json"),
    ("probe_ensemble.json", "probe_ensemble.json"),
    ("probe_spanmax_card.json", "probe_spanmax_card.json"),
]

DATA_FILES: list[tuple[str, str]] = [
    ("dataset.jsonl", "dataset.jsonl"),
    ("pairs_v2.jsonl", "pairs_v2.jsonl"),
    ("pairs_length_matched.jsonl", "pairs_length_matched.jsonl"),
    ("pairs_rich.jsonl", "pairs_rich.jsonl"),
]


# -----------------------------------------------------------------------------
# README templates (inline so the script is self-contained)
# -----------------------------------------------------------------------------

PROBE_README = """---
license: apache-2.0
language:
  - code
tags:
  - gemma
  - interpretability
  - linear-probe
  - vulnerability-detection
  - code-security
  - safety
library_name: huggingface_hub
base_model: google/gemma-3-4b-it
---

# GemmaForge Probe

Linear / multi-head / token-level probes trained on Gemma 4 hidden states to detect
vulnerable code **token-by-token, mid-generation**.

This repo ships the four probes evaluated in the GemmaForge writeup. Each `.npz`
is a small NumPy bundle holding the weights of a logistic-regression head (or a
trained token-level value head) over Gemma 4 hidden states.

Companion JSON cards (`probe_card.json`, `probe_per_cwe_card.json`,
`probe_ensemble.json`, `probe_spanmax_card.json`) carry the full per-layer
metrics, train/eval sizes, and split seeds so the numbers below are
reproducible without re-running evaluation.

## Headline results

| Probe                       | File                  | AUC                            | Notes                                              |
|-----------------------------|-----------------------|--------------------------------|----------------------------------------------------|
| Single-layer LogReg (L17)   | `probe.npz`           | **0.960** (test, layer 17)     | Shipped in the demo. 1,536-dim input.              |
| 4-layer ensemble (mean)     | `probe_ensemble.npz`  | **0.976** (uniform mean)       | Layers 8 / 17 / 26 / 34. Beats single-layer.       |
| Per-CWE 5-head (L17)        | `probe_per_cwe.npz`   | **0.973** macro-AUC            | CWE-78 / 338 / 95 / 94 / 328. Top-1 routing 94.7%. |
| Token-level span-max (L8)   | `probe_spanmax.npz`   | 0.768 token / 0.700 example    | Per-token head, Obeso/Arditi-style span-max loss.  |

Cross-language transfer (Python -> JavaScript, single-layer L17): **AUC 0.907**.
Group-by-repo split: **AUC 0.958**.

## Load it

```python
import numpy as np
from huggingface_hub import snapshot_download

local = snapshot_download("peaktwilight/gemmaforge-probe")
probe = np.load(f"{local}/probe.npz")
w, b, layer = probe["w"], probe["b"], int(probe["layer"])

# Score a Gemma 4 hidden state h (shape: [1536]) from `layer`:
score = 1.0 / (1.0 + np.exp(-(h @ w + b)))
```

For the per-CWE bundle the file holds one `(w, b)` pair per CWE plus a head ordering;
see `probe_per_cwe_card.json` for the head list. The ensemble bundle holds four
heads (one per probed layer) and is intended to be combined by uniform mean.

## Training data

These probes were trained on `peaktwilight/gemmaforge-data` (see that repo for
schema and licensing). The training set merges:

- **CyberSecEval** position-paired vulnerable / lead-up snippets (Meta, MIT-style).
- **SVEN** before/after CWE-tagged commits (MIT).
- A small natural-language negative set so the probe does not fire on chat preamble.

## Intended use & limits

GemmaForge is a research probe, not a production scanner. It complements
static analysis; it does not replace Snyk / Semgrep / CodeQL. The headline
0.96 AUC is on a held-out test split of the same SVEN + CyberSecEval pool;
performance on never-seen vulnerability classes will be lower (we provide
held-out-CWE numbers ranging 0.92 - 0.96 in the writeup for context).

## Citation

If you use this probe, please cite GemmaForge and the underlying SVEN and
CyberSecEval datasets.

## License

Apache-2.0 for our derived artifacts. Upstream SVEN code excerpts: MIT.
Upstream CyberSecEval code excerpts: see Meta's license at
https://github.com/meta-llama/PurpleLlama .
"""


DATA_README = """---
license: apache-2.0
language:
  - code
tags:
  - vulnerability-detection
  - code-security
  - cwe
  - sven
  - cybersec-eval
task_categories:
  - text-classification
  - token-classification
pretty_name: GemmaForge Data
size_categories:
  - 1K<n<10K
configs:
  - config_name: dataset
    data_files:
      - split: train
        path: dataset.jsonl
  - config_name: pairs_v2
    data_files:
      - split: train
        path: pairs_v2.jsonl
  - config_name: pairs_length_matched
    data_files:
      - split: train
        path: pairs_length_matched.jsonl
  - config_name: pairs_rich
    data_files:
      - split: train
        path: pairs_rich.jsonl
---

# GemmaForge Data

Labeled vulnerable / safe code snippets used to train the
[GemmaForge probes](https://huggingface.co/peaktwilight/gemmaforge-probe) on
Gemma 4 hidden states.

Four configs are shipped, each a JSONL file. They differ in **provenance**,
**balance**, and **annotation depth**, not in label semantics — `label==1` is
always "this code is vulnerable" and `label==0` is "this code is safe".

| Config                 | File                          | Rows | Source mix                      | What's special                              |
|------------------------|-------------------------------|------|---------------------------------|---------------------------------------------|
| `dataset`              | `dataset.jsonl`               | 1374 | SVEN before/after, diff-oracle  | Full SVEN-diff schema, token-level spans.   |
| `pairs_v2`             | `pairs_v2.jsonl`              | 1198 | CyberSecEval position-paired    | Vuln + lead-up positions from real repos.   |
| `pairs_length_matched` | `pairs_length_matched.jsonl`  |  460 | Subset of `pairs_v2`            | Vuln/safe matched on token length.          |
| `pairs_rich`           | `pairs_rich.jsonl`            |  100 | Hand-derived rich labels        | Adds sink / source / sanitizer token spans. |

## Schema

### `dataset.jsonl` (SVEN-diff schema)

```json
{
  "code": "selection = cursor.execute(\\"SELECT * FROM recipe WHERE name = \\" + name)",
  "label": 1,
  "is_completion_vulnerable": true,
  "cwe": "CWE-089",
  "lang": "python",
  "source": "SVEN-before",
  "vuln_type": "cwe-089",
  "token_labels": {
    "sink": [],
    "source": [],
    "sanitizer": [],
    "evidence": [[419, 421], [422, 429]],
    "vulnerable_line": [[419, 421], [422, 429]]
  },
  "label_confidence": "diff_oracle",
  "_func_name": "__init__.callback",
  "_file_name": "mealPlan.py"
}
```

Char-offset spans in `token_labels` refer to byte offsets inside `code`.
`label==0` rows ("SVEN-after") carry the same schema but empty span lists.

### `pairs_v2.jsonl` / `pairs_length_matched.jsonl`

```json
{
  "code": "...",
  "label": 0,
  "cwe": null,
  "cve": null,
  "source": "CyberSecEval-leadup",
  "lang": "javascript",
  "vuln_type": null,
  "_origin_repo": "cerebral/cerebral-debugger-prototype",
  "_line_no": 6
}
```

Position pairs: each vulnerable snippet (`label==1`) has a "lead-up" sibling
(`label==0`) drawn from the same file just before the vulnerable position.

### `pairs_rich.jsonl`

Same payload as `pairs_v2`, plus token-level spans
(`sink` / `source` / `sanitizer` / `evidence` / `vulnerable_line`) for
fine-grained value-head training. 100 hand-derived rows.

## Load it

```python
from datasets import load_dataset

ds = load_dataset("peaktwilight/gemmaforge-data", "dataset")
print(ds["train"][0])
```

Or pick a specific config:

```python
pairs = load_dataset("peaktwilight/gemmaforge-data", "pairs_v2")
length_matched = load_dataset("peaktwilight/gemmaforge-data", "pairs_length_matched")
rich = load_dataset("peaktwilight/gemmaforge-data", "pairs_rich")
```

## Languages & CWE coverage

Python, JavaScript, C, C++. CWE coverage spans CWE-22 / 78 / 79 / 89 / 94 /
95 / 295 / 327 / 328 / 330 / 338 / 352 / 502 / 798 / 918 / 1333.

## Provenance & licensing

This dataset is a derived corpus. Our derivations (selection, pairing,
rich-label annotations, dataset construction code) are released under
**Apache-2.0**. The underlying upstream code excerpts retain their own
licenses:

- **SVEN** — MIT. Please cite He & Vechev (2023), "Large Language Models for
  Code: Security Hardening and Adversarial Testing."
- **CyberSecEval** — Meta. See https://github.com/meta-llama/PurpleLlama for
  the upstream license terms.

If you use this dataset, please cite GemmaForge **and** both upstream sources.

## Limits

The dataset is research-grade. Lead-up snippets from CyberSecEval are
heuristic negatives, not formally proven safe. Token spans in
`pairs_rich.jsonl` are derived heuristically; treat them as supervision
signal, not ground truth.
"""


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


@dataclass
class UploadPlan:
    repo_id: str
    repo_type: str  # "model" or "dataset"
    files: list[tuple[Path, str]]  # (local_path, path_in_repo)
    readme_text: str


def _resolve_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HF_WRITE_TOKEN")
    if not token:
        print(
            "[publish_to_hub] ERROR: HF_TOKEN (or HF_WRITE_TOKEN) is not set.\n"
            "  Create a write-scoped token at https://huggingface.co/settings/tokens\n"
            "  then `export HF_TOKEN=hf_...` and re-run.",
            file=sys.stderr,
        )
        sys.exit(2)
    return token


def _check_files_exist(plan: UploadPlan) -> None:
    missing = [str(p) for p, _ in plan.files if not p.exists()]
    if missing:
        print(
            f"[publish_to_hub] ERROR: missing local files for {plan.repo_id}:\n  "
            + "\n  ".join(missing),
            file=sys.stderr,
        )
        sys.exit(3)


def _build_probe_plan() -> UploadPlan:
    files = [(DATA_DIR / src, dst) for src, dst in PROBE_FILES]
    return UploadPlan(
        repo_id=PROBE_REPO_ID,
        repo_type="model",
        files=files,
        readme_text=PROBE_README,
    )


def _build_data_plan() -> UploadPlan:
    files = [(DATA_DIR / src, dst) for src, dst in DATA_FILES]
    return UploadPlan(
        repo_id=DATA_REPO_ID,
        repo_type="dataset",
        files=files,
        readme_text=DATA_README,
    )


def _print_plan(plan: UploadPlan) -> None:
    print(f"\n=== {plan.repo_id} ({plan.repo_type}) ===")
    print(f"  README.md  ({len(plan.readme_text):,} bytes, inline template)")
    for local, remote in plan.files:
        size = local.stat().st_size if local.exists() else 0
        marker = "" if local.exists() else "  [MISSING]"
        print(f"  {remote:32s}  <- {local}  ({size:,} bytes){marker}")


def _execute_plan(plan: UploadPlan, token: str) -> None:
    # Imports deferred so `--dry-run` works without the dependency installed.
    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError

    api = HfApi(token=token)

    print(f"[publish_to_hub] Ensuring repo exists: {plan.repo_id} ({plan.repo_type})")
    try:
        api.create_repo(
            repo_id=plan.repo_id,
            repo_type=plan.repo_type,
            exist_ok=True,
            private=False,
        )
    except HfHubHTTPError as exc:
        print(f"[publish_to_hub] ERROR creating repo {plan.repo_id}: {exc}", file=sys.stderr)
        sys.exit(4)

    # 1. Upload the README from an inline template via a temp file so we can
    #    keep the script single-source-of-truth.
    with tempfile.TemporaryDirectory() as tmp:
        readme_path = Path(tmp) / "README.md"
        readme_path.write_text(plan.readme_text, encoding="utf-8")
        print(f"[publish_to_hub] Uploading README.md -> {plan.repo_id}")
        api.upload_file(
            path_or_fileobj=str(readme_path),
            path_in_repo="README.md",
            repo_id=plan.repo_id,
            repo_type=plan.repo_type,
            commit_message="Update README via scripts/publish_to_hub.py",
        )

    # 2. Upload each artifact individually (more diff-friendly than upload_folder
    #    when only one file changes between runs, and keeps commit messages tidy).
    for local, remote in plan.files:
        print(f"[publish_to_hub] Uploading {remote} -> {plan.repo_id}")
        api.upload_file(
            path_or_fileobj=str(local),
            path_in_repo=remote,
            repo_id=plan.repo_id,
            repo_type=plan.repo_type,
            commit_message=f"Update {remote} via scripts/publish_to_hub.py",
        )

    print(f"[publish_to_hub] Done: https://huggingface.co/{plan.repo_id}")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Publish GemmaForge probes + dataset to the Hugging Face Hub.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the upload plan but do not touch the Hub or require HF_TOKEN.",
    )
    p.add_argument(
        "--probe-only",
        action="store_true",
        help=f"Only publish the probe repo ({PROBE_REPO_ID}).",
    )
    p.add_argument(
        "--data-only",
        action="store_true",
        help=f"Only publish the dataset repo ({DATA_REPO_ID}).",
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.probe_only and args.data_only:
        print("[publish_to_hub] --probe-only and --data-only are mutually exclusive.", file=sys.stderr)
        return 2

    plans: list[UploadPlan] = []
    if not args.data_only:
        plans.append(_build_probe_plan())
    if not args.probe_only:
        plans.append(_build_data_plan())

    for plan in plans:
        _check_files_exist(plan)
        _print_plan(plan)

    if args.dry_run:
        print("\n[publish_to_hub] --dry-run: not uploading. Re-run without the flag to publish.")
        return 0

    token = _resolve_token()
    for plan in plans:
        _execute_plan(plan, token)

    print("\n[publish_to_hub] All uploads complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
