//! Curve-level BN254 reconstruction benchmark.
//!
//! This is deliberately not a weakened finite-domain relation: it instantiates
//! the same curve-generic reconstruction package on BN254 G1 with curve
//! ElGamal ciphertexts, cross-key negation proofs, Bayer--Groth rerandomized
//! permutation, and per-slot OR proofs. It uses the SHA3 Fiat--Shamir
//! transcript rather than the production StarkCurve Poseidon transcript.
//!
//! Run:
//! ```text
//! cargo run -p poker-protocol-proofs --release \
//!   --example reconstruction_bn254_benchmark -- [OUTPUT_JSON] [SAMPLES] [N] [K]
//! ```

use std::env;
use std::fs::File;
use std::io::Write;
use std::path::Path;
use std::time::Instant;

use poker_protocol_core::{Bn254Curve, Curve, CurveScalar, ElGamalCiphertextGeneric};
use poker_protocol_proofs::reconstruction::{ReconstructProof, ReconstructionStatement};
use poker_protocol_proofs::transcript_ext::{CryptoTranscript, FiatShamirTranscript};
use rand_core::OsRng;
use serde_json::json;

type Package = (
    ReconstructionStatement<Bn254Curve>,
    ReconstructProof<Bn254Curve>,
);

#[cfg(feature = "borsh")]
fn wire_bytes(package: &Package) -> (usize, usize) {
    (
        borsh::to_vec(&package.1)
            .expect("serialize BN254 reconstruction proof")
            .len(),
        borsh::to_vec(&package.0)
            .expect("serialize BN254 reconstruction statement")
            .len(),
    )
}

#[cfg(not(feature = "borsh"))]
fn wire_bytes(_package: &Package) -> (usize, usize) {
    (0, 0)
}

struct Fixture {
    cards: Vec<<Bn254Curve as Curve>::Point>,
    residual_carriers: Vec<ElGamalCiphertextGeneric<Bn254Curve>>,
    owner_sk: <Bn254Curve as Curve>::Scalar,
    owner_pk: <Bn254Curve as Curve>::Point,
    aggregate_pk: <Bn254Curve as Curve>::Point,
}

fn fixture(n: usize, k: usize) -> Fixture {
    let cards = (0..n)
        .map(|index| {
            Bn254Curve::hash_to_curve(
                format!("reconstruction-bn254-benchmark/card/{index}").as_bytes(),
            )
        })
        .collect::<Vec<_>>();
    let owner_sk = <<Bn254Curve as Curve>::Scalar as CurveScalar>::random(&mut OsRng);
    let other_sk = <<Bn254Curve as Curve>::Scalar as CurveScalar>::random(&mut OsRng);
    let aggregate_sk = owner_sk + other_sk;
    let owner_pk = Bn254Curve::base_g() * owner_sk;
    let aggregate_pk = Bn254Curve::base_g() * aggregate_sk;
    let residual_carriers = (0..k)
        .map(|carrier| {
            let randomness =
                <<Bn254Curve as Curve>::Scalar as CurveScalar>::from_u64(1_000 + carrier as u64);
            ElGamalCiphertextGeneric::encrypt(&cards[carrier], &owner_pk, &randomness)
        })
        .collect();
    Fixture {
        cards,
        residual_carriers,
        owner_sk,
        owner_pk,
        aggregate_pk,
    }
}

fn prove(fixture: &Fixture, epoch: u64) -> Package {
    let mut transcript = FiatShamirTranscript::new(b"reconstruction-bn254-benchmark");
    ReconstructProof::<Bn254Curve>::prove(
        [7u8; 32],
        epoch,
        [9u8; 32],
        fixture.cards.clone(),
        fixture.residual_carriers.clone(),
        &fixture.owner_sk,
        &fixture.owner_pk,
        &fixture.aggregate_pk,
        &mut OsRng,
        &mut transcript,
    )
    .expect("honest BN254 reconstruction proof")
}

