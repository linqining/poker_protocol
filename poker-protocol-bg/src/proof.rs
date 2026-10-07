use poker_protocol_core::{
    CryptoTranscript, Curve, CurvePoint, CurveScalar, ElGamalCiphertextGeneric, VerificationError,
};
use rand_core::{CryptoRng, RngCore};

const PROTOCOL_ID: &[u8] = b"poker/bayer-groth-shuffle/v2";
const COMMITMENT_H_DOMAIN: &[u8] = b"poker/bg12/v2/H";

/// Assemble all generator domain byte vectors (single loop per function:
/// Aeneas loop-fixed-point limitation).
// Used by CommitmentKey::derive; dead-code warnings appear only in
// extraction feature combinations where the prover (and thus derive) is
// gated out.
#[allow(dead_code)]
fn generator_domains(n: usize) -> Vec<Vec<u8>> {
    let mut domains: Vec<Vec<u8>> = Vec::with_capacity(n);
    for i in 0..n {
        domains.push(generator_domain(n, i));
    }
    domains
}

/// Hash every domain to a curve point (single loop per function).
#[allow(dead_code)]
fn hash_generators<C: Curve>(domains: &[Vec<u8>]) -> Vec<C::Point> {
    let mut generators: Vec<C::Point> = Vec::with_capacity(domains.len());
    for i in 0..domains.len() {
        generators.push(C::hash_to_curve(&domains[i]));
    }
    generators
}

/// Validity + pairwise-distinctness of the derived generators (outer loop
/// only; the pairwise check is a dedicated function).
#[allow(dead_code)]
fn generators_valid<C: Curve>(generators: &[C::Point], h: C::Point) -> bool {
    let mut valid = true;
    for i in 0..generators.len() {
        if generators[i].is_identity() || generators[i] == C::base_g() || generators[i] == h {
            valid = false;
            break;
        }
        if !pairwise_distinct_before::<C>(generators, i) {
            valid = false;
            break;
        }
    }
    valid
}

/// `generators[..=i]` has no duplicate of `generators[i]` among earlier
/// entries (inner loop extracted as its own function).
fn pairwise_distinct_before<C: Curve>(generators: &[C::Point], i: usize) -> bool {
    let mut distinct = true;
    for j in 0..i {
        if generators[j] == generators[i] {
            distinct = false;
            break;
        }
    }
    distinct
}

/// Domain bytes for the i-th generator: byte-for-byte identical to
/// `format!("poker/bg12/v2/G/{n}/{i}")` (decimal, no leading zeros).
fn generator_domain(n: usize, i: usize) -> Vec<u8> {
    let mut domain = Vec::with_capacity(32);
    domain.extend_from_slice(b"poker/bg12/v2/G/");
    push_decimal(&mut domain, n);
    domain.push(b'/');
    push_decimal(&mut domain, i);
    domain
}

/// Append the decimal encoding of `value` (no leading zeros) to `out` —
/// byte-for-byte identical to `usize`'s `Display`, without `format!`.
fn push_decimal(out: &mut Vec<u8>, value: usize) {
    if value == 0 {
        out.push(b'0');
        return;
    }
    let mut digits = [0u8; 20];
    let mut len = 0usize;
    let mut v = value;
    while v != 0 {
        digits[len] = b'0' + (v % 10) as u8;
        len += 1;
        v /= 10;
    }
    let mut i = len;
    while i > 0 {
        i -= 1;
        out.push(digits[i]);
    }
}

#[derive(Debug, Clone)]
struct CommitmentKey<C: Curve> {
    h: C::Point,
    generators: Vec<C::Point>,
}

