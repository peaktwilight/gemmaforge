#!/usr/bin/env bash
# demo_pipeline.sh — walk a viewer through the GemmaForge -> pwnkit pipeline.
#
# Pipeline:
#   1. `python -m src.scan <target>` walks the repo, runs the probe on each
#      chunk, and emits ND-JSON leads (gemmaforge.leads/v1).
#   2. pwnkit's `triage --seed-findings` consumes that same JSONL to focus
#      its agentic hunters on the regions the cheap probe lit up.
#
# This script can run in two modes:
#   - LIVE   (default): runs `python -m src.scan` for real. Requires the
#     probe .npz files and Gemma 4 weights to be available.
#   - REPLAY (--replay): skips the scan and just inspects the pre-computed
#     examples/leads.jsonl. Useful for judges / CI where weights aren't
#     available.
set -euo pipefail

# --------------- pretty output --------------- #
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; CYAN=$'\033[36m'; GREEN=$'\033[32m'
  YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
  BOLD=""; DIM=""; CYAN=""; GREEN=""; YELLOW=""; RESET=""
fi

step() { printf '\n%s== %s ==%s\n' "${BOLD}${CYAN}" "$1" "${RESET}"; }
info() { printf '%s%s%s\n' "${DIM}" "$1" "${RESET}"; }
ok()   { printf '%s>> %s%s\n' "${GREEN}" "$1" "${RESET}"; }
warn() { printf '%s!! %s%s\n' "${YELLOW}" "$1" "${RESET}"; }

# --------------- args --------------- #
MODE="live"
if [[ "${1:-}" == "--replay" ]]; then
  MODE="replay"
fi

# Resolve repo root from this script's location so `bash scripts/demo_pipeline.sh`
# works from anywhere.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TARGET="examples/vuln-express-app"
LEADS="examples/leads.jsonl"

# --------------- step 1: scan --------------- #
step "1. gemmaforge scan -> $LEADS"
info "scanning $TARGET with the GemmaForge probe; ND-JSON leads land in $LEADS"
if [[ "$MODE" == "live" ]]; then
  python -m src.scan "$TARGET" \
      --top-k 10 \
      --min-confidence 0.5 \
      --output "$LEADS"
  ok "scan complete"
else
  warn "--replay: skipping scan, using pre-computed $LEADS"
  if [[ ! -f "$LEADS" ]]; then
    echo "error: $LEADS not present; run without --replay or check in the file" >&2
    exit 1
  fi
fi

# --------------- step 2: inspect leads --------------- #
step "2. leads.jsonl summary"
LEAD_COUNT=$(grep -c '^{' "$LEADS" || true)
info "wrote $LEAD_COUNT lead(s) to $LEADS"
echo
info "first 3 records (pretty-printed):"
head -n 3 "$LEADS" | python -c '
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    print(json.dumps(json.loads(line), indent=2))
'

# --------------- step 3: feed pwnkit --------------- #
step "3. pwnkit triage --seed-findings"
info "this is the command an operator would run next:"
cat <<CMD

  ${BOLD}pwnkit triage \\
      --seed-findings $LEADS \\
      --target $TARGET${RESET}

CMD
info "(not executed here — requires pwnkit to be installed separately)"

# --------------- step 4: local adapter CLI --------------- #
step "4. integrations.pwnkit adapter — schema check + summary"
info "validates the JSONL against gemmaforge.leads/v1 and prints a ranked table"
python -m integrations.pwnkit "$LEADS"

ok "pipeline walkthrough complete"
