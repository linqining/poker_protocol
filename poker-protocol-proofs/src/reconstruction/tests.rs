use super::{
    apply_reconstruction_contributions, canonical_base_deck, ContributionBranch, ReconstructProof,
    ReconstructionStatement, SlotContributionOrProof, RECONSTRUCTION_PROOF_LABEL,
};
use crate::reconstruction::CrossKeyNegationProof;
use crate::transcript_ext::{CryptoTranscript, MerlinTranscript};
use curve25519_dalek::{ristretto::RistrettoPoint, scalar::Scalar};
use poker_protocol_core::{
    Curve, CurvePoint, CurveScalar, ElGamalCiphertextGeneric, RistrettoCurve,
};

type Ciphertext = ElGamalCiphertextGeneric<RistrettoCurve>;

struct ReconstructionFixture {
    statement: ReconstructionStatement<RistrettoCurve>,
    proof: ReconstructProof<RistrettoCurve>,
    aggregate_sk: Scalar,
    selected_indices: Vec<usize>,
}

fn scalar(value: u64) -> Scalar {
    <Scalar as CurveScalar>::from_u64(value)
}

fn fixture(
    n: usize,
    selected_indices: &[usize],
    transcript_label: &'static [u8],
) -> ReconstructionFixture {
    let cards = (0..n)
        .map(|i| RistrettoCurve::hash_to_curve(format!("reconstruction-card-{i}").as_bytes()))
        .collect::<Vec<_>>();
    let owner_sk = scalar(73);
    let other_players_sk = scalar(29);
    let aggregate_sk = owner_sk + other_players_sk;
    let owner_pk = RistrettoCurve::base_g() * owner_sk;
    let aggregate_pk = RistrettoCurve::base_g() * aggregate_sk;

    // These model the output of the authenticated prior-hand lineage: after
    // every non-owner reveal token is removed, each card remains encrypted
    // only under owner_pk with hidden accumulated randomness.
    let residual_carriers = selected_indices
        .iter()
        .enumerate()
        .map(|(j, index)| Ciphertext::encrypt(&cards[*index], &owner_pk, &scalar(1000 + j as u64)))
        .collect::<Vec<_>>();

    let mut transcript = MerlinTranscript::new(transcript_label);
    let (statement, proof) = ReconstructProof::prove(
        [7u8; 32],
        11,
        [9u8; 32],
        cards,
        residual_carriers,
        &owner_sk,
        &owner_pk,
        &aggregate_pk,
        &mut rand_core::OsRng,
        &mut transcript,
    )
    .unwrap();

    ReconstructionFixture {
        statement,
        proof,
        aggregate_sk,
        selected_indices: selected_indices.to_vec(),
    }
}

fn verify(
    fixture: &ReconstructionFixture,
    transcript_label: &'static [u8],
) -> Result<(), poker_protocol_core::VerificationError> {
    let mut transcript = MerlinTranscript::new(transcript_label);
    fixture.proof.verify(&fixture.statement, &mut transcript)
}

#[test]
fn reconstruction_honest_and_plaintext_semantics() {
    let fixture = fixture(8, &[1, 5], RECONSTRUCTION_PROOF_LABEL);
    verify(&fixture, RECONSTRUCTION_PROOF_LABEL).unwrap();

    // Each contribution decrypts to exactly zero or -card_i under the common
    // aggregate key.  No public coefficient is needed to inspect randomness.
    for (i, contribution) in fixture.statement.contributions.iter().enumerate() {
        let plaintext = contribution.decrypt(&fixture.aggregate_sk);
        if fixture.selected_indices.contains(&i) {
            assert_eq!(
                plaintext,
                RistrettoPoint::identity() - fixture.statement.cards[i]
            );
        } else {
            assert!(plaintext.is_identity());
        }
    }

    let base_deck = canonical_base_deck::<RistrettoCurve>(
        &fixture.statement.cards,
        &fixture.statement.aggregate_pk,
    )
    .unwrap();
    let rebuilt =
        apply_reconstruction_contributions(&base_deck, &fixture.statement.contributions).unwrap();
    for (i, ciphertext) in rebuilt.iter().enumerate() {
        let plaintext = ciphertext.decrypt(&fixture.aggregate_sk);
        if fixture.selected_indices.contains(&i) {
            assert!(plaintext.is_identity());
        } else {
            assert_eq!(plaintext, fixture.statement.cards[i]);
        }
    }
}

