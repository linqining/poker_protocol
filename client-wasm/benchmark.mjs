import { writeFileSync } from "node:fs";
import { reconstruction_benchmark_csv } from "./pkg/client_wasm.js";

const samples = Number(process.argv[2] ?? 7);
const output = process.argv[3];
const csv = reconstruction_benchmark_csv(samples);

if (output) {
  writeFileSync(output, csv);
} else {
  process.stdout.write(csv);
}
