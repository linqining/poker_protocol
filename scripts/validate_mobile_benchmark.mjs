#!/usr/bin/env node

import { readFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(fileURLToPath(import.meta.url), "../..");
const referenceWasmCsv = path.join(repoRoot, "paper/experiments/reconstruction_wasm.csv");

const options = {
  input: "",
  device: "",
  label: "",
  samples: 30,
};

function usage(message) {
  if (message) console.error(`error: ${message}`);
  console.error(`usage: ${path.basename(process.argv[1])} --input RESULT.json --device android-chrome|iphone-safari --label LABEL [--samples N]`);
  process.exit(message ? 2 : 0);
}

for (let index = 0; index < process.argv.slice(2).length; index += 1) {
  const arg = process.argv[index + 2];
  const value = process.argv[index + 3];
  if (value === undefined) usage(`missing value for ${arg}`);
  if (arg === "--input") options.input = value;
  else if (arg === "--device") options.device = value;
  else if (arg === "--label") options.label = value;
  else if (arg === "--samples") options.samples = Number(value);
  else usage(`unknown option ${arg}`);
  index += 1;
}

if (!options.input) usage("--input is required");
if (!["android-chrome", "iphone-safari"].includes(options.device)) {
  usage("--device must be android-chrome or iphone-safari");
}
if (!/^[\w.-]{1,48}$/.test(options.label)) {
  usage("--label may contain only letters, digits, underscores, dots, and dashes, with length 1-48");
}
if (!Number.isInteger(options.samples) || options.samples < 1 || options.samples > 101) {
  usage("--samples must be an integer from 1 through 101");
}

const failures = [];
const require = (condition, message) => {
  if (!condition) failures.push(message);
};
const nonNegativeNumber = (value, message) => {
  require(Number.isFinite(value) && value >= 0, message);
};

let result;
try {
  result = JSON.parse(readFileSync(options.input, "utf8"));
} catch (error) {
  console.error(`error: cannot read ${options.input}: ${error.message}`);
  process.exit(2);
}

const lines = readFileSync(referenceWasmCsv, "utf8").trim().split(/\r?\n/);
const header = lines[0].split(",");
const expectedSizes = new Map(lines.slice(1).map(line => {
  const row = Object.fromEntries(header.map((name, index) => [name, rowValue(line, index)]));
  return [`${row.n},${row.k}`, row];
}));

function rowValue(line, index) {
  return line.split(",")[index];
}

require(result.schema_version === 1, "schema_version must be 1");
require(result.label === options.label, "label mismatch");
require(result.samples_per_cell === options.samples, "samples_per_cell mismatch");
require(result.timing_clock?.includes("performance.now"), "timing_clock must use performance.now");
require(result.started_at && !Number.isNaN(Date.parse(result.started_at)), "started_at invalid");
require(result.completed_at && !Number.isNaN(Date.parse(result.completed_at)), "completed_at invalid");
require(Date.parse(result.completed_at) >= Date.parse(result.started_at), "completed_at precedes started_at");

const environment = result.environment ?? {};
const userAgent = environment.user_agent ?? "";
if (options.device === "android-chrome") {
  require(userAgent.includes("Android"), "Android Chrome UA must include Android");
  require(userAgent.includes("Chrome/"), "Android Chrome UA must include Chrome/");
  require(environment.ua_mobile === true, "Android Chrome must report ua_mobile=true");
} else {
  require(userAgent.includes("iPhone"), "iPhone Safari UA must include iPhone");
  require(userAgent.includes("Safari/"), "iPhone Safari UA must include Safari/");
  require(!userAgent.includes("Chrome/"), "iPhone Safari UA must not include Chrome");
}
require(!userAgent.includes("Headless"), "mobile UA must not be headless");
require(environment.webdriver === false, "mobile result must not be WebDriver-controlled");
require(environment.headless_ua === false, "mobile result must not identify a headless UA");
require(Number.isFinite(environment.screen_width) && environment.screen_width > 0, "screen_width invalid");
require(Number.isFinite(environment.screen_height) && environment.screen_height > 0, "screen_height invalid");
require(Number.isFinite(environment.device_pixel_ratio) && environment.device_pixel_ratio > 0, "device_pixel_ratio invalid");
require(typeof environment.language === "string" && environment.language.length > 0, "language missing");
require(typeof environment.timezone === "string" && environment.timezone.length > 0, "timezone missing");

const collection = result.collection ?? {};
require(collection.protocol === "manual browser page; no CDP or WebDriver", "collection protocol must identify a manual browser page");
require(collection.automation === true, "collection.automation must be true, meaning navigator.webdriver was false");
require(["cold", "warm"].includes(collection.run_state), "collection.run_state must be cold or warm");
require(typeof collection.device_model === "string" && collection.device_model.length > 0, "device_model missing");
require(typeof collection.os_version === "string" && collection.os_version.length > 0, "os_version missing");
require(typeof collection.operator === "string" && collection.operator.length > 0, "operator missing");
require(["wifi", "cellular", "ethernet", "usb-tethered"].includes(collection.network_class), "network_class invalid");
require(typeof collection.network_scope === "string" && collection.network_scope.includes("operator-declared"), "network scope missing");

const pageLoad = result.page_load ?? {};
require(["navigate", "reload"].includes(pageLoad.navigation_type), "page_load.navigation_type must be navigate or reload");
require(Number.isFinite(pageLoad.redirect_count), "page_load.redirect_count invalid");
require(Number.isFinite(pageLoad.dom_content_loaded_ms) && pageLoad.dom_content_loaded_ms >= 0, "page_load.dom_content_loaded_ms invalid");
require(Number.isFinite(pageLoad.load_event_end_ms) && pageLoad.load_event_end_ms >= 0, "page_load.load_event_end_ms invalid");
nonNegativeNumber(pageLoad.transfer_size, "page_load.transfer_size invalid");
if (collection.run_state === "cold") {
  require(pageLoad.navigation_type === "navigate", "cold run must be a fresh navigate, not reload");
  require(pageLoad.redirect_count === 0, "cold run must not redirect");
  require(pageLoad.transfer_size > 0, "cold run must show nonzero HTML transfer");
  require(typeof collection.cold_clearing_method === "string" && collection.cold_clearing_method.length > 0, "cold run requires cold_clearing_method");
  require(typeof collection.provenance === "string" && collection.provenance.length > 0, "cold run requires provenance");
}
const resourceTotals = {html: 0, javascript: 0, wasm: 0};
const resourceCounts = {html: 0, javascript: 0, wasm: 0};
for (const resource of pageLoad.resources ?? []) {
  if (!Object.hasOwn(resourceTotals, resource.name)) continue;
  nonNegativeNumber(resource.transfer_size, `${resource.name} transfer_size invalid`);
  nonNegativeNumber(resource.duration_ms, `${resource.name} duration invalid`);
  resourceTotals[resource.name] += resource.transfer_size;
  resourceCounts[resource.name] += 1;
}
require(resourceCounts.javascript > 0, "JavaScript resource timing missing");
require(resourceCounts.wasm > 0, "WASM resource timing missing");
if (collection.run_state === "cold") {
  require(resourceTotals.javascript > 0, "cold run must show nonzero JavaScript transfer");
  require(resourceTotals.wasm > 0, "cold run must show nonzero WASM transfer");
}

const initialization = result.initialization ?? {};
for (const key of ["script_start_relative_ms", "module_import_relative_ms", "wasm_initialized_relative_ms"]) {
  nonNegativeNumber(initialization[key], `initialization.${key} invalid`);
}
require(initialization.module_import_relative_ms >= initialization.script_start_relative_ms, "module import precedes script start");
require(initialization.wasm_initialized_relative_ms >= initialization.module_import_relative_ms, "WASM initialization precedes import");
nonNegativeNumber(result.total_wall_ms, "total_wall_ms invalid");
require(result.total_wall_ms > 0, "total_wall_ms must be positive");

require(Array.isArray(result.results) && result.results.length === 10, "result must contain ten cells");
const expected = new Map(lines.slice(1).map(line => {
  const row = Object.fromEntries(header.map((name, index) => [name, rowValue(line, index)]));
  return [`${row.n},${row.k}`, row];
}));
for (const [index, row] of (result.results ?? []).entries()) {
  require(row.samples === options.samples, `row ${index} sample count mismatch`);
  for (const key of [
    "prove_median_ms", "prove_mean_ms", "prove_stddev_ms", "prove_p95_ms",
    "verify_median_ms", "verify_mean_ms", "verify_stddev_ms", "verify_p95_ms",
    "outer_call_ms",
  ]) {
    require(Number.isFinite(row[key]) && row[key] >= 0, `row ${index}: invalid ${key}`);
  }
  const reference = expected.get(`${row.n},${row.k}`);
  require(reference, `row ${index}: unexpected grid cell`);
  if (reference) {
    for (const key of ["proof_bytes", "statement_bytes", "bundle_bytes"]) {
      require(row[key] === Number(reference[key]), `row ${index}: ${key} differs from committed wire baseline`);
    }
  }
}

if (failures.length) {
  console.error(`error: invalid mobile benchmark result:\n- ${failures.join("\n- ")}`);
  process.exit(1);
}

console.log(`[mobile-benchmark] valid ${options.device} ${collection.run_state} result: ${options.input}`);