impl<C: Curve> CommitmentKey<C> {
    fn derive(n: usize) -> Result<Self, VerificationError> {
        let h = C::hash_to_curve(COMMITMENT_H_DOMAIN);
        // Manual byte assembly (no `format!`, index loop, no map/collect):
        // the shapes the Aeneas extraction supports. The encoding matches
        // `format!("poker/bg12/v2/G/{n}/{i}")` byte for byte (decimal,
        // no leading zeros).
        // Single-purpose loops (Aeneas loop-fixed-point limitation): the
        // per-generator domain assembly lives in its own function so this
        // loop body is a single call.
        let mut domains: Vec<Vec<u8>> = Vec::with_capacity(n);
        for i in 0..n {
            domains.push(generator_domain(n, i));
        }
        let mut generators: Vec<C::Point> = Vec::with_capacity(n);
        for i in 0..n {
            generators.push(C::hash_to_curve(&domains[i]));
        }

        if h.is_identity() || h == C::base_g() {
            return Err(VerificationError::InvalidCommitmentKey);
        }
        let mut key_valid = true;
        for i in 0..n {
            if generators[i].is_identity() || generators[i] == C::base_g() || generators[i] == h {
                key_valid = false;
                break;
            }
            // Inline `generators[..i].contains(...)` as an index loop.
            let mut duplicate = false;
            for j in 0..i {
                if generators[j] == generators[i] {
                    duplicate = true;
                    break;
                }
            }
            if duplicate {
                key_valid = false;
                break;
            }
        }
        if !key_valid {
            return Err(VerificationError::InvalidCommitmentKey);
        }
        Ok(Self { h, generators })
    }

    fn scalar_commit(&self, value: C::Scalar, blinding: C::Scalar) -> C::Point {
        C::base_g() * value + self.h * blinding
    }

    fn vector_commit(
        &self,
        values: &[C::Scalar],
        blinding: C::Scalar,
    ) -> Result<C::Point, VerificationError> {
        if values.len() != self.generators.len() {
            return Err(VerificationError::LengthMismatch);
        }
        let mut scalars = Vec::with_capacity(values.len() + 1);
        scalars.extend_from_slice(values);
        scalars.push(blinding);
        let mut points = self.generators.clone();
        points.push(self.h);
        Ok(C::Point::vartime_multiscalar_mul(&scalars, &points))
    }
}

/// The Bayer--Groth multi-exponentiation argument.
#[derive(Debug, Clone)]
pub struct MultiExponentiationArgument<C: Curve> {
    pub c_alpha: C::Point,
    pub c_beta: C::Point,
    pub ciphertext_0: ElGamalCiphertextGeneric<C>,
    pub ciphertext_1: ElGamalCiphertextGeneric<C>,
    /// `alpha + challenge * x^pi`; fresh `alpha` information-theoretically
    /// masks the hidden permutation-dependent vector.
    pub alpha_response: Vec<C::Scalar>,
    pub commitment_response: C::Scalar,
    pub beta: C::Scalar,
    pub beta_blinding_response: C::Scalar,
    pub rerandomization_response: C::Scalar,
}

/// The Bayer--Groth single-value product argument used for `m = 1`.
#[derive(Debug, Clone)]
pub struct ProductArgument<C: Curve> {
    pub c_d: C::Point,
    pub c_delta: C::Point,
    pub c_capital_delta: C::Point,
    /// Masked Sigma responses, not raw permutation coefficients.
    pub a_response: Vec<C::Scalar>,
    pub b_response: Vec<C::Scalar>,
    pub r_response: C::Scalar,
    pub s_response: C::Scalar,
}

/// Bayer--Groth shuffle proof, protocol version 2.
#[derive(Debug, Clone)]
pub struct BayerGrothShuffleProof<C: Curve> {
    pub c_permutation: C::Point,
    pub c_permuted_powers: C::Point,
    pub multi_exponentiation: MultiExponentiationArgument<C>,
    pub product: ProductArgument<C>,
}

/// `(challenge^1, …, challenge^n)` in a dedicated single-purpose loop
/// (calling the generic `scalar_pow` inline inside verify's loops trips an
/// Aeneas generic-loop-body limitation).
fn public_powers<C: Curve>(challenge: C::Scalar, n: usize) -> Vec<C::Scalar> {
    // Recurrence `x^(i+1) = x^i * x` (no per-iteration call into the
    // generic square-and-multiply, which trips an Aeneas limitation).
    // Fill-then-index-update (index writes instead of pushes carrying
    // computed scalars): the Aeneas-supported shape.
    let mut powers: Vec<C::Scalar> = Vec::with_capacity(n);
    for _i in 0..n {
        powers.push(challenge);
    }
    for i in 1..n {
        powers[i] = powers[i - 1] * challenge;
    }
    powers
}

