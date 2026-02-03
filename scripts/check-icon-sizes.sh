#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

python3 - <<'PY'
from pathlib import Path
import re

icons_dir = Path('icons')

bad = []
svg_re = re.compile(r'<svg\s+[^>]*>', re.IGNORECASE)
width_re = re.compile(r'\bwidth\s*=\s*"?(\d+(?:\.\d+)?)"?', re.IGNORECASE)
height_re = re.compile(r'\bheight\s*=\s*"?(\d+(?:\.\d+)?)"?', re.IGNORECASE)

for path in icons_dir.rglob('*.svg'):
    text = path.read_text(errors='ignore')
    match = svg_re.search(text)
    if not match:
        bad.append((path, 'no <svg> tag'))
        continue
    tag = match.group(0)
    w = width_re.search(tag)
    h = height_re.search(tag)
    if not w or not h:
        bad.append((path, 'missing width/height'))
        continue
    try:
        width = float(w.group(1))
        height = float(h.group(1))
    except ValueError:
        bad.append((path, 'invalid width/height'))
        continue
    if width != 15 or height != 15:
        bad.append((path, f'width={width} height={height}'))

if bad:
    print('Non-15x15 icons:')
    for path, reason in sorted(bad, key=lambda x: str(x[0])):
        print(f'- {path}: {reason}')
    raise SystemExit(1)

print('All icons are 15x15')
PY
