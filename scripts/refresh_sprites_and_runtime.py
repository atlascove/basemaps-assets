#!/usr/bin/env python3
"""Refresh sprite sheets + runtime icon pack in one reproducible command.

This wraps the same steps we run manually:
1) icon size guard
2) build 1x sprites + vendor merge
3) build 2x sprites + vendor merge
4) build runtime webp icon pack
5) assert runtime missing_from_sprite is empty
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], dry_run: bool) -> None:
    pretty = " ".join(cmd)
    print(f"$ {pretty}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh sprites + runtime icon pack")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    args = parser.parse_args()

    run(["./scripts/check-icon-sizes.sh"], args.dry_run)
    run(["mkdir", "-p", "sprites"], args.dry_run)
    run(["spreet", "./icons", "./sprites/sprites"], args.dry_run)
    run(["./scripts/merge_vendor_sprite_keys.py", "--ratio", "1"], args.dry_run)

    run(["./scripts/check-icon-sizes.sh"], args.dry_run)
    run(["spreet", "--retina", "./icons", "./sprites/sprites@2x"], args.dry_run)
    run(["./scripts/merge_vendor_sprite_keys.py", "--ratio", "2"], args.dry_run)

    run(["./scripts/build_runtime_icon_pack.py"], args.dry_run)

    if args.dry_run:
        return 0

    missing_path = ROOT / "runtime" / "icon-pack" / "v1" / "missing_from_sprite.json"
    manifest_path = ROOT / "runtime" / "icon-pack" / "v1" / "manifest.json"

    missing = json.loads(missing_path.read_text(encoding="utf-8"))
    if missing:
        print(f"ERROR: {len(missing)} runtime icons are missing from sprite atlas.")
        print("First 20 missing:", ", ".join(missing[:20]))
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(
        "Refresh complete: "
        f"{manifest.get('icon_count', 'n/a')} runtime icons, "
        f"{manifest.get('missing_count', 'n/a')} missing."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

