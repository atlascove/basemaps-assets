#!/usr/bin/env python3
"""Update local id-tagging-schema tracking metadata after a sync/import."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TRACKING_PATH = ROOT / "meta" / "id_tagging_schema_tracking.json"


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "fotoshi-id-schema-track/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.load(resp)


def latest_release() -> dict[str, Any]:
    return fetch_json("https://api.github.com/repos/openstreetmap/id-tagging-schema/releases/latest")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark id-tagging-schema release as synced")
    parser.add_argument("--tag", help="Release tag to mark (default: latest)")
    parser.add_argument("--published-at", help="Optional override for published timestamp")
    parser.add_argument("--by", default="manual_sync", help="Marker for who/what synced")
    parser.add_argument("--note", default="", help="Optional note")
    args = parser.parse_args()

    release = latest_release() if not args.tag else None
    tag = args.tag or release["tag_name"]
    published_at = args.published_at or (release.get("published_at") if release else None)

    payload = {
        "tracked_release_tag": tag,
        "tracked_release_published_at": published_at,
        "tracked_by": args.by,
        "tracked_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "notes": args.note,
    }

    TRACKING_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"updated {TRACKING_PATH} -> {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

