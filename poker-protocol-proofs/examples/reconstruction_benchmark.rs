//! Reconstruction protocol benchmark for the paper's experiment report.
//!
//! Measures the full `ReconstructProof` package (cross-key negation proofs,
//! Bayer--Groth contribution shuffle, per-slot OR proofs) on the native
//! StarkCurve + Poseidon-felt transcript path (the production domain):
//!
//! - prove / verify wall time (median over samples),
//! - serialized proof and statement size (borsh, requires `--features borsh`),
//! - peak allocated bytes per phase, via a counting global allocator.
//!
//! Scaling grid: deck size `n` in {13, 26, 52} crossed with residual-carrier
//! count `k` in {1, 4, 13, 26} (k <= n), so both the linear growth in slot OR
//! proofs (n) and in cross-key proofs (k) are visible.
//!
//! Run:
//! ```text
//! cargo run -p poker-protocol-proofs --release --features borsh \
//!     --example reconstruction_benchmark -- [out.csv]
//! ```
//! With an argument, results are written as a CSV file; without one, only the
//! table is printed.

use std::alloc::{GlobalAlloc, Layout, System};
use std::hint::black_box;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use poker_protocol_core::{
    transcript_domains::RECONSTRUCT_POSEIDON, Curve, CurveScalar, ElGamalCiphertextGeneric,
    PoseidonFeltTranscript, StarkCurve,
};
use poker_protocol_proofs::reconstruction::{ReconstructProof, ReconstructionProfile};
use rand_core::OsRng;

const SAMPLES: usize = 7;
const WARMUP: usize = 1;

// ============================================================
// Counting allocator: peak concurrent allocated bytes per phase.
// ============================================================

static ALLOCATED: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);

struct PeakAlloc;

unsafe impl GlobalAlloc for PeakAlloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let ptr = System.alloc(layout);
        if !ptr.is_null() {
            let current = ALLOCATED.fetch_add(layout.size(), Ordering::Relaxed) + layout.size();
            PEAK.fetch_max(current, Ordering::Relaxed);
        }
        ptr
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        ALLOCATED.fetch_sub(layout.size(), Ordering::Relaxed);
        System.dealloc(ptr, layout);
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        let new_ptr = System.realloc(ptr, layout, new_size);
        if !new_ptr.is_null() {
            if new_size >= layout.size() {
                let delta = new_size - layout.size();
                let current = ALLOCATED.fetch_add(delta, Ordering::Relaxed) + delta;
                PEAK.fetch_max(current, Ordering::Relaxed);
            } else {
                ALLOCATED.fetch_sub(layout.size() - new_size, Ordering::Relaxed);
            }
        }
        new_ptr
    }
}

#[global_allocator]
static GLOBAL_ALLOCATOR: PeakAlloc = PeakAlloc;

fn reset_peak() {
    ALLOCATED.store(0, Ordering::Relaxed);
    PEAK.store(0, Ordering::Relaxed);
}

fn take_peak() -> usize {
    PEAK.load(Ordering::Relaxed)
}

// ============================================================
// Fixture: authenticated owner-residual carriers for k of n cards.
// ============================================================

type Package = (
    poker_protocol_proofs::reconstruction::ReconstructionStatement<StarkCurve>,
    ReconstructProof<StarkCurve>,
);

struct Fixture {
    cards: Vec<<StarkCurve as Curve>::Point>,
    residual_carriers: Vec<ElGamalCiphertextGeneric<StarkCurve>>,
    owner_sk: <StarkCurve as Curve>::Scalar,
    owner_pk: <StarkCurve as Curve>::Point,
    aggregate_pk: <StarkCurve as Curve>::Point,
}

