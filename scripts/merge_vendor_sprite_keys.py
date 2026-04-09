#!/usr/bin/env python3
"""Merge curated vendor sprite keys into generated sprites.

This is a post-build step after `spreet` so required non-SVG sprite keys are always present.
It only appends missing keys and never edits existing keys.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "maptiler-openstreetmap-sprite"
SPRITES = ROOT / "sprites"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def merge_variant(ratio: int) -> List[str]:
    if ratio not in (1, 2):
        raise ValueError("ratio must be 1 or 2")

    local_json_path = SPRITES / ("sprites@2x.json" if ratio == 2 else "sprites.json")
    local_png_path = SPRITES / ("sprites@2x.png" if ratio == 2 else "sprites.png")

    vendor_prefix = "2x" if ratio == 2 else "1x"
    vendor_json_path = VENDOR / f"{vendor_prefix}.json"
    vendor_png_path = VENDOR / f"{vendor_prefix}.png"
    keys_path = VENDOR / "keys.json"

    local = load_json(local_json_path)
    vendor = load_json(vendor_json_path)
    keys: List[str] = json.loads(keys_path.read_text(encoding="utf-8"))

    local_img = Image.open(local_png_path).convert("RGBA")
    vendor_img = Image.open(vendor_png_path).convert("RGBA")

    missing = [k for k in keys if k not in local and k in vendor]
    if not missing:
        return []

    atlas_width = max(local_img.width, 2048)
    x = 0
    y = local_img.height
    row_h = 0
    placements = {}

    for key in missing:
        m = vendor[key]
        w = int(m["width"])
        h = int(m["height"])
        if x + w > atlas_width:
            x = 0
            y += row_h
            row_h = 0
        placements[key] = (x, y, w, h)
        x += w
        row_h = max(row_h, h)

    out_h = y + row_h
    out = Image.new("RGBA", (atlas_width, out_h), (0, 0, 0, 0))
    out.paste(local_img, (0, 0))

    for key, (tx, ty, w, h) in placements.items():
        vm = vendor[key]
        sx = int(vm["x"])
        sy = int(vm["y"])
        tile = vendor_img.crop((sx, sy, sx + w, sy + h))
        out.paste(tile, (tx, ty))
        local[key] = {
            "height": h,
            "pixelRatio": ratio,
            "width": w,
            "x": tx,
            "y": ty,
        }

    out.save(local_png_path)
    save_json(local_json_path, local)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ratio", type=int, choices=[1, 2], required=True)
    args = parser.parse_args()

    merged = merge_variant(args.ratio)
    print(f"ratio={args.ratio} merged={len(merged)}")
    if merged:
        print("keys:", ", ".join(merged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