fn verify(package: &Package) {
    let mut transcript = FiatShamirTranscript::new(b"reconstruction-bn254-benchmark");
    package
        .1
        .verify(&package.0, &mut transcript)
        .expect("honest BN254 reconstruction proof verifies");
}

fn timing_samples(values: &[u128]) -> serde_json::Value {
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    let mean = sorted.iter().map(|value| *value as f64).sum::<f64>() / sorted.len() as f64;
    let variance = sorted
        .iter()
        .map(|value| {
            let delta = *value as f64 - mean;
            delta * delta
        })
        .sum::<f64>()
        / (sorted.len() - 1) as f64;
    json!({
        "median_us": sorted[sorted.len() / 2],
        "mean_us": mean,
        "sample_stddev_us": variance.sqrt(),
        "p95_us": sorted[(sorted.len() * 95 / 100).min(sorted.len() - 1)],
        "min_us": sorted[0],
        "max_us": sorted[sorted.len() - 1],
    })
}

fn main() {
    let mut arguments = env::args().skip(1);
    let output = arguments
        .next()
        .unwrap_or_else(|| ".repro/results/reconstruction_bn254_n52_k13.json".to_string());
    let samples = arguments
        .next()
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(30);
    let n = arguments
        .next()
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(52);
    let k = arguments
        .next()
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(13);
    if n != 52 || k != 13 || !(1..=101).contains(&samples) {
        eprintln!("this committed benchmark shape requires N=52 and K=13; samples may be 1..=101");
        std::process::exit(2);
    }

    let fixture = fixture(n, k);
    let _ = prove(&fixture, 0);

    let mut prove_us = Vec::with_capacity(samples);
    for sample in 0..samples {
        let started = Instant::now();
        let package = prove(&fixture, 1 + sample as u64);
        let elapsed = started.elapsed().as_micros();
        verify(&package);
        prove_us.push(elapsed);
    }

    let package = prove(&fixture, u64::MAX);
    let mut verify_us = Vec::with_capacity(samples);
    for _ in 0..samples {
        let started = Instant::now();
        verify(&package);
        verify_us.push(started.elapsed().as_micros());
    }

    let (proof_bytes, statement_bytes) = wire_bytes(&package);
    let codec = if cfg!(feature = "borsh") {
        "BN254 reconstruction v3 Borsh; 32-byte compressed G1 points and 32-byte canonical big-endian scalars"
    } else {
        "unavailable because this benchmark was built without the borsh feature"
    };

    let result = json!({
        "schema_version": 1,
        "baseline": "bn254-curve-reconstruction-generic",
        "curve": "BN254 G1",
        "transcript": "FiatShamirTranscript(SHA3)",
        "n": n,
        "k": k,
        "samples": samples,
        "timings": {
            "prove": timing_samples(&prove_us),
            "verify": timing_samples(&verify_us),
        },
        "wire_shape": {
            "codec": codec,
            "proof_bytes": proof_bytes,
            "statement_bytes": statement_bytes,
            "bundle_bytes": proof_bytes + statement_bytes,
        },
        "modeled_semantics": [
            "curve ElGamal ciphertexts",
            "cross-key negation proofs",
            "Bayer-Groth hidden rerandomized permutation",
            "per-slot zero-or-negative-card OR proofs",
            "exact residual-carrier coverage",
        ],
        "unsupported_semantics": [
            "production StarkCurve Poseidon transcript",
            "StarkCurve browser wire codec",
            "authenticated prior-state host integration",
            "chain settlement",
        ],
    });

    if let Some(parent) = Path::new(&output).parent() {
        std::fs::create_dir_all(parent).expect("create benchmark output directory");
    }
    let mut file = File::create(&output).expect("create BN254 benchmark output");
    file.write_all(format!("{result}\n").as_bytes())
        .expect("write BN254 benchmark output");
    println!("{result}");
}
