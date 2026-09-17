use super::{ContributionBranch, CrossKeyNegationProof, SlotContributionOrProof};
use crate::transcript_ext::CryptoTranscript;
use poker_protocol_bg::BayerGrothShuffleProof;
use poker_protocol_core::{
    Curve, CurvePoint, CurveScalar, ElGamalCiphertextGeneric, VerificationError,
};
use rand_core::{CryptoRng, RngCore};
use std::collections::{HashMap, HashSet};
use std::time::Instant;

const PROTOCOL_ID: &[u8] = b"poker/reconstruction";
pub const RECONSTRUCTION_PROOF_VERSION: u8 = 3;
pub const RECONSTRUCTION_PROOF_LABEL: &[u8] = b"zk_reconstruct_proof";

/// Public statement proved by reconstruction.
///
/// `prior_state_digest` is the bridge to the poker state machine: the host/AIR
/// must ensure it authenticates the previous hand assignments and their
/// init-deck lineage.  This proof checks the cryptographic relation against the
/// digest, but cannot reconstruct historical state by itself.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReconstructionStatement<C: Curve> {
    pub version: u8,
    /// Application-defined digest binding game id, table id and curve/domain.
    pub context_digest: [u8; 32],
    /// Monotonic reconstruction round, included to prevent proof replay.
    pub reconstruction_epoch: u64,
    /// Digest of the authenticated previous-round state.
    pub prior_state_digest: [u8; 32],
    pub aggregate_pk: C::Point,
    pub owner_pk: C::Point,
    /// Canonical public card points in their protocol-defined order.
    pub cards: Vec<C::Point>,
    /// Previous-round owner-residual ciphertexts.
    pub residual_carriers: Vec<ElGamalCiphertextGeneric<C>>,
    /// Canonical-slot contributions, each encrypting either zero or `-card_i`.
    pub contributions: Vec<ElGamalCiphertextGeneric<C>>,
}

impl<C: Curve> ReconstructionStatement<C> {
    pub fn validate(&self) -> Result<(), VerificationError> {
        let n = self.cards.len();
        let k = self.residual_carriers.len();
        if self.version != RECONSTRUCTION_PROOF_VERSION {
            return Err(VerificationError::InvalidInput);
        }
        if n < 2 || k == 0 || k > n || self.contributions.len() != n {
            return Err(VerificationError::LengthMismatch);
        }
        if self.aggregate_pk.is_identity() || self.owner_pk.is_identity() {
            return Err(VerificationError::InvalidPublicKey);
        }
        if self.cards.iter().any(CurvePoint::is_identity) {
            return Err(VerificationError::IdentityBasePoint);
        }
        let unique_cards = self
            .cards
            .iter()
            .map(|card| card.compress().as_ref().to_vec())
            .collect::<HashSet<_>>();
        if unique_cards.len() != n {
            return Err(VerificationError::InvalidInput);
        }
        if self
            .residual_carriers
            .iter()
            .chain(&self.contributions)
            .any(|ciphertext| !ciphertext.is_valid())
        {
            return Err(VerificationError::InvalidCiphertext);
        }
        Ok(())
    }

    /// Canonical transcript encoding shared by prover, verifier, precompile and
    /// eventually the AIR binding.  Do not reorder or omit fields when adding a
    /// host implementation.
    pub fn append_to_transcript(&self, transcript: &mut impl CryptoTranscript) {
        transcript.append_message(b"reconstruct_protocol", PROTOCOL_ID);
        transcript.append_message(b"reconstruct_version", &[self.version]);
        transcript.append_message(b"reconstruct_context_digest", &self.context_digest);
        transcript.append_message(
            b"reconstruct_epoch",
            &self.reconstruction_epoch.to_le_bytes(),
        );
        transcript.append_message(b"reconstruct_prior_state_digest", &self.prior_state_digest);
        transcript.append_message(
            b"reconstruct_card_count",
            &(self.cards.len() as u64).to_le_bytes(),
        );
        transcript.append_message(
            b"reconstruct_residual_carrier_count",
            &(self.residual_carriers.len() as u64).to_le_bytes(),
        );
        transcript.append_point::<C>(b"reconstruct_aggregate_pk", &self.aggregate_pk);
        transcript.append_point::<C>(b"reconstruct_owner_pk", &self.owner_pk);
        for card in &self.cards {
            transcript.append_point::<C>(b"reconstruct_card", card);
        }
        for ciphertext in &self.residual_carriers {
            append_ciphertext::<C>(transcript, b"residual_carrier", ciphertext);
        }
        for ciphertext in &self.contributions {
            append_ciphertext::<C>(transcript, b"contribution", ciphertext);
        }
    }
}

