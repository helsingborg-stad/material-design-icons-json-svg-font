#!/usr/bin/env python3
"""Exit 0 when upstream font binaries differ from the published package."""

import json
import sys
from pathlib import Path

from build import source_digest


upstream = Path(sys.argv[1])
metadata_path = Path(sys.argv[2])
old_digest = None
if metadata_path.is_file():
    old_digest = json.loads(metadata_path.read_text())["sourceFontsSha256"]
new_digest = source_digest(upstream)
print(f"Previous font digest: {old_digest or 'none'}")
print(f"Current font digest:  {new_digest}")
sys.exit(0 if old_digest != new_digest else 1)
