#!/usr/bin/env node
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(fileURLToPath(import.meta.url), "../..");
const serverScript = path.join(repoRoot, "client-wasm/browser_benchmark_server.mjs");
const browserPage = path.join(repoRoot, "client-wasm/browser_benchmark.html");
const webModule = path.join(repoRoot, "client-wasm/pkg-web/client_wasm.js");
const webWasm = path.join(repoRoot, "client-wasm/pkg-web/client_wasm_bg.wasm");
const referenceWasmCsv = path.join(repoRoot, "paper/experiments/reconstruction_wasm.csv");

const args = process.argv.slice(2);
const options = {
  browser: "",
  samples: 30,
  label: "chrome-headless",
  outputDir: path.join(repoRoot, ".repro/browser"),
  timeoutMs: 20 * 60 * 1000,
  headed: false,
  memorySamplingMs: 0,
};

function usage(message) {
  if (message) console.error(`error: ${message}`);
  console.error(`usage: ${path.basename(process.argv[1])} [--browser PATH] [--samples N] [--label NAME] [--output-dir DIR] [--timeout-ms MS] [--headed] [--memory-sampling-ms MS]`);
  process.exit(message ? 2 : 0);
}

for (let index = 0; index < args.length; index += 1) {
  const arg = args[index];
  if (arg === "--headed") {
    options.headed = true;
    continue;
  }
  const value = args[index + 1];
  if (value === undefined) usage(`missing value for ${arg}`);
  if (arg === "--browser") options.browser = value;
  else if (arg === "--samples") options.samples = Number(value);
  else if (arg === "--label") options.label = value;
  else if (arg === "--output-dir") options.outputDir = path.resolve(value);
  else if (arg === "--timeout-ms") options.timeoutMs = Number(value);
  else if (arg === "--memory-sampling-ms") options.memorySamplingMs = Number(value);
  else usage(`unknown option ${arg}`);
  index += 1;
}

if (!Number.isInteger(options.samples) || options.samples < 1 || options.samples > 101) {
  usage("--samples must be an integer from 1 through 101");
}
if (!Number.isInteger(options.timeoutMs) || options.timeoutMs < 30_000) {
  usage("--timeout-ms must be at least 30000");
}
if (!Number.isInteger(options.memorySamplingMs) || options.memorySamplingMs < 0 || options.memorySamplingMs > 5_000) {
  usage("--memory-sampling-ms must be an integer from 0 (disabled) through 5000");
}
if (!/^[\w.-]{1,48}$/.test(options.label)) {
  usage("--label may contain only letters, digits, underscores, dots, and dashes, with length 1-48");
}

async function resolveBrowser() {
  if (options.browser) {
    const info = await stat(options.browser).catch(() => null);
    if (!info?.isFile()) throw new Error(`browser executable not found: ${options.browser}`);
    return options.browser;
  }
  const candidates = [
    process.env.BROWSER,
    process.platform === "darwin" && "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    process.platform === "darwin" && "/Applications/Chromium.app/Contents/MacOS/Chromium",
    process.platform === "linux" && "/usr/bin/google-chrome",
    process.platform === "linux" && "/usr/bin/google-chrome-stable",
    process.platform === "linux" && "/usr/bin/chromium",
    process.platform === "linux" && "/usr/bin/chromium-browser",
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (await stat(candidate).then(info => info.isFile()).catch(() => false)) return candidate;
  }
  throw new Error("no Chrome/Chromium executable found; set --browser or BROWSER");
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForFile(file, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await stat(file).then(info => info.isFile()).catch(() => false)) return;
    await delay(50);
  }
  throw new Error(`timed out waiting for ${file}`);
}

async function readLines(file) {
  const content = await readFile(file, "utf8");
  return content.split(/\r?\n/).filter(Boolean);
}

async function removeProfile(directory) {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    try {
      await rm(directory, {recursive: true, force: true});
      return;
    } catch (error) {
      if (error.code !== "ENOTEMPTY" && error.code !== "EBUSY") throw error;
      await delay(100);
    }
  }
  await rm(directory, {recursive: true, force: true});
}

