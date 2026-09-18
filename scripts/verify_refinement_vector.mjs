#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const expected = JSON.parse(readFileSync(
  resolve(repoRoot, "paper/experiments/reconstruction_refinement_vector.json"),
  "utf8",
));
const leanOutput = execFileSync(
  "lake",
  ["env", "lean", "--run", "scripts/print_refinement_vector.lean"],
  { cwd: resolve(repoRoot, "poker_protocol_lean"), encoding: "utf8" },
).trim();
const values = leanOutput.split("\t");
if (values.length !== 5) throw new Error(`unexpected Lean vector output: ${leanOutput}`);
const actual = {
  version: Number(values[0]),
  reconstruction_epoch: Number(values[1]),
  card_count: Number(values[2]),
  residual_carrier_count: Number(values[3]),
  removed_bitmap: values[4],
};
for (const key of ["version", "reconstruction_epoch", "card_count", "residual_carrier_count", "removed_bitmap"]) {
  if (actual[key] !== expected[key]) {
    throw new Error(`Lean refinement vector mismatch for ${key}: ${actual[key]} != ${expected[key]}`);
  }
}
console.log("[refinement] Lean constants match the shared JSON vector");