/// Reconstruction proof package.
///
/// The hidden residual-carrier-to-canonical mapping is represented only by the
/// Bayer--Groth witness during proving.  It is not stored in this structure.
#[derive(Debug, Clone)]
pub struct ReconstructProof<C: Curve> {
    /// One aggregate-key encryption of `-plaintext(residual_carrier_j)` per carrier.
    pub negative_contributions: Vec<ElGamalCiphertextGeneric<C>>,
    pub cross_key_proofs: Vec<CrossKeyNegationProof<C>>,
    /// Proves that statement.contributions is a rerandomized permutation of
    /// negative_contributions followed by deterministic zero encryptions.
    pub contribution_shuffle_proof: BayerGrothShuffleProof<C>,
    /// Per-canonical-slot proof of plaintext membership `{0, -cards[i]}`.
    pub slot_membership_proofs: Vec<SlotContributionOrProof<C>>,
}

/// Optional stage timings collected by the benchmark harness.  The default
/// proving and verification APIs do not collect timings or change protocol
/// bytes; callers opt in through `*_with_profile`.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ReconstructionProfile {
    pub residual_setup_ns: u128,
    pub cross_key_ns: u128,
    pub bayer_groth_ns: u128,
    pub slot_or_ns: u128,
    pub verify_cross_key_ns: u128,
    pub verify_bayer_groth_ns: u128,
    pub verify_slot_or_ns: u128,
}

fn append_ciphertext<C: Curve>(
    transcript: &mut impl CryptoTranscript,
    role: &[u8],
    ciphertext: &ElGamalCiphertextGeneric<C>,
) {
    transcript.append_message(b"reconstruct_ciphertext_role", role);
    transcript.append_point::<C>(b"reconstruct_ciphertext_c1", &ciphertext.c1);
    transcript.append_point::<C>(b"reconstruct_ciphertext_c2", &ciphertext.c2);
}

/// Public zero encryptions used to pad the Bayer--Groth input to the deck size.
/// Their known randomness is harmless: they are known-zero inputs, and the
/// shuffle rerandomizes them before they become canonical contributions.
fn deterministic_zero_contributions<C: Curve>(
    count: usize,
    aggregate_pk: &C::Point,
) -> Result<Vec<(ElGamalCiphertextGeneric<C>, C::Scalar)>, VerificationError> {
    let mut output = Vec::with_capacity(count);
    for i in 0..count {
        let randomness = C::Scalar::from_u64((i as u64) + 1);
        if randomness == C::Scalar::zero() {
            return Err(VerificationError::InvalidInput);
        }
        let ciphertext = ElGamalCiphertextGeneric::<C>::encrypt(
            &C::Point::identity(),
            aggregate_pk,
            &randomness,
        );
        if !ciphertext.is_valid() {
            return Err(VerificationError::InvalidCiphertext);
        }
        output.push((ciphertext, randomness));
    }
    Ok(output)
}

fn ciphertext_add<C: Curve>(
    left: &ElGamalCiphertextGeneric<C>,
    right: &ElGamalCiphertextGeneric<C>,
) -> ElGamalCiphertextGeneric<C> {
    ElGamalCiphertextGeneric {
        c1: left.c1 + right.c1,
        c2: left.c2 + right.c2,
    }
}

/// Deterministic canonical base deck under the aggregate key.
///
/// Card points and their canonical order are public, so public base randomness
/// does not reveal private information.  Player contributions add fresh hidden
/// randomness before the next shuffle.
pub fn canonical_base_deck<C: Curve>(
    cards: &[C::Point],
    aggregate_pk: &C::Point,
) -> Result<Vec<ElGamalCiphertextGeneric<C>>, VerificationError> {
    if cards.len() < 2 || aggregate_pk.is_identity() {
        return Err(VerificationError::InvalidInput);
    }
    cards
        .iter()
        .enumerate()
        .map(|(i, card)| {
            if card.is_identity() {
                return Err(VerificationError::IdentityBasePoint);
            }
            let randomness = C::Scalar::from_u64((i as u64) + 1);
            let ciphertext =
                ElGamalCiphertextGeneric::<C>::encrypt(card, aggregate_pk, &randomness);
            if ciphertext.is_valid() {
                Ok(ciphertext)
            } else {
                Err(VerificationError::InvalidCiphertext)
            }
        })
        .collect()
}