fn fixture(n: usize, k: usize) -> Fixture {
    let cards = (0..n)
        .map(|i| StarkCurve::hash_to_curve(format!("reconstruction-benchmark-card-{i}").as_bytes()))
        .collect::<Vec<_>>();
    let owner_sk = <<StarkCurve as Curve>::Scalar as CurveScalar>::random(&mut OsRng);
    let other_sk = <<StarkCurve as Curve>::Scalar as CurveScalar>::random(&mut OsRng);
    let aggregate_sk = owner_sk + other_sk;
    let owner_pk = StarkCurve::base_g() * owner_sk;
    let aggregate_pk = StarkCurve::base_g() * aggregate_sk;
    // Deterministic per-carrier randomness mirrors the authenticated prior
    // hand: hidden accumulated masking, fixed by state, not by the prover.
    let residual_carriers = (0..k)
        .map(|j| {
            let randomness =
                <<StarkCurve as Curve>::Scalar as CurveScalar>::from_u64(1_000 + j as u64);
            ElGamalCiphertextGeneric::encrypt(&cards[j], &owner_pk, &randomness)
        })
        .collect::<Vec<_>>();
    Fixture {
        cards,
        residual_carriers,
        owner_sk,
        owner_pk,
        aggregate_pk,
    }
}

fn run_prove_profile(fixture: &Fixture, epoch: u64) -> (Box<Package>, ReconstructionProfile) {
    let mut transcript = PoseidonFeltTranscript::new_domain(RECONSTRUCT_POSEIDON);
    let mut profile = ReconstructionProfile::default();
    let result = ReconstructProof::<StarkCurve>::prove_with_profile(
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
        Some(&mut profile),
    )
    .expect("honest reconstruction proof");
    (Box::new(result), profile)
}

