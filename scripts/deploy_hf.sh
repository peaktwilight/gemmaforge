#!/usr/bin/env bash
# Deploy GemmaForge to HuggingFace Spaces.
#
# Requires: `hf` CLI (≥1.15) and a HuggingFace account.
# Run after the probe has been trained (data/probe.npz must exist).
#
# Usage:
#   bash scripts/deploy_hf.sh                  # creates peaktwilight/gemmaforge
#   HF_USER=youruser bash scripts/deploy_hf.sh  # override the namespace
set -euo pipefail

HF_USER="${HF_USER:-peaktwilight}"
SPACE_NAME="${SPACE_NAME:-gemmaforge}"
SDK="${SDK:-gradio}"

if ! command -v hf >/dev/null 2>&1; then
  echo "error: \`hf\` CLI not found. install with: pip install -U huggingface_hub" >&2
  exit 1
fi

if [ ! -f "data/probe.npz" ]; then
  echo "error: data/probe.npz missing. train the probe first:" >&2
  echo "  python -m src.extract_activations && python -m src.train_probe" >&2
  exit 1
fi

# Auth check.
if ! hf whoami >/dev/null 2>&1; then
  echo "not logged in. running \`hf auth login\`…"
  hf auth login
fi

# Copy probe into the space.
cp data/probe.npz hfspace/probe.npz
if [ -f "data/probe_card.json" ]; then
  cp data/probe_card.json hfspace/probe_card.json
fi

# Try create, ignore "already exists".
hf repo create "${HF_USER}/${SPACE_NAME}" --repo-type space --space_sdk "${SDK}" || true

# Upload everything in hfspace/ to the Space root.
hf upload "${HF_USER}/${SPACE_NAME}" hfspace/ . --repo-type space

echo ""
echo "deployed: https://huggingface.co/spaces/${HF_USER}/${SPACE_NAME}"
