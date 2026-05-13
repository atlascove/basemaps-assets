#!/usr/bin/env python3
"""Build runtime icon pack (webp) + manifest from current sprite atlas.

Output:
  runtime/icon-pack/v1/icons/*.webp
  runtime/icon-pack/v1/manifest.json
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PRESETS_PATH = ROOT / "meta" / "presets.json"
SPRITE_JSON_PATH = ROOT / "sprites" / "sprites@2x.json"
SPRITE_PNG_PATH = ROOT / "sprites" / "sprites@2x.png"
OUT_DIR = ROOT / "runtime" / "icon-pack" / "v1"
ICONS_DIR = OUT_DIR / "icons"


def safe_name(icon_name: str) -> str:
    name = icon_name.strip().lower()
    name = name.replace(" ", "-").replace("_", "-")
    name = re.sub(r"[^a-z0-9.-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "icon"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    presets = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    sprite_idx: Dict[str, Dict] = json.loads(SPRITE_JSON_PATH.read_text(encoding="utf-8"))
    sprite_img = Image.open(SPRITE_PNG_PATH).convert("RGBA")

    icon_names = sorted({p.get("icon", "").strip() for p in presets if p.get("icon")})
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    missing: List[str] = []
    collisions: Dict[str, List[str]] = {}
    chosen: Dict[str, str] = {}
    entries: List[Dict] = []

    for icon in icon_names:
        fn = safe_name(icon)
        collisions.setdefault(fn, []).append(icon)

    for icon in icon_names:
        if icon not in sprite_idx:
            missing.append(icon)
            continue

        meta = sprite_idx[icon]
        x, y, w, h = int(meta["x"]), int(meta["y"]), int(meta["width"]), int(meta["height"])
        crop = sprite_img.crop((x, y, x + w, y + h))

        base = safe_name(icon)
        owner = chosen.get(base)
        if owner is None:
            chosen[base] = icon
            filename = f"{base}.webp"
        elif owner == icon:
            filename = f"{base}.webp"
        else:
            suffix = hashlib.sha1(icon.encode("utf-8")).hexdigest()[:6]
            filename = f"{base}-{suffix}.webp"

        out_path = ICONS_DIR / filename
        crop.save(out_path, format="WEBP", quality=95, method=6, lossless=True)

        entries.append(
            {
                "icon": icon,
                "file": f"icons/{filename}",
                "width": w,
                "height": h,
                "sha256": sha256_file(out_path),
            }
        )

    manifest = {
        "version": "v1",
        "format": "webp",
        "source": "sprites/sprites@2x",
        "generated_from": {
            "presets": str(PRESETS_PATH.relative_to(ROOT)),
            "sprite_json": str(SPRITE_JSON_PATH.relative_to(ROOT)),
            "sprite_png": str(SPRITE_PNG_PATH.relative_to(ROOT)),
        },
        "icon_count": len(entries),
        "missing_count": len(missing),
        "collisions": {k: v for k, v in collisions.items() if len(v) > 1},
        "icons": entries,
    }

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "missing_from_sprite.json").write_text(json.dumps(missing, indent=2) + "\n", encoding="utf-8")

    print(f"Built runtime icon pack: {len(entries)} icons")
    print(f"Missing from sprite: {len(missing)}")
    print(f"Name collisions: {len(manifest['collisions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

