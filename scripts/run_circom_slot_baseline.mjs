#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { hrtime } from "node:process";

const repoRoot = resolve(import.meta.dirname, "..");
const circuit = resolve(repoRoot, "paper/baselines/circom_slot_relation.circom");
const outputPath = resolve(process.argv[2] ?? "paper/experiments/circom_slot_baseline.json");
const workDir = resolve(repoRoot, ".repro/baseline/circom-slot");
mkdirSync(workDir, { recursive: true });
mkdirSync(dirname(outputPath), { recursive: true });

const circom = process.env.CIRCOM_BIN ?? "circom";
const snarkjs = ["npx", ["--yes", "snarkjs@0.7.5"]];

function run(command, args, options = {}) {
  const start = hrtime.bigint();
  const stdout = execFileSync(command, args, {
    cwd: workDir,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });
  const elapsedNs = Number(hrtime.bigint() - start);
  return { stdout, elapsedNs };
}

function snark(args) {
  return run(snarkjs[0], [...snarkjs[1], ...args]);
}

const compile = run(circom, [circuit, "--r1cs", "--wasm", "--sym", "-o", workDir]);
const r1cs = resolve(workDir, "circom_slot_relation.r1cs");
const wasm = resolve(workDir, "circom_slot_relation_js/circom_slot_relation.wasm");
const info = snark(["r1cs", "info", r1cs]).stdout;
const constraints = Number(info.match(/Constraints:\s+(\d+)/i)?.[1]);
if (!Number.isFinite(constraints)) throw new Error(`could not parse constraint count from: ${info}`);

const ptau0 = resolve(workDir, "pot12_0000.ptau");
const ptau1 = resolve(workDir, "pot12_0001.ptau");
const ptau = resolve(workDir, "pot12_final.ptau");
snark(["powersoftau", "new", "bn128", "8", ptau0, "-v"]);
snark(["powersoftau", "contribute", ptau0, ptau1, "--name=local-baseline", "-e=local-baseline-entropy"]);
snark(["powersoftau", "prepare", "phase2", ptau1, ptau]);

const zkey0 = resolve(workDir, "slot_0000.zkey");
const zkey = resolve(workDir, "slot_final.zkey");
const vk = resolve(workDir, "verification_key.json");
snark(["groth16", "setup", r1cs, ptau, zkey0]);
snark(["zkey", "contribute", zkey0, zkey, "--name=local-baseline", "-e=local-baseline-zkey-entropy"]);
snark(["zkey", "export", "verificationkey", zkey, vk]);

const field = "21888242871839275222246405745257275088548364400416034343698204186575808495617";
const inputPath = resolve(workDir, "input.json");
writeFileSync(inputPath, JSON.stringify({ card: "7", out: (BigInt(field) - 7n).toString(), selector: "1" }) + "\n");
const witness = resolve(workDir, "witness.wtns");
const proof = resolve(workDir, "proof.json");
const publicSignals = resolve(workDir, "public.json");
const witnessRun = snark(["wtns", "calculate", wasm, inputPath, witness]);
const proveRun = snark(["groth16", "prove", zkey, witness, proof, publicSignals]);
const verifyRun = snark(["groth16", "verify", vk, publicSignals, proof]);
if (!/OK/i.test(verifyRun.stdout)) throw new Error(`verification did not report OK: ${verifyRun.stdout}`);

const result = {
  schema_version: 1,
  baseline: "circom-groth16-single-slot",
  circuit: "paper/baselines/circom_slot_relation.circom",
  circom_version: run(circom, ["--version"]).stdout.trim(),
  snarkjs_version: "0.7.5",
  curve: "bn128",
  setup: "local throwaway Powers of Tau contribution; performance-only, not a production ceremony",
  constraints,
  proof_bytes: statSync(proof).size,
  public_signal_bytes: statSync(publicSignals).size,
  witness_ms: witnessRun.elapsedNs / 1e6,
  prove_ms: proveRun.elapsedNs / 1e6,
  verify_ms: verifyRun.elapsedNs / 1e6,
  input: { card: "7", selector_private: "1", out: "-7 mod bn128 field" },
  unsupported_semantics: [
    "ElGamal ciphertext arithmetic and residual decryption",
    "cross-key proofs",
    "hidden carrier-to-slot mapping and Bayer-Groth shuffle",
    "authenticated state binding and reconstruction epochs",
    "dropout handling and multi-slot composition",
  ],
  commands: {
    compile: "circom 2.2.3 --r1cs --wasm --sym",
    setup: "snarkjs powersoftau new/contribute/prepare phase2; groth16 setup; zkey contribute",
    prove: "snarkjs wtns calculate + groth16 prove",
    verify: "snarkjs groth16 verify",
  },
};
writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result, null, 2));
