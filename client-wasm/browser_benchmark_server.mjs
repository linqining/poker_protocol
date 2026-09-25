#!/usr/bin/env node
import { createServer as createHttpServer } from "node:http";
import { createServer as createHttpsServer } from "node:https";
import { createReadStream, readFileSync } from "node:fs";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { networkInterfaces } from "node:os";
import { createHash, randomUUID } from "node:crypto";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const options = {
  host: "127.0.0.1",
  port: 4173,
  outputDir: path.resolve(root, "../.repro/browser"),
  cacheControl: "no-store",
  tls: false,
  tlsCert: "",
  tlsKey: "",
};

const networkObservations = new Map();
let bundleVerifierPromise;

async function verifyUploadedBundle(bytes) {
  bundleVerifierPromise ??= import("./pkg/client_wasm.js").then(async verifier => {
    return verifier.verify_reconstruction_bundle;
  });
  const verify = await bundleVerifierPromise;
  verify(bytes);
}

for (let index = 0; index < args.length; index += 2) {
  const key = args[index];
  const value = args[index + 1];
  if (value === undefined) usage("option values are required");
  if (key === "--host") options.host = value;
  else if (key === "--port") options.port = Number(value);
  else if (key === "--output-dir") options.outputDir = path.resolve(value);
  else if (key === "--cache-control") options.cacheControl = value;
  else if (key === "--tls") options.tls = value === "1" || value === "true";
  else if (key === "--tls-cert") options.tlsCert = value;
  else if (key === "--tls-key") options.tlsKey = value;
  else usage(`unknown option ${key}`);
}
if (!Number.isInteger(options.port) || options.port < 1 || options.port > 65535) {
  usage("--port must be an integer from 1 through 65535");
}
if (options.tls && (!options.tlsCert || !options.tlsKey)) {
  usage("--tls 1 requires --tls-cert CERT and --tls-key KEY");
}

function usage(message) {
  if (message) console.error(`error: ${message}`);
  console.error(`usage: ${path.basename(process.argv[1])} [--host HOST] [--port PORT] [--output-dir DIR] [--tls 0|1] [--tls-cert CERT --tls-key KEY]`);
  process.exit(message ? 2 : 0);
}

const mediaTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".wasm", "application/wasm"],
  [".css", "text/css; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".ico", "image/vnd.microsoft.icon"],
]);

function sessionFromRequest(request) {
  const url = new URL(request.url, "http://localhost");
  const querySession = url.searchParams.get("network_session");
  if (querySession && /^[\w-]{1,128}$/.test(querySession)) return querySession;
  const cookie = request.headers.cookie ?? "";
  const match = cookie.match(/(?:^|;\s*)poker_network_session=([\w-]+)/);
  return match?.[1] ?? null;
}

