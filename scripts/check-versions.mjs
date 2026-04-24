#!/usr/bin/env node
/**
 * check-versions.mjs
 *
 * Enforces that every plugin listed in `.claude-plugin/marketplace.json`
 * declares the same `version` as its own `.claude-plugin/plugin.json`.
 *
 * Why: Claude Code's update logic for relative-path plugins reads
 * `plugin.json` as the source of truth. If the two drift, published
 * version bumps appear to "do nothing" for end users.
 *
 * Usage:   node scripts/check-versions.mjs
 * Exits:   0 = in sync, 1 = mismatch or read error
 */

import { readFile } from "node:fs/promises";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const red = (s) => `\x1b[31m${s}\x1b[0m`;
const green = (s) => `\x1b[32m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;

const marketplacePath = join(repoRoot, ".claude-plugin", "marketplace.json");
const marketplace = JSON.parse(await readFile(marketplacePath, "utf8"));

if (!Array.isArray(marketplace.plugins) || marketplace.plugins.length === 0) {
  console.error(red("✗ marketplace.json has no plugins"));
  process.exit(1);
}

const failures = [];
let checked = 0;

for (const entry of marketplace.plugins) {
  const { name, source, version: mkt } = entry;

  if (typeof source !== "string") {
    console.log(`  ${yellow("–")} ${name} (non-relative source, skipped)`);
    continue;
  }

  const pluginJsonPath = join(repoRoot, source, ".claude-plugin", "plugin.json");
  let manifest;
  try {
    manifest = JSON.parse(await readFile(pluginJsonPath, "utf8"));
  } catch (err) {
    failures.push(`${name}: cannot read ${pluginJsonPath} (${err.message})`);
    continue;
  }

  if (manifest.name !== name) {
    failures.push(`${name}: plugin.json name is "${manifest.name}"`);
  }
  if (!mkt || !manifest.version) {
    failures.push(`${name}: missing version in marketplace or plugin.json`);
    continue;
  }
  if (manifest.version !== mkt) {
    failures.push(`${name}: marketplace=${mkt}, plugin.json=${manifest.version}`);
  } else {
    console.log(`  ${green("✓")} ${name} ${manifest.version}`);
    checked++;
  }
}

if (failures.length > 0) {
  console.error(red(`\n✗ ${failures.length} mismatch(es):`));
  for (const f of failures) console.error(`  ${red("✗")} ${f}`);
  process.exit(1);
}

console.log(green(`\n✓ All ${checked} plugin version(s) in sync.`));