#[test]
fn reconstruction_all_cards_removed() {
    let fixture = fixture(8, &(0..8).collect::<Vec<_>>(), b"reconstruction-all");
    verify(&fixture, b"reconstruction-all").unwrap();
    assert_eq!(fixture.proof.negative_contributions.len(), 8);
    assert_eq!(fixture.proof.slot_membership_proofs.len(), 8);
}

#[test]
fn reconstruction_rejects_statement_and_proof_tampering() {
    let fixture = fixture(8, &[1, 5], b"reconstruction-tamper");

    let mut tampered_statement = fixture.statement.clone();
    tampered_statement.contributions[2].c2 += RistrettoCurve::base_g();
    let mut transcript = MerlinTranscript::new(b"reconstruction-tamper");
    assert!(fixture
        .proof
        .verify(&tampered_statement, &mut transcript)
        .is_err());

    let mut tampered_proof = fixture.proof.clone();
    tampered_proof.negative_contributions[0].c2 += RistrettoCurve::base_g();
    let mut transcript = MerlinTranscript::new(b"reconstruction-tamper");
    assert!(tampered_proof
        .verify(&fixture.statement, &mut transcript)
        .is_err());

    let mut tampered_or = fixture.proof.clone();
    tampered_or.slot_membership_proofs[0].responses[0] += scalar(1);
    let mut transcript = MerlinTranscript::new(b"reconstruction-tamper");
    assert!(tampered_or
        .verify(&fixture.statement, &mut transcript)
        .is_err());
}

#[test]
fn reconstruction_rejects_wrong_context_epoch_and_prior_state() {
    let fixture = fixture(8, &[1, 5], b"reconstruction-binding");

    for mutation in 0..3 {
        let mut statement = fixture.statement.clone();
        match mutation {
            0 => statement.context_digest[0] ^= 1,
            1 => statement.reconstruction_epoch += 1,
            _ => statement.prior_state_digest[0] ^= 1,
        }
        let mut transcript = MerlinTranscript::new(b"reconstruction-binding");
        assert!(fixture.proof.verify(&statement, &mut transcript).is_err());
    }

    assert!(verify(&fixture, b"different-outer-transcript").is_err());
}

#[test]
fn reconstruction_shared_refinement_vector() {
    let vector: serde_json::Value = serde_json::from_str(include_str!(
        "../../../paper/experiments/reconstruction_refinement_vector.json"
    ))
    .unwrap();
    const REMOVED_BITMAP: [bool; 8] =
        [false, true, false, false, true, false, false, false];
    assert_eq!(vector["version"].as_u64(), Some(super::RECONSTRUCTION_PROOF_VERSION as u64));
    assert_eq!(vector["reconstruction_epoch"].as_u64(), Some(11));
    assert_eq!(vector["card_count"].as_u64(), Some(8));
    assert_eq!(vector["residual_carrier_count"].as_u64(), Some(2));
    assert_eq!(vector["removed_bitmap"].as_str(), Some("01001000"));
    assert_eq!(
        REMOVED_BITMAP.iter().filter(|removed| **removed).count(),
        vector["residual_carrier_count"].as_u64().unwrap() as usize
    );
}

#[test]
fn slot_or_rejects_cross_slot_plaintext() {
    let card_a = RistrettoCurve::hash_to_curve(b"reconstruction-attack-a");
    let card_b = RistrettoCurve::hash_to_curve(b"reconstruction-attack-b");
    assert_ne!(card_a, card_b);
    let aggregate_pk = RistrettoCurve::base_g() * scalar(91);
    let randomness = scalar(17);

    // Maliciously place Enc(-A) at B's canonical slot.  Bayer--Groth could
    // prove that this ciphertext came from the input multiset, but B's slot OR
    // relation requires Enc(0) or Enc(-B), so witness construction fails.
    let misplaced = Ciphertext::encrypt(
        &(RistrettoPoint::identity() - card_a),
        &aggregate_pk,
        &randomness,
    );
    let mut transcript = MerlinTranscript::new(b"reconstruction-misplaced");
    assert!(SlotContributionOrProof::<RistrettoCurve>::prove(
        &card_b,
        &misplaced,
        &randomness,
        ContributionBranch::NegativeCard,
        &aggregate_pk,
        &mut rand_core::OsRng,
        &mut transcript,
    )
    .is_err());
}

