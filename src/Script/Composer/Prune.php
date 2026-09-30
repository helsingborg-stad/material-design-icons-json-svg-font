<?php

declare(strict_types=1);

namespace HelsingborgStad\MaterialSymbols\Script\Composer;

use Composer\Script\Event;
use InvalidArgumentException;
use RuntimeException;

/** Opt-in pruning of an installed copy; the published package is never modified. */
final class Prune
{
    private const PACKAGE = 'helsingborg-stad/material-design-icons-json-svg-font';
    private const FORMATS = ['svg', 'ttf', 'otf', 'woff', 'woff2'];

    public static function run(Event $event): void
    {
        $extra = $event->getComposer()->getPackage()->getExtra();
        if (!array_key_exists(self::PACKAGE, $extra)) {
            return;
        }

        $config = $extra[self::PACKAGE];
        if (!is_array($config)) {
            throw new InvalidArgumentException(self::PACKAGE . ' config must be an object.');
        }

        $result = self::prune(dirname(__DIR__, 3), $config);
        $verb = $result['dryRun'] ? 'Would remove' : 'Removed';
        $event->getIO()->write(sprintf(
            '<info>Material Symbols: %s %d files (%.1f MiB).</info>',
            $verb,
            $result['files'],
            $result['bytes'] / 1048576
        ));
    }

    /** @return array{files:int,bytes:int,dryRun:bool} */
    public static function prune(string $root, array $config): array
    {
        $allowedKeys = ['variants', 'weights', 'formats', 'symbols', 'staticFonts', 'variableFonts', 'dryRun'];
        foreach (array_keys($config) as $key) {
            if (!in_array($key, $allowedKeys, true)) {
                throw new InvalidArgumentException("Unknown Material Symbols option: {$key}");
            }
        }
        if ($config === [] || !array_intersect(array_keys($config), array_diff($allowedKeys, ['dryRun']))) {
            throw new InvalidArgumentException('Specify at least one Material Symbols selection before pruning.');
        }

        $root = realpath($root);
        if ($root === false || !is_file($root . '/symbols.json') || !is_file($root . '/variants.json') || !is_file($root . '/weight.json')) {
            throw new RuntimeException('Material Symbols package directory is missing or incomplete.');
        }

        $allVariants = self::readArray($root . '/variants.json');
        $allWeights = self::readArray($root . '/weight.json');
        $allSymbols = self::readArray($root . '/symbols.json');
        $variants = self::selection($config, 'variants', $allVariants);
        $weights = self::selection($config, 'weights', $allWeights);
        $symbols = self::selection($config, 'symbols', $allSymbols);
        $formats = self::selection($config, 'formats', self::FORMATS);
        $staticFonts = self::boolean($config, 'staticFonts', true);
        $variableFonts = self::boolean($config, 'variableFonts', true);
        $dryRun = self::boolean($config, 'dryRun', false);
        $fontFormats = array_intersect($formats, ['ttf', 'otf', 'woff', 'woff2']);
        $variableFormats = array_intersect($formats, ['ttf', 'woff', 'woff2']);
        if (!in_array('svg', $formats, true) && !($staticFonts && $fontFormats) && !($variableFonts && $variableFormats)) {
            throw new InvalidArgumentException('This selection would keep no assets.');
        }

        $keepVariants = array_fill_keys($variants, true);
        $keepWeights = array_fill_keys(array_map('strval', $weights), true);
        $keepSymbols = array_fill_keys($symbols, true);
        $keepFormats = array_fill_keys($formats, true);
        $result = ['files' => 0, 'bytes' => 0, 'dryRun' => $dryRun];

        foreach ($allVariants as $variant) {
            $variantDir = $root . '/' . $variant;
            foreach ($allWeights as $weight) {
                $weightDir = $variantDir . '/' . $weight;
                if (!is_dir($weightDir) || is_link($weightDir)) {
                    continue;
                }
                foreach (new \DirectoryIterator($weightDir) as $file) {
                    if (!$file->isFile() || $file->isLink() || $file->getExtension() !== 'svg') {
                        continue;
                    }
                    $keep = isset($keepFormats['svg'], $keepVariants[$variant], $keepWeights[(string) $weight], $keepSymbols[$file->getBasename('.svg')]);
                    if (!$keep) {
                        self::removeFile($file->getPathname(), $result);
                    }
                }
                self::removeEmptyDirectory($weightDir, $dryRun);
            }
            self::removeEmptyDirectory($variantDir, $dryRun);
        }

        foreach ($allVariants as $variant) {
            $fontDir = $root . '/fonts/' . $variant;
            if (!is_dir($fontDir) || is_link($fontDir)) {
                continue;
            }
            foreach ($allWeights as $weight) {
                $weightDir = $fontDir . '/' . $weight;
                if (!is_dir($weightDir) || is_link($weightDir)) {
                    continue;
                }
                foreach (new \DirectoryIterator($weightDir) as $file) {
                    if (!$file->isFile() || $file->isLink() || !str_starts_with($file->getFilename(), 'material-symbols.')) {
                        continue;
                    }
                    $keep = $staticFonts && isset($keepVariants[$variant], $keepWeights[(string) $weight], $keepFormats[$file->getExtension()]);
                    if (!$keep) {
                        self::removeFile($file->getPathname(), $result);
                    }
                }
                self::removeEmptyDirectory($weightDir, $dryRun);
            }

            // A filled variant uses the matching base style's variable font with FILL=1.
            $baseNeeded = isset($keepVariants[$variant]) || isset($keepVariants[
                $variant === 'outlined' ? 'filled' : $variant . '-filled'
            ]);
            foreach (new \DirectoryIterator($fontDir) as $file) {
                if (!$file->isFile() || $file->isLink() || !str_starts_with($file->getFilename(), 'material-symbols-variable.')) {
                    continue;
                }
                if (!$variableFonts || !$baseNeeded || !isset($keepFormats[$file->getExtension()])) {
                    self::removeFile($file->getPathname(), $result);
                }
            }
            self::removeEmptyDirectory($fontDir, $dryRun);
        }

        self::removeEmptyDirectory($root . '/fonts', $dryRun);
        return $result;
    }