fn scalar_pow<S: CurveScalar>(mut base: S, mut exponent: usize) -> S {
    let mut result = S::one();
    while exponent != 0 {
        if exponent & 1 == 1 {
            result = result * base;
        }
        base = base * base;
        exponent >>= 1;
    }
    result
}

/// Derive a Fiat--Shamir challenge and fail closed on zero.
///
/// A zero challenge collapses the round's polynomial-identity check (the
/// soundness argument needs a nonzero sample), so it is rejected rather
/// than retried: honest transcripts derive zero with probability
/// 1/|Scalar| (~2^-250), which becomes the protocol's negligible
/// completeness error, and both `prove` and `verify` stay straight-line
/// code with a deterministic transcript schedule. For every nonzero
/// derivation (the only case ever observed or constructible without
/// breaking the hash) the byte-level transcript behavior is identical to
/// the previous retrying implementation.
fn challenge_nonzero<C: Curve>(
    transcript: &mut impl CryptoTranscript,
    label: &[u8],
) -> Result<C::Scalar, VerificationError> {
    let challenge = transcript.challenge::<C>(label).scalar;
    if challenge == C::Scalar::zero() {
        return Err(VerificationError::ZeroChallenge);
    }
    Ok(challenge)
}

fn append_ciphertext<C: Curve>(
    transcript: &mut impl CryptoTranscript,
    label: &[u8],
    ciphertext: &ElGamalCiphertextGeneric<C>,
) {
    transcript.append_message(b"bg12_ciphertext_label", label);
    transcript.append_point::<C>(b"bg12_ciphertext_c1", &ciphertext.c1);
    transcript.append_point::<C>(b"bg12_ciphertext_c2", &ciphertext.c2);
}

/// Append a whole ciphertext vector (single loop per function: Aeneas
/// loop-fixed-point limitation).
fn append_ciphertexts<C: Curve>(
    transcript: &mut impl CryptoTranscript,
    role: &[u8],
    ciphertexts: &[ElGamalCiphertextGeneric<C>],
) {
    for i in 0..ciphertexts.len() {
        transcript.append_message(b"bg12_ciphertext_label", role);
        transcript.append_point::<C>(b"bg12_ciphertext_c1", &ciphertexts[i].c1);
        transcript.append_point::<C>(b"bg12_ciphertext_c2", &ciphertexts[i].c2);
    }
}

fn append_statement<C: Curve>(
    transcript: &mut impl CryptoTranscript,
    input: &[ElGamalCiphertextGeneric<C>],
    output: &[ElGamalCiphertextGeneric<C>],
    public_key: &C::Point,
    c_permutation: &C::Point,
) {
    transcript.append_message(b"bg12_protocol", PROTOCOL_ID);
    transcript.append_message(b"bg12_deck_size", &(input.len() as u64).to_le_bytes());
    transcript.append_point::<C>(b"bg12_public_key", public_key);
    // Index loops with direct field appends (Aeneas extraction): pass the
    // point fields directly instead of a reference to the whole element.
    append_ciphertexts::<C>(transcript, b"input", input);
    append_ciphertexts::<C>(transcript, b"output", output);
    transcript.append_point::<C>(b"bg12_c_permutation", c_permutation);
}