async function serveFile(request, response) {
  const url = new URL(request.url, "http://localhost");
  const requestPath = decodeURIComponent(url.pathname);
  const coldServiceWorkerMatch = requestPath.match(/^\/cold\/[\w-]+\/?$/);
  const updateServiceWorkerMatch = requestPath.match(/^\/update\/[\w-]+\/?$/);
  const relativePath = requestPath === "/"
    ? "browser_benchmark.html"
    : coldServiceWorkerMatch
      ? "service_worker_cold_benchmark.html"
      : updateServiceWorkerMatch
        ? "service_worker_update_benchmark.html"
      : `.${requestPath}`;
  const filePath = path.normalize(path.join(root, relativePath));
  const allowed = filePath === path.join(root, "browser_benchmark.html")
    || filePath === path.join(root, "network_benchmark.html")
    || filePath === path.join(root, "upload_benchmark.html")
    || filePath === path.join(root, "service_worker_cold_benchmark.html")
    || filePath === path.join(root, "service_worker_update_benchmark.html")
    || filePath === path.join(root, "http_cache_benchmark.html")
    || filePath === path.join(root, "service_worker_bootstrap.html")
    || filePath === path.join(root, "service_worker_cache.js")
    || filePath.startsWith(path.join(root, "pkg-web") + path.sep);
  if (!allowed) {
    response.writeHead(403, {"content-type": "text/plain; charset=utf-8"});
    response.end("forbidden");
    return;
  }
  const info = await stat(filePath).catch(() => null);
  if (!info?.isFile()) {
    response.writeHead(404, {"content-type": "text/plain; charset=utf-8"});
    response.end("not found");
    return;
  }
  const headers = {
    "content-type": mediaTypes.get(path.extname(filePath).toLowerCase()) ?? "application/octet-stream",
    "cache-control": options.cacheControl,
    "content-length": info.size,
  };
  const networkSession = sessionFromRequest(request);
  if (networkSession) headers["set-cookie"] = `poker_network_session=${networkSession}; Path=/; SameSite=Strict`;
  if (filePath === path.join(root, "service_worker_cache.js")) {
    const updateCookie = request.headers.cookie ?? "";
    const versionMatch = updateCookie.match(/(?:^|;\s*)poker_sw_update_version=([12])/);
    if (versionMatch) {
      const body = `${readFileSync(filePath, "utf8")}\nself.SERVER_BYTE_VERSION=${versionMatch[1]};\n`;
      headers["content-length"] = Buffer.byteLength(body);
      response.writeHead(200, headers);
      response.end(request.method === "HEAD" ? undefined : body);
      if (networkSession) {
        const list = networkObservations.get(networkSession) ?? [];
        list.push({
          request_id: randomUUID(),
          path: url.pathname,
          method: request.method,
          status: response.statusCode,
          content_type: headers["content-type"],
          bytes_sent: Buffer.byteLength(body),
          service_worker_byte_version: Number(versionMatch[1]),
          observed_at: new Date().toISOString(),
        });
        networkObservations.set(networkSession, list);
      }
      return;
    }
  }
  response.writeHead(200, headers);
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  let bytesSent = 0;
  const stream = createReadStream(filePath);
  stream.on("data", chunk => {
    bytesSent += chunk.length;
  });
  stream.on("error", error => response.destroy(error));
  response.on("finish", () => {
    if (!networkSession) return;
    const list = networkObservations.get(networkSession) ?? [];
    list.push({
      request_id: randomUUID(),
      path: url.pathname,
      method: request.method,
      status: response.statusCode,
      content_type: headers["content-type"],
      bytes_sent: bytesSent,
      observed_at: new Date().toISOString(),
    });
    networkObservations.set(networkSession, list);
  });
  stream.pipe(response);
}

function validResult(payload) {
  return payload?.schema_version === 1
    && typeof payload.label === "string"
    && payload.label.length > 0
    && payload.label.length <= 48
    && Number.isInteger(payload.samples_per_cell)
    && payload.samples_per_cell >= 1
    && payload.samples_per_cell <= 101
    && payload.environment?.user_agent
    && Array.isArray(payload.results)
    && payload.results.length === 10
    && payload.results.every(row => Number.isFinite(row.prove_median_ms)
      && Number.isFinite(row.verify_median_ms)
      && Number.isFinite(row.prove_p95_ms)
      && Number.isFinite(row.verify_p95_ms)
      && Number.isFinite(row.bundle_bytes));
}

