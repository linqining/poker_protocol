#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { hrtime } from "node:process";

const repoRoot = resolve(import.meta.dirname, "..");
const circuit = resolve(repoRoot, "paper/baselines/circom_multislot_relation.circom");
const outputPath = resolve(process.argv[2] ?? "paper/experiments/circom_multislot_baseline.json");
const workDir = resolve(repoRoot, ".repro/baseline/circom-multislot");
mkdirSync(workDir, { recursive: true });
mkdirSync(dirname(outputPath), { recursive: true });

const circom = process.env.CIRCOM_BIN ?? "circom";
const snarkjsBinary = process.env.SNARKJS_BIN;
const snarkjs = snarkjsBinary ? [snarkjsBinary, []] : ["npx", ["--yes", "snarkjs@0.7.5"]];

function run(command, args) {
  const start = hrtime.bigint();
  const stdout = execFileSync(command, args, {
    cwd: workDir,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  return { stdout, elapsedMs: Number(hrtime.bigint() - start) / 1e6 };
}

function snark(args) {
  return run(snarkjs[0], [...snarkjs[1], ...args]);
}

const compileRun = run(circom, [circuit, "--r1cs", "--wasm", "--sym", "-o", workDir]);
const r1cs = resolve(workDir, "circom_multislot_relation.r1cs");
const wasm = resolve(workDir, "circom_multislot_relation_js/circom_multislot_relation.wasm");
for (const required of [r1cs, wasm]) {
  if (!existsSync(required)) throw new Error(`compiler did not create ${required}`);
}

const info = snark(["r1cs", "info", r1cs]).stdout;
const constraints = Number(info.match(/Constraints:\s+(\d+)/i)?.[1]);
const wires = Number(info.match(/# of Wires:\s+(\d+)/i)?.[1]);
if (!Number.isFinite(constraints) || constraints <= 2) throw new Error(`unexpected constraint count in: ${info}`);
if (!Number.isFinite(wires)) throw new Error(`could not parse wire count from: ${info}`);

// A deterministic 52-card, 13-carrier instance. Selected canonical slots are
// 2, 5, 11, 17, 19, 23, 29, 31, 37, 41, 43, 47, and 50.
const n = 52;
const k = 13;
const selectedSlots = [2, 5, 11, 17, 19, 23, 29, 31, 37, 41, 43, 47, 50];
const field = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const cards = Array.from({length: n}, (_, index) => String(index + 1));
const branch = Array.from({length: n}, (_, index) => selectedSlots.includes(index) ? "1" : "0");
const contributions = cards.map((card, index) => branch[index] === "1" ? String(field - BigInt(card)) : "0");
const carrierCards = selectedSlots.map(index => cards[index]);
const carrierMap = Array.from({length: k}, (_, carrier) =>
  Array.from({length: n}, (_, slot) => selectedSlots[carrier] === slot ? "1" : "0"),
);
const inputPath = resolve(workDir, "input.json");
writeFileSync(inputPath, `${JSON.stringify({cards, contributions, carrierCards, branch, carrierMap}, null, 2)}\n`);

const ptau0 = resolve(workDir, "multislot_pot12_0000.ptau");
const ptau1 = resolve(workDir, "multislot_pot12_0001.ptau");
const ptau = resolve(workDir, "multislot_pot12_final.ptau");
snark(["powersoftau", "new", "bn128", "12", ptau0, "-v"]);
snark(["powersoftau", "contribute", ptau0, ptau1, "--name=local-multislot", "-e=local-multislot-entropy"]);
const setupPtauRun = snark(["powersoftau", "prepare", "phase2", ptau1, ptau]);

const zkey0 = resolve(workDir, "multislot_0000.zkey");
const zkey = resolve(workDir, "multislot_final.zkey");
const vk = resolve(workDir, "verification_key.json");
const grothSetupRun = snark(["groth16", "setup", r1cs, ptau, zkey0]);
snark(["zkey", "contribute", zkey0, zkey, "--name=local-multislot", "-e=local-multislot-zkey-entropy"]);
snark(["zkey", "export", "verificationkey", zkey, vk]);

const witness = resolve(workDir, "witness.wtns");
const proof = resolve(workDir, "proof.json");
const publicSignals = resolve(workDir, "public.json");
const witnessRun = snark(["wtns", "calculate", wasm, inputPath, witness]);
const proveRun = snark(["groth16", "prove", zkey, witness, proof, publicSignals]);
const verifyRun = snark(["groth16", "verify", vk, publicSignals, proof]);
if (!/OK/i.test(verifyRun.stdout)) throw new Error(`verification did not report OK: ${verifyRun.stdout}`);

const result = {
  schema_version: 1,
  baseline: "circom-groth16-multislot-exact-coverage",
  circuit: "paper/baselines/circom_multislot_relation.circom",
  circom_version: run(circom, ["--version"]).stdout.trim(),
  snarkjs_version: "0.7.5",
  curve: "bn128",
  setup: "local throwaway Powers of Tau contribution; performance-only, not a production ceremony",
  parameters: {n, k},
  constraints,
  wires,
  proof_bytes: statSync(proof).size,
  public_signal_bytes: statSync(publicSignals).size,
  compile_ms: compileRun.elapsedMs,
  phase2_preparation_ms: setupPtauRun.elapsedMs,
  groth16_setup_ms: grothSetupRun.elapsedMs,
  witness_ms: witnessRun.elapsedMs,
  prove_ms: proveRun.elapsedMs,
  verify_ms: verifyRun.elapsedMs,
  input_scope: {
    cards: "public identifiers 1..52",
    contributions: "zero for retained slots and -card for 13 selected removal slots",
    selected_slots_zero_based: selectedSlots,
    private_witness: ["13 carrier card values", "52 branch bits", "13x52 one-hot carrier map"],
  },
  modeled_semantics: [
    "per-slot contribution belongs to {0, -card_i}",
    "each carrier maps to exactly one canonical slot",
    "each negative slot is covered by exactly one carrier",
    "carrier-to-slot map and branch bits are private",
  ],
  unsupported_semantics: [
    "curve ElGamal ciphertext arithmetic and residual decryption",
    "cross-key group equations and owner-secret knowledge",
    "hidden permutation and Bayer-Groth shuffle soundness",
    "authenticated state binding and reconstruction epochs",
    "ciphertext rerandomization and dropout protocol composition",
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
