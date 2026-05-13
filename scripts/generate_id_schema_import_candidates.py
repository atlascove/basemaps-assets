#!/usr/bin/env python3
"""Generate import-candidate patch data from id-tagging-schema deltas.

This script is intentionally non-destructive:
- it does NOT edit `meta/presets.json`
- it writes candidate artifacts under `tmp/`

Outputs:
- JSON patch-style candidate file
- TSV summary for quick review
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
TRACKING_PATH = ROOT / "meta" / "id_tagging_schema_tracking.json"
ICONS_DIR = ROOT / "icons"


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "fotoshi-id-schema-candidates/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)


def fetch_latest_release() -> dict[str, Any]:
    return fetch_json("https://api.github.com/repos/openstreetmap/id-tagging-schema/releases/latest")


def fetch_presets_for_tag(tag: str) -> dict[str, Any]:
    url = f"https://raw.githubusercontent.com/openstreetmap/id-tagging-schema/{tag}/dist/presets.json"
    data = fetch_json(url)
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected presets format for tag {tag}")
    return data


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def normalized_preset_for_diff(preset: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "name",
        "icon",
        "tags",
        "geometry",
        "terms",
        "fields",
        "searchable",
        "matchScore",
        "replacement",
    ]
    return {k: preset[k] for k in keys if k in preset}


def load_tracking_tag() -> str:
    if not TRACKING_PATH.exists():
        raise RuntimeError("Missing meta/id_tagging_schema_tracking.json")
    tracking = json.loads(TRACKING_PATH.read_text(encoding="utf-8"))
    tag = tracking.get("tracked_release_tag")
    if not tag:
        raise RuntimeError("tracking file missing tracked_release_tag")
    return str(tag)


def icon_sources(icon: str) -> Iterable[str]:
    if icon.startswith("temaki-"):
        yield f"https://raw.githubusercontent.com/rapideditor/temaki/main/icons/{icon}.svg"
        yield f"https://raw.githubusercontent.com/rapideditor/temaki/main/icons/{icon.removeprefix('temaki-')}.svg"
    elif icon.startswith("fas-"):
        yield f"https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/solid/{icon.removeprefix('fas-')}.svg"
    elif icon.startswith("far-"):
        yield f"https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/regular/{icon.removeprefix('far-')}.svg"
    elif icon.startswith("roentgen-"):
        yield f"https://raw.githubusercontent.com/enzet/Roentgen/master/src/{icon}.svg"
        yield f"https://raw.githubusercontent.com/enzet/Roentgen/master/icons/{icon}.svg"
    elif icon.startswith("maki-"):
        name = icon.removeprefix("maki-")
        yield f"https://raw.githubusercontent.com/mapbox/maki/main/icons/{name}.svg"
        yield f"https://raw.githubusercontent.com/mapbox/maki/main/icons/{name}-15.svg"
        yield f"https://raw.githubusercontent.com/mapbox/maki/main/icons/{name}-11.svg"
    elif icon.startswith("iD-"):
        name = icon.removeprefix("iD-")
        yield f"https://raw.githubusercontent.com/openstreetmap/id-tagging-schema/main/dist/img/presets/{name}.svg"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate id-tagging-schema import candidates")
    parser.add_argument("--baseline-tag", help="Override baseline tracked tag")
    parser.add_argument("--latest-tag", help="Override latest tag")
    parser.add_argument(
        "--out-json",
        default="tmp/id_tagging_schema_import_candidates.json",
        help="Output JSON path (repo-relative)",
    )
    parser.add_argument(
        "--out-tsv",
        default="tmp/id_tagging_schema_import_candidates.tsv",
        help="Output TSV path (repo-relative)",
    )
    args = parser.parse_args()

    baseline_tag = args.baseline_tag or load_tracking_tag()
    latest_tag = args.latest_tag or fetch_latest_release()["tag_name"]

    baseline = fetch_presets_for_tag(baseline_tag)
    latest = fetch_presets_for_tag(latest_tag)

    baseline_keys = set(baseline.keys())
    latest_keys = set(latest.keys())

    added = sorted(latest_keys - baseline_keys)
    common = baseline_keys & latest_keys

    changed: list[str] = []
    for key in common:
        if stable_hash(normalized_preset_for_diff(baseline[key])) != stable_hash(
            normalized_preset_for_diff(latest[key])
        ):
            changed.append(key)
    changed.sort()

    local_icons = {p.stem for p in ICONS_DIR.glob("*.svg")}

    candidates: list[dict[str, Any]] = []
    for status, keys in (("added", added), ("changed", changed)):
        for key in keys:
            p = latest[key]
            icon = str(p.get("icon")).strip() if p.get("icon") else ""
            has_local_icon = bool(icon and icon in local_icons)
            fetch_urls = list(icon_sources(icon)) if icon else []
            readiness = "ready"
            if icon and not has_local_icon:
                readiness = "needs_icon"
            elif not icon:
                readiness = "no_icon"
            candidates.append(
                {
                    "preset_key": key,
                    "status": status,
                    "readiness": readiness,
                    "icon": icon or None,
                    "has_local_icon": has_local_icon,
                    "icon_fetch_candidates": fetch_urls,
                    "upstream": {
                        "name": p.get("name"),
                        "tags": p.get("tags"),
                        "geometry": p.get("geometry"),
                        "terms": p.get("terms"),
                        "matchScore": p.get("matchScore"),
                    },
                    "recommended_action": (
                        "create_preset_from_upstream"
                        if status == "added"
                        else "review_and_update_existing_mapping"
                    ),
                }
            )

    out_json = ROOT / args.out_json
    out_tsv = ROOT / args.out_tsv
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_tsv.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "baseline_tag": baseline_tag,
        "latest_tag": latest_tag,
        "counts": {
            "added": len(added),
            "changed": len(changed),
            "total_candidates": len(candidates),
        },
        "candidates": candidates,
    }
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with out_tsv.open("w", encoding="utf-8") as f:
        f.write("status\treadiness\tpreset_key\tname\ticon\thas_local_icon\trecommended_action\n")
        for c in candidates:
            u = c["upstream"]
            f.write(
                f"{c['status']}\t{c['readiness']}\t{c['preset_key']}\t"
                f"{(u.get('name') or '').replace(chr(9), ' ')}\t"
                f"{(c.get('icon') or '')}\t{str(c.get('has_local_icon')).lower()}\t"
                f"{c['recommended_action']}\n"
            )

    print(
        f"baseline={baseline_tag} latest={latest_tag} "
        f"added={len(added)} changed={len(changed)} total={len(candidates)}"
    )
    print(f"json: {out_json}")
    print(f"tsv:  {out_tsv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

