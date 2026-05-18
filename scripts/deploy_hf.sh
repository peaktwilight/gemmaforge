#!/usr/bin/env bash
# Deploy GemmaForge to HuggingFace Spaces.
#
# Requires: `hf` CLI (≥1.15) and a HuggingFace account.
# Run after the probe has been trained (data/probe.npz must exist).
#
# Usage:
#   bash scripts/deploy_hf.sh                  # creates peaktwilight/gemma4ge
#   HF_USER=youruser bash scripts/deploy_hf.sh  # override the namespace
set -euo pipefail

HF_USER="${HF_USER:-peaktwilight}"
SPACE_NAME="${SPACE_NAME:-gemma4ge}"
SDK="${SDK:-docker}"

if ! command -v hf >/dev/null 2>&1; then
  echo "error: \`hf\` CLI not found. install with: pip install -U huggingface_hub" >&2
  exit 1
fi

# Auth check.
if ! hf auth whoami >/dev/null 2>&1; then
  echo "not logged in. running \`hf auth login\`…"
  hf auth login
fi

# Sync the canonical dashboard sources + demo leads into the space staging
# dir (idempotent — overwrites if they have drifted since the last deploy).
mkdir -p hfspace/dashboard hfspace/examples
cp dashboard/index.html dashboard/style.css dashboard/server.py dashboard/__init__.py hfspace/dashboard/
cp examples/leads.jsonl hfspace/examples/leads.jsonl

# Try create, ignore "already exists".
hf repo create "${HF_USER}/${SPACE_NAME}" --repo-type space --space-sdk "${SDK}" || true

# Upload everything in hfspace/ to the Space root.
hf upload "${HF_USER}/${SPACE_NAME}" hfspace/ . --repo-type space

echo ""
echo "deployed: https://huggingface.co/spaces/${HF_USER}/${SPACE_NAME}"
