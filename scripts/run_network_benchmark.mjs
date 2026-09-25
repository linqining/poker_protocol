#!/usr/bin/env node
import { execFile, spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdir, mkdtemp, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { isIP } from "node:net";
import tls from "node:tls";
import { tmpdir } from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(fileURLToPath(import.meta.url), "../..");
const serverScript = path.join(repoRoot, "client-wasm/browser_benchmark_server.mjs");
const networkPage = path.join(repoRoot, "client-wasm/network_benchmark.html");
const uploadPage = path.join(repoRoot, "client-wasm/upload_benchmark.html");
const coldServiceWorkerPage = path.join(repoRoot, "client-wasm/service_worker_cold_benchmark.html");
const serviceWorkerUpdatePage = path.join(repoRoot, "client-wasm/service_worker_update_benchmark.html");
const httpCachePage = path.join(repoRoot, "client-wasm/http_cache_benchmark.html");
const serviceWorkerBootstrapPage = path.join(repoRoot, "client-wasm/service_worker_bootstrap.html");
const serviceWorkerScript = path.join(repoRoot, "client-wasm/service_worker_cache.js");
const webModule = path.join(repoRoot, "client-wasm/pkg-web/client_wasm.js");
const webWasm = path.join(repoRoot, "client-wasm/pkg-web/client_wasm_bg.wasm");
const nodeVerifierModule = path.join(repoRoot, "client-wasm/pkg/client_wasm.js");

const options = {
  browser: "",
  runs: 30,
  label: "chrome-cache-disabled-loopback",
  outputDir: path.join(repoRoot, ".repro/network"),
  timeoutMs: 10 * 60 * 1000,
  upload: false,
  serviceWorker: false,
  coldServiceWorker: false,
  serviceWorkerUpdate: false,
  httpCacheReuse: false,
  tls: false,
  remoteServerUrl: "",
  networkClass: "",
  allowInsecureTransport: false,
  allowInvalidCertificate: false,
  remoteLoopbackSmoke: false,
  coldBrowserProcess: false,
  requireValidCertificate: false,
};

function usage(message) {
  if (message) console.error(`error: ${message}`);
  console.error(`usage: ${path.basename(process.argv[1])} [--browser PATH] [--runs N] [--label NAME] [--output-dir DIR] [--timeout-ms MS] [--upload] [--service-worker] [--cold-service-worker] [--service-worker-update] [--http-cache-reuse] [--tls] [--remote-server-url URL --network-class lan|internet] [--allow-insecure-transport] [--allow-invalid-certificate] [--require-valid-certificate] [--cold-browser-process] [--remote-loopback-smoke]`);
  process.exit(message ? 2 : 0);
}

for (let index = 0; index < process.argv.slice(2).length; index += 1) {
  const arg = process.argv[index + 2];
  if (arg === "--upload") {
    options.upload = true;
    continue;
  }
  if (arg === "--service-worker") {
    options.upload = true;
    options.serviceWorker = true;
    continue;
  }
  if (arg === "--cold-service-worker") {
    options.serviceWorker = true;
    options.coldServiceWorker = true;
    continue;
  }
  if (arg === "--service-worker-update") {
    options.serviceWorker = true;
    options.serviceWorkerUpdate = true;
    continue;
  }
  if (arg === "--http-cache-reuse") {
    options.upload = true;
    options.httpCacheReuse = true;
    continue;
  }
  if (arg === "--tls") {
    options.tls = true;
    continue;
  }
  if (arg === "--allow-insecure-transport") {
    options.allowInsecureTransport = true;
    continue;
  }
  if (arg === "--allow-invalid-certificate") {
    options.allowInvalidCertificate = true;
    continue;
  }
  if (arg === "--remote-loopback-smoke") {
    options.remoteLoopbackSmoke = true;
    continue;
  }
  if (arg === "--cold-browser-process") {
    options.coldBrowserProcess = true;
    continue;
  }
  if (arg === "--require-valid-certificate") {
    options.requireValidCertificate = true;
    continue;
  }
  const value = process.argv[index + 3];
  if (value === undefined) usage(`missing value for ${arg}`);
  if (arg === "--browser") options.browser = value;
  else if (arg === "--runs") options.runs = Number(value);
  else if (arg === "--label") options.label = value;
  else if (arg === "--output-dir") options.outputDir = path.resolve(value);
  else if (arg === "--timeout-ms") options.timeoutMs = Number(value);
  else if (arg === "--remote-server-url") options.remoteServerUrl = value;
  else if (arg === "--network-class") options.networkClass = value;
  else usage(`unknown option ${arg}`);
  index += 1;
}
if (!Number.isInteger(options.runs) || options.runs < 1 || options.runs > 101) {
  usage("--runs must be an integer from 1 through 101");
}
if (!Number.isInteger(options.timeoutMs) || options.timeoutMs < 30_000) {
  usage("--timeout-ms must be at least 30000");
}
if (!/^[\w.-]{1,48}$/.test(options.label)) {
  usage("--label may contain only letters, digits, underscores, dots, and dashes, with length 1-48");
}
if (!options.serviceWorker && options.label.includes("service-worker")) {
  usage("service-worker labels require --service-worker");
}
if (options.tls && !options.label.includes("tls")) {
  usage("TLS run labels must contain 'tls'");
}
if (options.tls && (options.coldServiceWorker || options.serviceWorkerUpdate || options.httpCacheReuse)) {
  usage("service-worker installation/update and browser HTTP-cache benchmarks are HTTP loopback measurements and cannot be combined with --tls");
}
if (options.httpCacheReuse && (options.serviceWorker || options.coldServiceWorker || options.serviceWorkerUpdate)) {
  usage("--http-cache-reuse must not be combined with service-worker modes");
}
if (options.tls) process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
if (options.coldBrowserProcess && !options.remoteServerUrl) {
  usage("--cold-browser-process requires --remote-server-url");
}
if (options.requireValidCertificate && !options.remoteServerUrl) {
  usage("--require-valid-certificate requires --remote-server-url");
}
if (options.remoteServerUrl) {
  if (!options.upload || options.tls || options.serviceWorker || options.coldServiceWorker
    || options.serviceWorkerUpdate || options.httpCacheReuse) {
    usage("--remote-server-url currently supports only cache-disabled --upload");
  }
  if (!["lan", "internet"].includes(options.networkClass)) {
    usage("--network-class must be lan or internet");
  }
  let remoteUrl;
  try {
    remoteUrl = new URL(options.remoteServerUrl);
  } catch {
    usage("--remote-server-url must be a valid absolute origin");
  }
  if ((remoteUrl.pathname && remoteUrl.pathname !== "/") || remoteUrl.search || remoteUrl.hash) {
    usage("--remote-server-url must be an origin such as https://host:port");
  }
  if (remoteUrl.protocol !== "https:" && remoteUrl.protocol !== "http:") {
    usage("--remote-server-url must use http: or https:");
  }
  if (remoteUrl.protocol === "http:" && !options.allowInsecureTransport) {
    usage("HTTP requires --allow-insecure-transport; remote measurements should normally use HTTPS");
  }
  if (options.requireValidCertificate) {
    if (remoteUrl.protocol !== "https:") {
      usage("--require-valid-certificate requires an https remote server");
    }
    if (options.allowInvalidCertificate) {
      usage("--require-valid-certificate cannot be combined with --allow-invalid-certificate");
    }
  }
  const remoteHost = remoteUrl.hostname.toLowerCase();
  if (["127.0.0.1", "localhost", "::1"].includes(remoteHost) && !options.remoteLoopbackSmoke) {
    usage("loopback remote servers require --remote-loopback-smoke and remain smoke tests, not LAN/Internet evidence");
  }
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
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

async function waitForFile(file, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (await stat(file).then(info => info.isFile()).catch(() => false)) return;
    await delay(50);
  }
  throw new Error(`timed out waiting for ${file}`);
}

async function readLines(file) {
  return (await readFile(file, "utf8")).split(/\r?\n/).filter(Boolean);
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

async function waitForNetworkRun(cdp, sessionId, directory, existingFiles, label, session, timeoutMs) {
  const started = Date.now();
  let heartbeat = Date.now();
  while (Date.now() - started < timeoutMs) {
    const entries = await readdir(directory).catch(() => []);
    const candidate = entries.find(name =>
      name.startsWith(`network_run_${label}_${session}_`) &&
      name.endsWith(".json") &&
      !existingFiles.has(name),
    );
    if (candidate) {
      const outputPath = path.join(directory, candidate);
      const firstSize = (await stat(outputPath)).size;
      await delay(100);
      if ((await stat(outputPath)).size === firstSize) return {path: outputPath, filename: candidate};
    }
    const evaluated = await cdp.send("Runtime.evaluate", {
      expression: "document.getElementById('status')?.textContent ?? ''",
      returnByValue: true,
    }, sessionId).catch(() => null);
    const status = evaluated?.result?.value ?? "";
    if (status.startsWith("Failed:")) throw new Error(status);
    if (Date.now() - heartbeat > 30_000) {
      heartbeat = Date.now();
      console.log(`[network-runner] waiting for run ${session} (${Math.round((Date.now() - started) / 1000)}s)`);
    }
    await delay(250);
  }
  throw new Error(`timed out after ${timeoutMs} ms for session ${session}`);
}

async function waitForRemoteNetworkRun(cdp, sessionId, timeoutMs) {
  const started = Date.now();
  let heartbeat = Date.now();
  while (Date.now() - started < timeoutMs) {
    const evaluated = await cdp.send("Runtime.evaluate", {
      expression: "document.getElementById('status')?.textContent ?? ''",
      returnByValue: true,
    }, sessionId).catch(() => null);
    const status = evaluated?.result?.value ?? "";
    const saved = status.match(/^Saved ([\w.-]+\.json)$/);
    if (saved) return saved[1];
    if (status.startsWith("Failed:")) throw new Error(status);
    if (Date.now() - heartbeat > 30_000) {
      heartbeat = Date.now();
      console.log(`[network-runner] waiting for remote run (${Math.round((Date.now() - started) / 1000)}s)`);
    }
    await delay(250);
  }
  throw new Error(`timed out waiting for remote network result after ${timeoutMs} ms`);
}

async function startRemoteBrowser(browserExecutable, profileDir) {
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
    "--disable-keep-alive",
    "--remote-allow-origins=*",
    "--headless=new",
    "--disable-gpu",
    ...(options.allowInvalidCertificate ? ["--ignore-certificate-errors"] : []),
  ];
  const chrome = spawn(browserExecutable, chromeArgs, {stdio: ["ignore", "pipe", "pipe"]});
  chrome.stderr.on("data", chunk => {
    if (process.env.POKER_REMOTE_BROWSER_DEBUG === "1") {
      process.stderr.write(`[remote-browser] ${chunk}`);
    }
  });
  const devtoolsPortFile = path.join(profileDir, "DevToolsActivePort");
  await waitForFile(devtoolsPortFile, 15_000);
  const [debugPort] = await readLines(devtoolsPortFile);
  const version = await fetchJson(`http://127.0.0.1:${debugPort}/json/version`);
  const cdp = new CdpConnection(version.webSocketDebuggerUrl);
  await cdp.connect();
  const browserInfo = await cdp.send("Browser.getVersion");
  return {profileDir, chromeArgs, chrome, cdp, browserInfo, version};
}

async function stopRemoteBrowser(session) {
  if (!session) return;
  session.chrome.kill("SIGKILL");
  session.cdp.close();
  const exited = new Promise(resolve => session.chrome.once("exit", resolve));
  await exited;
  await removeProfile(session.profileDir);
}

async function waitForPageStatus(cdp, sessionId, timeoutMs = 30_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const evaluated = await cdp.send("Runtime.evaluate", {
      expression: "document.getElementById('status')?.textContent ?? ''",
      returnByValue: true,
    }, sessionId);
    const status = evaluated.result?.value ?? "";
    if (status.startsWith("Service worker ready:")) return status;
    if (status.startsWith("Failed:")) throw new Error(status);
    await delay(100);
  }
  throw new Error("timed out waiting for service-worker bootstrap");
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

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

function runOpenSsl(arguments_) {
  return new Promise((resolve, reject) => {
    execFile("openssl", arguments_, error => {
      if (error) reject(error);
      else resolve();
    });
  });
}

function tlsName(value) {
  if (!value) return null;
  if (typeof value === "string") return value;
  return value.CN ?? value.O ?? null;
}

export async function inspectRemoteCertificate(serverUrl, timeoutMs) {
  return await new Promise((resolve, reject) => {
    const port = Number(serverUrl.port || 443);
    const socket = tls.connect({
      host: serverUrl.hostname,
      port,
      rejectUnauthorized: true,
      ...(isIP(serverUrl.hostname) ? {} : {servername: serverUrl.hostname}),
    });
    const fail = error => {
      socket.destroy();
      reject(error instanceof Error ? error : new Error(String(error)));
    };
    socket.setTimeout(timeoutMs, () => fail(new Error(`TLS inspection timed out after ${timeoutMs} ms`)));
    socket.once("error", fail);
    socket.once("secureConnect", () => {
      try {
        const certificate = socket.getPeerCertificate(false);
        if (!certificate || Object.keys(certificate).length === 0) {
          fail(new Error("remote server did not present a TLS certificate"));
          return;
        }
        const hostnameError = tls.checkServerIdentity(serverUrl.hostname, certificate);
        if (hostnameError) {
          fail(hostnameError);
          return;
        }
        if (!socket.authorized) {
          fail(new Error(socket.authorizationError || "TLS certificate was not authorized by the system trust store"));
          return;
        }
        const result = {
          authorized: socket.authorized,
          authorization_error: null,
          trust_source: "Node.js system trust store",
          hostname: serverUrl.hostname,
          hostname_verified: true,
          subject_common_name: tlsName(certificate.subject),
          subject_organization: certificate.subject?.O ?? null,
          issuer_organization: certificate.issuer?.O ?? null,
          issuer_common_name: tlsName(certificate.issuer),
          valid_from: certificate.valid_from ?? null,
          valid_to: certificate.valid_to ?? null,
          subject_alt_names: typeof certificate.subjectaltname === "string"
            ? certificate.subjectaltname.split(/,\s+/)
            : [],
          sha256_fingerprint: certificate.fingerprint256 ?? null,
        };
        socket.end(() => resolve(result));
      } catch (error) {
        fail(error);
      }
    });
  });
}

function validateColdServiceWorkerRun(run, index) {
  const failures = [];
  if (run.schema_version !== 1
    || run.kind !== "cold-service-worker-install-single-run"
    || run.label !== options.label) {
    failures.push("invalid cold service-worker identity");
  }
  if (!run.network_session
    || run.environment?.service_worker !== true
    || run.service_worker?.controlled !== true
    || run.service_worker?.state !== "activated"
    || !run.service_worker?.script_url?.includes("/service_worker_cache.js")
    || !run.service_worker?.cache_name?.includes(run.network_session ?? "")) {
    failures.push("service worker did not activate with a run-specific cache");
  }
  const pageScope = new URL("./", run.environment?.href ?? "http://localhost/").href;
  if (run.service_worker?.scope !== pageScope) {
    failures.push("service-worker scope does not match the unique cold page");
  }
  for (const key of ["register_ms", "ready_ms", "controller_ms", "total_ms"]) {
    if (!Number.isFinite(run.initialization?.[key]) || run.initialization[key] < 0) {
      failures.push(`invalid ${key}`);
    }
  }
  const cacheEntries = new Map((run.cache_entries ?? []).map(entry => [entry.name, entry]));
  const expectedSizes = new Map([
    ["html", 6827],
    ["javascript", 18618],
    ["wasm", 247743],
  ]);
  if (cacheEntries.size !== 3) failures.push("cache entry count is not three");
  for (const [name, expectedBytes] of expectedSizes) {
    if (cacheEntries.get(name)?.response_bytes !== expectedBytes || cacheEntries.get(name)?.ok !== true) {
      failures.push(`${name} cache entry is missing or has unexpected bytes`);
    }
  }

  const observations = run.server_observations ?? [];
  const observedPaths = new Set(observations.map(item => item.path));
  for (const expected of [
    `/cold/${run.network_session}/`,
    "/service_worker_cache.js",
    "/upload_benchmark.html",
    "/pkg-web/client_wasm.js",
    "/pkg-web/client_wasm_bg.wasm",
  ]) {
    if (!observedPaths.has(expected)) failures.push(`server observation missing for ${expected}`);
  }
  if (observations.length !== 5 || observations.some(item => item.bytes_sent <= 0)) {
    failures.push("cold install did not fetch exactly the page, worker, HTML, JavaScript, and WASM from the server");
  }
  if (failures.length) throw new Error(`cold service-worker run ${index} invalid:\n- ${failures.join("\n- ")}`);
}

function validateServiceWorkerUpdateRun(run, index) {
  const failures = [];
  if (run.schema_version !== 1
    || run.kind !== "service-worker-update-single-run"
    || run.label !== options.label) {
    failures.push("invalid service-worker update identity");
  }
  if (!run.network_session
    || run.environment?.service_worker !== true
    || run.service_worker?.controlled !== true
    || run.service_worker?.state !== "activated"
    || run.service_worker?.initial_byte_version !== 1
    || run.service_worker?.updated_byte_version !== 2) {
    failures.push("page did not observe byte versions 1 then 2 under an active controller");
  }
  if (run.service_worker?.scope !== new URL("./", run.environment?.href ?? "http://localhost/").href) {
    failures.push("service-worker scope does not match the unique update page");
  }
  if (!run.service_worker?.cache_name?.includes(run.network_session ?? "")) {
    failures.push("service-worker cache name is not run-specific");
  }
  for (const key of [
    "initial_register_ms",
    "initial_version_query_ms",
    "update_call_ms",
    "updated_activation_ms",
    "updated_version_query_ms",
    "total_ms",
  ]) {
    if (!Number.isFinite(run.initialization?.[key]) || run.initialization[key] < 0) {
      failures.push(`invalid ${key}`);
    }
  }
  const expectedSizes = new Map([
    ["html", 6827],
    ["javascript", 18618],
    ["wasm", 247743],
  ]);
  for (const [field, expectedCount] of [["initial_cache_entries", 3], ["updated_cache_entries", 3]]) {
    const entries = new Map((run[field] ?? []).map(entry => [entry.name, entry]));
    if (entries.size !== expectedCount) failures.push(`${field} count is not three`);
    for (const [name, expectedBytes] of expectedSizes) {
      if (entries.get(name)?.response_bytes !== expectedBytes || entries.get(name)?.ok !== true) {
        failures.push(`${field} ${name} entry is missing or has unexpected bytes`);
      }
    }
  }

  const observations = run.server_observations ?? [];
  const observedPaths = new Set(observations.map(item => item.path));
  if (!observedPaths.has(`/update/${run.network_session}/`)) failures.push("server observation missing update page");
  for (const expected of ["/upload_benchmark.html", "/pkg-web/client_wasm.js", "/pkg-web/client_wasm_bg.wasm"]) {
    if (observations.filter(item => item.path === expected).length !== 2) {
      failures.push(`${expected} was not fetched once for each worker generation`);
    }
  }
  const scriptVersions = observations
    .filter(item => item.path === "/service_worker_cache.js")
    .map(item => item.service_worker_byte_version)
    .sort();
  if (JSON.stringify(scriptVersions) !== JSON.stringify([1, 2])) {
    failures.push("server did not observe byte-different worker versions 1 and 2");
  }
  if (failures.length) throw new Error(`service-worker update run ${index} invalid:\n- ${failures.join("\n- ")}`);
}

function validateHttpCacheReuseRun(run, index, seed = false) {
  const failures = [];
  if (run.schema_version !== 1
    || run.kind !== "http-cache-reuse-upload-single-run"
    || run.label !== options.label) {
    failures.push("invalid HTTP-cache identity");
  }
  if (!run.network_session
    || run.environment?.service_worker !== false
    || run.environment?.http_cache_reuse !== true) {
    failures.push("run does not identify normal browser HTTP-cache reuse");
  }
  if (run.proof?.n !== 52 || run.proof?.k !== 13 || run.proof?.samples !== 1) failures.push("unexpected proof grid");
  if (run.proof?.proof_bytes !== 21781) failures.push("proof byte size mismatch");
  if (run.proof?.statement_bytes !== 5969) failures.push("statement byte size mismatch");
  if (run.proof?.bundle_bytes !== 27750) failures.push("bundle byte size mismatch");
  const resources = new Map((run.resources ?? []).map(resource => [resource.name, resource]));
  for (const name of ["html", "javascript", "wasm"]) {
    if (!resources.has(name)) failures.push(`${name} resource timing missing`);
  }
  for (const [name, resource] of resources) {
    if (!Number.isFinite(resource.transfer_size) || resource.transfer_size < 0) failures.push(`${name} transfer size invalid`);
  }
  if (seed) {
    if (resources.get("javascript")?.transfer_size === 0 || resources.get("wasm")?.transfer_size === 0) {
      failures.push("seed run did not populate the browser HTTP cache");
    }
  } else {
    for (const name of ["html", "javascript", "wasm"]) {
      if (resources.get(name)?.transfer_size !== 0) failures.push(`${name} was not reused from the browser HTTP cache`);
    }
  }
  const observations = run.server_observations ?? [];
  const uploadObservations = observations.filter(item => item.direction === "browser-to-server");
  if (uploadObservations.length !== 1
    || uploadObservations[0]?.bytes_received !== 27750
    || uploadObservations[0]?.verified !== true) {
    failures.push("server upload observation is missing or invalid");
  }
  const staticObservations = observations.filter(item => item.direction !== "browser-to-server");
  if (!seed && staticObservations.length !== 0) {
    failures.push("warm HTTP-cache run unexpectedly fetched static assets from the server");
  }
  if (run.upload?.request_bytes !== 27750
    || run.upload?.server_received_bytes !== 27750
    || run.upload?.server_accepted !== true
    || run.upload?.server_verified !== true) {
    failures.push("server did not accept and verify upload");
  }
  if (failures.length) throw new Error(`HTTP-cache run ${index}${seed ? " (seed)" : ""} invalid:\n- ${failures.join("\n- ")}`);
}

function validateRun(run, index) {
  if (options.httpCacheReuse) {
    validateHttpCacheReuseRun(run, index, index === 0);
    return;
  }
  if (options.coldServiceWorker) {
    validateColdServiceWorkerRun(run, index);
    return;
  }
  if (options.serviceWorkerUpdate) {
    validateServiceWorkerUpdateRun(run, index);
    return;
  }
  const failures = [];
  const expectedKind = options.serviceWorker
    ? "warm-service-worker-upload-single-run"
    : options.upload
      ? "cold-network-upload-single-run"
      : "cold-network-single-run";
  if (run.schema_version !== 1 || run.kind !== expectedKind) failures.push("invalid run identity");
  if (run.label !== options.label) failures.push("label mismatch");
  if (!run.network_session) failures.push("network session missing");
  if (!run.environment?.user_agent) failures.push("user agent missing");
  if (run.proof?.n !== 52 || run.proof?.k !== 13 || run.proof?.samples !== 1) failures.push("unexpected proof grid");
  if (run.proof?.proof_bytes !== 21781) failures.push("proof byte size mismatch");
  if (run.proof?.statement_bytes !== 5969) failures.push("statement byte size mismatch");
  if (run.proof?.bundle_bytes !== 27750) failures.push("bundle byte size mismatch");
  const resources = new Map((run.resources ?? []).map(resource => [resource.name, resource]));
  for (const name of ["html", "javascript", "wasm"]) {
    if (!resources.has(name)) failures.push(`${name} resource timing missing`);
  }
  for (const [name, resource] of resources) {
    if (!Number.isFinite(resource.transfer_size) || resource.transfer_size < 0) failures.push(`${name} transfer size invalid`);
    if (!Number.isFinite(resource.duration_ms) || resource.duration_ms < 0) failures.push(`${name} duration invalid`);
  }
  if (options.serviceWorker) {
    if (run.service_worker?.enabled !== true
      || !run.service_worker.controller_script_url?.endsWith("/service_worker_cache.js")
      || !run.service_worker.scope?.endsWith("/")) {
      failures.push("service worker does not control the measured page");
    }
    for (const name of ["html", "javascript", "wasm"]) {
      if (resources.get(name)?.transfer_size !== 0) failures.push(`${name} was not served from the service-worker cache`);
    }
  } else {
    if (resources.get("javascript")?.transfer_size === 0) failures.push("JavaScript transfer size is zero; cache disabling may have failed");
    if (resources.get("wasm")?.transfer_size === 0) failures.push("WASM transfer size is zero; cache disabling may have failed");
  }

  const observations = run.server_observations ?? [];
  const observedPaths = new Set(observations.map(item => item.path));
  const expectedPage = options.upload ? "/upload_benchmark.html" : "/network_benchmark.html";
  const expectedStaticPaths = options.serviceWorker
    ? []
    : [expectedPage, "/pkg-web/client_wasm.js", "/pkg-web/client_wasm_bg.wasm"];
  for (const expected of expectedStaticPaths) {
    if (!observedPaths.has(expected)) failures.push(`server observation missing for ${expected}`);
  }
  if (!options.serviceWorker && observations.some(item => item.bytes_sent <= 0)) failures.push("server observation has zero bytes");
  if (options.upload) {
    if (run.upload?.request_bytes !== 27750) failures.push("upload request size mismatch");
    if (run.upload?.server_received_bytes !== 27750) failures.push("server upload size mismatch");
    if (run.upload?.server_accepted !== true || run.upload?.server_verified !== true) failures.push("server did not accept and verify upload");
    if (!Number.isFinite(run.upload?.upload_wall_ms) || run.upload.upload_wall_ms < 0) failures.push("upload wall timing invalid");
    if (!Number.isFinite(run.upload?.resource_transfer_size) || run.upload.resource_transfer_size <= 0) failures.push("upload resource transfer size invalid");
    const uploadObservations = observations.filter(item => item.direction === "browser-to-server");
    const staticObservations = observations.filter(item => item.direction !== "browser-to-server");
    if (uploadObservations.length !== 1 || uploadObservations[0].bytes_received !== 27750 || uploadObservations[0].verified !== true) {
      failures.push("server upload observation is missing or invalid");
    }
    if (options.serviceWorker) {
      if (staticObservations.length !== 0) failures.push("service-worker run unexpectedly downloaded static assets from the server");
    } else if (staticObservations.length !== 3 || staticObservations.some(item => item.bytes_sent <= 0)) {
      failures.push("static download observations changed unexpectedly");
    }
  }
  if (failures.length) throw new Error(`network run ${index} invalid:\n- ${failures.join("\n- ")}`);
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

async function main() {
  for (const required of [
    serverScript,
    options.coldServiceWorker
      ? coldServiceWorkerPage
      : options.serviceWorkerUpdate
        ? serviceWorkerUpdatePage
        : options.httpCacheReuse
          ? httpCachePage
        : options.upload
          ? uploadPage
          : networkPage,
    ...(options.serviceWorker && !options.coldServiceWorker ? [serviceWorkerBootstrapPage] : []),
    ...(options.serviceWorker ? [serviceWorkerScript] : []),
    ...(options.httpCacheReuse ? [nodeVerifierModule] : []),
    webModule,
    webWasm,
    ...(options.upload && !options.remoteServerUrl ? [nodeVerifierModule] : []),
  ]) {
    if (!await stat(required).then(info => info.isFile()).catch(() => false)) {
      throw new Error(`missing required file: ${required}`);
    }
  }
  await mkdir(options.outputDir, {recursive: true});
  const browserExecutable = await resolveBrowser();
  if (options.remoteServerUrl) {
    await runRemoteUploadBenchmark(browserExecutable);
    return;
  }
  const port = 20000 + Math.floor(Math.random() * 25000);
  const tlsDir = options.tls
    ? await mkdtemp(path.join(tmpdir(), "poker-network-tls-"))
    : null;
  const tlsCert = tlsDir ? path.join(tlsDir, "cert.pem") : "";
  const tlsKey = tlsDir ? path.join(tlsDir, "key.pem") : "";
  if (options.tls) {
    await runOpenSsl([
      "req", "-x509", "-newkey", "rsa:2048",
      "-keyout", tlsKey, "-out", tlsCert, "-days", "1", "-nodes",
      "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost",
    ]);
  }
  const server = spawn(process.execPath, [
    serverScript,
    "--host", "127.0.0.1",
    "--port", String(port),
    "--output-dir", options.outputDir,
    "--cache-control", options.httpCacheReuse
      ? "public,max-age=31536000,immutable"
      : "no-store",
    ...(options.tls ? ["--tls", "1", "--tls-cert", tlsCert, "--tls-key", tlsKey] : []),
  ], {stdio: ["ignore", "pipe", "pipe"]});
  let serverError = "";
  server.stdout.on("data", chunk => process.stdout.write(`[server] ${chunk}`));
  server.stderr.on("data", chunk => {
    serverError += chunk;
    process.stderr.write(`[server-error] ${chunk}`);
  });

  const profileDir = await mkdtemp(path.join(tmpdir(), "poker-network-profile-"));
  let chrome;
  let cdp;
  const generatedRunFiles = [];
  try {
    const baseUrl = `${options.tls ? "https" : "http"}://127.0.0.1:${port}`;
    let serverReady = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (server.exitCode !== null) throw new Error(`benchmark server exited early: ${serverError}`);
      if (await fetch(`${baseUrl}/network_benchmark.html`, {method: "HEAD"}).then(response => response.ok).catch(() => false)) {
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
      "--disable-keep-alive",
      "--remote-allow-origins=*",
      "--headless=new",
      "--disable-gpu",
      ...(options.tls ? ["--ignore-certificate-errors"] : []),
    ];
    chrome = spawn(browserExecutable, chromeArgs, {stdio: ["ignore", "pipe", "pipe"]});
    let chromeError = "";
    chrome.stderr.on("data", chunk => {
      chromeError += chunk;
    });
    const devtoolsPortFile = path.join(profileDir, "DevToolsActivePort");
    await waitForFile(devtoolsPortFile, 15_000);
    const [debugPort] = await readLines(devtoolsPortFile);
    const version = await fetchJson(`http://127.0.0.1:${debugPort}/json/version`);
    cdp = new CdpConnection(version.webSocketDebuggerUrl);
    await cdp.connect();
    const browserInfo = await cdp.send("Browser.getVersion");
    const safeLabel = options.label.replace(/[^\w.-]+/g, "-");
    const runs = [];

    if (options.serviceWorker && !options.coldServiceWorker && !options.serviceWorkerUpdate) {
      const bootstrapTarget = await cdp.send("Target.createTarget", {url: "about:blank"});
      const bootstrapAttached = await cdp.send("Target.attachToTarget", {
        targetId: bootstrapTarget.targetId,
        flatten: true,
      });
      await cdp.send("Page.enable", {}, bootstrapAttached.sessionId);
      await cdp.send("Page.navigate", {
        url: `${baseUrl}/service_worker_bootstrap.html?label=${encodeURIComponent(options.label)}`,
      }, bootstrapAttached.sessionId);
      const bootstrapStatus = await waitForPageStatus(cdp, bootstrapAttached.sessionId);
      console.log(`[network-runner] ${bootstrapStatus}`);
      await cdp.send("Target.closeTarget", {targetId: bootstrapTarget.targetId}).catch(() => undefined);
    }

    const totalIterations = options.httpCacheReuse ? options.runs + 1 : options.runs;
    for (let index = 0; index < totalIterations; index += 1) {
      const httpCacheSeed = options.httpCacheReuse && index === 0;
      const session = randomUUID();
      const existingFiles = new Set(await readdir(options.outputDir).catch(() => []));
      const target = await cdp.send("Target.createTarget", {url: "about:blank"});
      const attached = await cdp.send("Target.attachToTarget", {
        targetId: target.targetId,
        flatten: true,
      });
      const sessionId = attached.sessionId;
      const pageErrors = [];
      const listener = event => {
        if (event.sessionId !== sessionId) return;
        if (event.method === "Runtime.exceptionThrown") {
          pageErrors.push(event.params.exceptionDetails?.text ?? "page exception");
        }
      };
      cdp.listeners.add(listener);
      await cdp.send("Network.enable", {}, sessionId);
      await cdp.send("Page.enable", {}, sessionId);
      if (options.httpCacheReuse) {
        if (httpCacheSeed) await cdp.send("Network.clearBrowserCache", {}, sessionId);
        await cdp.send("Network.setCacheDisabled", {cacheDisabled: false}, sessionId);
        await cdp.send("Network.setBypassServiceWorker", {bypass: true}, sessionId);
        await cdp.send("Network.setCookie", {
          name: "poker_network_session",
          value: session,
          url: baseUrl,
        }, sessionId);
        await cdp.send("Network.setCookie", {
          name: "poker_network_label",
          value: options.label,
          url: baseUrl,
        }, sessionId);
      } else if (options.coldServiceWorker || options.serviceWorkerUpdate) {
        await cdp.send("Network.clearBrowserCache", {}, sessionId);
        await cdp.send("Network.setCacheDisabled", {cacheDisabled: true}, sessionId);
        await cdp.send("Network.setBypassServiceWorker", {bypass: false}, sessionId);
      } else if (options.serviceWorker) {
        await cdp.send("Network.setCacheDisabled", {cacheDisabled: false}, sessionId);
        await cdp.send("Network.setBypassServiceWorker", {bypass: false}, sessionId);
      } else {
        await cdp.send("Network.clearBrowserCache", {}, sessionId);
        await cdp.send("Network.setCacheDisabled", {cacheDisabled: true}, sessionId);
        await cdp.send("Network.setBypassServiceWorker", {bypass: true}, sessionId);
      }
      const pagePath = options.coldServiceWorker
        ? `cold/${session}/`
        : options.serviceWorkerUpdate
          ? `update/${session}/`
        : options.httpCacheReuse
          ? "http_cache_benchmark.html"
          : options.upload
            ? "upload_benchmark.html"
            : "network_benchmark.html";
      const pageUrl = options.httpCacheReuse
        ? `${baseUrl}/${pagePath}`
        : `${baseUrl}/${pagePath}?label=${encodeURIComponent(options.label)}&network_session=${session}${options.serviceWorker && !options.coldServiceWorker && !options.serviceWorkerUpdate ? "&service_worker=1" : ""}`;
      await cdp.send("Page.navigate", {url: pageUrl}, sessionId);
      const {path: runPath, filename} = await waitForNetworkRun(
        cdp,
        sessionId,
        options.outputDir,
        existingFiles,
        safeLabel,
        session,
        options.timeoutMs,
      );
      if (pageErrors.length) throw new Error(`network page exception: ${pageErrors[0]}`);
      const run = JSON.parse(await readFile(runPath, "utf8"));
      validateRun(run, options.httpCacheReuse ? index : index);
      generatedRunFiles.push(runPath);
      if (httpCacheSeed) {
        console.log(`[network-runner] seeded browser HTTP cache from one full upload load`);
        cdp.listeners.delete(listener);
        await cdp.send("Target.closeTarget", {targetId: target.targetId}).catch(() => undefined);
        continue;
      }
      run.run_index = index;
      runs.push(run);
      const serverBytes = run.server_observations.reduce(
        (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
        0,
      );
      if (options.coldServiceWorker) {
        console.log(`[network-runner] cold install ${index}/${options.runs}: register=${run.initialization.register_ms.toFixed(1)}ms ready=${run.initialization.ready_ms.toFixed(1)}ms server=${serverBytes}B`);
      } else if (options.serviceWorkerUpdate) {
        console.log(`[network-runner] update ${index}/${options.runs}: initial=${run.initialization.initial_register_ms.toFixed(1)}ms update=${run.initialization.update_call_ms.toFixed(1)}ms server=${serverBytes}B`);
      } else if (options.httpCacheReuse) {
        console.log(`[network-runner] HTTP-cache reuse ${run.run_index}/${options.runs}: browser-transfer=${run.resources.reduce((sum, item) => sum + item.transfer_size, 0)}B upload=${run.upload?.request_bytes ?? 0}B`);
      } else {
        console.log(`[network-runner] run ${index}/${options.runs}: download-transfer=${run.resources.reduce((sum, item) => sum + item.transfer_size, 0)}B server=${serverBytes}B upload=${run.upload?.request_bytes ?? 0}B`);
      }
      cdp.listeners.delete(listener);
      await cdp.send("Target.closeTarget", {targetId: target.targetId}).catch(() => undefined);
    }

    const metric = run => {
      if (options.coldServiceWorker) {
        return {
          register_ms: run.initialization.register_ms,
          ready_ms: run.initialization.ready_ms,
          controller_ms: run.initialization.controller_ms,
          total_ms: run.initialization.total_ms,
          cached_bytes_total: run.cache_entries.reduce((sum, item) => sum + item.response_bytes, 0),
          server_bytes_total: run.server_observations.reduce(
            (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
            0,
          ),
          server_observation_count: run.server_observations.length,
        };
      }
      if (options.serviceWorkerUpdate) {
        return {
          initial_register_ms: run.initialization.initial_register_ms,
          initial_version_query_ms: run.initialization.initial_version_query_ms,
          update_call_ms: run.initialization.update_call_ms,
          updated_activation_ms: run.initialization.updated_activation_ms,
          updated_version_query_ms: run.initialization.updated_version_query_ms,
          total_ms: run.initialization.total_ms,
          initial_cached_bytes_total: run.initial_cache_entries.reduce((sum, item) => sum + item.response_bytes, 0),
          updated_cached_bytes_total: run.updated_cache_entries.reduce((sum, item) => sum + item.response_bytes, 0),
          server_bytes_total: run.server_observations.reduce(
            (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
            0,
          ),
          server_observation_count: run.server_observations.length,
        };
      }
      return {
        browser_transfer_bytes_total: run.resources.reduce((sum, item) => sum + item.transfer_size, 0),
        server_bytes_total: run.server_observations.reduce(
          (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
          0,
        ),
        wasm_transfer_bytes: run.resources.find(item => item.name === "wasm")?.transfer_size ?? 0,
        javascript_transfer_bytes: run.resources.find(item => item.name === "javascript")?.transfer_size ?? 0,
        html_transfer_bytes: run.resources.find(item => item.name === "html")?.transfer_size ?? 0,
        wasm_duration_ms: run.resources.find(item => item.name === "wasm")?.duration_ms ?? 0,
        wasm_initialized_ms: run.initialization.wasm_initialized_relative_ms - run.initialization.script_start_relative_ms,
        prove_ms: run.proof.prove_ms,
        verify_ms: run.proof.verify_ms,
        outer_call_ms: run.proof.outer_call_ms,
        navigation_response_start_ms: run.navigation.response_start_ms,
        dom_content_loaded_ms: run.navigation.dom_content_loaded_ms,
        load_event_end_ms: run.navigation.load_event_end_ms,
        upload_request_bytes: run.upload?.request_bytes ?? 0,
        upload_wall_ms: run.upload?.upload_wall_ms ?? 0,
        upload_resource_duration_ms: run.upload?.resource_duration_ms ?? 0,
        upload_resource_transfer_bytes: run.upload?.resource_transfer_size ?? 0,
      };
    };
    const firstMetrics = metric(runs[0]);
    const summary = Object.fromEntries(
      Object.keys(firstMetrics).map(key => [key, summarize(runs.map(run => metric(run)[key]))]),
    );
    const aggregate = {
      schema_version: 1,
      kind: options.coldServiceWorker
        ? "cold-service-worker-install-aggregate"
        : options.serviceWorkerUpdate
        ? "service-worker-update-aggregate"
        : options.httpCacheReuse
        ? "http-cache-reuse-upload-aggregate"
        : options.serviceWorker
        ? "warm-service-worker-upload-aggregate"
        : options.upload
          ? "cold-network-upload-aggregate"
          : "cold-network-aggregate",
      label: options.label,
      run_count: runs.length,
      environment: runs[0].environment,
      collection: {
        protocol: "Chrome DevTools Protocol",
        browser_executable: browserExecutable,
        browser_version: firstBrowserSession.browserInfo.product,
        user_agent_version: firstBrowserSession.version["User-Agent"],
        headless: true,
        cache_disabled: options.coldServiceWorker || options.serviceWorkerUpdate || (!options.httpCacheReuse && !options.serviceWorker),
        browser_cache_cleared_before_each_run: options.coldServiceWorker || options.serviceWorkerUpdate || (!options.httpCacheReuse && !options.serviceWorker),
        service_worker_enabled: options.serviceWorker,
        service_worker_bypassed: !options.serviceWorker,
        service_worker_warm_before_measured_runs: options.serviceWorker && !options.coldServiceWorker && !options.serviceWorkerUpdate,
        cold_service_worker_unique_scope_and_cache_per_run: options.coldServiceWorker,
        service_worker_update_unique_scope_and_cache_per_run: options.serviceWorkerUpdate,
        http_cache_seeded_before_measured_runs: options.httpCacheReuse,
        measured_runs_reuse_browser_http_cache: options.httpCacheReuse,
        browser_http_cache_cleared_before_seed_only: options.httpCacheReuse,
        measured_runs_have_browser_http_cache_enabled: options.httpCacheReuse,
        chrome_arguments: chromeArgs,
        network_path: options.tls
          ? "HTTPS/TLS loopback to 127.0.0.1"
          : "HTTP loopback to 127.0.0.1",
        proof_upload_verified: options.upload,
        scope: options.coldServiceWorker
          ? "cold service-worker installation in a unique scope with a unique cache name for each run; HTML/JavaScript/WASM are fetched from the server during install and browser HTTP cache is disabled; not service-worker update invalidation, browser HTTP-cache behavior, TLS, LAN, or Internet"
          : options.serviceWorkerUpdate
          ? "same-URL service-worker update from byte version 1 to byte-different version 2 in a unique scope; both generations install HTML/JavaScript/WASM, the new worker activates and controls the page, and browser HTTP cache is disabled; not browser HTTP-cache behavior, TLS, LAN, or Internet"
          : options.serviceWorker
          ? "warm service-worker cache hits for HTML/JavaScript/WASM plus cryptographically verified binary proof upload over HTTP loopback; proof upload and result submission bypass the cache; not cold service-worker install, browser HTTP-cache behavior, cold TCP, TLS, LAN, or Internet"
          : options.tls
            ? "cache-disabled TLS loopback code download plus cryptographically verified binary proof upload with a temporary self-signed certificate and Chrome certificate-error bypass; not public PKI, LAN, or Internet"
            : options.httpCacheReuse
              ? "normal browser HTTP-cache reuse after one immutable seed load: measured HTML/JavaScript/WASM transfers are zero, while each proof upload bypasses the cache and is cryptographically verified; not service-worker Cache Storage, TLS, LAN, or Internet"
              : options.upload
                ? "cache-disabled local-loopback code download plus cryptographically verified binary proof upload; not cold TCP connection, LAN, or Internet"
                : "cache-disabled local-loopback network load; not a cold TCP connection, LAN, or Internet measurement",
        node: process.version,
        recorded_at: new Date().toISOString(),
      },
      summary,
      runs,
    };
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const outputPath = path.join(options.outputDir, `network_${safeLabel}_${stamp}.json`);
    await writeFile(outputPath, `${JSON.stringify(aggregate, null, 2)}\n`);
    await Promise.all(generatedRunFiles.map(file => rm(file, {force: true})));
    console.log(`[network-runner] validated and aggregated ${runs.length} runs into ${outputPath}`);

    cdp.close();
    cdp = undefined;
    chrome.kill("SIGTERM");
    await new Promise(resolve => chrome.once("exit", resolve));
    chrome = undefined;
    server.kill("SIGTERM");
    await new Promise(resolve => server.once("exit", resolve));
    await removeProfile(profileDir);
    if (tlsDir) await rm(tlsDir, {recursive: true, force: true});
  } catch (error) {
    cdp?.close();
    chrome?.kill("SIGTERM");
    server.kill("SIGTERM");
    await Promise.all(generatedRunFiles.map(file => rm(file, {force: true}).catch(() => undefined)));
    await removeProfile(profileDir).catch(() => undefined);
    if (tlsDir) await rm(tlsDir, {recursive: true, force: true}).catch(() => undefined);
    throw error;
  }
}

async function runRemoteUploadBenchmark(browserExecutable) {
  await mkdir(options.outputDir, {recursive: true});
  const serverUrl = new URL(options.remoteServerUrl);
  let tlsCertificate = null;
  if (serverUrl.protocol === "https:" && options.requireValidCertificate) {
    tlsCertificate = await inspectRemoteCertificate(serverUrl, Math.min(options.timeoutMs, 15_000));
    console.log(`[network-runner] TLS certificate authorized: issuer=${tlsCertificate.issuer_organization ?? tlsCertificate.issuer_common_name ?? "unknown"} fingerprint=${tlsCertificate.sha256_fingerprint}`);
  }
  let browserSession;
  let firstBrowserSession;
  const runs = [];
  try {
    if (serverUrl.protocol === "http:") {
      const health = await fetch(new URL("/upload_benchmark.html", serverUrl), {method: "HEAD"})
        .then(response => response.ok)
        .catch(() => false);
      if (!health) throw new Error(`remote benchmark server is not reachable at ${serverUrl.origin}`);
    }
    if (!options.coldBrowserProcess) {
      const profileDir = await mkdtemp(path.join(tmpdir(), "poker-remote-network-profile-"));
      browserSession = await startRemoteBrowser(browserExecutable, profileDir);
      firstBrowserSession = browserSession;
    }

    for (let index = 0; index < options.runs; index += 1) {
      if (options.coldBrowserProcess) {
        const profileDir = await mkdtemp(path.join(tmpdir(), "poker-remote-network-profile-"));
        browserSession = await startRemoteBrowser(browserExecutable, profileDir);
        if (!firstBrowserSession) firstBrowserSession = browserSession;
      }
      const {chrome, cdp} = browserSession;
      const session = randomUUID();
      const target = await cdp.send("Target.createTarget", {url: "about:blank"});
      const attached = await cdp.send("Target.attachToTarget", {
        targetId: target.targetId,
        flatten: true,
      });
      const sessionId = attached.sessionId;
      const pageErrors = [];
      const listener = event => {
        if (event.sessionId !== sessionId) return;
        if (event.method === "Runtime.exceptionThrown") {
          pageErrors.push(event.params.exceptionDetails?.text ?? "page exception");
        }
      };
      cdp.listeners.add(listener);
      await cdp.send("Network.enable", {}, sessionId);
      await cdp.send("Page.enable", {}, sessionId);
      await cdp.send("Network.clearBrowserCache", {}, sessionId);
      await cdp.send("Network.setCacheDisabled", {cacheDisabled: true}, sessionId);
      await cdp.send("Network.setBypassServiceWorker", {bypass: true}, sessionId);
      await cdp.send("Network.setCookie", {
        name: "poker_network_session",
        value: session,
        url: serverUrl.origin,
      }, sessionId);
      await cdp.send("Network.setCookie", {
        name: "poker_network_label",
        value: options.label,
        url: serverUrl.origin,
      }, sessionId);
      await cdp.send("Page.navigate", {
        url: `${serverUrl.origin}/upload_benchmark.html?label=${encodeURIComponent(options.label)}&network_session=${session}`,
      }, sessionId);
      const filename = await waitForRemoteNetworkRun(cdp, sessionId, options.timeoutMs);
      if (pageErrors.length) throw new Error(`remote network page exception: ${pageErrors[0]}`);
      const resultResponse = await fetch(`${serverUrl.origin}/network-run/${encodeURIComponent(filename)}`);
      if (!resultResponse.ok) throw new Error(`remote result ${filename} returned ${resultResponse.status}`);
      const run = await resultResponse.json();
      run.run_index = index;
      validateRun(run, index);
      runs.push(run);
      console.log(`[network-runner] remote run ${index + 1}/${options.runs}: download-transfer=${run.resources.reduce((sum, item) => sum + item.transfer_size, 0)}B upload=${run.upload?.request_bytes ?? 0}B wall=${run.upload.upload_wall_ms.toFixed(1)}ms`);
      cdp.listeners.delete(listener);
      await cdp.send("Target.closeTarget", {targetId: target.targetId}).catch(() => undefined);
      if (options.coldBrowserProcess) {
        await stopRemoteBrowser(browserSession);
        browserSession = undefined;
      }
    }

    const metric = run => ({
      browser_transfer_bytes_total: run.resources.reduce((sum, item) => sum + item.transfer_size, 0),
      server_bytes_total: run.server_observations.reduce(
        (sum, item) => sum + (item.bytes_sent ?? item.bytes_received ?? 0),
        0,
      ),
      wasm_transfer_bytes: run.resources.find(item => item.name === "wasm")?.transfer_size ?? 0,
      javascript_transfer_bytes: run.resources.find(item => item.name === "javascript")?.transfer_size ?? 0,
      html_transfer_bytes: run.resources.find(item => item.name === "html")?.transfer_size ?? 0,
      wasm_duration_ms: run.resources.find(item => item.name === "wasm")?.duration_ms ?? 0,
      wasm_initialized_ms: run.initialization.wasm_initialized_relative_ms - run.initialization.script_start_relative_ms,
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
    });
    const firstMetrics = metric(runs[0]);
    const summary = Object.fromEntries(
      Object.keys(firstMetrics).map(key => [key, summarize(runs.map(run => metric(run)[key]))]),
    );
    const certificateValidation = serverUrl.protocol === "https:"
      ? (options.allowInvalidCertificate
        ? "browser_certificate_errors_ignored"
        : "browser_validated_certificate_chain")
      : "none_unencrypted_http";
    const aggregate = {
      schema_version: 1,
      kind: "remote-network-upload-aggregate",
      label: options.label,
      run_count: runs.length,
      environment: runs[0].environment,
      collection: {
        protocol: "Chrome DevTools Protocol",
        browser_executable: browserExecutable,
        browser_version: firstBrowserSession.browserInfo.product,
        user_agent_version: firstBrowserSession.version["User-Agent"],
        headless: true,
        cache_disabled: true,
        browser_cache_cleared_before_each_run: true,
        service_worker_enabled: false,
        service_worker_bypassed: true,
        remote_mode: true,
        remote_server_url: serverUrl.origin,
        declared_network_class: options.networkClass,
        transport: serverUrl.protocol === "https:" ? "HTTPS" : "HTTP",
        certificate_validation: certificateValidation,
        require_valid_certificate: options.requireValidCertificate,
        tls_certificate: tlsCertificate,
        public_pki_claimed: false,
        cold_tcp_isolated: options.coldBrowserProcess,
        browser_process_reused_across_runs: !options.coldBrowserProcess,
        new_browser_process_and_profile_per_run: options.coldBrowserProcess,
        browser_process_exit_confirmed_between_runs: options.coldBrowserProcess,
        chrome_arguments: firstBrowserSession.chromeArgs,
        network_path: `${serverUrl.protocol.toUpperCase()} remote origin ${serverUrl.host}`,
        proof_upload_verified: true,
        remote_loopback_smoke: options.remoteLoopbackSmoke,
        scope: options.remoteLoopbackSmoke
          ? "remote-server plumbing smoke test over a loopback hostname; explicitly not LAN, Internet, public-PKI, cold-TCP, mobile, or deployment evidence"
          : `cache-disabled remote-${options.networkClass} code download plus cryptographically verified binary proof upload; certificate validation is browser-chain validation${options.requireValidCertificate ? " plus Node system-store chain and hostname validation" : ""}, but the result does not by itself establish a public CA or deployment identity; ${options.coldBrowserProcess ? "each run uses a new browser process and temporary profile, and the prior process exits before the next run, isolating browser TCP state" : "the browser process is reused and TCP connections are not isolated, so this is not a cold-TCP measurement"}`,
        node: process.version,
        recorded_at: new Date().toISOString(),
      },
      summary,
      runs,
    };
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const outputPath = path.join(options.outputDir, `network_${options.label}_${stamp}.json`);
    await writeFile(outputPath, `${JSON.stringify(aggregate, null, 2)}\n`);
    console.log(`[network-runner] validated and aggregated ${runs.length} remote runs into ${outputPath}`);
    await stopRemoteBrowser(browserSession);
    browserSession = undefined;
  } catch (error) {
    await stopRemoteBrowser(browserSession).catch(() => undefined);
    browserSession = undefined;
    throw error;
  }
}

const invokedDirectly = Boolean(process.argv[1])
  && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (invokedDirectly) {
  main().catch(error => {
    console.error(`[network-runner] ${error?.stack ?? error}`);
    process.exit(1);
  });
}
