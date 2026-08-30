#!/usr/bin/env python3
"""Validate a Korux capability package directory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from package_validate import validate_package_dir  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_capability_package.py <package-dir>", file=sys.stderr)
        return 2
    errors = validate_package_dir(Path(sys.argv[1]))
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