/// Homomorphically apply one verified player's contribution vector to a deck.
pub fn apply_reconstruction_contributions<C: Curve>(
    deck: &[ElGamalCiphertextGeneric<C>],
    contributions: &[ElGamalCiphertextGeneric<C>],
) -> Result<Vec<ElGamalCiphertextGeneric<C>>, VerificationError> {
    if deck.is_empty() || deck.len() != contributions.len() {
        return Err(VerificationError::LengthMismatch);
    }
    Ok(deck
        .iter()
        .zip(contributions)
        .map(|(card, contribution)| ciphertext_add(card, contribution))
        .collect())
}

impl<C: Curve> ReconstructProof<C> {
    /// Generate the public statement and proof together.  Returning them as
    /// one pair prevents callers from accidentally proving against a different
    /// contribution vector than the one sent to the verifier/precompile.
    #[allow(clippy::too_many_arguments)]
    pub fn prove(
        context_digest: [u8; 32],
        reconstruction_epoch: u64,
        prior_state_digest: [u8; 32],
        cards: Vec<C::Point>,
        residual_carriers: Vec<ElGamalCiphertextGeneric<C>>,
        owner_sk: &C::Scalar,
        owner_pk: &C::Point,
        aggregate_pk: &C::Point,
        rng: &mut (impl CryptoRng + RngCore),
        transcript: &mut impl CryptoTranscript,
    ) -> Result<(ReconstructionStatement<C>, Self), VerificationError> {
        Self::prove_with_profile(
            context_digest,
            reconstruction_epoch,
            prior_state_digest,
            cards,
            residual_carriers,
            owner_sk,
            owner_pk,
            aggregate_pk,
            rng,
            transcript,
            None,
        )
    }