fn ciphertext_msm<C: Curve>(
    ciphertexts: &[ElGamalCiphertextGeneric<C>],
    scalars: &[C::Scalar],
) -> Result<ElGamalCiphertextGeneric<C>, VerificationError> {
    if ciphertexts.is_empty() || ciphertexts.len() != scalars.len() {
        return Err(VerificationError::LengthMismatch);
    }
    // Index loops with push (no iter/map/collect): Aeneas extraction shapes.
    let mut c1_points: Vec<C::Point> = Vec::with_capacity(ciphertexts.len());
    let mut c2_points: Vec<C::Point> = Vec::with_capacity(ciphertexts.len());
    for i in 0..ciphertexts.len() {
        c1_points.push(ciphertexts[i].c1);
        c2_points.push(ciphertexts[i].c2);
    }
    Ok(ElGamalCiphertextGeneric {
        c1: C::Point::vartime_multiscalar_mul(scalars, &c1_points),
        c2: C::Point::vartime_multiscalar_mul(scalars, &c2_points),
    })
}

fn validate_statement<C: Curve>(
    input: &[ElGamalCiphertextGeneric<C>],
    output: &[ElGamalCiphertextGeneric<C>],
    public_key: &C::Point,
) -> Result<(), VerificationError> {
    if input.len() < 2 || input.len() != output.len() {
        return Err(VerificationError::InvalidInput);
    }
    // Index loops with flag+break (no iter/chain/any): Aeneas shapes.
    let mut all_valid = true;
    if public_key.is_identity() {
        all_valid = false;
    }
    // `is_valid()` (the inherent ElGamal method) instead of per-field
    // trait-method calls: identical semantics, extraction-friendly shape.
    if all_valid {
        for i in 0..input.len() {
            if !input[i].is_valid() {
                all_valid = false;
                break;
            }
        }
    }
    if all_valid {
        for i in 0..output.len() {
            if !output[i].is_valid() {
                all_valid = false;
                break;
            }
        }
    }
    if !all_valid {
        return Err(VerificationError::IdentityBasePoint);
    }
    Ok(())
}

fn validate_proof_shape<C: Curve>(
    proof: &BayerGrothShuffleProof<C>,
    n: usize,
) -> Result<(), VerificationError> {
    if proof.multi_exponentiation.alpha_response.len() != n
        || proof.product.a_response.len() != n
        || proof.product.b_response.len() != n
    {
        return Err(VerificationError::LengthMismatch);
    }
    // Straight-line checks (no `points.iter().any` over a local array of
    // associated-type elements — an Aeneas unsupported shape); the
    // acceptance condition is identical.
    let mexp = &proof.multi_exponentiation;
    let product = &proof.product;
    if proof.c_permutation.is_identity()
        || proof.c_permuted_powers.is_identity()
        || mexp.c_alpha.is_identity()
        || mexp.c_beta.is_identity()
        || mexp.ciphertext_0.c1.is_identity()
        || mexp.ciphertext_0.c2.is_identity()
        || mexp.ciphertext_1.c1.is_identity()
        || mexp.ciphertext_1.c2.is_identity()
        || product.c_d.is_identity()
        || product.c_delta.is_identity()
        || product.c_capital_delta.is_identity()
    {
        return Err(VerificationError::IdentityBasePoint);
    }
    Ok(())
}

