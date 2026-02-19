#!/usr/bin/env python3
"""Build scaled SVGs for SDF sprites.

Creates a 64x64 viewBox wrapper and scales original SVG artwork to fit within
48x48, centered with 8px padding on each side.
"""

from __future__ import annotations

import copy
import math
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET


def parse_length(value: str) -> float:
    if value is None:
        return float("nan")
    match = re.match(r"^\s*([0-9.]+)", value)
    if not match:
        return float("nan")
    return float(match.group(1))


def get_viewbox_size(root: ET.Element) -> tuple[float, float]:
    viewbox = root.get("viewBox") or root.get("viewbox")
    if viewbox:
        parts = [p for p in re.split(r"[ ,]+", viewbox.strip()) if p]
        if len(parts) == 4:
            _, _, w, h = parts
            return float(w), float(h)

    width = parse_length(root.get("width"))
    height = parse_length(root.get("height"))
    if not math.isnan(width) and not math.isnan(height):
        return width, height

    raise ValueError("SVG missing viewBox/width/height")


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
TARGET_SIZE = 58.0  # spreet --sdf adds 3px padding each side, resulting in 64px total
CONTENT_SIZE = 48.0
PADDING = (TARGET_SIZE - CONTENT_SIZE) / 2.0


def strip_namespaces(elem: ET.Element) -> None:
    if elem.tag.startswith("{"):
        elem.tag = elem.tag.split("}", 1)[1]
    new_attrib = {}
    for key, value in elem.attrib.items():
        if key.startswith("{"):
            key = key.split("}", 1)[1]
        new_attrib[key] = value
    elem.attrib = new_attrib
    for child in list(elem):
        strip_namespaces(child)


def build_scaled_svg(src_path: str, dest_path: str) -> None:
    tree = ET.parse(src_path)
    root = tree.getroot()

    # Always provide SVG namespace on root for compatibility.
    attrs = {"xmlns": SVG_NS}
    has_xlink = any(k.startswith(f"{{{XLINK_NS}}}") or k.startswith("xlink:") for k in root.attrib)
    if has_xlink or "xmlns:xlink" in root.attrib:
        attrs["xmlns:xlink"] = XLINK_NS

    view_w, view_h = get_viewbox_size(root)
    if view_w <= 0 or view_h <= 0:
        raise ValueError("SVG has non-positive viewBox")

    scale = min(CONTENT_SIZE / view_w, CONTENT_SIZE / view_h)
    scaled_w = view_w * scale
    scaled_h = view_h * scale
    offset_x = PADDING + (CONTENT_SIZE - scaled_w) / 2.0
    offset_y = PADDING + (CONTENT_SIZE - scaled_h) / 2.0

    new_root = ET.Element(
        "svg",
        {
            **attrs,
            "width": f"{TARGET_SIZE:.0f}",
            "height": f"{TARGET_SIZE:.0f}",
            "viewBox": f"0 0 {TARGET_SIZE:.0f} {TARGET_SIZE:.0f}",
            "version": "1.1",
        },
    )
    group = ET.SubElement(
        new_root,
        "g",
        {
            "transform": f"translate({offset_x:.6f} {offset_y:.6f}) scale({scale:.6f})",
        },
    )

    # Copy all children into group
    for child in list(root):
        cloned = copy.deepcopy(child)
        strip_namespaces(cloned)
        group.append(cloned)

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    ET.ElementTree(new_root).write(dest_path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: build_sdf_icons.py <src_dir> <dest_dir>")
        return 1

    src_dir, dest_dir = sys.argv[1], sys.argv[2]
    if not os.path.isdir(src_dir):
        print(f"Source dir not found: {src_dir}")
        return 1

    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)

    for name in sorted(os.listdir(src_dir)):
        if not name.lower().endswith(".svg"):
            continue
        src_path = os.path.join(src_dir, name)
        dest_path = os.path.join(dest_dir, name)
        build_scaled_svg(src_path, dest_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
