#!/usr/bin/env python3
"""Check openstreetmap/id-tagging-schema for release/preset updates.

Outputs a JSON report with:
- tracked release vs latest release
- preset key deltas between baseline and latest
- icon key deltas and which new icon keys are missing locally

This script does not mutate local presets; it only reports.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TRACKING_PATH = ROOT / "meta" / "id_tagging_schema_tracking.json"
ICONS_DIR = ROOT / "icons"
TMP_DIR = ROOT / "tmp"


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "fotoshi-id-schema-check/1.0"})
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


def normalize_preset_for_hash(preset: dict[str, Any]) -> dict[str, Any]:
    # Keep fields that materially affect our mapping/import behavior.
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
    out: dict[str, Any] = {}
    for k in keys:
        if k in preset:
            out[k] = preset[k]
    return out


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def load_tracking() -> dict[str, Any]:
    if not TRACKING_PATH.exists():
        return {}
    return json.loads(TRACKING_PATH.read_text(encoding="utf-8"))


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check id-tagging-schema updates")
    parser.add_argument("--baseline-tag", help="Override baseline tag (default: tracking file)")
    parser.add_argument(
        "--report",
        default="tmp/id_tagging_schema_update_report.json",
        help="Report path (repo-relative)",
    )
    parser.add_argument(
        "--cache-presets",
        action="store_true",
        help="Cache baseline/latest upstream presets under tmp/id-tagging-schema/<tag>/",
    )
    args = parser.parse_args()

    tracking = load_tracking()
    baseline_tag = args.baseline_tag or tracking.get("tracked_release_tag")
    if not baseline_tag:
        raise SystemExit("No baseline tag. Set meta/id_tagging_schema_tracking.json or pass --baseline-tag.")

    latest_release = fetch_latest_release()
    latest_tag = latest_release["tag_name"]

    baseline = fetch_presets_for_tag(baseline_tag)
    latest = fetch_presets_for_tag(latest_tag)

    baseline_keys = set(baseline.keys())
    latest_keys = set(latest.keys())

    added_keys = sorted(latest_keys - baseline_keys)
    removed_keys = sorted(baseline_keys - latest_keys)
    common_keys = baseline_keys & latest_keys

    changed_keys: list[str] = []
    for key in common_keys:
        b = normalize_preset_for_hash(baseline[key])
        l = normalize_preset_for_hash(latest[key])
        if stable_hash(b) != stable_hash(l):
            changed_keys.append(key)
    changed_keys.sort()

    baseline_icons = {str(v.get("icon")).strip() for v in baseline.values() if v.get("icon")}
    latest_icons = {str(v.get("icon")).strip() for v in latest.values() if v.get("icon")}
    new_icon_keys = sorted(latest_icons - baseline_icons)

    local_icon_keys = {p.stem for p in ICONS_DIR.glob("*.svg")}
    missing_local_icons = sorted(i for i in new_icon_keys if i not in local_icon_keys)

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    report: dict[str, Any] = {
        "checked_at": now,
        "tracking": tracking,
        "baseline_tag": baseline_tag,
        "latest_tag": latest_tag,
        "latest_published_at": latest_release.get("published_at"),
        "is_update_available": baseline_tag != latest_tag,
        "counts": {
            "baseline_preset_count": len(baseline_keys),
            "latest_preset_count": len(latest_keys),
            "added_preset_keys": len(added_keys),
            "removed_preset_keys": len(removed_keys),
            "changed_preset_keys": len(changed_keys),
            "new_icon_keys": len(new_icon_keys),
            "new_icon_keys_missing_locally": len(missing_local_icons),
        },
        "samples": {
            "added_preset_keys": added_keys[:50],
            "removed_preset_keys": removed_keys[:50],
            "changed_preset_keys": changed_keys[:50],
            "new_icon_keys": new_icon_keys[:100],
            "new_icon_keys_missing_locally": missing_local_icons[:100],
        },
    }

    if args.cache_presets:
        for tag, payload in [(baseline_tag, baseline), (latest_tag, latest)]:
            out = TMP_DIR / "id-tagging-schema" / tag / "dist.presets.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload), encoding="utf-8")

    report_path = ROOT / args.report
    write_report(report_path, report)

    print(f"baseline={baseline_tag} latest={latest_tag} update_available={baseline_tag != latest_tag}")
    print(
        "deltas: "
        f"added={len(added_keys)} removed={len(removed_keys)} changed={len(changed_keys)} "
        f"new_icons={len(new_icon_keys)} missing_local_icons={len(missing_local_icons)}"
    )
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

