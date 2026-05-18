#!/usr/bin/env python3
"""Generate the Hungarian preset localization sidecar."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

script = Path(__file__).with_name("generate_presets_i18n_machine.py")
raise SystemExit(subprocess.call([sys.executable, str(script), "--lang", "hu", *sys.argv[1:]]))