impl<C: Curve> BayerGrothShuffleProof<C> {
    /// Hidden from Charon/Aeneas extraction builds (`skip-prover`): the
    /// prover samples random blinding (and its callers hold rejection
    /// loops); the deterministic verification path is extracted whole.
    #[cfg(not(feature = "skip-prover"))]
    pub fn prove(
        input: &[ElGamalCiphertextGeneric<C>],
        output: &[ElGamalCiphertextGeneric<C>],
        permutation: &[usize],
        rerandomizers: &[C::Scalar],
        public_key: &C::Point,
        rng: &mut (impl CryptoRng + RngCore),
        transcript: &mut impl CryptoTranscript,
    ) -> Result<Self, VerificationError> {
        validate_statement(input, output, public_key)?;
        let n = input.len();
        if rerandomizers.len() != n {
            return Err(VerificationError::InvalidRerandomizerCount);
        }
        if permutation.len() != n {
            return Err(VerificationError::InvalidPermutation);
        }
        let mut seen = vec![false; n];
        for &index in permutation {
            if index >= n || seen[index] {
                return Err(VerificationError::InvalidPermutation);
            }
            seen[index] = true;
        }
        for i in 0..n {
            if output[i] != input[permutation[i]].re_encrypt(public_key, &rerandomizers[i]) {
                return Err(VerificationError::InvalidInput);
            }
        }

        let commitment_key = CommitmentKey::<C>::derive(n)?;
        let pi: Vec<C::Scalar> = permutation
            .iter()
            .map(|index| C::Scalar::from_u64((*index as u64) + 1))
            .collect();
        let permutation_blinding = C::Scalar::random(rng);
        let c_permutation = commitment_key.vector_commit(&pi, permutation_blinding)?;

        append_statement::<C>(transcript, input, output, public_key, &c_permutation);
        let powers_challenge = challenge_nonzero::<C>(transcript, b"bg12_powers_challenge")?;
        let permuted_powers: Vec<C::Scalar> = permutation
            .iter()
            .map(|index| scalar_pow(powers_challenge, index + 1))
            .collect();
        let powers_blinding = C::Scalar::random(rng);
        let c_permuted_powers = commitment_key.vector_commit(&permuted_powers, powers_blinding)?;
        transcript.append_point::<C>(b"bg12_c_permuted_powers", &c_permuted_powers);
        let product_y = challenge_nonzero::<C>(transcript, b"bg12_product_y")?;
        let product_z = challenge_nonzero::<C>(transcript, b"bg12_product_z")?;

        let alpha: Vec<C::Scalar> = (0..n).map(|_| C::Scalar::random(rng)).collect();
        let beta = C::Scalar::random(rng);
        let alpha_blinding = C::Scalar::random(rng);
        let beta_blinding = C::Scalar::random(rng);
        let c_alpha = commitment_key.vector_commit(&alpha, alpha_blinding)?;
        let c_beta = commitment_key.scalar_commit(beta, beta_blinding);
        let tau_0 = C::Scalar::random(rng);
        let output_alpha = ciphertext_msm::<C>(output, &alpha)?;
        let ciphertext_0 = ElGamalCiphertextGeneric {
            c1: C::base_g() * tau_0 + output_alpha.c1,
            c2: C::base_g() * beta + *public_key * tau_0 + output_alpha.c2,
        };
        let rho_aggregate = -(0..n)
            .map(|i| rerandomizers[i] * permuted_powers[i])
            .sum::<C::Scalar>();
        let output_powers = ciphertext_msm::<C>(output, &permuted_powers)?;
        let ciphertext_1 = ElGamalCiphertextGeneric {
            c1: C::base_g() * rho_aggregate + output_powers.c1,
            c2: *public_key * rho_aggregate + output_powers.c2,
        };
        transcript.append_point::<C>(b"bg12_mexp_c_alpha", &c_alpha);
        transcript.append_point::<C>(b"bg12_mexp_c_beta", &c_beta);
        append_ciphertext::<C>(transcript, b"mexp_0", &ciphertext_0);
        append_ciphertext::<C>(transcript, b"mexp_1", &ciphertext_1);
        let mexp_challenge = challenge_nonzero::<C>(transcript, b"bg12_mexp_challenge")?;

        #[cfg(feature = "debug-print-challenges")]
        {
            use k256::elliptic_curve::PrimeField as _;
            let _ = &mexp_challenge;
        }
        let alpha_response: Vec<C::Scalar> = (0..n)
            .map(|i| alpha[i] + mexp_challenge * permuted_powers[i])
            .collect();
        let multi_exponentiation = MultiExponentiationArgument {
            c_alpha,
            c_beta,
            ciphertext_0,
            ciphertext_1,
            alpha_response,
            commitment_response: alpha_blinding + mexp_challenge * powers_blinding,
            beta,
            beta_blinding_response: beta_blinding,
            rerandomization_response: tau_0 + mexp_challenge * rho_aggregate,
        };

        let d: Vec<C::Scalar> = (0..n).map(|_| C::Scalar::random(rng)).collect();
        let d_blinding = C::Scalar::random(rng);
        let c_d = commitment_key.vector_commit(&d, d_blinding)?;
        let mut delta = vec![C::Scalar::zero(); n];
        delta[0] = d[0];
        for value in delta.iter_mut().take(n - 1).skip(1) {
            *value = C::Scalar::random(rng);
        }
        let mut delta_products = vec![C::Scalar::zero(); n];
        for i in 0..n - 1 {
            delta_products[i] = -(delta[i] * d[i + 1]);
        }
        let delta_blinding = C::Scalar::random(rng);
        let c_delta = commitment_key.vector_commit(&delta_products, delta_blinding)?;
        let a: Vec<C::Scalar> = (0..n)
            .map(|i| product_y * pi[i] + permuted_powers[i] - product_z)
            .collect();
        let mut b = vec![C::Scalar::one(); n];
        b[0] = a[0];
        for i in 1..n {
            b[i] = b[i - 1] * a[i];
        }
        let mut capital_delta = vec![C::Scalar::zero(); n];
        for i in 0..n - 1 {
            capital_delta[i] = delta[i + 1] - a[i + 1] * delta[i] - b[i] * d[i + 1];
        }
        let capital_delta_blinding = C::Scalar::random(rng);
        let c_capital_delta =
            commitment_key.vector_commit(&capital_delta, capital_delta_blinding)?;
        transcript.append_point::<C>(b"bg12_product_c_d", &c_d);
        transcript.append_point::<C>(b"bg12_product_c_delta", &c_delta);
        transcript.append_point::<C>(b"bg12_product_c_capital_delta", &c_capital_delta);
        let product_challenge = challenge_nonzero::<C>(transcript, b"bg12_product_challenge")?;
        let a_response: Vec<C::Scalar> = (0..n).map(|i| product_challenge * a[i] + d[i]).collect();
        let b_response: Vec<C::Scalar> = (0..n)
            .map(|i| product_challenge * b[i] + delta[i])
            .collect();
        let a_blinding = product_y * permutation_blinding + powers_blinding;
        let product = ProductArgument {
            c_d,
            c_delta,
            c_capital_delta,
            a_response,
            b_response,
            r_response: product_challenge * a_blinding + d_blinding,
            s_response: product_challenge * capital_delta_blinding + delta_blinding,
        };

        Ok(Self {
            c_permutation,
            c_permuted_powers,
            multi_exponentiation,
            product,
        })
    }

