#!/usr/bin/env python3
"""Build icon assets exclusively from the upstream font files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


WEIGHTS = (100, 200, 300, 400, 500, 600, 700)
SYMBOL_STYLES = ("outlined", "rounded", "sharp")
VARIANTS = (
    ("outlined", "outlined", 0, "outlined"),
    ("rounded", "rounded", 0, "rounded"),
    ("sharp", "sharp", 0, "sharp"),
    ("filled", "outlined", 1, "filled"),
    ("rounded-filled", "rounded", 1, None),
    ("sharp-filled", "sharp", 1, None),
    ("two-tone", None, None, "two-tone"),
)
SAFE_NAME = re.compile(r"^[a-z0-9_]+$")
SOURCE_URL = "https://github.com/google/material-design-icons"


def icon_names(font: TTFont) -> dict[str, tuple[int, str]]:
    """Read ligature text and Unicode values from GSUB and cmap, as upstream does."""
    cmap = font.getBestCmap()
    reverse = {glyph: codepoint for codepoint, glyph in cmap.items()}
    icons: dict[str, tuple[int, str]] = {}
    if "GSUB" not in font:
        raise ValueError("Icon font has no GSUB table")
    for lookup in font["GSUB"].table.LookupList.Lookup:
        for subtable in lookup.SubTable:
            if lookup.LookupType == 7 and subtable.ExtensionLookupType == 4:
                subtable = subtable.ExtSubTable
            elif lookup.LookupType != 4:
                continue
            for first, ligatures in subtable.ligatures.items():
                for ligature in ligatures:
                    glyphs = (first, *ligature.Component)
                    try:
                        name = "".join(chr(reverse[glyph]) for glyph in glyphs)
                        codepoint = reverse[ligature.LigGlyph]
                    except KeyError:
                        continue
                    if SAFE_NAME.fullmatch(name) and (
                        0xE000 <= codepoint <= 0xF8FF
                        or 0xF0000 <= codepoint <= 0xFFFFD
                        or 0x100000 <= codepoint <= 0x10FFFD
                    ):
                        icons[name] = (codepoint, ligature.LigGlyph)
    if not icons:
        raise ValueError("No icon names found in font ligatures")
    return dict(sorted(icons.items()))


def find_fonts(upstream: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    symbols = {}
    for style in SYMBOL_STYLES:
        matches = list((upstream / "variablefont").glob(f"MaterialSymbols{style.title()}*.ttf"))
        if len(matches) != 1:
            raise ValueError(f"Expected one variable font for {style}, found {matches}")
        symbols[style] = matches[0]
    classic_patterns = {
        "outlined": "MaterialIconsOutlined-Regular.otf",
        "rounded": "MaterialIconsRound-Regular.otf",
        "sharp": "MaterialIconsSharp-Regular.otf",
        "filled": "MaterialIcons-Regular.ttf",
        "two-tone": "MaterialIconsTwoTone-Regular.otf",
    }
    classic = {style: upstream / "font" / name for style, name in classic_patterns.items()}
    for path in classic.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    return symbols, classic


def axes(font: TTFont) -> dict[str, dict[str, float]]:
    if "fvar" not in font:
        return {}
    return {
        axis.axisTag: {
            "min": axis.minValue,
            "default": axis.defaultValue,
            "max": axis.maxValue,
        }
        for axis in font["fvar"].axes
    }


def source_digest(upstream: Path) -> str:
    """Hash only the font binaries that determine the published assets."""
    symbol_paths, classic_paths = find_fonts(upstream)
    paths = set((*symbol_paths.values(), *classic_paths.values()))
    paths.update(path.with_suffix(".woff2") for path in symbol_paths.values()
                 if path.with_suffix(".woff2").is_file())
    paths = sorted(paths)
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(upstream)).encode("utf-8"))
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def svg(font: TTFont, glyph_name: str) -> str:
    units = font["head"].unitsPerEm
    glyph_set = font.getGlyphSet()
    layers = (
        font["COLR"].ColorLayers.get(glyph_name)
        if "COLR" in font and font["COLR"].version == 0
        else None
    )
    paths = []
    for layer in layers or [None]:
        layer_name = layer.name if layer else glyph_name
        pen = SVGPathPen(glyph_set)
        glyph_set[layer_name].draw(TransformPen(pen, (1, 0, 0, -1, 0, units)))
        path = pen.getCommands()
        if not path:
            continue
        opacity = ""
        if layer:
            color = font["CPAL"].palettes[0][layer.colorID]
            if color.alpha < 255:
                opacity = f' opacity="{color.alpha / 255:.3f}"'
        paths.append(f'<path{opacity} d="{path}"/>')
    if not paths:
        raise ValueError(f"Glyph {glyph_name} has no outline")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {units} {units}">'
        + "".join(paths) + "</svg>\n"
    )


def convert_with_fontforge(source: Path, target: Path) -> None:
    if not shutil.which("fontforge"):
        raise RuntimeError("fontforge is required to produce real OTF/TTF conversions")
    result = subprocess.run(
        ["fontforge", "-lang=ff", "-c", "Open($1); Generate($2)", str(source), str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"fontforge failed for {source}: {result.stderr[-3000:]}")
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError(f"fontforge did not create {target}")


def web_fonts(source: Path, directory: Path, stem: str) -> None:
    for extension, flavor in (("woff", "woff"), ("woff2", "woff2")):
        font = TTFont(source)
        font.flavor = flavor
        font.save(directory / f"{stem}.{extension}")
        font.close()


def save_static_fonts(font: TTFont, directory: Path, stem: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    source_extension = "otf" if font.sfntVersion == "OTTO" else "ttf"
    source = directory / f"{stem}.{source_extension}"
    font.save(source)
    target_extension = "ttf" if source_extension == "otf" else "otf"
    converted_path = directory / f"{stem}.{target_extension}"
    convert_with_fontforge(source, converted_path)
    converted = TTFont(converted_path)
    # FontForge ignores color tables when converting the classic two-tone font.
    # The layer glyph names survive, so reattach the original tables.
    if "COLR" in font:
        converted["CPAL"] = font["CPAL"]
        converted["COLR"] = font["COLR"]
        converted.save(converted_path)
    if set(icon_names(converted)) != set(icon_names(font)):
        raise ValueError(f"Font conversion changed the icon ligatures in {converted_path}")
    converted.close()
    web_fonts(source, directory, stem)


def choose_names(mapping: dict[str, tuple[int, str]], sample: int | None) -> dict[str, tuple[int, str]]:
    return dict(list(mapping.items())[:sample]) if sample else mapping


def build(upstream: Path, output: Path, commit: str, sample: int | None, no_fonts: bool) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("--source-commit must be a full lowercase Git SHA")
    symbol_paths, classic_paths = find_fonts(upstream)
    symbol_fonts = {style: TTFont(path) for style, path in symbol_paths.items()}
    classic_fonts = {style: TTFont(path) for style, path in classic_paths.items()}
    symbol_names = {style: choose_names(icon_names(font), sample) for style, font in symbol_fonts.items()}
    classic_names = {style: choose_names(icon_names(font), sample) for style, font in classic_fonts.items()}

    if output.resolve() == Path.cwd().resolve():
        for variant, *_ in VARIANTS:
            shutil.rmtree(output / variant, ignore_errors=True)
        shutil.rmtree(output / "fonts", ignore_errors=True)
        for filename in ("symbols.json", "variants.json", "weight.json", "metadata.json"):
            (output / filename).unlink(missing_ok=True)
    elif output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    metadata: dict = {
        "source": SOURCE_URL,
        "sourceCommit": commit,
        "sourceFontsSha256": source_digest(upstream),
        "license": "Apache-2.0",
        "axes": {style: axes(font) for style, font in symbol_fonts.items()},
        "svgSettings": {"opsz": 24, "GRAD": 0},
        "icons": {},
    }
    all_names: set[str] = set()

    # Variable fonts retain all axes. The filled variants use the same base font,
    # with FILL=1 specified by the caller (recorded in metadata).
    if not no_fonts:
        for style, path in symbol_paths.items():
            directory = output / "fonts" / style
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / "material-symbols-variable.ttf"
            shutil.copy2(path, target)
            original_woff2 = path.with_suffix(".woff2")
            if original_woff2.is_file():
                shutil.copy2(original_woff2, directory / "material-symbols-variable.woff2")
            else:
                font = TTFont(path)
                font.flavor = "woff2"
                font.save(directory / "material-symbols-variable.woff2")
            variable = TTFont(path)
            variable.flavor = "woff"
            variable.save(directory / "material-symbols-variable.woff")

    for variant, symbol_style, fill, classic_style in VARIANTS:
        preferred = symbol_names[symbol_style] if symbol_style else {}
        fallback = classic_names[classic_style] if classic_style else {}
        names = dict(preferred)
        names.update({name: value for name, value in fallback.items() if name not in names})
        all_names.update(names)
        for name, (codepoint, _) in names.items():
            source = "symbols" if name in preferred else "icons"
            metadata["icons"].setdefault(name, {})[variant] = {
                "source": source,
                "codepoint": f"{codepoint:x}",
                "weights": list(WEIGHTS) if source == "symbols" else [400],
            }

        if symbol_style:
            for weight in WEIGHTS:
                print(f"Building {variant}/{weight} ({len(preferred)} Symbols)", flush=True)
                font = TTFont(symbol_paths[symbol_style])
                font = instantiateVariableFont(
                    font,
                    {"FILL": fill, "GRAD": 0, "opsz": 24, "wght": weight},
                    inplace=True,
                )
                directory = output / variant / str(weight)
                directory.mkdir(parents=True, exist_ok=True)
                for name, (_, glyph_name) in preferred.items():
                    (directory / f"{name}.svg").write_text(svg(font, glyph_name), encoding="utf-8")
                if not no_fonts:
                    save_static_fonts(font, output / "fonts" / variant / str(weight), "material-symbols")
                font.close()

        if fallback:
            directory = output / variant / "400"
            directory.mkdir(parents=True, exist_ok=True)
            font = classic_fonts[classic_style]
            fallback_only = {name: entry for name, entry in fallback.items() if name not in preferred}
            print(f"Building {variant}/400 ({len(fallback_only)} classic fallbacks)", flush=True)
            for name, (_, glyph_name) in fallback_only.items():
                (directory / f"{name}.svg").write_text(svg(font, glyph_name), encoding="utf-8")
            if not no_fonts:
                save_static_fonts(font, output / "fonts" / variant / "400", "material-icons-fallback")

    for filename, values in (
        ("symbols.json", sorted(all_names)),
        ("variants.json", [variant for variant, *_ in VARIANTS]),
        ("weight.json", list(WEIGHTS)),
    ):
        (output / filename).write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    metadata["icons"] = dict(sorted(metadata["icons"].items()))
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    for font in (*symbol_fonts.values(), *classic_fonts.values()):
        font.close()
    print(f"Built {len(all_names)} unique names across {len(VARIANTS)} variants", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--sample", type=int, help="Build only the first N names per font for smoke testing")
    parser.add_argument("--no-fonts", action="store_true", help="Skip font output for smoke testing")
    args = parser.parse_args()
    if args.sample is not None and args.sample <= 0:
        parser.error("--sample must be positive")
    build(args.upstream, args.output, args.source_commit, args.sample, args.no_fonts)


if __name__ == "__main__":
    main()
