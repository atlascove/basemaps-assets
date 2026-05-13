#!/usr/bin/env python3
"""Detect missing preset icons and attempt to fetch source SVGs.

Detection source:
- `meta/presets.json` icon field
- local `icons/*.svg`

Fetch strategy:
1) local mirror folders (temaki/, fas/)
2) known upstream raw URLs (Roentgen, Temaki, Font Awesome)

By default this runs as a dry-run. Use `--apply` to write files.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
PRESETS_PATH = ROOT / "meta" / "presets.json"
ICONS_DIR = ROOT / "icons"
TMP_DIR = ROOT / "tmp"

SVG_RE = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
WIDTH_RE = re.compile(r'\bwidth\s*=\s*"[^"]*"', re.IGNORECASE)
HEIGHT_RE = re.compile(r'\bheight\s*=\s*"[^"]*"', re.IGNORECASE)


def load_preset_icons() -> set[str]:
    presets = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    return {str(p.get("icon")).strip() for p in presets if p.get("icon")}


def load_local_icons() -> set[str]:
    return {p.stem for p in ICONS_DIR.glob("*.svg")}


def force_svg_15x15(svg_text: str) -> str:
    m = SVG_RE.search(svg_text)
    if not m:
        return svg_text
    tag = m.group(0)
    tag2 = WIDTH_RE.sub("", tag)
    tag2 = HEIGHT_RE.sub("", tag2)
    tag2 = tag2.replace("<svg", '<svg width="15" height="15"', 1)
    return svg_text[: m.start()] + tag2 + svg_text[m.end() :]


def read_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="ignore")


def try_url(url: str, timeout: int = 20) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "fotoshi-icon-fetcher/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            raw = resp.read()
    except (urllib.error.URLError, TimeoutError):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="ignore")


def candidate_sources(icon: str) -> Iterable[tuple[str, str]]:
    # Local mirrors in this repo
    if icon.startswith("temaki-"):
        yield ("local:temaki", str(ROOT / "temaki" / f"{icon}.svg"))
        yield (
            "raw:temaki-main",
            f"https://raw.githubusercontent.com/rapideditor/temaki/main/icons/{icon}.svg",
        )
        yield (
            "raw:temaki-main-unprefixed",
            f"https://raw.githubusercontent.com/rapideditor/temaki/main/icons/{icon.removeprefix('temaki-')}.svg",
        )
    elif icon.startswith("fas-") or icon.startswith("far-"):
        yield ("local:fas", str(ROOT / "fas" / f"{icon}.svg"))
        yield (
            "raw:fontawesome-solid",
            f"https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/solid/{icon.removeprefix('fas-')}.svg",
        )
        yield (
            "raw:fontawesome-regular",
            f"https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/regular/{icon.removeprefix('far-')}.svg",
        )
    elif icon.startswith("roentgen-"):
        yield (
            "raw:roentgen-src",
            f"https://raw.githubusercontent.com/enzet/Roentgen/master/src/{icon}.svg",
        )
        yield (
            "raw:roentgen-icons",
            f"https://raw.githubusercontent.com/enzet/Roentgen/master/icons/{icon}.svg",
        )
    elif icon.startswith("maki-"):
        name = icon.removeprefix("maki-")
        yield ("raw:maki-main", f"https://raw.githubusercontent.com/mapbox/maki/main/icons/{name}.svg")
        yield (
            "raw:maki-main-15",
            f"https://raw.githubusercontent.com/mapbox/maki/main/icons/{name}-15.svg",
        )
        yield (
            "raw:maki-main-11",
            f"https://raw.githubusercontent.com/mapbox/maki/main/icons/{name}-11.svg",
        )
    elif icon.startswith("iD-"):
        name = icon.removeprefix("iD-")
        yield (
            "raw:id-tagging-schema",
            f"https://raw.githubusercontent.com/openstreetmap/id-tagging-schema/main/dist/img/presets/{name}.svg",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect and fetch missing preset icons")
    parser.add_argument("--apply", action="store_true", help="Write fetched icons into icons/")
    parser.add_argument("--limit", type=int, default=0, help="Optional max missing icons to process")
    parser.add_argument(
        "--report",
        default="tmp/missing_preset_icons_report.json",
        help="Report path (repo-relative)",
    )
    args = parser.parse_args()

    preset_icons = load_preset_icons()
    local_icons = load_local_icons()
    missing = sorted(i for i in preset_icons if i and i not in local_icons)
    if args.limit > 0:
        missing = missing[: args.limit]

    report: dict[str, object] = {
        "preset_icon_count": len(preset_icons),
        "local_icon_count": len(local_icons),
        "missing_count": len(missing),
        "apply": args.apply,
        "results": [],
    }

    fetched = 0
    unresolved = 0
    for icon in missing:
        out = ICONS_DIR / f"{icon}.svg"
        entry: dict[str, object] = {"icon": icon, "resolved": False, "source": None}
        body: str | None = None

        for src_name, src in candidate_sources(icon):
            if src_name.startswith("local:"):
                body = read_if_exists(Path(src))
            else:
                body = try_url(src)
            if body and "<svg" in body.lower():
                entry["resolved"] = True
                entry["source"] = src_name
                break
            body = None

        if body and entry["resolved"]:
            body = force_svg_15x15(body)
            if args.apply:
                out.write_text(body, encoding="utf-8")
            fetched += 1
        else:
            unresolved += 1

        report["results"].append(entry)

    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] missing icons considered: {len(missing)}")
    print(f"[{mode}] fetched/resolved: {fetched}")
    print(f"[{mode}] unresolved: {unresolved}")
    print(f"report: {report_path}")
    if unresolved > 0:
        print("Unresolved icons:")
        for r in report["results"]:
            if not r["resolved"]:
                print(f"- {r['icon']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

