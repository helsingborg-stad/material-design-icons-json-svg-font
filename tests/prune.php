<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/Script/Composer/Prune.php';

use HelsingborgStad\MaterialSymbols\Script\Composer\Prune;

$root = sys_get_temp_dir() . '/material-symbols-prune-' . bin2hex(random_bytes(8));
$write = static function (string $path, string $content = 'data') use ($root): void {
    $full = $root . '/' . $path;
    if (!is_dir(dirname($full))) {
        mkdir(dirname($full), 0777, true);
    }
    file_put_contents($full, $content);
};
$exists = static fn (string $path): bool => is_file($root . '/' . $path);

try {
    $write('symbols.json', '["home","search"]');
    $write('variants.json', '["outlined","filled"]');
    $write('weight.json', '[400,700]');
    foreach (['outlined', 'filled'] as $variant) {
        foreach ([400, 700] as $weight) {
            foreach (['home', 'search'] as $symbol) {
                $write("{$variant}/{$weight}/{$symbol}.svg");
            }
            $write("fonts/{$variant}/{$weight}/material-symbols.ttf");
            $write("fonts/{$variant}/{$weight}/material-symbols.woff2");
        }
    }
    $write('fonts/outlined/material-symbols-variable.ttf');
    $write('fonts/outlined/material-symbols-variable.woff2');

    $config = [
        'variants' => ['filled'],
        'weights' => [400],
        'formats' => ['svg', 'woff2'],
        'symbols' => ['home'],
        'staticFonts' => false,
        'variableFonts' => true,
        'dryRun' => true,
    ];
    $preview = Prune::prune($root, $config);
    assert($preview['files'] === 16);
    assert($exists('outlined/700/search.svg'));

    $config['dryRun'] = false;
    $result = Prune::prune($root, $config);
    assert($result['files'] === $preview['files']);
    assert($exists('filled/400/home.svg'));
    assert($exists('fonts/outlined/material-symbols-variable.woff2'));
    assert(!$exists('outlined/700/search.svg'));
    assert(!$exists('filled/400/search.svg'));
    assert(!$exists('fonts/outlined/material-symbols-variable.ttf'));
    assert(!$exists('fonts/filled/400/material-symbols.woff2'));
    assert(Prune::prune($root, $config)['files'] === 0);

    try {
        Prune::prune($root, ['symbols' => ['../home']]);
        throw new RuntimeException('Invalid symbol was accepted');
    } catch (InvalidArgumentException $expected) {
        // Validation happens before any deletion.
    }
    assert($exists('filled/400/home.svg'));
    echo "Prune test passed\n";
} finally {
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($iterator as $item) {
        $item->isDir() ? rmdir($item->getPathname()) : unlink($item->getPathname());
    }
    rmdir($root);
}