async function saveResult(request, response) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 1_000_000) {
      response.writeHead(413, {"content-type": "text/plain; charset=utf-8"});
      response.end("result too large");
      return;
    }
    chunks.push(chunk);
  }
  let payload;
  try {
    payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    response.writeHead(400, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid JSON");
    return;
  }
  if (!validResult(payload)) {
    response.writeHead(422, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid benchmark result");
    return;
  }
  await mkdir(options.outputDir, {recursive: true});
  const safeLabel = payload.label.replace(/[^\w.-]+/g, "-");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = `browser_${safeLabel}_${stamp}.json`;
  const outputPath = path.join(options.outputDir, filename);
  await writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`);
  response.writeHead(201, {"content-type": "text/plain; charset=utf-8"});
  response.end(filename);
  console.log(`[browser-benchmark] saved ${outputPath}`);
}

function validNetworkResult(payload) {
  const resourceNames = new Set((payload.resources ?? []).map(resource => resource.name));
  const uploadResult = payload.kind === "cold-network-upload-single-run";
  const serviceWorkerResult = payload.kind === "warm-service-worker-upload-single-run";
  const httpCacheResult = payload.kind === "http-cache-reuse-upload-single-run";
  return payload?.schema_version === 1
    && (payload.kind === "cold-network-single-run" || uploadResult || serviceWorkerResult || httpCacheResult)
    && typeof payload.label === "string"
    && payload.label.length > 0
    && payload.label.length <= 48
    && /^[\w-]{1,128}$/.test(payload.network_session ?? "")
    && payload.environment?.user_agent
    && ["html", "javascript", "wasm"].every(kind => resourceNames.has(kind))
    && payload.proof?.n === 52
    && payload.proof?.k === 13
    && Number.isFinite(payload.proof.prove_ms)
    && Number.isFinite(payload.proof.verify_ms)
    && Number.isFinite(payload.initialization?.wasm_initialized_relative_ms)
    && Number.isFinite(payload.navigation?.response_start_ms)
    && Array.isArray(payload.resources)
    && payload.resources.every(resource => Number.isFinite(resource.transfer_size)
      && Number.isFinite(resource.encoded_body_size)
      && Number.isFinite(resource.decoded_body_size)
      && Number.isFinite(resource.duration_ms));
  if (!uploadResult && !serviceWorkerResult && !httpCacheResult) return true;
  if (serviceWorkerResult
    && (payload.service_worker?.enabled !== true
      || typeof payload.service_worker?.controller_script_url !== "string"
      || typeof payload.service_worker?.scope !== "string")) {
    return false;
  }
  if (httpCacheResult && payload.environment?.http_cache_reuse !== true) return false;
  return payload.upload?.request_bytes === 27750
    && Number.isFinite(payload.upload.upload_wall_ms)
    && Number.isFinite(payload.upload.resource_transfer_size)
    && payload.upload.server_accepted === true;
}

function validColdServiceWorkerResult(payload) {
  const entries = new Map((payload.cache_entries ?? []).map(entry => [entry.name, entry]));
  return payload?.schema_version === 1
    && payload.kind === "cold-service-worker-install-single-run"
    && typeof payload.label === "string"
    && payload.label.length > 0
    && payload.label.length <= 48
    && /^[\w-]{1,128}$/.test(payload.network_session ?? "")
    && payload.environment?.user_agent
    && payload.service_worker?.scope?.endsWith("/")
    && payload.service_worker?.script_url?.includes("/service_worker_cache.js")
    && payload.service_worker?.cache_name?.includes(payload.network_session)
    && payload.service_worker?.controlled === true
    && payload.service_worker?.state === "activated"
    && ["html", "javascript", "wasm"].every(name => entries.has(name))
    && [...entries.values()].every(entry => entry.ok === true
      && Number.isFinite(entry.response_bytes)
      && entry.response_bytes > 0)
    && ["register_ms", "ready_ms", "controller_ms", "total_ms"]
      .every(key => Number.isFinite(payload.initialization?.[key])
        && payload.initialization[key] >= 0);
}

function validServiceWorkerUpdateResult(payload) {
  const initialEntries = new Map((payload.initial_cache_entries ?? []).map(entry => [entry.name, entry]));
  const updatedEntries = new Map((payload.updated_cache_entries ?? []).map(entry => [entry.name, entry]));
  return payload?.schema_version === 1
    && payload.kind === "service-worker-update-single-run"
    && typeof payload.label === "string"
    && payload.label.length > 0
    && payload.label.length <= 48
    && /^[\w-]{1,128}$/.test(payload.network_session ?? "")
    && payload.environment?.user_agent
    && payload.service_worker?.scope?.endsWith("/")
    && payload.service_worker?.script_url?.includes("/service_worker_cache.js")
    && payload.service_worker?.cache_name?.includes(payload.network_session)
    && payload.service_worker?.initial_byte_version === 1
    && payload.service_worker?.updated_byte_version === 2
    && payload.service_worker?.controlled === true
    && payload.service_worker?.state === "activated"
    && ["initial_cache_entries", "updated_cache_entries"].every(key => {
      const entries = key === "initial_cache_entries" ? initialEntries : updatedEntries;
      return ["html", "javascript", "wasm"].every(name => entries.has(name))
        && [...entries.values()].every(entry => entry.ok === true
          && Number.isFinite(entry.response_bytes)
          && entry.response_bytes > 0);
    })
    && ["initial_register_ms", "initial_version_query_ms", "update_call_ms", "updated_activation_ms", "updated_version_query_ms", "total_ms"]
      .every(key => Number.isFinite(payload.initialization?.[key])
        && payload.initialization[key] >= 0);
}

async function saveProofUpload(request, response) {
  const url = new URL(request.url, "http://localhost");
  const session = sessionFromRequest(request);
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 1_000_000) {
      response.writeHead(413, {"content-type": "application/json; charset=utf-8"});
      response.end(JSON.stringify({accepted: false, error: "bundle too large"}));
      return;
    }
    chunks.push(chunk);
  }
  const bundle = Buffer.concat(chunks);
  if (bundle.length !== 27750) {
    response.writeHead(422, {"content-type": "application/json; charset=utf-8"});
    response.end(JSON.stringify({
      accepted: false,
      error: `expected 27750 bundle bytes, received ${bundle.length}`,
    }));
    return;
  }
  try {
    await verifyUploadedBundle(new Uint8Array(bundle));
  } catch (error) {
    response.writeHead(422, {"content-type": "application/json; charset=utf-8"});
    response.end(JSON.stringify({accepted: false, error: "bundle verification failed"}));
    return;
  }
  const sha256 = createHash("sha256").update(bundle).digest("hex");
  if (session) {
    const list = networkObservations.get(session) ?? [];
    list.push({
      request_id: randomUUID(),
      path: url.pathname,
      method: request.method,
      direction: "browser-to-server",
      status: 200,
      bytes_received: bundle.length,
      sha256,
      verified: true,
      observed_at: new Date().toISOString(),
    });
    networkObservations.set(session, list);
  }
  response.writeHead(200, {"content-type": "application/json; charset=utf-8"});
  response.end(JSON.stringify({
    accepted: true,
    received_bytes: bundle.length,
    sha256,
    verified: true,
  }));
  console.log(`[browser-benchmark] verified uploaded reconstruction bundle (${bundle.length} bytes, ${sha256})`);
}

async function saveNetworkResult(request, response) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 1_000_000) {
      response.writeHead(413, {"content-type": "text/plain; charset=utf-8"});
      response.end("result too large");
      return;
    }
    chunks.push(chunk);
  }
  let payload;
  try {
    payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    response.writeHead(400, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid JSON");
    return;
  }
  if (!validNetworkResult(payload)) {
    response.writeHead(422, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid network benchmark result");
    return;
  }
  payload.server_observations = networkObservations.get(payload.network_session) ?? [];
  networkObservations.delete(payload.network_session);
  await mkdir(options.outputDir, {recursive: true});
  const safeLabel = payload.label.replace(/[^\w.-]+/g, "-");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = `network_run_${safeLabel}_${payload.network_session}_${stamp}.json`;
  const outputPath = path.join(options.outputDir, filename);
  await writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`);
  response.writeHead(201, {"content-type": "text/plain; charset=utf-8"});
  response.end(filename);
  console.log(`[browser-benchmark] saved network run ${outputPath}`);
}

