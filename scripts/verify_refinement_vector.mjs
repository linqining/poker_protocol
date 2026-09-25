#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const expected = JSON.parse(readFileSync(
  resolve(repoRoot, "paper/experiments/reconstruction_refinement_vector.json"),
  "utf8",
));
const schema = JSON.parse(readFileSync(
  resolve(repoRoot, "paper/experiments/reconstruction_statement_schema_v3.json"),
  "utf8",
));
const leanOutput = execFileSync(
  "lake",
  ["env", "lean", "--run", "scripts/print_refinement_vector.lean"],
  { cwd: resolve(repoRoot, "poker_protocol_lean"), encoding: "utf8" },
).trim();
const [semanticLine, schemaLine, proofLine] = leanOutput.split(/\r?\n/);
if (!semanticLine || !schemaLine || !proofLine) {
  throw new Error(`unexpected Lean refinement output: ${leanOutput}`);
}
const values = semanticLine.split("\t");
if (values.length !== 5) throw new Error(`unexpected Lean vector output: ${semanticLine}`);
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

const schemaValues = schemaLine.split("\t");
if (schemaValues.length !== 6) throw new Error(`unexpected Lean schema output: ${schemaLine}`);
const actualSchema = {
  schema_version: Number(schemaValues[0]),
  byte_length: Number(schemaValues[1]),
  field_count: Number(schemaValues[2]),
  prefix_length: Number(schemaValues[3]),
  prefix_hex: schemaValues[4],
  sha256: schemaValues[5],
};
for (const key of Object.keys(actualSchema)) {
  if (actualSchema[key] !== schema[key]) {
    throw new Error(`Lean statement schema mismatch for ${key}: ${actualSchema[key]} != ${schema[key]}`);
  }
}

const proofValues = proofLine.split("\t");
if (proofValues.length !== 7) throw new Error(`unexpected Lean proof schema output: ${proofLine}`);
const actualProofSchema = {
  schema_version: Number(proofValues[0]),
  byte_length: Number(proofValues[1]),
  field_count: Number(proofValues[2]),
  nested_field_count: Number(proofValues[3]),
  prefix_length: Number(proofValues[4]),
  prefix_hex: proofValues[5],
  sha256: proofValues[6],
};
const proofSchema = schema.proof;
for (const key of Object.keys(actualProofSchema)) {
  const expectedKey = key === "schema_version" ? key : key;
  if (actualProofSchema[key] !== proofSchema[expectedKey]) {
    throw new Error(`Lean proof schema mismatch for ${key}: ${actualProofSchema[key]} != ${proofSchema[expectedKey]}`);
  }
}

const expectedFields = [
  ["version", 0, 1],
  ["context_digest", 1, 32],
  ["reconstruction_epoch", 33, 8],
  ["prior_state_digest", 41, 32],
  ["aggregate_pk", 73, 32],
  ["owner_pk", 105, 32],
  ["card_count", 137, 4],
  ["cards", 141, 256],
  ["residual_carrier_count", 397, 4],
  ["residual_carriers", 401, 128],
  ["contributions", 529, 512],
];
const bytes = Buffer.from(schema.bytes_hex, "hex");
if (bytes.length !== schema.byte_length || bytes.length !== 1041) {
  throw new Error(`statement fixture has unexpected byte length: ${bytes.length}`);
}
if (createHash("sha256").update(bytes).digest("hex") !== schema.sha256) {
  throw new Error("statement fixture SHA-256 does not match bytes_hex");
}
if (schema.bytes_hex.slice(0, schema.prefix_length * 2) !== schema.prefix_hex) {
  throw new Error("statement fixture prefix does not match bytes_hex");
}
let cursor = 0;
for (const [index, expectedField] of expectedFields.entries()) {
  const field = schema.fields[index];
  const [name, offset, length] = expectedField;
  if (!field || field.name !== name || field.offset !== offset || field.length !== length) {
    throw new Error(`statement fixture field ${index} does not match the frozen v3 schema`);
  }
  if (field.offset !== cursor) throw new Error(`statement fixture field ${name} leaves a gap or overlap`);
  if (bytes.subarray(offset, offset + length).toString("hex") !== field.hex) {
    throw new Error(`statement fixture slice mismatch for ${name}`);
  }
  cursor += length;
}
if (cursor !== bytes.length) throw new Error(`statement fields cover ${cursor} bytes, not ${bytes.length}`);

