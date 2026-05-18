#!/usr/bin/env bash
set -euo pipefail

# GPU-friendly wrapper for the repo-level probe benchmark.
#
# Typical full run:
#   CUDA_VISIBLE_DEVICES=0 bash scripts/run_repo_scan_gpu.sh
#
# Four-way sharded run, one process per GPU/machine:
#   CUDA_VISIBLE_DEVICES=0 NUM_SHARDS=4 SHARD_INDEX=0 bash scripts/run_repo_scan_gpu.sh
#   CUDA_VISIBLE_DEVICES=1 NUM_SHARDS=4 SHARD_INDEX=1 bash scripts/run_repo_scan_gpu.sh
#
# After all shards finish, aggregate the full report:
#   uv run python scripts/eval_repo_leads.py \
#     --manifest data/repo_benchmark/manifest.jsonl \
#     --leads-dir data/repo_benchmark/leads_weak_full \
#     --out-json data/eval/repo_scan_report_weak_full.json

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

MODEL_ID="${MODEL_ID:-google/gemma-4-E2B-it}"
PROBE_PROFILE="${PROBE_PROFILE:-weak-probe}"
TOP_K="${TOP_K:-25}"
MIN_CONFIDENCE="${MIN_CONFIDENCE:-0.5}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-data/repo_benchmark}"
LEADS_DIR="${LEADS_DIR:-data/repo_benchmark/leads_weak_full}"
OUT_JSON="${OUT_JSON:-data/eval/repo_scan_report_weak_full.json}"
NUM_SHARDS="${NUM_SHARDS:-1}"
SHARD_INDEX="${SHARD_INDEX:-0}"
MAX_REPOS="${MAX_REPOS:-}"
START="${START:-0}"

cmd=(
  uv run python scripts/run_repo_scan_benchmark.py
  --benchmark-root "$BENCHMARK_ROOT"
  --leads-dir "$LEADS_DIR"
  --out-json "$OUT_JSON"
  --model-id "$MODEL_ID"
  --probe-profile "$PROBE_PROFILE"
  --top-k "$TOP_K"
  --min-confidence "$MIN_CONFIDENCE"
  --num-shards "$NUM_SHARDS"
  --shard-index "$SHARD_INDEX"
  --start "$START"
  --resume
)

if [[ -n "$MAX_REPOS" ]]; then
  cmd+=(--max-repos "$MAX_REPOS")
fi

echo "[gpu-run] CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
echo "[gpu-run] MODEL_ID=$MODEL_ID"
echo "[gpu-run] PROBE_PROFILE=$PROBE_PROFILE"
echo "[gpu-run] LEADS_DIR=$LEADS_DIR"
echo "[gpu-run] OUT_JSON=$OUT_JSON"
echo "[gpu-run] SHARD=$SHARD_INDEX/$NUM_SHARDS"
echo "[gpu-run] command: ${cmd[*]} $*"

"${cmd[@]}" "$@"