    pub fn verify(
        &self,
        input: &[ElGamalCiphertextGeneric<C>],
        output: &[ElGamalCiphertextGeneric<C>],
        public_key: &C::Point,
        transcript: &mut impl CryptoTranscript,
    ) -> Result<(), VerificationError> {
        validate_statement(input, output, public_key)?;
        let n = input.len();
        validate_proof_shape(self, n)?;
        let commitment_key = CommitmentKey::<C>::derive(n)?;

        append_statement::<C>(transcript, input, output, public_key, &self.c_permutation);
        let powers_challenge = challenge_nonzero::<C>(transcript, b"bg12_powers_challenge")?;
        transcript.append_point::<C>(b"bg12_c_permuted_powers", &self.c_permuted_powers);
        let product_y = challenge_nonzero::<C>(transcript, b"bg12_product_y")?;
        let product_z = challenge_nonzero::<C>(transcript, b"bg12_product_z")?;

        let mexp = &self.multi_exponentiation;
        transcript.append_point::<C>(b"bg12_mexp_c_alpha", &mexp.c_alpha);
        transcript.append_point::<C>(b"bg12_mexp_c_beta", &mexp.c_beta);
        append_ciphertext::<C>(transcript, b"mexp_0", &mexp.ciphertext_0);
        append_ciphertext::<C>(transcript, b"mexp_1", &mexp.ciphertext_1);
        let mexp_challenge = challenge_nonzero::<C>(transcript, b"bg12_mexp_challenge")?;

        #[cfg(feature = "debug-print-challenges")]
        {
            use k256::elliptic_curve::PrimeField as _;
            let _ = &mexp_challenge;
        }

        let powers = public_powers::<C>(powers_challenge, n);
        let expected_ciphertext_1 = ciphertext_msm::<C>(input, &powers)?;
        if mexp.ciphertext_1 != expected_ciphertext_1 {
            return Err(VerificationError::InvalidBayerGrothProof);
        }
        let commitment_lhs = self.c_permuted_powers * mexp_challenge + mexp.c_alpha;
        let commitment_rhs =
            commitment_key.vector_commit(&mexp.alpha_response, mexp.commitment_response)?;
        if commitment_lhs != commitment_rhs
            || mexp.c_beta != commitment_key.scalar_commit(mexp.beta, mexp.beta_blinding_response)
        {
            return Err(VerificationError::InvalidBayerGrothProof);
        }
        let output_response = ciphertext_msm::<C>(output, &mexp.alpha_response)?;
        let ciphertext_lhs: ElGamalCiphertextGeneric<C> = ElGamalCiphertextGeneric {
            c1: mexp.ciphertext_0.c1 + mexp.ciphertext_1.c1 * mexp_challenge,
            c2: mexp.ciphertext_0.c2 + mexp.ciphertext_1.c2 * mexp_challenge,
        };
        let ciphertext_rhs: ElGamalCiphertextGeneric<C> = ElGamalCiphertextGeneric {
            c1: C::base_g() * mexp.rerandomization_response + output_response.c1,
            c2: C::base_g() * mexp.beta
                + *public_key * mexp.rerandomization_response
                + output_response.c2,
        };
        if ciphertext_lhs != ciphertext_rhs {
            return Err(VerificationError::InvalidBayerGrothProof);
        }

        let product = &self.product;
        transcript.append_point::<C>(b"bg12_product_c_d", &product.c_d);
        transcript.append_point::<C>(b"bg12_product_c_delta", &product.c_delta);
        transcript.append_point::<C>(b"bg12_product_c_capital_delta", &product.c_capital_delta);
        let product_challenge = challenge_nonzero::<C>(transcript, b"bg12_product_challenge")?;
        // Manual fill (no `vec![-x; n]`): Aeneas extraction shape.
        let mut minus_z: Vec<C::Scalar> = Vec::with_capacity(n);
        for _ in 0..n {
            minus_z.push(-product_z);
        }
        let c_minus_z = commitment_key.vector_commit(&minus_z, C::Scalar::zero())?;
        let c_a = self.c_permutation * product_y + self.c_permuted_powers;
        let product_check_1_lhs = product.c_d + (c_a + c_minus_z) * product_challenge;
        let product_check_1_rhs =
            commitment_key.vector_commit(&product.a_response, product.r_response)?;
        if product_check_1_lhs != product_check_1_rhs {
            return Err(VerificationError::InvalidBayerGrothProof);
        }
        // Index loop (no iter_mut/enumerate/take): Aeneas extraction shape.
        let mut recurrence: Vec<C::Scalar> = Vec::with_capacity(n);
        for _ in 0..n {
            recurrence.push(C::Scalar::zero());
        }
        for i in 0..n - 1 {
            recurrence[i] = product_challenge * product.b_response[i + 1]
                - product.b_response[i] * product.a_response[i + 1];
        }
        let product_check_2_lhs = product.c_delta + product.c_capital_delta * product_challenge;
        let product_check_2_rhs = commitment_key.vector_commit(&recurrence, product.s_response)?;
        if product_check_2_lhs != product_check_2_rhs
            || product.b_response[0] != product.a_response[0]
        {
            return Err(VerificationError::InvalidBayerGrothProof);
        }
        // Accumulating loop with an inline power recurrence (no map/fold,
        // no calls into generic scalar_pow): Aeneas extraction shape.
        let mut expected_product = C::Scalar::one();
        let mut xpow = C::Scalar::one();
        for i in 1..=n {
            xpow = xpow * powers_challenge;
            let factor =
                product_y * C::Scalar::from_u64(i as u64) + xpow - product_z;
            expected_product = expected_product * factor;
        }
        if product.b_response[n - 1] != product_challenge * expected_product {
            return Err(VerificationError::InvalidBayerGrothProof);
        }
        Ok(())
    }
}