const expectedProofFields = [
  ["version", 0, 1],
  ["negative_contribution_count", 1, 4],
  ["negative_contributions", 5, 128],
  ["cross_key_proofs", 133, 320],
  ["contribution_shuffle_proof", 453, 1324],
  ["slot_membership_proof_count", 1777, 4],
  ["slot_membership_proofs", 1781, 2048],
];
const proofBytes = Buffer.from(proofSchema.bytes_hex, "hex");
if (proofBytes.length !== proofSchema.byte_length || proofBytes.length !== 3829) {
  throw new Error(`proof fixture has unexpected byte length: ${proofBytes.length}`);
}
if (createHash("sha256").update(proofBytes).digest("hex") !== proofSchema.sha256) {
  throw new Error("proof fixture SHA-256 does not match bytes_hex");
}
if (proofSchema.bytes_hex.slice(0, proofSchema.prefix_length * 2) !== proofSchema.prefix_hex) {
  throw new Error("proof fixture prefix does not match bytes_hex");
}
cursor = 0;
for (const [index, expectedField] of expectedProofFields.entries()) {
  const field = proofSchema.fields[index];
  const [name, offset, length] = expectedField;
  if (!field || field.name !== name || field.offset !== offset || field.length !== length) {
    throw new Error(`proof fixture field ${index} does not match the frozen v3 schema`);
  }
  if (field.offset !== cursor) throw new Error(`proof fixture field ${name} leaves a gap or overlap`);
  if (proofBytes.subarray(offset, offset + length).toString("hex") !== field.hex) {
    throw new Error(`proof fixture slice mismatch for ${name}`);
  }
  cursor += length;
}
if (cursor !== proofBytes.length) throw new Error(`proof fields cover ${cursor} bytes, not ${proofBytes.length}`);

const expectedNestedNames = [
  "negative_contributions[0]",
  "negative_contributions[1]",
  "cross_key_proofs[0]",
  "cross_key_proofs[1]",
  "contribution_shuffle_proof.c_permutation",
  "contribution_shuffle_proof.c_permuted_powers",
  "contribution_shuffle_proof.multi_exponentiation.c_alpha",
  "contribution_shuffle_proof.multi_exponentiation.c_beta",
  "contribution_shuffle_proof.multi_exponentiation.ciphertext_0",
  "contribution_shuffle_proof.multi_exponentiation.ciphertext_1",
  "contribution_shuffle_proof.multi_exponentiation.alpha_response",
  "contribution_shuffle_proof.multi_exponentiation.commitment_response",
  "contribution_shuffle_proof.multi_exponentiation.beta",
  "contribution_shuffle_proof.multi_exponentiation.beta_blinding_response",
  "contribution_shuffle_proof.multi_exponentiation.rerandomization_response",
  "contribution_shuffle_proof.product.c_d",
  "contribution_shuffle_proof.product.c_delta",
  "contribution_shuffle_proof.product.c_capital_delta",
  "contribution_shuffle_proof.product.a_response",
  "contribution_shuffle_proof.product.b_response",
  "contribution_shuffle_proof.product.r_response",
  "contribution_shuffle_proof.product.s_response",
  "slot_membership_proofs[0]",
  "slot_membership_proofs[1]",
  "slot_membership_proofs[2]",
  "slot_membership_proofs[3]",
  "slot_membership_proofs[4]",
  "slot_membership_proofs[5]",
  "slot_membership_proofs[6]",
  "slot_membership_proofs[7]",
];
if (proofSchema.nested_fields.length !== 30) {
  throw new Error(`proof fixture nested field count is ${proofSchema.nested_fields.length}, expected 30`);
}
for (const [index, name] of expectedNestedNames.entries()) {
  const field = proofSchema.nested_fields[index];
  if (field.name !== name) throw new Error(`proof nested field ${index} is ${field.name}, expected ${name}`);
  const offset = field.offset;
  const length = field.length;
  if (offset + length > proofBytes.length) throw new Error(`proof nested field ${name} exceeds package`);
  if (proofBytes.subarray(offset, offset + length).toString("hex") !== field.hex) {
    throw new Error(`proof nested slice mismatch for ${name}`);
  }
}

console.log("[refinement] Lean constants and full statement/proof schemas match the shared JSON fixtures");
