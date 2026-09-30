'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {prune} = require('../bin/prune');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'material-symbols-prune-'));
const write = (relative, content = 'data') => {
  const file = path.join(root, relative);
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, content);
};
const exists = relative => fs.existsSync(path.join(root, relative));

try {
  write('symbols.json', '["home","search"]');
  write('variants.json', '["outlined","filled"]');
  write('weight.json', '[400,700]');
  for (const variant of ['outlined', 'filled']) {
    for (const weight of [400, 700]) {
      for (const symbol of ['home', 'search']) write(`${variant}/${weight}/${symbol}.svg`);
      write(`fonts/${variant}/${weight}/material-symbols.ttf`);
      write(`fonts/${variant}/${weight}/material-symbols.woff2`);
    }
  }
  write('fonts/outlined/material-symbols-variable.ttf');
  write('fonts/outlined/material-symbols-variable.woff2');

  const config = {
    variants: ['filled'], weights: [400], formats: ['svg', 'woff2'], symbols: ['home'],
    staticFonts: false, variableFonts: true, dryRun: true,
  };
  const preview = prune(root, config);
  assert.equal(preview.files, 16);
  assert.ok(exists('outlined/700/search.svg'));
  config.dryRun = false;
  assert.equal(prune(root, config).files, preview.files);
  assert.ok(exists('filled/400/home.svg'));
  assert.ok(exists('fonts/outlined/material-symbols-variable.woff2'));
  assert.ok(!exists('outlined/700/search.svg'));
  assert.ok(!exists('filled/400/search.svg'));
  assert.ok(!exists('fonts/outlined/material-symbols-variable.ttf'));
  assert.ok(!exists('fonts/filled/400/material-symbols.woff2'));
  assert.equal(prune(root, config).files, 0);
  assert.throws(() => prune(root, {symbols: ['../home']}));
  assert.ok(exists('filled/400/home.svg'));
  console.log('Prune test passed');
} finally {
  fs.rmSync(root, {recursive: true, force: true});
}
