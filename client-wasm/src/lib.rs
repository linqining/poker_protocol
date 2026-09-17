//! Browser bridge for the StarkCurve reconstruction proof.
//!
//! The proof implementation is shared with the native host. This crate only
//! provides the wasm-bindgen benchmark boundary and the byte-identical Borsh
//! verifier bundle used by a browser or host verifier.

#[cfg(not(target_arch = "wasm32"))]
use std::time::{SystemTime, UNIX_EPOCH};

use borsh::BorshDeserialize;
#[cfg(target_arch = "wasm32")]
use js_sys::Date;
use poker_protocol::browser_proof_bundle::BrowserReconstructionV3Bundle;
use poker_protocol::transcript_domains::RECONSTRUCT_POSEIDON;
use poker_protocol::zk_shuffle::transcript_ext::PoseidonFeltTranscript;
use poker_protocol_core::{Curve, CurveScalar, ElGamalCiphertextGeneric, StarkCurve};
use poker_protocol_proofs::reconstruction::{ReconstructProof, ReconstructionStatement};
use rand_core::OsRng;
use wasm_bindgen::prelude::*;

type Package = (
    ReconstructionStatement<StarkCurve>,
    ReconstructProof<StarkCurve>,
);

#[derive(Debug)]
struct Fixture {
    cards: Vec<<StarkCurve as Curve>::Point>,
    residual_carriers: Vec<ElGamalCiphertextGeneric<StarkCurve>>,
    owner_sk: <StarkCurve as Curve>::Scalar,
    owner_pk: <StarkCurve as Curve>::Point,
    aggregate_pk: <StarkCurve as Curve>::Point,
}

fn fixture(n: usize, k: usize) -> Result<Fixture, JsValue> {
    if !(2..=1024).contains(&n) || !(1..=n).contains(&k) {
        return Err(JsValue::from_str("require 2 <= n <= 1024 and 1 <= k <= n"));
    }

    let cards = (0..n)
        .map(|i| {
            StarkCurve::hash_to_curve(format!("client-wasm-reconstruction-card-{i}").as_bytes())
        })
        .collect::<Vec<_>>();
    let owner_sk = StarkCurve::hash_to_scalar(format!("client-wasm-owner/{n}/{k}").as_bytes());
    let other_sk = StarkCurve::hash_to_scalar(format!("client-wasm-other/{n}/{k}").as_bytes());
    if owner_sk == <StarkCurve as Curve>::Scalar::zero()
        || other_sk == <StarkCurve as Curve>::Scalar::zero()
    {
        return Err(JsValue::from_str("fixture scalar generation failed"));
    }
    let owner_pk = StarkCurve::base_g() * owner_sk;
    let aggregate_pk = StarkCurve::base_g() * (owner_sk + other_sk);
    let residual_carriers = (0..k)
        .map(|j| {
            let randomness =
                StarkCurve::hash_to_scalar(format!("client-wasm-residual/{n}/{k}/{j}").as_bytes());
            ElGamalCiphertextGeneric::encrypt(&cards[j], &owner_pk, &randomness)
        })
        .collect::<Vec<_>>();

    Ok(Fixture {
        cards,
        residual_carriers,
        owner_sk,
        owner_pk,
        aggregate_pk,
    })
}