async function readNetworkResult(request, response, pathname) {
  const filename = pathname.match(/^\/network-run\/([\w.-]+\.json)$/)?.[1];
  if (!filename || filename.includes("..")) {
    response.writeHead(404, {"content-type": "text/plain; charset=utf-8"});
    response.end("network result not found");
    return;
  }
  const filePath = path.join(options.outputDir, filename);
  const payload = await readFile(filePath, "utf8").catch(() => null);
  if (!payload) {
    response.writeHead(404, {"content-type": "text/plain; charset=utf-8"});
    response.end("network result not found");
    return;
  }
  response.writeHead(200, {"content-type": "application/json; charset=utf-8"});
  response.end(payload);
}

async function saveColdServiceWorkerResult(request, response) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 1_000_000) {
      response.writeHead(413, {"content-type": "text/plain; charset=utf-8"});
      response.end("result too large");
      return;
    }
    chunks.push(chunk);
  }
  let payload;
  try {
    payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    response.writeHead(400, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid JSON");
    return;
  }
  if (!validColdServiceWorkerResult(payload)) {
    response.writeHead(422, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid cold service-worker benchmark");
    return;
  }
  payload.server_observations = networkObservations.get(payload.network_session) ?? [];
  networkObservations.delete(payload.network_session);
  await mkdir(options.outputDir, {recursive: true});
  const safeLabel = payload.label.replace(/[^\w.-]+/g, "-");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = `network_run_${safeLabel}_${payload.network_session}_${stamp}.json`;
  const outputPath = path.join(options.outputDir, filename);
  await writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`);
  response.writeHead(201, {"content-type": "text/plain; charset=utf-8"});
  response.end(filename);
  console.log(`[browser-benchmark] saved cold service-worker run ${outputPath}`);
}

async function saveServiceWorkerUpdateResult(request, response) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 1_000_000) {
      response.writeHead(413, {"content-type": "text/plain; charset=utf-8"});
      response.end("result too large");
      return;
    }
    chunks.push(chunk);
  }
  let payload;
  try {
    payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    response.writeHead(400, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid JSON");
    return;
  }
  if (!validServiceWorkerUpdateResult(payload)) {
    response.writeHead(422, {"content-type": "text/plain; charset=utf-8"});
    response.end("invalid service-worker update benchmark");
    return;
  }
  payload.server_observations = networkObservations.get(payload.network_session) ?? [];
  networkObservations.delete(payload.network_session);
  await mkdir(options.outputDir, {recursive: true});
  const safeLabel = payload.label.replace(/[^\w.-]+/g, "-");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = `network_run_${safeLabel}_${payload.network_session}_${stamp}.json`;
  const outputPath = path.join(options.outputDir, filename);
  await writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`);
  response.writeHead(201, {"content-type": "text/plain; charset=utf-8"});
  response.end(filename);
  console.log(`[browser-benchmark] saved service-worker update run ${outputPath}`);
}