    /// Prove while optionally collecting stage timings for reproducibility
    /// experiments.  `profile` is deliberately outside the proof object.
    #[allow(clippy::too_many_arguments)]
    pub fn prove_with_profile(
        context_digest: [u8; 32],
        reconstruction_epoch: u64,
        prior_state_digest: [u8; 32],
        cards: Vec<C::Point>,
        residual_carriers: Vec<ElGamalCiphertextGeneric<C>>,
        owner_sk: &C::Scalar,
        owner_pk: &C::Point,
        aggregate_pk: &C::Point,
        rng: &mut (impl CryptoRng + RngCore),
        transcript: &mut impl CryptoTranscript,
        mut profile: Option<&mut ReconstructionProfile>,
    ) -> Result<(ReconstructionStatement<C>, Self), VerificationError> {
        let setup_start = profile.as_ref().map(|_| Instant::now());
        let n = cards.len();
        let k = residual_carriers.len();
        if n < 2 || k == 0 || k > n {
            return Err(VerificationError::LengthMismatch);
        }
        if *owner_sk == C::Scalar::zero()
            || owner_pk.is_identity()
            || *owner_pk != C::base_g() * *owner_sk
        {
            return Err(VerificationError::InvalidPublicKey);
        }
        if aggregate_pk.is_identity() {
            return Err(VerificationError::InvalidPublicKey);
        }

        let card_indices = cards
            .iter()
            .enumerate()
            .map(|(i, card)| (card.compress().as_ref().to_vec(), i))
            .collect::<HashMap<_, _>>();
        if card_indices.len() != n || cards.iter().any(CurvePoint::is_identity) {
            return Err(VerificationError::InvalidInput);
        }

        let mut seen_plaintexts = HashSet::with_capacity(k);
        let mut canonical_indices = Vec::with_capacity(k);
        let mut negative_contributions = Vec::with_capacity(k);
        let mut negative_randomness = Vec::with_capacity(k);
        for residual_carrier in &residual_carriers {
            if !residual_carrier.is_valid() {
                return Err(VerificationError::InvalidCiphertext);
            }
            let plaintext = residual_carrier.decrypt(owner_sk);
            let plaintext_key = plaintext.compress().as_ref().to_vec();
            let canonical_index = *card_indices
                .get(&plaintext_key)
                .ok_or(VerificationError::InvalidPlaintext)?;
            if !seen_plaintexts.insert(plaintext_key) {
                return Err(VerificationError::InvalidPlaintext);
            }

            // Group negation is expressed as `identity - plaintext` because the
            // generic CurvePoint trait intentionally exposes subtraction only.
            let negative_plaintext = C::Point::identity() - plaintext;
            let (randomness, ciphertext) = loop {
                let randomness = C::Scalar::random(rng);
                if randomness == C::Scalar::zero() {
                    continue;
                }
                let ciphertext = ElGamalCiphertextGeneric::<C>::encrypt(
                    &negative_plaintext,
                    aggregate_pk,
                    &randomness,
                );
                if ciphertext.is_valid() {
                    break (randomness, ciphertext);
                }
            };
            canonical_indices.push(canonical_index);
            negative_randomness.push(randomness);
            negative_contributions.push(ciphertext);
        }

        let zero_contributions = deterministic_zero_contributions::<C>(n - k, aggregate_pk)?;
        let mut shuffle_input = negative_contributions.clone();
        shuffle_input.extend(
            zero_contributions
                .iter()
                .map(|(ciphertext, _)| ciphertext.clone()),
        );
        let mut input_randomness = negative_randomness.clone();
        input_randomness.extend(zero_contributions.iter().map(|(_, randomness)| *randomness));

        // Bayer--Groth uses the output-to-input convention:
        // `output[i] = rerandomize(input[permutation[i]])`.
        let mut permutation = vec![usize::MAX; n];
        for (negative_position, canonical_index) in canonical_indices.iter().enumerate() {
            permutation[*canonical_index] = negative_position;
        }
        let mut zero_cursor = 0usize;
        for input_index in &mut permutation {
            if *input_index == usize::MAX {
                *input_index = k + zero_cursor;
                zero_cursor += 1;
            }
        }

        let mut rerandomizers = Vec::with_capacity(n);
        let mut contribution_randomness = Vec::with_capacity(n);
        let mut contributions = Vec::with_capacity(n);
        let mut branches = Vec::with_capacity(n);
        for i in 0..n {
            let input_index = permutation[i];
            let (rerandomizer, total_randomness, contribution) = loop {
                let rerandomizer = C::Scalar::random(rng);
                let total_randomness = input_randomness[input_index] + rerandomizer;
                if total_randomness == C::Scalar::zero() {
                    continue;
                }
                let contribution =
                    shuffle_input[input_index].re_encrypt(aggregate_pk, &rerandomizer);
                if contribution.is_valid() {
                    break (rerandomizer, total_randomness, contribution);
                }
            };
            rerandomizers.push(rerandomizer);
            contribution_randomness.push(total_randomness);
            contributions.push(contribution);
            branches.push(if input_index < k {
                ContributionBranch::NegativeCard
            } else {
                ContributionBranch::Zero
            });
        }

        let statement = ReconstructionStatement {
            version: RECONSTRUCTION_PROOF_VERSION,
            context_digest,
            reconstruction_epoch,
            prior_state_digest,
            aggregate_pk: *aggregate_pk,
            owner_pk: *owner_pk,
            cards,
            residual_carriers,
            contributions,
        };
        statement.validate()?;
        statement.append_to_transcript(transcript);
        if let (Some(start), Some(profile)) = (setup_start, profile.as_deref_mut()) {
            profile.residual_setup_ns = start.elapsed().as_nanos();
        }

        let cross_key_start = profile.as_ref().map(|_| Instant::now());
        let mut cross_key_proofs = Vec::with_capacity(k);
        for j in 0..k {
            cross_key_proofs.push(CrossKeyNegationProof::prove(
                &statement.residual_carriers[j],
                &negative_contributions[j],
                owner_sk,
                &negative_randomness[j],
                owner_pk,
                aggregate_pk,
                rng,
                transcript,
            )?);
        }
        if let (Some(start), Some(profile)) = (cross_key_start, profile.as_deref_mut()) {
            profile.cross_key_ns = start.elapsed().as_nanos();
        }

        let bayer_groth_start = profile.as_ref().map(|_| Instant::now());
        let contribution_shuffle_proof = BayerGrothShuffleProof::prove(
            &shuffle_input,
            &statement.contributions,
            &permutation,
            &rerandomizers,
            aggregate_pk,
            rng,
            transcript,
        )?;
        if let (Some(start), Some(profile)) = (bayer_groth_start, profile.as_deref_mut()) {
            profile.bayer_groth_ns = start.elapsed().as_nanos();
        }

        let slot_or_start = profile.as_ref().map(|_| Instant::now());
        let mut slot_membership_proofs = Vec::with_capacity(n);
        for i in 0..n {
            slot_membership_proofs.push(SlotContributionOrProof::prove(
                &statement.cards[i],
                &statement.contributions[i],
                &contribution_randomness[i],
                branches[i],
                aggregate_pk,
                rng,
                transcript,
            )?);
        }
        if let (Some(start), Some(profile)) = (slot_or_start, profile.as_deref_mut()) {
            profile.slot_or_ns = start.elapsed().as_nanos();
        }

        Ok((
            statement,
            Self {
                negative_contributions,
                cross_key_proofs,
                contribution_shuffle_proof,
                slot_membership_proofs,
            },
        ))
    }