fn prove(fixture: &Fixture, epoch: u64) -> Result<Package, JsValue> {
    let mut transcript = PoseidonFeltTranscript::new_domain(RECONSTRUCT_POSEIDON);
    ReconstructProof::<StarkCurve>::prove(
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
    .map_err(|err| JsValue::from_str(&err.to_string()))
}

fn verify(package: &Package) -> Result<(), JsValue> {
    let mut transcript = PoseidonFeltTranscript::new_domain(RECONSTRUCT_POSEIDON);
    package
        .1
        .verify(&package.0, &mut transcript)
        .map_err(|err| JsValue::from_str(&err.to_string()))
}

fn bundle_bytes(package: &Package) -> Result<(Vec<u8>, Vec<u8>, Vec<u8>), JsValue> {
    let proof_bytes =
        borsh::to_vec(&package.1).map_err(|err| JsValue::from_str(&err.to_string()))?;
    let statement_bytes =
        borsh::to_vec(&package.0).map_err(|err| JsValue::from_str(&err.to_string()))?;
    let bundle = BrowserReconstructionV3Bundle {
        statement: package.0.clone(),
        proof: package.1.clone(),
    };
    let bundle_bytes = borsh::to_vec(&bundle).map_err(|err| JsValue::from_str(&err.to_string()))?;
    Ok((proof_bytes, statement_bytes, bundle_bytes))
}

fn median(values: &mut [f64]) -> f64 {
    values.sort_by(|left, right| left.partial_cmp(right).expect("finite timing"));
    values[values.len() / 2]
}

fn wasm_now_ms() -> f64 {
    #[cfg(target_arch = "wasm32")]
    {
        Date::now()
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock precedes UNIX epoch")
            .as_secs_f64()
            * 1_000.0
    }
}

/// Metrics returned to JavaScript. Times are wall-clock milliseconds measured
/// inside the WASM boundary; byte counts use canonical Borsh encodings.
#[wasm_bindgen]
#[derive(Debug, Clone, Copy)]
pub struct ReconstructionMetrics {
    n: usize,
    k: usize,
    samples: usize,
    prove_ms: f64,
    verify_ms: f64,
    proof_bytes: usize,
    statement_bytes: usize,
    bundle_bytes: usize,
}

#[wasm_bindgen]
impl ReconstructionMetrics {
    #[wasm_bindgen(getter)]
    pub fn n(&self) -> usize {
        self.n
    }
    #[wasm_bindgen(getter)]
    pub fn k(&self) -> usize {
        self.k
    }
    #[wasm_bindgen(getter)]
    pub fn samples(&self) -> usize {
        self.samples
    }
    #[wasm_bindgen(getter)]
    pub fn prove_ms(&self) -> f64 {
        self.prove_ms
    }
    #[wasm_bindgen(getter)]
    pub fn verify_ms(&self) -> f64 {
        self.verify_ms
    }
    #[wasm_bindgen(getter)]
    pub fn proof_bytes(&self) -> usize {
        self.proof_bytes
    }
    #[wasm_bindgen(getter)]
    pub fn statement_bytes(&self) -> usize {
        self.statement_bytes
    }
    #[wasm_bindgen(getter)]
    pub fn bundle_bytes(&self) -> usize {
        self.bundle_bytes
    }
}

/// Generate and verify reconstruction packages on the production WASM path.
///
/// One warmup proof is excluded. The reported proof is then regenerated for
/// each timed sample; verification is repeated against one accepted package.
/// The accepted package is also encoded, decoded as a
/// `BrowserReconstructionV3Bundle`, and re-verified before timings return.
#[wasm_bindgen]
pub fn run_reconstruction_benchmark(
    n: usize,
    k: usize,
    samples: usize,
) -> Result<ReconstructionMetrics, JsValue> {
    if samples == 0 || samples > 101 {
        return Err(JsValue::from_str("samples must be in 1..=101"));
    }
    let fixture = fixture(n, k)?;

    prove(&fixture, 0)?;

    let mut prove_times = Vec::with_capacity(samples);
    let mut accepted = None;
    for sample in 0..samples {
        let start = wasm_now_ms();
        let package = prove(&fixture, 1 + sample as u64)?;
        prove_times.push(wasm_now_ms() - start);
        accepted = Some(package);
    }
    let package = accepted.expect("at least one sample");

    let mut verify_times = Vec::with_capacity(samples);
    for _ in 0..samples {
        let start = wasm_now_ms();
        verify(&package)?;
        verify_times.push(wasm_now_ms() - start);
    }

    let (proof_bytes, statement_bytes, bundle_bytes) = bundle_bytes(&package)?;
    let decoded = BrowserReconstructionV3Bundle::try_from_slice(&bundle_bytes)
        .map_err(|err| JsValue::from_str(&err.to_string()))?;
    decoded
        .verify()
        .map_err(|err| JsValue::from_str(&err.to_string()))?;

    Ok(ReconstructionMetrics {
        n,
        k,
        samples,
        prove_ms: median(&mut prove_times),
        verify_ms: median(&mut verify_times),
        proof_bytes: proof_bytes.len(),
        statement_bytes: statement_bytes.len(),
        bundle_bytes: bundle_bytes.len(),
    })
}

/// Return the benchmark grid as CSV. This gives the paper reproducibility
/// script one deterministic wire output on any JavaScript host.
#[wasm_bindgen]
pub fn reconstruction_benchmark_csv(samples: usize) -> Result<String, JsValue> {
    const GRID: &[(usize, &[usize])] =
        &[(13, &[1, 4, 13]), (26, &[1, 4, 13]), (52, &[1, 4, 13, 26])];
    let mut csv =
        String::from("n,k,prove_ms,verify_ms,proof_bytes,statement_bytes,bundle_bytes,samples\n");
    for (n, ks) in GRID {
        for k in *ks {
            let metrics = run_reconstruction_benchmark(*n, *k, samples)?;
            csv.push_str(&format!(
                "{},{},{:.3},{:.3},{},{},{},{}\n",
                metrics.n,
                metrics.k,
                metrics.prove_ms,
                metrics.verify_ms,
                metrics.proof_bytes,
                metrics.statement_bytes,
                metrics.bundle_bytes,
                metrics.samples
            ));
        }
    }
    Ok(csv)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(target_arch = "wasm32")]
    use wasm_bindgen_test::wasm_bindgen_test;

    #[test]
    fn reconstruction_benchmark_accepts_and_roundtrips() {
        let metrics = run_reconstruction_benchmark(4, 1, 1).unwrap();
        assert_eq!(metrics.n, 4);
        assert_eq!(metrics.k, 1);
        assert!(metrics.prove_ms > 0.0);
        assert!(metrics.verify_ms > 0.0);
        assert!(metrics.bundle_bytes > metrics.proof_bytes);
    }

    #[cfg(target_arch = "wasm32")]
    #[wasm_bindgen_test]
    fn wasm_reconstruction_benchmark_accepts() {
        let metrics = run_reconstruction_benchmark(4, 1, 1).unwrap();
        assert_eq!((metrics.n, metrics.k), (4, 1));
        assert!(metrics.bundle_bytes > metrics.proof_bytes);
    }
}
