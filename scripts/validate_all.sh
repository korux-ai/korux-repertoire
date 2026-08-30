#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

# packages/<namespace>/<name>/ or legacy flat packages/<id>/ (skip _template)
while IFS= read -r -d '' dir; do
  rel="${dir#"$ROOT"/packages/}"
  rel="${rel%/}"
  name="$(basename "$dir")"
  parent="$(basename "$(dirname "$dir")")"
  if [[ "$name" == _template || "$parent" == _template || "$rel" == _template ]]; then
    continue
  fi
  # Only validate dirs that contain manifest.json
  if [[ ! -f "$dir/manifest.json" ]]; then
    continue
  fi
  echo "validate $rel"
  if ! python3 "$ROOT/scripts/validate_capability_package.py" "$dir"; then
    fail=1
  fi
done < <(find "$ROOT/packages" -mindepth 1 -maxdepth 2 -type d -print0 | sort -z)

exit "$fail"