async function waitForResultFile(directory, existingFiles, safeLabel, timeoutMs, sampleMemory = null) {
  const startedAt = Date.now();
  let lastHeartbeat = Date.now();
  const pollIntervalMs = sampleMemory ? Math.min(options.memorySamplingMs, 500) : 500;
  while (Date.now() - startedAt < timeoutMs) {
    const entries = await readdir(directory).catch(() => []);
    const candidate = entries.find(name =>
      name.startsWith(`browser_${safeLabel}_`) &&
      name.endsWith(".json") &&
      !existingFiles.has(name),
    );
    if (candidate) {
      const outputPath = path.join(directory, candidate);
      const firstSize = (await stat(outputPath)).size;
      await delay(250);
      if ((await stat(outputPath)).size === firstSize) return outputPath;
    }
    if (sampleMemory) await sampleMemory();
    if (Date.now() - lastHeartbeat > 30_000) {
      lastHeartbeat = Date.now();
      console.log(`[browser-benchmark-runner] waiting for result (${Math.round((Date.now() - startedAt) / 1000)}s elapsed)`);
    }
    await delay(pollIntervalMs);
  }
  throw new Error(`timed out after ${timeoutMs} ms`);
}

class CdpConnection {
  constructor(url) {
    this.url = url;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Set();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.socket = new WebSocket(this.url);
      this.socket.onerror = () => reject(new Error(`cannot connect to Chrome DevTools at ${this.url}`));
      this.socket.onopen = () => resolve();
      this.socket.onmessage = event => this.receive(String(event.data));
      this.socket.onclose = () => {
        for (const {reject} of this.pending.values()) reject(new Error("Chrome DevTools connection closed"));
        this.pending.clear();
      };
    });
  }

  receive(message) {
    const event = JSON.parse(message);
    if (event.id && this.pending.has(event.id)) {
      const pending = this.pending.get(event.id);
      this.pending.delete(event.id);
      if (event.error) pending.reject(new Error(`${event.error.message}: ${event.error.data ?? ""}`));
      else pending.resolve(event.result);
      return;
    }
    for (const listener of this.listeners) listener(event);
  }

  send(method, params = {}, sessionId) {
    const id = this.nextId++;
    const message = {id, method, params};
    if (sessionId) message.sessionId = sessionId;
    const promise = new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`Chrome DevTools call timed out: ${method}`));
        }
      }, 30_000).unref();
    });
    this.socket.send(JSON.stringify(message));
    return promise;
  }

  close() {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.close();
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

async function parseReferenceSizes() {
  const lines = await readLines(referenceWasmCsv);
  const header = lines[0].split(",");
  const sizes = new Map();
  for (const line of lines.slice(1)) {
    const values = line.split(",");
    const row = Object.fromEntries(header.map((name, index) => [name, values[index]]));
    sizes.set(`${row.n},${row.k}`, row);
  }
  if (sizes.size !== 10) throw new Error(`reference WASM grid has ${sizes.size} rows; expected 10`);
  return sizes;
}

function validateResult(payload, expectedSizes) {
  const failures = [];
  if (payload.schema_version !== 1) failures.push("schema_version must be 1");
  if (payload.label !== options.label) failures.push("label mismatch");
  if (payload.samples_per_cell !== options.samples) failures.push("sample count mismatch");
  if (!Array.isArray(payload.results) || payload.results.length !== 10) failures.push("result must contain exactly ten cells");
  if (!payload.environment?.user_agent) failures.push("browser user agent is missing");
  if (options.headed && payload.environment?.headless_ua) failures.push("headed run unexpectedly reports HeadlessChrome");
  if (!options.headed && !payload.environment?.headless_ua) failures.push("headless run does not report HeadlessChrome");

  for (const [index, row] of (payload.results ?? []).entries()) {
    for (const key of [
      "prove_median_ms", "prove_mean_ms", "prove_stddev_ms", "prove_p95_ms",
      "verify_median_ms", "verify_mean_ms", "verify_stddev_ms", "verify_p95_ms",
      "outer_call_ms",
    ]) {
      if (!Number.isFinite(row[key]) || row[key] < 0) failures.push(`row ${index}: invalid ${key}`);
    }
    if (row.samples !== options.samples) failures.push(`row ${index}: sample count mismatch`);
    const expected = expectedSizes.get(`${row.n},${row.k}`);
    if (!expected) {
      failures.push(`row ${index}: unexpected grid cell ${row.n},${row.k}`);
      continue;
    }
    for (const key of ["proof_bytes", "statement_bytes", "bundle_bytes"]) {
      if (row[key] !== Number(expected[key])) failures.push(`row ${index}: ${key} differs from committed wire baseline`);
    }
  }
  if (failures.length) throw new Error(`invalid browser result:\n- ${failures.join("\n- ")}`);
}

function performanceMetric(metrics, name) {
  return (metrics.metrics ?? metrics).find(metric => metric.name === name)?.value;
}

function validateMemoryCollection(collection) {
  const memory = collection?.memory;
  if (!memory) return;
  for (const key of [
    "js_heap_used_peak_bytes",
    "js_heap_total_peak_bytes",
    "final_js_heap_used_bytes",
    "final_js_heap_total_bytes",
    "metric_samples",
    "sampling_interval_ms",
  ]) {
    if (!Number.isFinite(memory[key]) || memory[key] < 0) {
      throw new Error(`invalid CDP memory collection field: ${key}`);
    }
  }
  if (memory.metric_samples < 1
    || memory.sampling_interval_ms < 1
    || memory.js_heap_used_peak_bytes <= 0
    || memory.js_heap_total_peak_bytes < memory.js_heap_used_peak_bytes
    || memory.final_js_heap_total_bytes < memory.final_js_heap_used_bytes) {
    throw new Error("invalid CDP JS-heap memory statistics");
  }
}

async function main() {
  for (const required of [browserPage, webModule, webWasm, serverScript, referenceWasmCsv]) {
    if (!await stat(required).then(info => info.isFile()).catch(() => false)) {
      throw new Error(`missing required file; build the web target first: ${required}`);
    }
  }
  const browserExecutable = await resolveBrowser();
  const expectedSizes = await parseReferenceSizes();
  const port = 20000 + Math.floor(Math.random() * 25000);
  const server = spawn(process.execPath, [
    serverScript,
    "--host", "127.0.0.1",
    "--port", String(port),
    "--output-dir", options.outputDir,
  ], {stdio: ["ignore", "pipe", "pipe"]});

  let serverError = "";
  server.stdout.on("data", chunk => process.stdout.write(`[server] ${chunk}`));
  server.stderr.on("data", chunk => {
    serverError += chunk;
    process.stderr.write(`[server-error] ${chunk}`);
  });

  const profileDir = await mkdtemp(path.join(tmpdir(), "poker-browser-profile-"));
  let chrome;
  let cdp;
  let targetId;
  const memory = {
    js_heap_used_peak_bytes: 0,
    js_heap_total_peak_bytes: 0,
    final_js_heap_used_bytes: 0,
    final_js_heap_total_bytes: 0,
    metric_samples: 0,
  };
  try {
    const baseUrl = `http://127.0.0.1:${port}`;
    await mkdir(options.outputDir, {recursive: true});
    const safeLabel = options.label.replace(/[^\w.-]+/g, "-");
    const existingFiles = new Set(await readdir(options.outputDir).catch(() => []));
    let serverReady = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (server.exitCode !== null) throw new Error(`benchmark server exited early: ${serverError}`);
      if (await fetch(`${baseUrl}/`, {method: "HEAD"}).then(response => response.ok).catch(() => false)) {
        serverReady = true;
        break;
      }
      await delay(50);
    }
    if (!serverReady) throw new Error("benchmark server did not become ready");

    const chromeArgs = [
      `--user-data-dir=${profileDir}`,
      "--remote-debugging-port=0",
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-extensions",
      "--disable-background-networking",
      "--disable-background-timer-throttling",
      "--disable-backgrounding-occluded-windows",
      "--disable-renderer-backgrounding",
      "--remote-allow-origins=*",
    ];
    if (!options.headed) chromeArgs.push("--headless=new", "--disable-gpu");

    chrome = spawn(browserExecutable, chromeArgs, {stdio: ["ignore", "pipe", "pipe"]});
    let chromeError = "";
    chrome.stderr.on("data", chunk => {
      chromeError += chunk;
    });
    const devtoolsPortFile = path.join(profileDir, "DevToolsActivePort");
    await waitForFile(devtoolsPortFile, 15_000);
    const [debugPort, browserWsPath] = (await readLines(devtoolsPortFile));
    const version = await fetchJson(`http://127.0.0.1:${debugPort}/json/version`);
    cdp = new CdpConnection(version.webSocketDebuggerUrl);
    await cdp.connect();
    const browserInfo = await cdp.send("Browser.getVersion");

    const pageUrl = `${baseUrl}/?label=${encodeURIComponent(options.label)}&samples=${options.samples}&autorun=1${options.memorySamplingMs > 0 ? "&memory=1" : ""}`;
    ({targetId} = await cdp.send("Target.createTarget", {url: pageUrl}));
    const attached = await cdp.send("Target.attachToTarget", {targetId, flatten: true});
    const sessionId = attached.sessionId;
    const sampleMemory = async () => {
      const metrics = await cdp.send("Performance.getMetrics", {}, sessionId);
      const used = performanceMetric(metrics, "JSHeapUsedSize");
      const total = performanceMetric(metrics, "JSHeapTotalSize");
      if (!Number.isFinite(used) || !Number.isFinite(total) || used < 0 || total < used) {
        throw new Error("Chrome returned invalid JS-heap performance metrics");
      }
      memory.js_heap_used_peak_bytes = Math.max(memory.js_heap_used_peak_bytes, used);
      memory.js_heap_total_peak_bytes = Math.max(memory.js_heap_total_peak_bytes, total);
      memory.final_js_heap_used_bytes = used;
      memory.final_js_heap_total_bytes = total;
      memory.metric_samples += 1;
    };
    if (options.memorySamplingMs > 0) await cdp.send("Performance.enable", {}, sessionId);
    console.log("[browser-benchmark-runner] browser target opened; waiting for the ten-cell run");
    const startedAt = Date.now();
    const outputPath = await waitForResultFile(
      options.outputDir,
      existingFiles,
      safeLabel,
      options.timeoutMs,
      options.memorySamplingMs > 0 ? sampleMemory : null,
    );
    const payload = JSON.parse(await readFile(outputPath, "utf8"));
    if (options.memorySamplingMs > 0) await sampleMemory();
    payload.collection = {
      protocol: "Chrome DevTools Protocol",
      browser_executable: browserExecutable,
      browser_version: browserInfo.product,
      user_agent_version: version["User-Agent"],
      headless: !options.headed,
      chrome_arguments: chromeArgs,
      runner_started_at: new Date(startedAt).toISOString(),
      runner_completed_at: new Date().toISOString(),
      node: process.version,
    };
    if (options.memorySamplingMs > 0) {
      payload.collection.memory = {
        ...memory,
        sampling_interval_ms: options.memorySamplingMs,
        method: "Chrome DevTools Protocol Performance.getMetrics polling",
        scope: "renderer JS heap only; not browser-process RSS, native peak memory, Safari, or mobile-device memory",
      };
    }
    validateResult(payload, expectedSizes);
    validateMemoryCollection(payload.collection);
    await writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`);
    console.log(`[browser-benchmark-runner] validated and enriched ${outputPath}`);

    await cdp.send("Target.closeTarget", {targetId}).catch(() => undefined);
    targetId = undefined;
    cdp.close();
    cdp = undefined;
    chrome.kill("SIGTERM");
    await new Promise(resolve => chrome.once("exit", resolve));
    chrome = undefined;
    server.kill("SIGTERM");
    await new Promise(resolve => server.once("exit", resolve));
    await removeProfile(profileDir);
  } catch (error) {
    if (cdp && targetId) await cdp.send("Target.closeTarget", {targetId}).catch(() => undefined);
    cdp?.close();
    chrome?.kill("SIGTERM");
    server.kill("SIGTERM");
    await removeProfile(profileDir).catch(() => undefined);
    throw error;
  }
}

main().catch(error => {
  console.error(`[browser-benchmark-runner] ${error?.stack ?? error}`);
  process.exit(1);
});