fn run_prove(fixture: &Fixture, epoch: u64) -> Box<Package> {
    let mut transcript = PoseidonFeltTranscript::new_domain(RECONSTRUCT_POSEIDON);
    let result = ReconstructProof::<StarkCurve>::prove(
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
    .expect("honest reconstruction proof");
    Box::new(result)
}

fn run_verify_profile(package: &Package) -> ReconstructionProfile {
    let mut transcript = PoseidonFeltTranscript::new_domain(RECONSTRUCT_POSEIDON);
    let mut profile = ReconstructionProfile::default();
    package
        .1
        .verify_with_profile(&package.0, &mut transcript, Some(&mut profile))
        .expect("honest reconstruction proof verifies");
    profile
}

fn run_verify(package: &Package) {
    let mut transcript = PoseidonFeltTranscript::new_domain(RECONSTRUCT_POSEIDON);
    package
        .1
        .verify(&package.0, &mut transcript)
        .expect("honest reconstruction proof verifies");
}

fn median(samples: &mut [u128]) -> u128 {
    samples.sort_unstable();
    samples[samples.len() / 2]
}

#[cfg(feature = "borsh")]
fn report_sizes(package: &Package) -> (usize, usize) {
    let statement_bytes = borsh::to_vec(&package.0).expect("statement borsh");
    let proof_bytes = borsh::to_vec(&package.1).expect("proof borsh");
    (proof_bytes.len(), statement_bytes.len())
}

#[cfg(not(feature = "borsh"))]
fn report_sizes(_package: &Package) -> (usize, usize) {
    (0, 0)
}

fn main() {
    let grid: Vec<(usize, usize)> = [
        (13usize, &[1usize, 4, 13][..]),
        (26, &[1, 4, 13]),
        (52, &[1, 4, 13, 26]),
    ]
    .iter()
    .flat_map(|(n, ks)| ks.iter().map(move |k| (*n, *k)))
    .collect();

    println!("curve=StarkCurve transcript=PoseidonFelt samples={SAMPLES} (median) release build");
    println!(
        "{:>4} {:>4} {:>12} {:>12} {:>10} {:>10} {:>14} {:>14}",
        "n", "k", "prove_us", "verify_us", "proof_B", "stmt_B", "prove_peak_KiB", "verify_peak_KiB"
    );

    let csv_path = std::env::args().nth(1);
    let profile_csv_path = std::env::args().nth(2);
    let mut csv = String::from(
        "n,k,prove_us,verify_us,proof_bytes,statement_bytes,prove_peak_bytes,verify_peak_bytes\n",
    );
    let mut profile_csv = String::from(
        "n,k,residual_setup_ns,cross_key_ns,bayer_groth_ns,slot_or_ns,prove_total_ns,serialization_ns,verify_cross_key_ns,verify_bayer_groth_ns,verify_slot_or_ns,verify_total_ns\n",
    );

    for (n, k) in grid {
        let fixture = fixture(n, k);

        for _ in 0..WARMUP {
            black_box(run_prove(&fixture, 0));
        }

        let mut prove_times = Vec::with_capacity(SAMPLES);
        let mut prove_peak = 0usize;
        let mut first_package: Option<Box<Package>> = None;
        for sample in 0..SAMPLES {
            let epoch = 1 + sample as u64;
            reset_peak();
            let start = Instant::now();
            let package = run_prove(&fixture, epoch);
            prove_times.push(start.elapsed().as_micros());
            prove_peak = prove_peak.max(take_peak());
            if sample == 0 {
                first_package = Some(package);
            } else {
                black_box(package);
            }
        }

        let package = first_package.expect("first prove sample");
        let mut verify_times = Vec::with_capacity(SAMPLES);
        let mut verify_peak = 0usize;
        for _ in 0..SAMPLES {
            reset_peak();
            let start = Instant::now();
            run_verify(package.as_ref());
            verify_times.push(start.elapsed().as_micros());
            verify_peak = verify_peak.max(take_peak());
        }
        let prove_us = median(&mut prove_times);
        let verify_us = median(&mut verify_times);
        let (proof_bytes, statement_bytes) = report_sizes(package.as_ref());
        black_box(package.as_ref());

        println!(
            "{:>4} {:>4} {:>12} {:>12} {:>10} {:>10} {:>14} {:>14}",
            n,
            k,
            prove_us,
            verify_us,
            proof_bytes,
            statement_bytes,
            prove_peak / 1024,
            verify_peak / 1024
        );
        csv.push_str(&format!(
            "{n},{k},{},{},{proof_bytes},{statement_bytes},{prove_peak},{verify_peak}\n",
            prove_us,
            verify_us,
        ));

        let mut prove_profile_totals = Vec::with_capacity(SAMPLES);
        let mut prove_profiles = Vec::with_capacity(SAMPLES);
        for sample in 0..SAMPLES {
            let start = Instant::now();
            let (profile_package, profile) = run_prove_profile(&fixture, 100 + sample as u64);
            prove_profile_totals.push(start.elapsed().as_nanos());
            prove_profiles.push(profile);
            black_box(profile_package);
        }
        let mut verify_profile_totals = Vec::with_capacity(SAMPLES);
        let mut verify_profiles = Vec::with_capacity(SAMPLES);
        for _ in 0..SAMPLES {
            let start = Instant::now();
            verify_profiles.push(run_verify_profile(package.as_ref()));
            verify_profile_totals.push(start.elapsed().as_nanos());
        }
        let mut serialization_times = Vec::with_capacity(SAMPLES);
        for _ in 0..SAMPLES {
            let serialization_start = Instant::now();
            black_box(report_sizes(package.as_ref()));
            serialization_times.push(serialization_start.elapsed().as_nanos());
        }
        let median_profile = |field: fn(&ReconstructionProfile) -> u128,
                              samples: &[ReconstructionProfile]| {
            let mut values = samples.iter().map(field).collect::<Vec<_>>();
            median(&mut values)
        };
        let prove_total_ns = median(&mut prove_profile_totals);
        let verify_total_ns = median(&mut verify_profile_totals);
        let serialization_ns = median(&mut serialization_times);
        profile_csv.push_str(&format!(
            "{n},{k},{},{},{},{},{},{},{},{},{},{}\n",
            median_profile(|p| p.residual_setup_ns, &prove_profiles),
            median_profile(|p| p.cross_key_ns, &prove_profiles),
            median_profile(|p| p.bayer_groth_ns, &prove_profiles),
            median_profile(|p| p.slot_or_ns, &prove_profiles),
            prove_total_ns,
            serialization_ns,
            median_profile(|p| p.verify_cross_key_ns, &verify_profiles),
            median_profile(|p| p.verify_bayer_groth_ns, &verify_profiles),
            median_profile(|p| p.verify_slot_or_ns, &verify_profiles),
            verify_total_ns,
        ));
    }

    if let Some(path) = csv_path {
        std::fs::write(&path, csv).expect("write csv");
        eprintln!("csv written to {path}");
    }
    if let Some(path) = profile_csv_path {
        std::fs::write(&path, profile_csv).expect("write profile csv");
        eprintln!("profile csv written to {path}");
    }
}