#[test]
fn cross_key_rejects_foreign_card_negation() {
    // Non-owner veto attempt: the attacker's authenticated carrier decrypts to
    // card A, but the negative contribution encrypts -B for someone else's
    // card B.  The joint c2 equation cannot hold without DL(R.c1), so honest
    // witness construction is impossible and prove must fail closed.
    let card_a = RistrettoCurve::hash_to_curve(b"cross-key-owned-a");
    let card_b = RistrettoCurve::hash_to_curve(b"cross-key-foreign-b");
    let owner_sk = scalar(73);
    let owner_pk = RistrettoCurve::base_g() * owner_sk;
    let aggregate_pk = RistrettoCurve::base_g() * scalar(102);

    let residual_carrier = Ciphertext::encrypt(&card_a, &owner_pk, &scalar(11));
    let foreign_negation = Ciphertext::encrypt(
        &(RistrettoPoint::identity() - card_b),
        &aggregate_pk,
        &scalar(12),
    );
    let mut transcript = MerlinTranscript::new(b"cross-key-foreign");
    assert!(CrossKeyNegationProof::<RistrettoCurve>::prove(
        &residual_carrier,
        &foreign_negation,
        &owner_sk,
        &scalar(12),
        &owner_pk,
        &aggregate_pk,
        &mut rand_core::OsRng,
        &mut transcript,
    )
    .is_err());

    // The same attack with a zero contribution (removing a card while
    // contributing nothing) is equally unprovable.
    let zero_contribution = Ciphertext::encrypt(&RistrettoPoint::identity(), &aggregate_pk, &scalar(13));
    let mut transcript = MerlinTranscript::new(b"cross-key-zero");
    assert!(CrossKeyNegationProof::<RistrettoCurve>::prove(
        &residual_carrier,
        &zero_contribution,
        &owner_sk,
        &scalar(13),
        &owner_pk,
        &aggregate_pk,
        &mut rand_core::OsRng,
        &mut transcript,
    )
    .is_err());
}

#[test]
fn cross_key_rejects_mismatched_owner_key() {
    // Claiming another player's owner_pk: the pk/sk pairing equation fails
    // before any proof bytes are produced.
    let card = RistrettoCurve::hash_to_curve(b"cross-key-owned-a");
    let owner_sk = scalar(73);
    let owner_pk = RistrettoCurve::base_g() * owner_sk;
    let other_pk = RistrettoCurve::base_g() * scalar(74);
    let aggregate_pk = RistrettoCurve::base_g() * scalar(102);
    let residual_carrier = Ciphertext::encrypt(&card, &owner_pk, &scalar(11));
    let negation = Ciphertext::encrypt(&(RistrettoPoint::identity() - card), &aggregate_pk, &scalar(12));

    let mut transcript = MerlinTranscript::new(b"cross-key-wrong-pk");
    assert!(CrossKeyNegationProof::<RistrettoCurve>::prove(
        &residual_carrier,
        &negation,
        &owner_sk,
        &scalar(12),
        &other_pk,
        &aggregate_pk,
        &mut rand_core::OsRng,
        &mut transcript,
    )
    .is_err());
}

#[test]
fn cross_key_verify_rejects_swapped_owner_key() {
    // An honestly produced proof does not verify against a different owner
    // key: the transcript challenge and both response equations break.
    let card = RistrettoCurve::hash_to_curve(b"cross-key-owned-a");
    let owner_sk = scalar(73);
    let owner_pk = RistrettoCurve::base_g() * owner_sk;
    let other_pk = RistrettoCurve::base_g() * scalar(74);
    let aggregate_pk = RistrettoCurve::base_g() * scalar(102);
    let residual_carrier = Ciphertext::encrypt(&card, &owner_pk, &scalar(11));
    let negation = Ciphertext::encrypt(&(RistrettoPoint::identity() - card), &aggregate_pk, &scalar(12));

    let proof = CrossKeyNegationProof::<RistrettoCurve>::prove(
        &residual_carrier,
        &negation,
        &owner_sk,
        &scalar(12),
        &owner_pk,
        &aggregate_pk,
        &mut rand_core::OsRng,
        &mut MerlinTranscript::new(b"cross-key-swap"),
    )
    .unwrap();

    let mut transcript = MerlinTranscript::new(b"cross-key-swap");
    assert!(proof
        .verify(&residual_carrier, &negation, &other_pk, &aggregate_pk, &mut transcript)
        .is_err());
}

#[test]
fn reconstruction_proofs_are_randomized_without_mapping_fields() {
    let fixture_1 = fixture(8, &[1, 5], b"reconstruction-randomized");
    let fixture_2 = fixture(8, &[1, 5], b"reconstruction-randomized");

    assert_ne!(
        fixture_1.proof.contribution_shuffle_proof.c_permutation,
        fixture_2.proof.contribution_shuffle_proof.c_permutation
    );
    assert_ne!(
        fixture_1.proof.cross_key_proofs[0].response_owner_sk,
        fixture_2.proof.cross_key_proofs[0].response_owner_sk
    );
}
