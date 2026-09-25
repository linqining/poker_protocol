#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const fixturePath = resolve(repoRoot, "paper/experiments/settlement_pstx_v1_kat.json");
const settlementSourcePath = resolve(repoRoot, "poker_protocol/src/reconstruction_settlement.rs");

function fail(message) {
  console.error(`[pstx-kat] error: ${message}`);
  process.exit(1);
}

function failUnless(condition, message) {
  if (!condition) fail(message);
}

function hexBytes(value, name) {
  failUnless(typeof value === "string", `${name} must be a hex string`);
  failUnless(/^[0-9a-f]+$/.test(value), `${name} must be lowercase hex`);
  failUnless(value.length % 2 === 0, `${name} must contain whole bytes`);
  return Buffer.from(value, "hex");
}

function requireUint(value, name) {
  failUnless(/^\d+$/.test(String(value)), `${name} must be a nonnegative decimal integer`);
  return BigInt(value);
}

const fixture = JSON.parse(readFileSync(fixturePath, "utf8"));
const source = readFileSync(settlementSourcePath, "utf8");

failUnless(fixture.schema_version === 1, "unexpected fixture schema_version");
failUnless(fixture.wire_format === "PSTX", "unexpected wire format");
failUnless(fixture.wire_version === 1, "unexpected wire version");
failUnless(fixture.curve === "StarkCurve", "unexpected curve");
failUnless(fixture.signature_scheme === "StarkSchnorr", "unexpected signature scheme");
failUnless(fixture.message_domain === "poker.settlement.tx.v1", "unexpected message domain");
failUnless(fixture.wire_byte_length === 474, "unexpected wire byte length");

const bytes = hexBytes(fixture.wire_bytes_hex, "wire_bytes_hex");
failUnless(bytes.length === fixture.wire_byte_length, "wire byte length mismatch");
const wireSha256 = createHash("sha256").update(bytes).digest("hex");
failUnless(wireSha256 === fixture.wire_sha256, "wire SHA-256 mismatch");
failUnless(bytes.subarray(0, 4).toString("hex") === "50535458", "wire magic mismatch");
failUnless(bytes[4] === 1, "wire version mismatch");

const deploymentDigest = bytes.subarray(5, 37).toString("hex");
failUnless(deploymentDigest === fixture.deployment?.digest_hex, "deployment digest mismatch");
failUnless(
  fixture.deployment?.chain_id === "test-chain-42"
    && fixture.deployment?.contract_address === "0xpstxcontract"
    && fixture.deployment?.adapter_version === "pstx-adapter-v1",
  "deployment identity mismatch",
);

const nonce = bytes.readBigUInt64BE(37);
const gasLimit = bytes.readBigUInt64BE(45); // high 64 bits checked below
const gasLimitLow = bytes.readBigUInt64BE(53);
const publicKey = bytes.subarray(61, 93).toString("hex");
failUnless(nonce === requireUint(fixture.transaction?.nonce, "nonce"), "nonce mismatch");
failUnless(gasLimit === 0n, "gas limit high word mismatch");
failUnless(gasLimitLow === requireUint(fixture.transaction?.gas_limit, "gas_limit"), "gas limit mismatch");
failUnless(publicKey === fixture.transaction?.public_key_hex, "public key mismatch");

const signature = bytes.subarray(bytes.length - 64).toString("hex");
failUnless(signature === fixture.transaction?.signature_hex, "signature mismatch");
failUnless(
  fixture.transaction_hash_hex === "05d05f4ea9918adedb43e3d392402eca70bbd262dfa90b06d52ab730c10e4a58",
  "transaction hash mismatch",
);

const proposal = fixture.proposal ?? {};
failUnless(proposal.reconstruction_epoch === 11, "proposal epoch mismatch");
failUnless(proposal.finalized_at === 100, "proposal finalization time mismatch");
failUnless(
  JSON.stringify(proposal.missed_submitters) === JSON.stringify(["carol"]),
  "missed submitter mismatch",
);
failUnless(Array.isArray(proposal.settlements) && proposal.settlements.length === 3, "settlement count mismatch");
let penaltyTotal = 0n;
let compensationTotal = 0n;
let refundTotal = 0n;
let lockedTotal = 0n;
for (const [index, player] of proposal.settlements.entries()) {
  const locked = requireUint(player.locked_deposit, `settlement ${index} locked_deposit`);
  const penalty = requireUint(player.penalty, `settlement ${index} penalty`);
  const refund = requireUint(player.refund, `settlement ${index} refund`);
  const compensation = requireUint(player.compensation, `settlement ${index} compensation`);
  const release = requireUint(player.net_release, `settlement ${index} net_release`);
  requireUint(player.submitted ? 1 : 0, `settlement ${index} submitted invalid`);
  failUnless(locked === refund + penalty, `settlement ${index} refund invariant failed`);
  failUnless(release === refund + compensation, `settlement ${index} release consistency failed`);
  penaltyTotal += penalty;
  compensationTotal += compensation;
  refundTotal += refund;
  lockedTotal += locked;
}
const burned = requireUint(proposal.burned_penalty_remainder, "burned remainder");
failUnless(penaltyTotal === compensationTotal + burned, "penalty conservation failed");
failUnless(lockedTotal === refundTotal + compensationTotal + burned, "locked conservation failed");

const sourceWire = source.match(/PSTX_KAT_WIRE_HEX: &str = "([0-9a-f]+)"/)?.[1];
const sourceHash = source.match(/PSTX_KAT_TX_HASH_HEX: &str =\s*\n?\s*"([0-9a-f]+)"/)?.[1];
failUnless(sourceWire === fixture.wire_bytes_hex, "Rust KAT wire bytes drifted from fixture");
failUnless(sourceHash === fixture.transaction_hash_hex, "Rust KAT transaction hash drifted from fixture");

console.log(`[pstx-kat] PSTX v1 vector and Rust source agree: ${fixturePath}`);
