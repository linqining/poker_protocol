#!/usr/bin/env node

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";

function fail(message) {
  console.error(`[manual-http-cache] error: ${message}`);
  process.exit(1);
}

function summarize(values) {
  const sorted = [...values].sort((left, right) => left - right);
  const mean = sorted.reduce((sum, value) => sum + value, 0) / sorted.length;
  const variance = sorted.length > 1
    ? sorted.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (sorted.length - 1)
    : 0;
  const p95Index = Math.max(0, Math.ceil(sorted.length * 0.95) - 1);
  return {
    median: sorted[Math.floor(sorted.length / 2)],
    mean,
    sample_stddev: Math.sqrt(variance),
    p95: sorted[p95Index],
    min: sorted[0],
    max: sorted[sorted.length - 1],
  };
}

function number(value) {
  return Number.isFinite(value) ? value : 0;
}

function metric(run) {
  const resources = new Map(run.resources.map(resource => [resource.name, resource]));
  return {
    browser_transfer_bytes_total: run.resources.reduce((sum, item) => sum + item.transfer_size, 0),
    server_bytes_total: run.server_observations.reduce(
      (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
      0,
    ),
    wasm_transfer_bytes: resources.get("wasm")?.transfer_size ?? 0,
    javascript_transfer_bytes: resources.get("javascript")?.transfer_size ?? 0,
    html_transfer_bytes: resources.get("html")?.transfer_size ?? 0,
    wasm_duration_ms: resources.get("wasm")?.duration_ms ?? 0,
    wasm_initialized_ms: run.initialization.wasm_initialized_relative_ms
      - run.initialization.script_start_relative_ms,
    prove_ms: run.proof.prove_ms,
    verify_ms: run.proof.verify_ms,
    outer_call_ms: run.proof.outer_call_ms,
    navigation_response_start_ms: run.navigation.response_start_ms,
    dom_content_loaded_ms: run.navigation.dom_content_loaded_ms,
    load_event_end_ms: run.navigation.load_event_end_ms,
    upload_request_bytes: run.upload.request_bytes,
    upload_wall_ms: run.upload.upload_wall_ms,
    upload_resource_duration_ms: run.upload.resource_duration_ms,
    upload_resource_transfer_bytes: run.upload.resource_transfer_size,
  };
}

const inputIndex = process.argv.indexOf("--input-dir");
const outputIndex = process.argv.indexOf("--output");
if (inputIndex < 0 || outputIndex < 0 || process.argv.length !== 6) {
  fail("usage: summarize_manual_http_cache.mjs --input-dir DIR --output FILE");
}

const inputDir = path.resolve(process.argv[inputIndex + 1]);
const output = path.resolve(process.argv[outputIndex + 1]);
const files = readdirSync(inputDir)
  .filter(name => name.startsWith("network_run_") && name.endsWith(".json"))
  .sort();
const runs = files.map(name => JSON.parse(readFileSync(path.join(inputDir, name), "utf8")));
const measured = runs.filter(run => run.server_observations.length === 1
  && run.resources.reduce((sum, resource) => sum + resource.transfer_size, 0) === 0);
if (runs.length < 31 || measured.length < 30) {
  fail(`expected one seed plus at least 30 measured runs; received ${runs.length} runs, ${measured.length} measured`);
}
measured.sort((left, right) => Date.parse(left.completed_at) - Date.parse(right.completed_at));
const selected = measured.slice(-30);

for (const [index, run] of selected.entries()) {
  const failures = [];
  if (run.schema_version !== 1
    || run.kind !== "http-cache-reuse-upload-single-run"
    || run.environment?.service_worker !== false
    || run.environment?.http_cache_reuse !== true) {
    failures.push("invalid HTTP-cache identity");
  }
  const resources = new Map(run.resources.map(resource => [resource.name, resource]));
  for (const name of ["html", "javascript", "wasm"]) {
    if (resources.get(name)?.transfer_size !== 0) failures.push(`${name} was not reused from HTTP cache`);
  }
  if (run.server_observations.length !== 1
    || run.server_observations[0].direction !== "browser-to-server"
    || run.server_observations[0].bytes_received !== 27750
    || run.server_observations[0].verified !== true) {
    failures.push("proof upload observation is missing or unverified");
  }
  if (failures.length) fail(`measured run ${index + 1} invalid:\n- ${failures.join("\n- ")}`);
}

const manualMetric = measured_run => ({
  browser_transfer_bytes_total: measured_run.resources.reduce((sum, item) => sum + item.transfer_size, 0),
  server_bytes_total: measured_run.server_observations.reduce(
    (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
    0,
  ),
  wasm_transfer_bytes: measured_run.resources.find(item => item.name === "wasm")?.transfer_size ?? 0,
  javascript_transfer_bytes: measured_run.resources.find(item => item.name === "javascript")?.transfer_size ?? 0,
  html_transfer_bytes: measured_run.resources.find(item => item.name === "html")?.transfer_size ?? 0,
  wasm_duration_ms: measured_run.resources.find(item => item.name === "wasm")?.duration_ms ?? 0,
  wasm_initialized_ms: measured_run.initialization.wasm_initialized_relative_ms
    - measured_run.initialization.script_start_relative_ms,
  prove_ms: measured_run.proof.prove_ms,
  verify_ms: measured_run.proof.verify_ms,
  outer_call_ms: measured_run.proof.outer_call_ms,
  navigation_response_start_ms: measured_run.navigation.response_start_ms,
  dom_content_loaded_ms: measured_run.navigation.dom_content_loaded_ms,
  load_event_end_ms: measured_run.navigation.load_event_end_ms,
  upload_request_bytes: measured_run.upload.request_bytes,
  upload_wall_ms: measured_run.upload.upload_wall_ms,
  upload_resource_duration_ms: measured_run.upload.resource_duration_ms,
  upload_resource_transfer_bytes: measured_run.upload.resource_transfer_size,
});

const firstMetrics = manualMetric(selected[0]);
const summary = Object.fromEntries(
  Object.keys(firstMetrics).map(key => [key, summarize(selected.map(run => manualMetric(run)[key]))]),
);

const aggregate = {
  schema_version: 1,
  kind: "http-cache-reuse-upload-aggregate",
  artifact_form: "summary-and-per-run-invariants",
  label: selected[0].label,
  run_count: selected.length,
  environment: selected[0].environment,
  collection: {
    protocol: "manual same-origin page reloads; no CDP automation",
    browser: measured[0].environment.user_agent,
    headless: false,
    cache_disabled: false,
    browser_cache_cleared_before_each_run: false,
    service_worker_enabled: false,
    service_worker_bypassed: false,
    http_cache_seeded_before_measured_runs: true,
    measured_runs_reuse_browser_http_cache: true,
    network_path: "HTTP loopback to 127.0.0.1",
    proof_upload_verified: true,
    scope: "manual Safari normal browser HTTP-cache reuse after one immutable seed load; measured HTML/JavaScript/WASM transfers are zero, while proof upload bypasses the cache and is cryptographically verified; not service-worker Cache Storage, TLS, LAN, or Internet",
    node: "not recorded for manual browser-only run",
    recorded_at: new Date().toISOString(),
  },
  summary,
  per_run_invariants: {
    run_count: selected.length,
    all_no_service_worker: true,
    all_zero_static_transfer: true,
    all_upload_27750: true,
    all_server_observation_count_one: true,
    all_server_bytes_27750: true,
  },
  measured_run_files: files.filter(file => {
    const run = JSON.parse(readFileSync(path.join(inputDir, file), "utf8"));
    return run.server_observations.length === 1
      && run.resources.reduce((sum, resource) => sum + resource.transfer_size, 0) === 0;
  }).slice(-30),
};

writeFileSync(output, `${JSON.stringify(aggregate, null, 2)}\n`);
console.log(`[manual-http-cache] summarized ${selected.length} runs into ${output}`);
