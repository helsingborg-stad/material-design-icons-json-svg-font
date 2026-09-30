#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PACKAGE = '@helsingborg-stad/material-design-icons-json-svg-font';
const FORMATS = ['svg', 'ttf', 'otf', 'woff', 'woff2'];
const KEYS = ['variants', 'weights', 'formats', 'symbols', 'staticFonts', 'variableFonts', 'dryRun'];

function readArray(file) {
  const value = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!Array.isArray(value)) throw new Error(`Expected a JSON array at ${file}`);
  return value;
}

function selection(config, key, allowed) {
  if (!(key in config)) return allowed;
  const value = config[key];
  if (!Array.isArray(value) || value.length === 0 || value.some(item => !allowed.includes(item))) {
    throw new Error(`Material Symbols ${key} must be a non-empty array of known values.`);
  }
  return [...new Set(value)];
}

function flag(config, key, fallback) {
  if (!(key in config)) return fallback;
  if (typeof config[key] !== 'boolean') throw new Error(`Material Symbols ${key} must be a boolean.`);
  return config[key];
}

function prune(root, config) {
  if (!config || Array.isArray(config) || typeof config !== 'object') {
    throw new Error('Material Symbols config must be an object.');
  }
  for (const key of Object.keys(config)) {
    if (!KEYS.includes(key)) throw new Error(`Unknown Material Symbols option: ${key}`);
  }
  if (!Object.keys(config).some(key => key !== 'dryRun')) {
    throw new Error('Specify at least one Material Symbols selection before pruning.');
  }

  const allVariants = readArray(path.join(root, 'variants.json'));
  const allWeights = readArray(path.join(root, 'weight.json'));
  const allSymbols = readArray(path.join(root, 'symbols.json'));
  const variants = new Set(selection(config, 'variants', allVariants));
  const weights = new Set(selection(config, 'weights', allWeights));
  const symbols = new Set(selection(config, 'symbols', allSymbols));
  const formats = new Set(selection(config, 'formats', FORMATS));
  const staticFonts = flag(config, 'staticFonts', true);
  const variableFonts = flag(config, 'variableFonts', true);
  const dryRun = flag(config, 'dryRun', false);
  if (!formats.has('svg') &&
      !(staticFonts && [...formats].some(format => format !== 'svg')) &&
      !(variableFonts && ['ttf', 'woff', 'woff2'].some(format => formats.has(format)))) {
    throw new Error('This selection would keep no assets.');
  }

  const result = {files: 0, bytes: 0, dryRun};
  const isDirectory = dir => fs.existsSync(dir) && fs.lstatSync(dir).isDirectory();
  const files = dir => isDirectory(dir) ? fs.readdirSync(dir, {withFileTypes: true}) : [];
  const remove = file => {
    result.files++;
    result.bytes += fs.statSync(file).size;
    if (!dryRun) fs.unlinkSync(file);
  };
  const removeEmpty = dir => {
    if (!dryRun && isDirectory(dir) && fs.readdirSync(dir).length === 0) fs.rmdirSync(dir);
  };

  for (const variant of allVariants) {
    const variantDir = path.join(root, variant);
    for (const weight of allWeights) {
      const dir = path.join(variantDir, String(weight));
      for (const entry of files(dir)) {
        if (!entry.isFile() || !entry.name.endsWith('.svg')) continue;
        const symbol = entry.name.slice(0, -4);
        if (!(formats.has('svg') && variants.has(variant) && weights.has(weight) && symbols.has(symbol))) {
          remove(path.join(dir, entry.name));
        }
      }
      removeEmpty(dir);
    }
    removeEmpty(variantDir);
  }

  for (const variant of allVariants) {
    const dir = path.join(root, 'fonts', variant);
    for (const weight of allWeights) {
      const weightDir = path.join(dir, String(weight));
      for (const entry of files(weightDir)) {
        if (!entry.isFile() || !entry.name.startsWith('material-symbols.')) continue;
        const format = path.extname(entry.name).slice(1);
        if (!(staticFonts && variants.has(variant) && weights.has(weight) && formats.has(format))) {
          remove(path.join(weightDir, entry.name));
        }
      }
      removeEmpty(weightDir);
    }

    const filled = variant === 'outlined' ? 'filled' : `${variant}-filled`;
    const baseNeeded = variants.has(variant) || variants.has(filled);
    for (const entry of files(dir)) {
      if (!entry.isFile() || !entry.name.startsWith('material-symbols-variable.')) continue;
      const format = path.extname(entry.name).slice(1);
      if (!(variableFonts && baseNeeded && formats.has(format))) remove(path.join(dir, entry.name));
    }
    removeEmpty(dir);
  }
  removeEmpty(path.join(root, 'fonts'));
  return result;
}

if (require.main === module) {
  try {
    const project = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'package.json'), 'utf8'));
    const config = project[PACKAGE];
    if (config === undefined) throw new Error(`Add a ${PACKAGE} selection to your project's package.json.`);
    const result = prune(path.resolve(__dirname, '..'), config);
    const verb = result.dryRun ? 'Would remove' : 'Removed';
    console.log(`Material Symbols: ${verb} ${result.files} files (${(result.bytes / 1048576).toFixed(1)} MiB).`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = {prune};
