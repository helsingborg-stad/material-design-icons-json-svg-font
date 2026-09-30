# Material Design Icons JSON, SVG and Fonts

Generated package of [Google Material Symbols and Material Icons](https://github.com/google/material-design-icons), published as:

- npm: `@helsingborg-stad/material-design-icons-json-svg-font`
- Composer: `helsingborg-stad/material-design-icons-json-svg-font`

The icon names and Unicode code points come from the fonts' OpenType ligatures and character maps. Material Symbols are preferred. A classic Material Icon is used only when that name is absent in the matching Symbols style. Classic Icons have regular weight only.

## Package layout

Generated data is at the package root:

```text
symbols.json                    sorted array of all icon names
variants.json                   array of available variants
weight.json                     [100, 200, 300, 400, 500, 600, 700]
metadata.json                   source commit, font digest, axes, code points, availability
outlined/400/home.svg           SVGs at variant/weight/name.svg
filled/700/home.svg
fonts/outlined/material-symbols-variable.ttf
fonts/outlined/material-symbols-variable.woff
fonts/outlined/material-symbols-variable.woff2
fonts/outlined/400/material-symbols.ttf
fonts/outlined/400/material-symbols.otf
fonts/outlined/400/material-symbols.woff
fonts/outlined/400/material-symbols.woff2
fonts/outlined/400/material-icons-fallback.*
```

Variants are `outlined`, `rounded`, `sharp`, `filled`, `rounded-filled`, `sharp-filled`, and `two-tone`. `filled` uses the outlined Symbols font at `FILL=1`; the other filled variants do the same for rounded and sharp. `two-tone` comes from classic Material Icons, including its color layer opacity. SVGs use optical size 24 and grade 0. SVGs and static font files exist only at weights the source supports, so classic-only icons appear at weight 400. Use `metadata.json` to check availability rather than assuming every name is present in every directory.

SVGs use `currentColor` by default. Define `--icon-color` on an SVG or an ancestor to override it. Two-tone SVGs also accept `--icon-color-alt` for the lighter layer; when that variable is absent, the lighter layer uses `--icon-color` if set, then `currentColor`. The lighter layer retains the opacity encoded in Google's font.

The variable fonts retain all upstream axes. They are stored once per Symbols style, under `fonts/outlined`, `fonts/rounded`, and `fonts/sharp`. To display filled icons with a variable font, set `FILL` to `1`.

The static `material-symbols` fonts contain Symbols glyphs. The `material-icons-fallback` fonts contain the classic font for the matching style. When using font files, load the fallback font separately for missing classic icons. The SVG directories already apply the fallback choice per icon.

### npm

```sh
npm install @helsingborg-stad/material-design-icons-json-svg-font
```

### Composer

```sh
composer require helsingborg-stad/material-design-icons-json-svg-font
```

The files are available at `vendor/helsingborg-stad/material-design-icons-json-svg-font/`.

## Build locally

Install Python 3.12+, [FontForge](https://fontforge.org/), and the Python dependencies:

```sh
python -m pip install -r requirements.txt
git clone --depth 1 --filter=blob:none --sparse https://github.com/google/material-design-icons.git upstream
git -C upstream sparse-checkout set font variablefont
python scripts/build.py --upstream upstream --output . --source-commit "$(git -C upstream rev-parse HEAD)"
python scripts/verify.py .
```

The builder uses the source font binaries. It does not use upstream `.codepoints` files, SVG assets, or metadata to infer names. FontForge converts static TrueType and OpenType fonts to their counterpart format; FontTools writes WOFF and WOFF2. `--sample N --no-fonts` is available for a quick SVG smoke test.

## Automatic releases

The [sync workflow](.github/workflows/sync.yml) checks upstream `master` daily and can be run manually. It compares a hash of the source font binaries with the last package. When they change, it rebuilds the generated files, commits them, increments the patch version, tags the commit, publishes npm, registers or updates Packagist, and creates a GitHub release. Committed package changes also trigger a release on the next run. The first release is `1.0.0`. Package format changes should be versioned manually as minor or major releases before the next sync; automatic source updates remain patch releases.

Configure these GitHub Actions secrets before the first run:

- `NPM_TOKEN`: npm token with publish access to the `@helsingborg-stad` scope.
- `PACKAGIST_USERNAME`: Packagist account name.
- `PACKAGIST_API_TOKEN`: main Packagist API token, needed to register the package on first release.

Allow GitHub Actions to write repository contents and create tags. If the default branch is protected, permit the workflow bot to push generated commits, or adapt the release step to use an approved bot identity. If publishing fails after a tag is pushed, run the workflow manually with `retry_publish` to publish that tag again.

## License

The source icons and fonts are by Google LLC under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution. The build tooling is also distributed under Apache 2.0.
