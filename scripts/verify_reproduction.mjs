#!/usr/bin/env node

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { arch, cpus, platform, release } from "node:os";
import { relative, resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const metadataPath = resolve(repoRoot, "paper/experiments/benchmark_metadata.json");
const nativeBaseline = resolve(repoRoot, "paper/experiments/reconstruction_stark.csv");
const componentBaseline = resolve(repoRoot, "paper/experiments/reconstruction_components.csv");
const baselineJson = resolve(repoRoot, "paper/experiments/circom_slot_baseline.json");
const curveBaselineJson = resolve(repoRoot, "paper/experiments/reconstruction_bn254_n52_k13_30.json");
const multislotBaselineJson = resolve(repoRoot, "paper/experiments/circom_multislot_baseline.json");
const statementSchemaJson = resolve(repoRoot, "paper/experiments/reconstruction_statement_schema_v3.json");
const pstxAdapterVectorJson = resolve(repoRoot, "paper/experiments/settlement_pstx_v1_kat.json");
const wasmBaseline = resolve(repoRoot, "paper/experiments/reconstruction_wasm.csv");
const browserJson = resolve(repoRoot, "paper/experiments/browser_chrome_headless_153_macos_20260924.json");
const browserMemoryJson = resolve(repoRoot, "paper/experiments/browser_chrome_headless_memory_153_macos_20260924.json");
const headedBrowserJson = resolve(repoRoot, "paper/experiments/browser_chrome_headed_153_macos_20260924.json");
const safariBrowserJson = resolve(repoRoot, "paper/experiments/browser_safari_desktop_macos_20260924.json");
const networkJson = resolve(repoRoot, "paper/experiments/network_chrome_cache_disabled_loopback_30_20260924.json");
const networkColdServiceWorkerJson = resolve(repoRoot, "paper/experiments/network_chrome_cold_service_worker_install_30_20260924.json");
const networkHttpCurrentJson = resolve(repoRoot, "paper/experiments/network_chrome_http_current_loopback_upload_30_20260924.json");
const networkServiceWorkerJson = resolve(repoRoot, "paper/experiments/network_chrome_service_worker_loopback_upload_30_20260924.json");
const networkServiceWorkerUpdateJson = resolve(repoRoot, "paper/experiments/network_chrome_service_worker_update_30_20260925.json");
const networkHttpCacheJson = resolve(repoRoot, "paper/experiments/network_chrome_http_cache_reuse_30_20260925.json");
const networkSafariHttpCacheJson = resolve(repoRoot, "paper/experiments/network_safari_http_cache_reuse_30_20260925.json");
const networkTlsJson = resolve(repoRoot, "paper/experiments/network_chrome_tls_loopback_upload_30_20260924.json");
const networkUploadJson = resolve(repoRoot, "paper/experiments/network_chrome_loopback_upload_30_20260924.json");

function fail(message) {
  console.error(`[repro-verify] error: ${message}`);
  process.exit(1);
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function parseCsv(path, expectedHeader) {
  const lines = readFileSync(path, "utf8").trim().split(/\r?\n/);
  if (lines[0] !== expectedHeader.join(",")) {
    fail(`${path} has an unexpected CSV header`);
  }
  const rows = lines.slice(1).map((line, index) => {
    const values = line.split(",");
    if (values.length !== expectedHeader.length) {
      fail(`${path}:${index + 2} has ${values.length} fields; expected ${expectedHeader.length}`);
    }
    return Object.fromEntries(expectedHeader.map((name, column) => [name, values[column]]));
  });
  if (rows.length !== 10) {
    fail(`${path} has ${rows.length} data rows; expected 10`);
  }
  return rows;
}

function requirePositiveNumbers(rows, columns, path) {
  for (const [index, row] of rows.entries()) {
    for (const column of columns) {
      const value = Number(row[column]);
      if (!Number.isFinite(value) || value <= 0) {
        fail(`${path}:${index + 2} has invalid ${column}: ${row[column]}`);
      }
    }
  }
}

function requireNonNegativeNumbers(rows, columns, path) {
  for (const [index, row] of rows.entries()) {
    for (const column of columns) {
      const value = Number(row[column]);
      if (!Number.isFinite(value) || value < 0) {
        fail(`${path}:${index + 2} has invalid ${column}: ${row[column]}`);
      }
    }
  }
}

function gridKey(row) {
  return `${row.n},${row.k}`;
}

function commandOutput(command, args, cwd = repoRoot) {
  return execFileSync(command, args, { cwd, encoding: "utf8" }).trim().split(/\r?\n/)[0];
}

function requireSameGrid(actual, baseline, path) {
  const actualGrid = actual.map(gridKey).join(";");
  const expectedGrid = baseline.map(gridKey).join(";");
  if (actualGrid !== expectedGrid) {
    fail(`${path} does not use the committed (n,k) parameter grid`);
  }
}

const nativeHeader = [
  "n", "k", "prove_median_us", "prove_mean_us", "prove_stddev_us", "prove_p95_us",
  "verify_median_us", "verify_mean_us", "verify_stddev_us", "verify_p95_us",
  "proof_bytes", "statement_bytes", "prove_peak_bytes", "verify_peak_bytes", "samples",
];
const wasmHeader = [
  "n", "k", "prove_median_ms", "prove_mean_ms", "prove_stddev_ms", "prove_p95_ms",
  "verify_median_ms", "verify_mean_ms", "verify_stddev_ms", "verify_p95_ms",
  "proof_bytes", "statement_bytes", "bundle_bytes", "samples",
];
const componentHeader = [
  "n", "k", "residual_setup_ns", "cross_key_ns", "bayer_groth_ns", "slot_or_ns",
  "prove_total_ns", "serialization_ns", "verify_cross_key_ns", "verify_bayer_groth_ns",
  "verify_slot_or_ns", "verify_total_ns",
];

const mode = process.argv[2];
function validateScopedBaseline(path) {
  const baseline = JSON.parse(readFileSync(path, "utf8"));
  if (baseline.baseline !== "bn254-curve-reconstruction-generic") {
    for (const key of ["constraints", "proof_bytes", "public_signal_bytes", "witness_ms", "prove_ms", "verify_ms"]) {
      if (!Number.isFinite(Number(baseline[key])) || Number(baseline[key]) <= 0) {
        fail(`${path} has invalid ${key}`);
      }
    }
  }
  if (baseline.baseline === "circom-groth16-single-slot") {
    if (!Array.isArray(baseline.unsupported_semantics) || baseline.unsupported_semantics.length < 4) {
      fail(`${path} is missing unsupported semantics`);
    }
    return;
  }
  if (baseline.baseline === "circom-groth16-multislot-exact-coverage") {
    for (const key of ["wires", "compile_ms", "phase2_preparation_ms", "groth16_setup_ms"]) {
      if (!Number.isFinite(Number(baseline[key])) || Number(baseline[key]) <= 0) fail(`${path} has invalid ${key}`);
    }
    if (baseline.parameters?.n !== 52 || baseline.parameters?.k !== 13) fail(`${path} has unexpected finite-domain parameters`);
    if (baseline.constraints !== 2197 || baseline.wires !== 846) fail(`${path} has an unexpected circuit size`);
    if (baseline.proof_bytes !== 807 || baseline.public_signal_bytes !== 1657) fail(`${path} has unexpected deterministic artifact sizes`);
    for (const key of ["modeled_semantics", "unsupported_semantics"]) {
      if (!Array.isArray(baseline[key]) || baseline[key].length < 4) fail(`${path} has incomplete ${key}`);
    }
    return;
  }
  if (baseline.baseline === "bn254-curve-reconstruction-generic") {
    if (baseline.curve !== "BN254 G1"
      || baseline.transcript !== "FiatShamirTranscript(SHA3)"
      || baseline.n !== 52
      || baseline.k !== 13
      || baseline.samples !== 30) {
      fail(`${path} has an unexpected curve-baseline identity or shape`);
    }
    for (const stage of ["prove", "verify"]) {
      const timing = baseline.timings?.[stage];
      for (const key of ["median_us", "mean_us", "sample_stddev_us", "p95_us", "min_us", "max_us"]) {
        if (!Number.isFinite(Number(timing?.[key])) || Number(timing?.[key]) <= 0) {
          fail(`${path} has invalid ${stage} ${key}`);
        }
      }
    }
    if (baseline.wire_shape?.proof_bytes !== 21781
      || baseline.wire_shape?.statement_bytes !== 5969
      || baseline.wire_shape?.bundle_bytes !== 27750
      || !String(baseline.wire_shape?.codec ?? "").includes("BN254 reconstruction v3 Borsh")) {
      fail(`${path} has an unexpected curve-baseline wire shape`);
    }
    for (const key of ["modeled_semantics", "unsupported_semantics"]) {
      if (!Array.isArray(baseline[key]) || baseline[key].length < 4) {
        fail(`${path} has incomplete curve-baseline ${key}`);
      }
    }
    return;
  }
  fail(`${path} has an unknown baseline identity`);
}

function validateBrowserBenchmark(path, expectedLabel, expectedHeadless, engine = "chrome", expectMemory = false) {
  const result = JSON.parse(readFileSync(path, "utf8"));
  const reference = parseCsv(wasmBaseline, wasmHeader);
  if (result.schema_version !== 1 || result.label !== expectedLabel || result.samples_per_cell !== 30) {
    fail(`${path} has an unexpected browser-result identity or sample count`);
  }
  if (engine === "safari") {
    const userAgent = result.environment?.user_agent ?? "";
    if (!userAgent.includes(" Safari/") || userAgent.includes("Chrome/") || userAgent.includes("Headless")) {
      fail(`${path} does not identify desktop Safari`);
    }
    if (result.environment?.headless_ua !== false || result.environment?.webdriver !== false || result.environment?.platform !== "MacIntel") {
      fail(`${path} does not identify a user-normal desktop Safari run`);
    }
  } else if (result.environment?.headless_ua !== expectedHeadless || result.environment?.webdriver !== true || result.collection?.headless !== expectedHeadless) {
    fail(`${path} does not identify the expected automated Chrome mode`);
  }
  if (engine !== "safari"
    && (result.collection?.protocol !== "Chrome DevTools Protocol" || !result.collection?.browser_version?.startsWith("Chrome/153."))) {
    fail(`${path} has an unexpected collection protocol or browser version`);
  }
  const initializationKeys = [
    "script_start_relative_ms",
    "module_import_relative_ms",
    "wasm_initialized_relative_ms",
  ];
  for (const key of initializationKeys) {
    const value = Number(result.initialization?.[key]);
    if (!Number.isFinite(value) || value < 0) fail(`${path} has invalid initialization timing for ${key}`);
  }
  if (!Number.isFinite(Number(result.total_wall_ms)) || Number(result.total_wall_ms) <= 0) {
    fail(`${path} has invalid total wall time`);
  }
  if (expectMemory) {
    const memory = result.collection?.memory;
    const expectedMemory = {
      js_heap_used_peak_bytes: 37506736,
      js_heap_total_peak_bytes: 58982400,
      final_js_heap_used_bytes: 714552,
      final_js_heap_total_bytes: 50855936,
      metric_samples: 1432,
      sampling_interval_ms: 100,
    };
    for (const [key, expected] of Object.entries(expectedMemory)) {
      if (memory?.[key] !== expected) fail(`${path} has an unexpected memory field ${key}`);
    }
    if (memory?.method !== "Chrome DevTools Protocol Performance.getMetrics polling"
      || !String(memory?.scope ?? "").startsWith("renderer JS heap only")) {
      fail(`${path} does not scope the memory measurement to renderer JS heap`);
    }
  } else if (result.collection?.memory) {
    fail(`${path} unexpectedly contains a memory collection in a timing-only benchmark`);
  }
  if (!Array.isArray(result.results) || result.results.length !== 10) {
    fail(`${path} does not contain the ten-cell parameter grid`);
  }
  const expected = new Map(reference.map(row => [gridKey(row), row]));
  for (const [index, row] of result.results.entries()) {
    if (row.samples !== 30) fail(`${path} result ${index} does not record 30 samples`);
    for (const key of [
      "prove_median_ms", "prove_mean_ms", "prove_stddev_ms", "prove_p95_ms",
      "verify_median_ms", "verify_mean_ms", "verify_stddev_ms", "verify_p95_ms",
      "outer_call_ms",
    ]) {
      const value = Number(row[key]);
      if (!Number.isFinite(value) || value < 0) fail(`${path} result ${index} has invalid ${key}`);
    }
    const referenceRow = expected.get(gridKey(row));
    if (!referenceRow) fail(`${path} result ${index} has an unexpected grid cell`);
    for (const key of ["proof_bytes", "statement_bytes", "bundle_bytes"]) {
      if (row[key] !== Number(referenceRow[key])) {
        fail(`${path} result ${index} has a ${key} mismatch against the committed WASM baseline`);
      }
    }
  }
}

function validateNetworkBenchmark(path) {
  const result = JSON.parse(readFileSync(path, "utf8"));
  if (result.kind === "remote-network-upload-aggregate") {
    const collection = result.collection ?? {};
    let serverUrl;
    try {
      serverUrl = new URL(collection.remote_server_url ?? "");
    } catch {
      serverUrl = null;
    }
    const transportMatches = serverUrl
      && collection.transport === (serverUrl.protocol === "https:" ? "HTTPS" : "HTTP");
    const certificateMatches = serverUrl?.protocol === "https:"
      ? ["browser_validated_certificate_chain", "browser_certificate_errors_ignored"].includes(collection.certificate_validation)
      : collection.certificate_validation === "none_unencrypted_http";
    const coldTcpIsolated = collection.cold_tcp_isolated;
    const browserProcessReused = collection.browser_process_reused_across_runs;
    const requireValidCertificate = collection.require_valid_certificate;
    const tlsCertificate = collection.tls_certificate;
    if (result.schema_version !== 1
      || !Number.isInteger(result.run_count)
      || result.run_count < 1
      || result.run_count !== result.runs?.length
      || !serverUrl
      || !["http:", "https:"].includes(serverUrl.protocol)
      || !["lan", "internet"].includes(collection.declared_network_class)
      || collection.remote_mode !== true
      || !transportMatches
      || !certificateMatches
      || collection.public_pki_claimed !== false
      || typeof coldTcpIsolated !== "boolean"
      || typeof browserProcessReused !== "boolean"
      || coldTcpIsolated === browserProcessReused
      || collection.new_browser_process_and_profile_per_run !== coldTcpIsolated
      || collection.browser_process_exit_confirmed_between_runs !== coldTcpIsolated
      || typeof requireValidCertificate !== "boolean"
      || collection.proof_upload_verified !== true
      || typeof collection.scope !== "string") {
      fail(`${path} has an invalid remote-network result identity or overclaims transport`);
    }
    if (requireValidCertificate
      && (tlsCertificate?.authorized !== true
        || tlsCertificate?.hostname_verified !== true
        || tlsCertificate?.authorization_error !== null
        || tlsCertificate?.trust_source !== "Node.js system trust store"
        || !Array.isArray(tlsCertificate?.subject_alt_names)
        || typeof tlsCertificate?.sha256_fingerprint !== "string")) {
      fail(`${path} claims required TLS validation but lacks certificate evidence`);
    }
    if (!requireValidCertificate && collection.tls_certificate !== null) {
      fail(`${path} contains a TLS certificate without requiring valid TLS validation`);
    }
    for (const [index, run] of (result.runs ?? []).entries()) {
      const uploadObservations = (run.server_observations ?? [])
        .filter(item => item.direction === "browser-to-server");
      if (run.upload?.request_bytes !== 27750
        || run.upload?.server_received_bytes !== 27750
        || run.upload?.server_accepted !== true
        || run.upload?.server_verified !== true
        || uploadObservations.length !== 1
        || uploadObservations[0]?.bytes_received !== 27750
        || uploadObservations[0]?.verified !== true) {
        fail(`${path} remote run ${index} has an invalid verified upload`);
      }
    }
    console.log(`[repro-verify] remote network result is structurally valid: ${path}`);
    return;
  }
  const upload = result.kind === "cold-network-upload-aggregate";
  const serviceWorker = result.kind === "warm-service-worker-upload-aggregate";
  const coldServiceWorker = result.kind === "cold-service-worker-install-aggregate";
  const serviceWorkerUpdate = result.kind === "service-worker-update-aggregate";
  const safariHttpCache = result.kind === "http-cache-reuse-upload-aggregate"
    && result.label === "safari-http-cache";
  const httpCache = result.kind === "http-cache-reuse-upload-aggregate" && !safariHttpCache;
  const tls = result.label === "chrome-tls-loopback-upload-30";
  const httpCurrent = result.label === "chrome-http-current-loopback-upload-30";
  if (result.schema_version !== 1
    || (!upload && !serviceWorker && !coldServiceWorker && !serviceWorkerUpdate && !httpCache && !safariHttpCache && result.kind !== "cold-network-aggregate")) {
    fail(`${path} has an unexpected network-result identity`);
  }
  const expectedLabel = serviceWorker
    ? "chrome-service-worker-loopback-upload-30"
    : coldServiceWorker
      ? "chrome-cold-service-worker-install-30-current"
    : serviceWorkerUpdate
      ? "chrome-service-worker-update-30"
    : httpCache
      ? "chrome-http-cache-reuse-30"
    : safariHttpCache
      ? "safari-http-cache"
    : tls
      ? "chrome-tls-loopback-upload-30"
    : httpCurrent
      ? "chrome-http-current-loopback-upload-30"
    : upload
      ? "chrome-loopback-upload-30"
      : "chrome-cache-disabled-loopback-30";
  if (result.label !== expectedLabel || result.run_count !== 30
    || ((!serviceWorker && !coldServiceWorker && !serviceWorkerUpdate && !httpCache && !safariHttpCache && !tls && !httpCurrent) && result.runs.length !== 30)
    || (safariHttpCache && result.runs !== undefined)) {
    fail(`${path} does not contain the committed 30-run network aggregate`);
  }
  if (serviceWorker || coldServiceWorker || serviceWorkerUpdate || httpCache || safariHttpCache || tls || httpCurrent) {
    if (result.artifact_form !== "summary-and-per-run-invariants"
      || result.per_run_invariants?.run_count !== 30
      || Object.entries(result.per_run_invariants ?? {}).some(([key, value]) => key !== "run_count" && value !== true)) {
      fail(`${path} does not prove its committed per-run invariants`);
    }
  }
  if (serviceWorker) {
    if (result.collection?.cache_disabled !== false
      || result.collection?.browser_cache_cleared_before_each_run !== false
      || result.collection?.service_worker_enabled !== true
      || result.collection?.service_worker_bypassed !== false
      || result.collection?.service_worker_warm_before_measured_runs !== true) {
      fail(`${path} does not identify warm service-worker collection`);
    }
  } else if (!httpCache && !safariHttpCache && (!result.collection?.cache_disabled || !result.collection?.browser_cache_cleared_before_each_run)) {
    fail(`${path} does not identify cache-disabled collection`);
  }
  if (coldServiceWorker
    && (result.collection?.cache_disabled !== true
      || result.collection?.browser_cache_cleared_before_each_run !== true
      || result.collection?.service_worker_enabled !== true
      || result.collection?.service_worker_bypassed !== false
      || result.collection?.service_worker_warm_before_measured_runs !== false
      || result.collection?.cold_service_worker_unique_scope_and_cache_per_run !== true)) {
    fail(`${path} does not identify unique-scope cold service-worker installation`);
  }
  if (serviceWorkerUpdate
    && (result.collection?.cache_disabled !== true
      || result.collection?.browser_cache_cleared_before_each_run !== true
      || result.collection?.service_worker_enabled !== true
      || result.collection?.service_worker_bypassed !== false
      || result.collection?.service_worker_warm_before_measured_runs !== false
      || result.collection?.service_worker_update_unique_scope_and_cache_per_run !== true)) {
    fail(`${path} does not identify same-URL service-worker update collection`);
  }
  if (httpCache
    && (result.collection?.cache_disabled !== false
      || result.collection?.browser_cache_cleared_before_each_run !== false
      || result.collection?.service_worker_enabled !== false
      || result.collection?.service_worker_bypassed !== true
      || result.collection?.http_cache_seeded_before_measured_runs !== true
      || result.collection?.measured_runs_reuse_browser_http_cache !== true)) {
    fail(`${path} does not identify browser HTTP-cache reuse collection`);
  }
  if (safariHttpCache
    && (result.collection?.cache_disabled !== false
      || result.collection?.browser_cache_cleared_before_each_run !== false
      || result.collection?.service_worker_enabled !== false
      || result.collection?.service_worker_bypassed !== false
      || result.collection?.http_cache_seeded_before_measured_runs !== true
      || result.collection?.measured_runs_reuse_browser_http_cache !== true
      || result.collection?.protocol !== "manual same-origin page reloads; no CDP automation")) {
    fail(`${path} does not identify manual Safari HTTP-cache reuse collection`);
  }
  if (tls
    && (!result.collection?.transport?.includes("HTTPS/1.1 over TLS")
      || result.collection?.chrome_certificate_errors_ignored !== true)) {
    fail(`${path} does not identify the self-signed TLS loopback collection`);
  }
  if (result.collection?.network_path !== (tls ? "HTTPS/TLS loopback to 127.0.0.1" : "HTTP loopback to 127.0.0.1")
    || ((upload || serviceWorker || httpCache || tls || httpCurrent) && !result.collection.proof_upload_verified)) {
    fail(`${path} does not identify the controlled loopback network path`);
  }
  if (!result.collection?.browser_version?.startsWith("Chrome/153.")
    && !result.collection?.browser?.includes("Version/18.3 Safari/605.1.15")) {
    fail(`${path} has an unexpected network browser version`);
  }
  const byteExpectations = serviceWorker ? {
    browser_transfer_bytes_total: 0,
    server_bytes_total: 27750,
    wasm_transfer_bytes: 0,
    javascript_transfer_bytes: 0,
    html_transfer_bytes: 0,
    upload_request_bytes: 27750,
    upload_resource_transfer_bytes: 432,
  } : coldServiceWorker ? {
    cached_bytes_total: 273188,
    server_bytes_total: 279716,
    server_observation_count: 5,
  } : serviceWorkerUpdate ? {
    initial_cached_bytes_total: 273188,
    updated_cached_bytes_total: 273188,
    server_bytes_total: 557084,
    server_observation_count: 9,
  } : httpCache ? {
    browser_transfer_bytes_total: 0,
    server_bytes_total: 27750,
    wasm_transfer_bytes: 0,
    javascript_transfer_bytes: 0,
    html_transfer_bytes: 0,
    upload_request_bytes: 27750,
    upload_resource_transfer_bytes: 432,
  } : safariHttpCache ? {
    browser_transfer_bytes_total: 0,
    server_bytes_total: 27750,
    wasm_transfer_bytes: 0,
    javascript_transfer_bytes: 0,
    html_transfer_bytes: 0,
    upload_request_bytes: 27750,
    upload_resource_transfer_bytes: 443,
  } : tls || httpCurrent ? {
    browser_transfer_bytes_total: 274088,
    server_bytes_total: 300938,
    wasm_transfer_bytes: 248043,
    javascript_transfer_bytes: 18918,
    html_transfer_bytes: 7127,
    upload_request_bytes: 27750,
    upload_resource_transfer_bytes: 432,
  } : upload ? {
    browser_transfer_bytes_total: 273389,
    server_bytes_total: 300239,
    wasm_transfer_bytes: 248043,
    javascript_transfer_bytes: 18918,
    html_transfer_bytes: 6428,
    upload_request_bytes: 27750,
    upload_resource_transfer_bytes: 432,
  } : {
    browser_transfer_bytes_total: 264119,
    server_bytes_total: 263219,
    wasm_transfer_bytes: 243942,
    javascript_transfer_bytes: 14899,
    html_transfer_bytes: 5278,
  };
  for (const [key, expected] of Object.entries(byteExpectations)) {
    const value = result.summary?.[key];
    if (value?.median !== expected || value?.min !== expected || value?.max !== expected) {
      fail(`${path} has non-deterministic ${key} statistics`);
    }
  }
  for (const run of (serviceWorker || coldServiceWorker || serviceWorkerUpdate || httpCache || safariHttpCache || tls || httpCurrent) ? [] : result.runs) {
    if (run.proof?.n !== 52 || run.proof?.k !== 13 || run.proof?.samples !== 1) {
      fail(`${path} contains an unexpected proof grid`);
    }
    if (run.proof?.proof_bytes !== 21781 || run.proof?.statement_bytes !== 5969 || run.proof?.bundle_bytes !== 27750) {
      fail(`${path} contains deterministic wire sizes that differ from the committed baseline`);
    }
    const resources = new Map(run.resources?.map(resource => [resource.name, resource]));
    if (!resources.has("html") || !resources.has("javascript") || !resources.has("wasm")) {
      fail(`${path} omits a required HTML, JavaScript, or WASM resource entry`);
    }
    const expectedWasmTransfer = upload ? 248043 : 243942;
    const expectedJavaScriptTransfer = upload ? 18918 : 14899;
    if (resources.get("wasm")?.transfer_size !== expectedWasmTransfer
      || resources.get("javascript")?.transfer_size !== expectedJavaScriptTransfer) {
      fail(`${path} has unexpected resource transfer sizes`);
    }
    if (upload && (run.upload?.request_bytes !== 27750
      || run.upload?.server_received_bytes !== 27750
      || run.upload?.server_accepted !== true
      || run.upload?.server_verified !== true)) {
      fail(`${path} contains an invalid binary upload record`);
    }
    const observations = run.server_observations ?? [];
    const observedBytes = observations.reduce(
      (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
      0,
    );
    const expectedObservations = upload ? 4 : 3;
    const expectedBytes = upload ? 300239 : 263219;
    if (observations.length !== expectedObservations || observedBytes !== expectedBytes) {
      fail(`${path} has incomplete server observations or an unexpected byte total`);
    }
    if (upload && !observations.some(item => item.direction === "browser-to-server" && item.verified === true)) {
      fail(`${path} does not contain a verified upload observation`);
    }
  }
}

if (mode === "--baseline") {
  if (process.argv.length !== 4) fail("usage: verify_reproduction.mjs --baseline BASELINE_JSON");
  validateScopedBaseline(resolve(process.argv[3]));
  console.log(`[repro-verify] scoped Circom baseline is valid: ${resolve(process.argv[3])}`);
} else if (mode === "--network") {
  if (process.argv.length !== 4) fail("usage: verify_reproduction.mjs --network NETWORK_JSON");
  validateNetworkBenchmark(resolve(process.argv[3]));
  console.log(`[repro-verify] network benchmark is valid: ${resolve(process.argv[3])}`);
} else if (mode === "--committed") {
  const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
  const checks = [
    [nativeBaseline, metadata.native_benchmark.csv_sha256],
    [componentBaseline, metadata.native_benchmark.component_csv_sha256],
    [baselineJson, metadata.scoped_baseline.json_sha256],
    [curveBaselineJson, metadata.curve_level_baseline.json_sha256],
    [multislotBaselineJson, metadata.multislot_baseline.json_sha256],
    [statementSchemaJson, metadata.statement_schema_refinement.json_sha256],
    [pstxAdapterVectorJson, metadata.pstx_adapter_vector.json_sha256],
    [networkJson, metadata.network_benchmark.json_sha256],
    [networkColdServiceWorkerJson, metadata.network_cold_service_worker_benchmark.json_sha256],
    [networkHttpCurrentJson, metadata.network_http_current_benchmark.json_sha256],
    [networkServiceWorkerJson, metadata.network_service_worker_benchmark.json_sha256],
    [networkServiceWorkerUpdateJson, metadata.network_service_worker_update_benchmark.json_sha256],
    [networkHttpCacheJson, metadata.network_http_cache_reuse_benchmark.json_sha256],
    [networkTlsJson, metadata.network_tls_benchmark.json_sha256],
    [networkUploadJson, metadata.network_upload_benchmark.json_sha256],
    [resolve(repoRoot, metadata.multislot_baseline.circuit), metadata.multislot_baseline.circuit_sha256],
    [resolve(repoRoot, metadata.multislot_baseline.runner), metadata.multislot_baseline.runner_sha256],
    [resolve(repoRoot, metadata.curve_level_baseline.example), metadata.curve_level_baseline.example_sha256],
    [resolve(repoRoot, metadata.curve_level_baseline.test), metadata.curve_level_baseline.test_sha256],
    [resolve(repoRoot, metadata.curve_level_baseline.codec_module), metadata.curve_level_baseline.codec_module_sha256],
    [resolve(repoRoot, metadata.curve_level_baseline.core_borsh_module), metadata.curve_level_baseline.core_borsh_module_sha256],
    [resolve(repoRoot, metadata.curve_level_baseline.bg_borsh_module), metadata.curve_level_baseline.bg_borsh_module_sha256],
    [resolve(repoRoot, metadata.curve_level_baseline.bundle_verifier_module), metadata.curve_level_baseline.bundle_verifier_module_sha256],
    ...Object.entries(metadata.statement_schema_refinement.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_service_worker_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_cold_service_worker_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_service_worker_update_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_http_cache_reuse_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_safari_http_cache_reuse_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_http_current_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_tls_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.network_upload_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    [wasmBaseline, metadata.benchmark.csv_sha256],
    ...metadata.browser_benchmarks.map(entry => [resolve(repoRoot, entry.json), entry.json_sha256]),
    ...Object.entries(metadata.native_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.browser_benchmark_common.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
  ];
  for (const [path, expected] of checks) {
    const actual = sha256(path);
    if (actual !== expected) {
      fail(`${path} SHA-256 is ${actual}; metadata records ${expected}`);
    }
  }
  parseCsv(nativeBaseline, nativeHeader);
  parseCsv(componentBaseline, componentHeader);
  validateScopedBaseline(baselineJson);
  parseCsv(wasmBaseline, wasmHeader);
  validateBrowserBenchmark(browserJson, "chrome-headless-153-macos", true);
  validateBrowserBenchmark(browserMemoryJson, "chrome-headless-memory-153-macos", true, "chrome", true);
  validateBrowserBenchmark(headedBrowserJson, "chrome-headed-153-macos", false);
  validateBrowserBenchmark(safariBrowserJson, "safari-desktop-macos", false, "safari");
  validateNetworkBenchmark(networkJson);
  validateNetworkBenchmark(networkColdServiceWorkerJson);
  validateNetworkBenchmark(networkHttpCurrentJson);
  validateNetworkBenchmark(networkServiceWorkerJson);
  validateNetworkBenchmark(networkServiceWorkerUpdateJson);
  validateNetworkBenchmark(networkHttpCacheJson);
  validateNetworkBenchmark(networkSafariHttpCacheJson);
  validateNetworkBenchmark(networkTlsJson);
  validateNetworkBenchmark(networkUploadJson);
  console.log(`[repro-verify] committed artifacts match ${metadataPath}`);
} else if (mode === "--generated") {
  const hasMetadataOutput = process.argv.length === 9 && process.argv[7] === "--metadata";
  if ((process.argv.length !== 7 && !hasMetadataOutput) || process.argv[5] !== "--samples") {
    fail("usage: verify_reproduction.mjs --generated NATIVE_CSV WASM_CSV --samples N [--metadata FILE]");
  }
  const nativePath = resolve(process.argv[3]);
  const wasmPath = resolve(process.argv[4]);
  const componentPath = resolve(nativePath, "../reconstruction_components.csv");
  const samples = process.argv[6];
  const nativeRows = parseCsv(nativePath, nativeHeader);
  const componentRows = parseCsv(componentPath, componentHeader);
  const wasmRows = parseCsv(wasmPath, wasmHeader);
  const nativeReference = parseCsv(nativeBaseline, nativeHeader);
  const wasmReference = parseCsv(wasmBaseline, wasmHeader);

  requirePositiveNumbers(
    nativeRows,
    nativeHeader.slice(2).filter((column) => !column.endsWith("stddev_us")),
    nativePath,
  );
  requireNonNegativeNumbers(nativeRows, ["prove_stddev_us", "verify_stddev_us"], nativePath);
  requirePositiveNumbers(
    wasmRows,
    wasmHeader.slice(2).filter((column) => !column.endsWith("stddev_ms")),
    wasmPath,
  );
  requireNonNegativeNumbers(wasmRows, ["prove_stddev_ms", "verify_stddev_ms"], wasmPath);
  requirePositiveNumbers(componentRows, componentHeader.slice(2), componentPath);
  requireSameGrid(nativeRows, nativeReference, nativePath);
  requireSameGrid(componentRows, parseCsv(componentBaseline, componentHeader), componentPath);
  requireSameGrid(wasmRows, wasmReference, wasmPath);

  for (let index = 0; index < nativeRows.length; index += 1) {
    const component = componentRows[index];
    const proveParts = ["residual_setup_ns", "cross_key_ns", "bayer_groth_ns", "slot_or_ns"];
    const verifyParts = ["verify_cross_key_ns", "verify_bayer_groth_ns", "verify_slot_or_ns"];
    for (const key of [...proveParts, ...verifyParts]) {
      const total = key.startsWith("verify_") ? Number(component.verify_total_ns) : Number(component.prove_total_ns);
      if (Number(component[key]) > total) {
        fail(`${componentPath}:${index + 2} ${key} exceeds its total`);
      }
    }
    const proveSum = proveParts.reduce((sum, key) => sum + Number(component[key]), 0);
    const verifySum = verifyParts.reduce((sum, key) => sum + Number(component[key]), 0);
    if (proveSum > Number(component.prove_total_ns) * 1.25 || verifySum > Number(component.verify_total_ns) * 1.25) {
      fail(`${componentPath}:${index + 2} component sum exceeds 25% timing-overhead tolerance`);
    }
    for (const column of ["proof_bytes", "statement_bytes"]) {
      if (nativeRows[index][column] !== nativeReference[index][column]) {
        fail(`${nativePath}:${index + 2} changed deterministic ${column}`);
      }
      if (wasmRows[index][column] !== wasmReference[index][column]) {
        fail(`${wasmPath}:${index + 2} changed deterministic ${column}`);
      }
      if (nativeRows[index][column] !== wasmRows[index][column]) {
        fail(`native/WASM ${column} differs for grid cell ${gridKey(nativeRows[index])}`);
      }
    }
    const expectedBundle = Number(wasmRows[index].proof_bytes) + Number(wasmRows[index].statement_bytes);
    if (Number(wasmRows[index].bundle_bytes) !== expectedBundle) {
      fail(`${wasmPath}:${index + 2} bundle_bytes is not statement_bytes + proof_bytes`);
    }
    if (wasmRows[index].samples !== samples) {
      fail(`${wasmPath}:${index + 2} records ${wasmRows[index].samples} samples; expected ${samples}`);
    }
    if (nativeRows[index].samples !== "30") {
      fail(`${nativePath}:${index + 2} records ${nativeRows[index].samples} samples; expected 30`);
    }
  }
  console.log(`[repro-verify] generated native SHA-256: ${sha256(nativePath)}`);
  console.log(`[repro-verify] generated WASM SHA-256:   ${sha256(wasmPath)}`);
  console.log("[repro-verify] generated grids and deterministic sizes are valid");

  if (hasMetadataOutput) {
    const outputPath = resolve(process.argv[8]);
    const gitStatus = execFileSync("git", ["status", "--porcelain"], {
      cwd: repoRoot,
      encoding: "utf8",
    }).trim();
    const runMetadata = {
      schema_version: 1,
      recorded_at: new Date().toISOString(),
      git_revision: commandOutput("git", ["rev-parse", "HEAD"]),
      working_tree_dirty: gitStatus.length > 0,
      samples_per_wasm_cell: Number(samples),
      results: {
        native_csv: relative(repoRoot, nativePath),
        native_csv_sha256: sha256(nativePath),
        component_csv: relative(repoRoot, componentPath),
        component_csv_sha256: sha256(componentPath),
        wasm_csv: relative(repoRoot, wasmPath),
        wasm_csv_sha256: sha256(wasmPath),
      },
      machine: {
        platform: platform(),
        release: release(),
        architecture: arch(),
        cpu_model: cpus()[0]?.model ?? "unknown",
        cpu_cores: cpus().length,
      },
      software: {
        node: process.version,
        v8: process.versions.v8,
        rustc: commandOutput("rustc", ["--version"]),
        cargo: commandOutput("cargo", ["--version"]),
        wasm_pack: commandOutput("wasm-pack", ["--version"]),
        lean: commandOutput("lean", ["--version"], resolve(repoRoot, "poker_protocol_lean")),
        lake: commandOutput("lake", ["--version"], resolve(repoRoot, "poker_protocol_lean")),
      },
      scope: "Node/V8 host and native measurements; not a browser-page or mobile-device run",
    };
    writeFileSync(outputPath, `${JSON.stringify(runMetadata, null, 2)}\n`);
    console.log(`[repro-verify] run metadata written to ${outputPath}`);
  }
} else {
  fail("usage: verify_reproduction.mjs --committed | --generated NATIVE_CSV WASM_CSV --samples N [--metadata FILE]");
}
