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
const wasmBaseline = resolve(repoRoot, "paper/experiments/reconstruction_wasm.csv");

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
  "n", "k", "prove_us", "verify_us", "proof_bytes", "statement_bytes",
  "prove_peak_bytes", "verify_peak_bytes",
];
const wasmHeader = [
  "n", "k", "prove_ms", "verify_ms", "proof_bytes", "statement_bytes",
  "bundle_bytes", "samples",
];
const componentHeader = [
  "n", "k", "residual_setup_ns", "cross_key_ns", "bayer_groth_ns", "slot_or_ns",
  "prove_total_ns", "serialization_ns", "verify_cross_key_ns", "verify_bayer_groth_ns",
  "verify_slot_or_ns", "verify_total_ns",
];

const mode = process.argv[2];
if (mode === "--committed") {
  const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
  const checks = [
    [nativeBaseline, metadata.native_benchmark.csv_sha256],
    [componentBaseline, metadata.native_benchmark.component_csv_sha256],
    [wasmBaseline, metadata.benchmark.csv_sha256],
    ...Object.entries(metadata.native_benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
    ...Object.entries(metadata.benchmark.source_sha256).map(([path, hash]) => [resolve(repoRoot, path), hash]),
  ];
  for (const [path, expected] of checks) {
    const actual = sha256(path);
    if (actual !== expected) {
      fail(`${path} SHA-256 is ${actual}; metadata records ${expected}`);
    }
  }
  parseCsv(nativeBaseline, nativeHeader);
  parseCsv(componentBaseline, componentHeader);
  parseCsv(wasmBaseline, wasmHeader);
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

  requirePositiveNumbers(nativeRows, nativeHeader.slice(2), nativePath);
  requirePositiveNumbers(wasmRows, wasmHeader.slice(2), wasmPath);
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
