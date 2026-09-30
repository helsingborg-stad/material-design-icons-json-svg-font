#!/usr/bin/env python3
"""Check that all declared SVGs and font formats exist and parse."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools.ttLib import TTFont


root = Path(sys.argv[1])
symbols = json.loads((root / "symbols.json").read_text())
variants = json.loads((root / "variants.json").read_text())
weights = json.loads((root / "weight.json").read_text())
metadata = json.loads((root / "metadata.json").read_text())
assert symbols == sorted(set(symbols))
assert set(symbols) == set(metadata["icons"])
assert len(variants) == len(set(variants))
assert weights == [100, 200, 300, 400, 500, 600, 700]
assert len(metadata["sourceCommit"]) == 40
assert len(metadata["sourceFontsSha256"]) == 64

svg_count = 0
for name, availability in metadata["icons"].items():
    for variant, record in availability.items():
        assert variant in variants
        for weight in record["weights"]:
            path = root / variant / str(weight) / f"{name}.svg"
            assert path.is_file(), path
            assert ET.parse(path).getroot().tag == "{http://www.w3.org/2000/svg}svg"
            svg_count += 1

font_count = 0
for directory in (root / "fonts").glob("*/*"):
    if not directory.is_dir():
        continue
    stems = {path.stem for path in directory.iterdir() if path.suffix == ".ttf"}
    for stem in stems:
        for extension in ("ttf", "otf", "woff", "woff2"):
            path = directory / f"{stem}.{extension}"
            assert path.is_file(), path
            font = TTFont(path, lazy=True)
            assert font.getBestCmap(), path
            if extension == "otf":
                assert font.sfntVersion == "OTTO", path
            if "two-tone" in path.parts:
                assert "COLR" in font and "CPAL" in font, path
            font.close()
            font_count += 1

assert svg_count > 0
assert font_count > 0
print(f"Verified {svg_count} SVG files and {font_count} static font files")