    pub fn verify(
        &self,
        statement: &ReconstructionStatement<C>,
        transcript: &mut impl CryptoTranscript,
    ) -> Result<(), VerificationError> {
        self.verify_with_profile(statement, transcript, None)
    }

    /// Verify while optionally collecting component timings for experiments.
    pub fn verify_with_profile(
        &self,
        statement: &ReconstructionStatement<C>,
        transcript: &mut impl CryptoTranscript,
        mut profile: Option<&mut ReconstructionProfile>,
    ) -> Result<(), VerificationError> {
        statement.validate()?;
        let n = statement.cards.len();
        let k = statement.residual_carriers.len();
        if self.negative_contributions.len() != k
            || self.cross_key_proofs.len() != k
            || self.slot_membership_proofs.len() != n
            || self
                .negative_contributions
                .iter()
                .any(|ciphertext| !ciphertext.is_valid())
        {
            return Err(VerificationError::LengthMismatch);
        }

        statement.append_to_transcript(transcript);
        let cross_key_start = profile.as_ref().map(|_| Instant::now());
        for j in 0..k {
            self.cross_key_proofs[j]
                .verify(
                    &statement.residual_carriers[j],
                    &self.negative_contributions[j],
                    &statement.owner_pk,
                    &statement.aggregate_pk,
                    transcript,
                )
                .map_err(|_| VerificationError::InvalidProofAtPosition(j))?;
        }
        if let (Some(start), Some(profile)) = (cross_key_start, profile.as_deref_mut()) {
            profile.verify_cross_key_ns = start.elapsed().as_nanos();
        }

        let zero_contributions =
            deterministic_zero_contributions::<C>(n - k, &statement.aggregate_pk)?;
        let mut shuffle_input = self.negative_contributions.clone();
        shuffle_input.extend(
            zero_contributions
                .iter()
                .map(|(ciphertext, _)| ciphertext.clone()),
        );
        let bayer_groth_start = profile.as_ref().map(|_| Instant::now());
        self.contribution_shuffle_proof.verify(
            &shuffle_input,
            &statement.contributions,
            &statement.aggregate_pk,
            transcript,
        )?;
        if let (Some(start), Some(profile)) = (bayer_groth_start, profile.as_deref_mut()) {
            profile.verify_bayer_groth_ns = start.elapsed().as_nanos();
        }

        let slot_or_start = profile.as_ref().map(|_| Instant::now());
        for i in 0..n {
            self.slot_membership_proofs[i]
                .verify(
                    &statement.cards[i],
                    &statement.contributions[i],
                    &statement.aggregate_pk,
                    transcript,
                )
                .map_err(|_| VerificationError::InvalidProofAtPosition(i))?;
        }
        if let (Some(start), Some(profile)) = (slot_or_start, profile.as_deref_mut()) {
            profile.verify_slot_or_ns = start.elapsed().as_nanos();
        }
        Ok(())
    }
}