    private static function readArray(string $path): array
    {
        $value = json_decode((string) file_get_contents($path), true, 512, JSON_THROW_ON_ERROR);
        if (!is_array($value) || !array_is_list($value)) {
            throw new RuntimeException("Expected a JSON array at {$path}");
        }
        return $value;
    }

    private static function selection(array $config, string $key, array $allowed): array
    {
        if (!array_key_exists($key, $config)) {
            return $allowed;
        }
        $selected = $config[$key];
        if (!is_array($selected) || !array_is_list($selected) || $selected === []) {
            throw new InvalidArgumentException("Material Symbols {$key} must be a non-empty array.");
        }
        foreach ($selected as $item) {
            if (!in_array($item, $allowed, true)) {
                throw new InvalidArgumentException("Unknown Material Symbols {$key} value: " . json_encode($item));
            }
        }
        return array_values(array_unique($selected));
    }

    private static function boolean(array $config, string $key, bool $default): bool
    {
        if (!array_key_exists($key, $config)) {
            return $default;
        }
        if (!is_bool($config[$key])) {
            throw new InvalidArgumentException("Material Symbols {$key} must be a boolean.");
        }
        return $config[$key];
    }

    private static function removeFile(string $path, array &$result): void
    {
        $size = filesize($path);
        if ($size === false) {
            throw new RuntimeException("Cannot read file size: {$path}");
        }
        if (!$result['dryRun'] && !unlink($path)) {
            throw new RuntimeException("Cannot remove file: {$path}");
        }
        ++$result['files'];
        $result['bytes'] += $size;
    }

    private static function removeEmptyDirectory(string $path, bool $dryRun): void
    {
        if ($dryRun || !is_dir($path) || is_link($path)) {
            return;
        }
        $iterator = new \FilesystemIterator($path);
        if (!$iterator->valid()) {
            rmdir($path);
        }
    }
}
