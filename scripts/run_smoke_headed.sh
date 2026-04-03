#!/usr/bin/env bash
# Activate project venv and run smoke tests in a visible browser (manual OTP).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -f "$ROOT/.venv/bin/activate" ]]; then
  echo "No .venv found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install chromium"
  exit 1
fi
# shellcheck source=/dev/null
source "$ROOT/.venv/bin/activate"
export HEADED=true MANUAL_OTP=true USER_MANUAL_OTP=true
exec pytest tests/smoke -m smoke -v --tb=short "$@"
