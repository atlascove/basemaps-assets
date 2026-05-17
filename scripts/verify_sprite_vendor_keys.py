#!/usr/bin/env python3
"""Verify deployable sprite atlases include required vendor-only keys."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPRITES = ROOT / "sprites"
VENDOR_KEYS = ROOT / "vendor" / "maptiler-openstreetmap-sprite" / "keys.json"

ATLAS_FILES = [
    SPRITES / "sprites.json",
    SPRITES / "sprites@2x.json",
    SPRITES / "sprites@64.json",
]


def main() -> int:
    required = json.loads(VENDOR_KEYS.read_text(encoding="utf-8"))
    failures: list[str] = []

    for atlas_path in ATLAS_FILES:
        atlas = json.loads(atlas_path.read_text(encoding="utf-8"))
        missing = [key for key in required if key not in atlas]
        print(f"{atlas_path.relative_to(ROOT)}: {len(atlas)} keys, missing_vendor={len(missing)}")
        if missing:
            failures.append(f"{atlas_path.relative_to(ROOT)} missing: {', '.join(missing)}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
