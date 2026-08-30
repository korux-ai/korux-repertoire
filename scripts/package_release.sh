#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: package_release.sh vX.Y.Z" >&2
  exit 2
fi
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "version must look like v0.1.0, got: $VERSION" >&2
  exit 2
fi

"$ROOT/scripts/validate_all.sh"

DIST="$ROOT/dist"
rm -rf "$DIST"
mkdir -p "$DIST"
ZIP_NAME="korux-repertoire-${VERSION}.zip"
ZIP_PATH="$DIST/$ZIP_NAME"

# Staging tree: packages/<id>/... excluding _template
STAGE="$DIST/stage"
mkdir -p "$STAGE/packages"
for dir in "$ROOT"/packages/*/; do
  name="$(basename "$dir")"
  if [[ "$name" == _template ]]; then
    continue
  fi
  cp -R "$dir" "$STAGE/packages/$name"
done

(
  cd "$STAGE"
  zip -r "$ZIP_PATH" packages
)

(
  cd "$DIST"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$ZIP_NAME" > SHA256SUMS
  else
    shasum -a 256 "$ZIP_NAME" > SHA256SUMS
  fi
)

rm -rf "$STAGE"
echo "wrote $ZIP_PATH"
echo "wrote $DIST/SHA256SUMS"
