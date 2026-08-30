#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
for dir in "$ROOT"/packages/*/; do
  name="$(basename "$dir")"
  if [[ "$name" == _template ]]; then
    continue
  fi
  echo "validate $name"
  if ! python3 "$ROOT/scripts/validate_capability_package.py" "$dir"; then
    fail=1
  fi
done
exit "$fail"
