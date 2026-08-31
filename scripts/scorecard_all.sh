#!/usr/bin/env bash
# Authoring scorecard for all catalog packages (hard = structural; soft = docs quality).
# Soft warnings do not fail by default; pass --fail-on-warn to treat them as errors.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/package_scorecard.py" "$@"
