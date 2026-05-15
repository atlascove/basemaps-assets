#!/usr/bin/env python3
"""Validate preset localization sidecars against canonical presets.json."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESETS = ROOT / "meta" / "presets.json"
DEFAULT_LOCALIZATION = ROOT / "meta" / "presets_it.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--presets", default=DEFAULT_PRESETS)
    parser.add_argument("--localization", default=DEFAULT_LOCALIZATION)
    args = parser.parse_args()

    presets = json.loads(Path(args.presets).read_text(encoding="utf-8"))
    localization = json.loads(Path(args.localization).read_text(encoding="utf-8"))
    preset_ids = {str(item["id"]) for item in presets}
    loc_ids = set(localization)

    errors: list[str] = []
    missing = sorted(preset_ids - loc_ids, key=int)
    extra = sorted(loc_ids - preset_ids, key=int)
    if missing:
        errors.append(f"missing localization ids: {missing[:20]}{'...' if len(missing) > 20 else ''}")
    if extra:
        errors.append(f"unknown localization ids: {extra[:20]}{'...' if len(extra) > 20 else ''}")

    term_pattern = re.compile(r"^\S(?:.*\S)?$")
    for pid, item in localization.items():
        if not isinstance(item, dict):
            errors.append(f"{pid}: value must be an object")
            continue
        name = item.get("name")
        terms = item.get("terms")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{pid}: name must be a non-empty string")
        if not isinstance(terms, list):
            errors.append(f"{pid}: terms must be a list")
            continue
        seen = set()
        for term in terms:
            if not isinstance(term, str) or not term_pattern.match(term):
                errors.append(f"{pid}: invalid term {term!r}")
                continue
            if term != term.lower():
                errors.append(f"{pid}: term is not lowercase: {term!r}")
            if term in seen:
                errors.append(f"{pid}: duplicate term {term!r}")
            seen.add(term)

    if errors:
        print("presets i18n validation failed:")
        for error in errors[:100]:
            print(f"- {error}")
        if len(errors) > 100:
            print(f"- ... {len(errors) - 100} more")
        return 1

    quality_counts: dict[str, int] = {}
    for item in localization.values():
        quality = str(item.get("quality", "unspecified"))
        quality_counts[quality] = quality_counts.get(quality, 0) + 1
    print(
        f"validated {len(localization)} localized presets against {len(presets)} canonical presets; "
        f"quality={quality_counts}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
