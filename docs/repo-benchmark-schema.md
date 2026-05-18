# Repo Benchmark Schema

`scripts/build_repo_benchmark.py` converts token-labelled examples into
repo-level fixtures for `python -m src.scan`.

The generated tree is:

```text
data/repo_benchmark/
  manifest.jsonl
  summary.json
  manifests/<repo_id>.json
  repos/<repo_id>/
    src/...
    fixed/...
    decoys/...
```

Each manifest has schema `gemmaforge.repo_benchmark/v1`.

Required fields:

| Field | Meaning |
|---|---|
| `repo_id` | Stable generated repo id. |
| `repo_path` | Path to the repo relative to the benchmark root. |
| `source` | Dataset construction source. Current value: `dataset_microrepo`. |
| `source_row` | Row index in the source JSONL for the vulnerable file. |
| `pair_group` | Pairing key used to link vulnerable/fixed variants. |
| `language` | Primary language of the vulnerable row. |
| `cwe` | CWE for the vulnerable row. |
| `files` | Files written into the repo with roles: `vulnerable`, `fixed_counterpart`, `safe_decoy`. |
| `vulnerability_traces` | Ground-truth vulnerable regions with file, char offsets, line range, CWE, role. |
| `negative_regions` | Regions expected to be safe, usually fixed counterparts and decoys. |
| `security_oracles` | Provenance of the label. For micro-repos this is `diff_trace`. |

The first repo-level eval should treat a scan lead as a hit when:

1. `lead.file == trace.file`
2. line ranges overlap: `lead.start_line <= trace.end_line` and
   `lead.end_line >= trace.start_line`

Primary scanner metrics:

| Metric | Definition |
|---|---|
| `repo_recall@K` | Fraction of repos with at least one trace hit in the top K leads. |
| `trace_recall@K` | Fraction of all traces hit by top K leads. |
| `first_hit_rank` / `MRR` | Rank of the first true lead. |
| `precision@K` | Fraction of top K leads that overlap any trace. |
| `false_positives_per_kloc` | Non-overlapping leads normalized by scanned code size. |
| `cwe_top1_on_hits` | CWE accuracy for leads that overlap a trace. |

Micro-repos are not a substitute for outcome-grounded repos with tests and
exploits. They are the fast path for training/evaluating repo-level ranking
behavior before adding CWEval/SecureAgentBench-style oracles.
