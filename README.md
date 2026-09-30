# Material Symbols JSON, SVG and Fonts

Generated package of [Google Material Symbols](https://github.com/google/material-design-icons), published as:

- GitHub Packages (npm): `@helsingborg-stad/material-design-icons-json-svg-font`
- Composer: `helsingborg-stad/material-design-icons-json-svg-font`

All icon names and Unicode code points come from the Material Symbols variable fonts' OpenType ligatures and character maps. The package does not include classic Material Icons.

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
```

Variants are `outlined`, `rounded`, `sharp`, `filled`, `rounded-filled`, and `sharp-filled`. The filled variants set the matching Symbols font's `FILL` axis to `1`. SVGs use optical size 24 and grade 0. All seven weights are generated for each variant.

SVGs use `currentColor` by default. Define `--icon-color` on an SVG or an ancestor to override it. Material Symbols has no two-tone variant, so `--icon-color-alt` is not used.

The variable fonts retain all upstream axes. They are stored once per Symbols style, under `fonts/outlined`, `fonts/rounded`, and `fonts/sharp`. To display filled icons with a variable font, set `FILL` to `1`.

The static `material-symbols` fonts contain the Symbols glyphs for each variant and weight.

### npm

GitHub Packages requires authentication to install npm packages, including public ones. In your consuming project, add this `.npmrc` and set `GITHUB_PACKAGES_TOKEN` to a GitHub personal access token (classic) with `read:packages`:

```ini
@helsingborg-stad:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_PACKAGES_TOKEN}
```

```sh
npm install @helsingborg-stad/material-design-icons-json-svg-font
```

GitHub Actions consumers can use their repository's `GITHUB_TOKEN` instead if that repository has been granted access to the package. See [GitHub's npm registry guide](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-npm-registry).

### Composer

```sh
composer require helsingborg-stad/material-design-icons-json-svg-font
```

The files are available at `vendor/helsingborg-stad/material-design-icons-json-svg-font/`.

## Keep only the assets your project uses (Composer)

Like the [AWS SDK for PHP's Composer pruning hook](https://github.com/aws/aws-sdk-php/blob/master/src/Script/Composer/README.md), this package offers an opt-in `pre-autoload-dump` script. Add this to your **project's** `composer.json`:

```json
{
  "scripts": {
    "pre-autoload-dump": "HelsingborgStad\\MaterialSymbols\\Script\\Composer\\Prune::run"
  },
  "extra": {
    "helsingborg-stad/material-design-icons-json-svg-font": {
      "variants": ["outlined", "filled"],
      "weights": [400],
      "formats": ["svg", "woff2"],
      "symbols": ["home", "search"],
      "staticFonts": false,
      "variableFonts": true,
      "dryRun": true
    }
  }
}
```

Run `composer install` or `composer dump-autoload` to preview the number of files and bytes that would be removed. Set `dryRun` to `false` (or remove it) and run the command again to prune the installed copy. Omit a selection to keep all its values. Accepted formats are `svg`, `ttf`, `otf`, `woff`, and `woff2`; both font switches default to `true`. An unknown or empty selection fails without deleting files. With no `extra` entry, the hook does nothing.

The `symbols` selection removes unused **SVG files**. Font files retain all glyphs; the script selects whole fonts by variant, weight, format, and static or variable type. A variable font supports every weight, so `weights` applies to SVGs and static fonts only. Selecting a filled variant also keeps its base style's variable font (`outlined` for `filled`, and similarly for rounded and sharp), where you can set `FILL` to `1`.

The root JSON files remain the complete upstream catalog after pruning. Use your project selection to determine which asset paths are still present. Changing the selection to keep more assets requires `composer reinstall helsingborg-stad/material-design-icons-json-svg-font`, then rerunning the hook. The script only changes the installed package under `vendor/`, not this repository or the published package.

### npm projects

Add the same selection to your project's `package.json`, under the npm package name. Run the installed command explicitly after `npm install`:

```json
{
  "scripts": {
    "prune:icons": "material-symbols-prune"
  },
  "@helsingborg-stad/material-design-icons-json-svg-font": {
    "variants": ["outlined", "filled"],
    "weights": [400],
    "formats": ["svg", "woff2"],
    "symbols": ["home", "search"],
    "staticFonts": false,
    "variableFonts": true,
    "dryRun": true
  }
}
```

Run `npm run prune:icons` to preview, then set `dryRun` to `false` and run it again to remove files. The options and behavior match the Composer hook. To restore assets after changing a selection, reinstall the npm package.

## Build locally

Install Python 3.12+, [FontForge](https://fontforge.org/), and the Python dependencies:

```sh
python -m pip install -r requirements.txt
git clone --depth 1 --filter=blob:none --sparse https://github.com/google/material-design-icons.git upstream
git -C upstream sparse-checkout set variablefont
python scripts/build.py --upstream upstream --output . --source-commit "$(git -C upstream rev-parse HEAD)"
python scripts/verify.py .
```

The builder uses only the source Symbols font binaries. It does not use upstream `.codepoints` files, SVG assets, or metadata to infer names. FontForge converts static TrueType fonts to OpenType; FontTools writes WOFF and WOFF2. `--sample N --no-fonts` is available for a quick SVG smoke test.

## Automatic releases

The [sync workflow](.github/workflows/sync.yml) checks upstream `master` daily and can be run manually. It compares a hash of the source font binaries with the last package. When they change, it rebuilds the generated files, commits them, increments the patch version, tags the commit, publishes the npm package to GitHub Packages, and creates a GitHub release. Committed package changes also trigger a release on the next run. Packagist reads the Git tags from the already registered repository. The first release is `1.0.0`. Package format changes should be versioned manually as minor or major releases before the next sync; automatic source updates remain patch releases.

### GitHub Packages and Packagist setup

The workflow publishes to `https://npm.pkg.github.com` with its automatic `GITHUB_TOKEN` and `packages: write` permission. No npmjs.org account, trusted publisher, or rotating publish secret is needed. The package must be associated with this repository and this repository must have Actions write access to the package. If an existing package was published from another repository, grant this repository access under the package's **Manage Actions access** settings. GitHub Packages defaults new packages to private; set package visibility to public in GitHub if that is the intended audience. GitHub Packages limits each npm version tarball to less than 256 MB; the workflow checks this before tagging a release. See [GitHub's package publishing guide](https://docs.github.com/en/actions/tutorials/publish-packages/publish-nodejs-packages).

The Composer package is already registered on Packagist. Enable its [GitHub hook](https://packagist.org/about#how-to-update-packages) in Packagist for prompt updates after a tag is pushed. Without the hook, Packagist still crawls registered packages periodically; no Packagist credentials are needed in GitHub Actions.

Allow GitHub Actions to write repository contents and create tags. If the default branch is protected, permit the workflow bot to push generated commits, or adapt the release step to use an approved bot identity. If publishing fails after a tag is pushed, run the workflow manually with `retry_publish` to publish that tag again.

## License

The source icons and fonts are by Google LLC under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution. The build tooling is also distributed under Apache 2.0.
