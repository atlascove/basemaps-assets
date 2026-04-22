#!/usr/bin/env python3
"""Build a 64px sprite atlas from SVG source icons.

Output:
- sprites/sprites@64.png
- sprites/sprites@64.json

Rules:
- 15x15 source SVGs render to 64x64
- 30x30 *-big variants render to 128x128
- required vendor-only keys are merged from vendor 1x atlas, scaled by 64/15
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, List

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT / "icons"
SPRITES_DIR = ROOT / "sprites"
VENDOR_DIR = ROOT / "vendor" / "maptiler-openstreetmap-sprite"

OUT_PNG = SPRITES_DIR / "sprites@64.png"
OUT_JSON = SPRITES_DIR / "sprites@64.json"

BASE_ICON_SIZE = 15.0
TARGET_ICON_SIZE = 64.0
SCALE = TARGET_ICON_SIZE / BASE_ICON_SIZE
# Keep selected icons "standard" in @64 even if source SVG is 30x30.
# This lets us run enlarged train icons in 1x/2x sprites while retaining 64x64 in sprites@64.
FORCE_STANDARD_64_KEYS = {
    "temaki-train-big",
    "temaki-airport-big",
    "ocha-train-big",
    "ocha-train-whitefill-big",
    "ocha-airport-whitefill-big",
    "ocha-airport-whitefill",
    "ocha-aerialway-station-whitefill",
    "ocha-board-bus-whitefill",
    "ocha-bus-stop-whitefill",
    "ocha-bus-whitefill",
    "ocha-ferry-maki-whitefill",
    "ocha-ferry-whitefill",
    "ocha-hanging-rail-whitefill",
    "ocha-light-rail-whitefill",
    "ocha-monorail-whitefill",
    "ocha-tram-whitefill",
    "fts-subway-whitefill",
    "fts-subway",
    "temaki-subway",
}
SOURCE_OVERRIDE_64 = {}

SVG_TAG_RE = re.compile(r"<svg\s+[^>]*>", re.IGNORECASE)
WIDTH_RE = re.compile(r'\bwidth\s*=\s*"?(\d+(?:\.\d+)?)"?', re.IGNORECASE)
HEIGHT_RE = re.compile(r'\bheight\s*=\s*"?(\d+(?:\.\d+)?)"?', re.IGNORECASE)
XMLNS_RE = re.compile(r'\s+xmlns\s*=\s*"[^"]*"', re.IGNORECASE)


@dataclass
class SpriteItem:
    name: str
    image: Image.Image
    width: int
    height: int


def parse_svg_size(path: Path) -> Tuple[float, float]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    tag_match = SVG_TAG_RE.search(text)
    if not tag_match:
        raise ValueError(f"no <svg> tag in {path}")
    tag = tag_match.group(0)
    w = WIDTH_RE.search(tag)
    h = HEIGHT_RE.search(tag)
    if not w or not h:
        raise ValueError(f"missing width/height in {path}")
    return float(w.group(1)), float(h.group(1))


def render_svg(path: Path, out_w: int, out_h: int) -> Image.Image:
    svg_text = path.read_text(encoding="utf-8", errors="ignore")
    # Some source SVGs include duplicate xmlns on the root tag; sanitize before rendering.
    m = SVG_TAG_RE.search(svg_text)
    if m:
        tag = m.group(0)
        cleaned = XMLNS_RE.sub("", tag)
        cleaned = cleaned.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        svg_text = svg_text[: m.start()] + cleaned + svg_text[m.end() :]
    cmd = ["rsvg-convert", "-w", str(out_w), "-h", str(out_h), "-"]
    proc = subprocess.run(cmd, input=svg_text.encode("utf-8"), check=True, capture_output=True)
    from io import BytesIO

    img = Image.open(BytesIO(proc.stdout)).convert("RGBA")
    return img


def load_local_items() -> List[SpriteItem]:
    items: List[SpriteItem] = []
    for svg in sorted(ICONS_DIR.glob("*.svg")):
        source_svg = svg
        source_stem = SOURCE_OVERRIDE_64.get(svg.stem)
        if source_stem:
            source_svg = ICONS_DIR / f"{source_stem}.svg"
        out_w = int(TARGET_ICON_SIZE)
        out_h = int(TARGET_ICON_SIZE)
        img = render_svg(source_svg, out_w, out_h)
        items.append(SpriteItem(name=svg.stem, image=img, width=img.width, height=img.height))
    return items


def pack_items(items: List[SpriteItem], min_width: int = 4096) -> Tuple[Image.Image, Dict[str, Dict[str, float]], int]:
    atlas_w = min_width
    x = 0
    y = 0
    row_h = 0
    placements: Dict[str, Tuple[int, int, int, int]] = {}

    for it in items:
        if x + it.width > atlas_w:
            x = 0
            y += row_h
            row_h = 0
        placements[it.name] = (x, y, it.width, it.height)
        x += it.width
        row_h = max(row_h, it.height)

    atlas_h = y + row_h
    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))

    for it in items:
        px, py, _, _ = placements[it.name]
        atlas.paste(it.image, (px, py))

    index: Dict[str, Dict[str, float]] = {}
    for name, (px, py, w, h) in placements.items():
        index[name] = {"x": px, "y": py, "width": w, "height": h, "pixelRatio": 1}

    return atlas, index, atlas_w


def merge_vendor_keys(
    atlas: Image.Image,
    index: Dict[str, Dict[str, float]],
    atlas_w: int,
) -> Tuple[Image.Image, Dict[str, Dict[str, float]], List[str]]:
    vendor_json = json.loads((VENDOR_DIR / "1x.json").read_text(encoding="utf-8"))
    vendor_keys = json.loads((VENDOR_DIR / "keys.json").read_text(encoding="utf-8"))
    vendor_png = Image.open(VENDOR_DIR / "1x.png").convert("RGBA")

    missing = [k for k in vendor_keys if k not in index and k in vendor_json]
    if not missing:
        return atlas, index, []

    x = 0
    y = atlas.height
    row_h = 0
    scaled_tiles: Dict[str, Image.Image] = {}
    placements: Dict[str, Tuple[int, int, int, int]] = {}

    for key in missing:
        vm = vendor_json[key]
        sx, sy = int(vm["x"]), int(vm["y"])
        sw, sh = int(vm["width"]), int(vm["height"])
        tile = vendor_png.crop((sx, sy, sx + sw, sy + sh))
        tw = int(TARGET_ICON_SIZE)
        th = int(TARGET_ICON_SIZE)
        scaled = tile.resize((tw, th), Image.Resampling.LANCZOS)
        scaled_tiles[key] = scaled

        if x + tw > atlas_w:
            x = 0
            y += row_h
            row_h = 0
        placements[key] = (x, y, tw, th)
        x += tw
        row_h = max(row_h, th)

    out_h = y + row_h
    out = Image.new("RGBA", (atlas_w, out_h), (0, 0, 0, 0))
    out.paste(atlas, (0, 0))

    for key in missing:
        px, py, tw, th = placements[key]
        out.paste(scaled_tiles[key], (px, py))
        index[key] = {"x": px, "y": py, "width": tw, "height": th, "pixelRatio": 1}

    return out, index, missing


def main() -> int:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)

    items = load_local_items()
    atlas, index, atlas_w = pack_items(items)
    atlas, index, merged = merge_vendor_keys(atlas, index, atlas_w)

    atlas.save(OUT_PNG)
    OUT_JSON.write_text(json.dumps(index, separators=(",", ":")) + "\n", encoding="utf-8")

    # Sanity prints for quick checks in CI/local logs
    print(f"built: {OUT_PNG} ({atlas.width}x{atlas.height})")
    print(f"built: {OUT_JSON} ({len(index)} keys)")
    print(f"vendor_merged: {len(merged)}")
    for key in ("maki-shop", "fas-scales", "temaki-train-big"):
        if key in index:
            m = index[key]
            print(f"{key}: {int(m['width'])}x{int(m['height'])} px")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