const requestHandler = async (request, response) => {
  try {
    if (request.method === "POST" && request.url === "/results") {
      await saveResult(request, response);
      return;
    }
    if (request.method === "POST" && request.url === "/network-results") {
      await saveNetworkResult(request, response);
      return;
    }
    if (request.method === "GET" && new URL(request.url, "http://localhost").pathname.startsWith("/network-run/")) {
      await readNetworkResult(request, response, new URL(request.url, "http://localhost").pathname);
      return;
    }
    if (request.method === "POST" && request.url === "/service-worker-results") {
      await saveColdServiceWorkerResult(request, response);
      return;
    }
    if (request.method === "POST" && request.url === "/service-worker-update-results") {
      await saveServiceWorkerUpdateResult(request, response);
      return;
    }
    if (request.method === "POST" && new URL(request.url, "http://localhost").pathname === "/proof-upload") {
      await saveProofUpload(request, response);
      return;
    }
    if (request.method === "GET" || request.method === "HEAD") {
      await serveFile(request, response);
      return;
    }
    response.writeHead(405, {"allow": "GET, HEAD, POST", "content-type": "text/plain; charset=utf-8"});
    response.end("method not allowed");
  } catch (error) {
    console.error(`[browser-benchmark] ${error?.stack ?? error}`);
    if (!response.headersSent) response.writeHead(500, {"content-type": "text/plain; charset=utf-8"});
    response.end("server error");
  }
};

const server = options.tls
  ? createHttpsServer({
    cert: readFileSync(options.tlsCert),
    key: readFileSync(options.tlsKey),
  }, requestHandler)
  : createHttpServer(requestHandler);

server.listen(options.port, options.host, () => {
  const hosts = options.host === "0.0.0.0"
    ? [...new Set(Object.values(networkInterfaces()).flat().filter(info => info?.family === "IPv4" && !info.internal).map(info => info.address))]
    : [options.host];
  console.log(`[browser-benchmark] serving ${pathToFileURL(root).href}`);
  for (const host of hosts) {
    console.log(`[browser-benchmark] open ${options.tls ? "https" : "http"}://${host}:${options.port}/?label=chrome-desktop`);
  }
  console.log(`[browser-benchmark] results will be written to ${options.outputDir}`);
  console.log("[browser-benchmark] press Ctrl-C to stop");
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
