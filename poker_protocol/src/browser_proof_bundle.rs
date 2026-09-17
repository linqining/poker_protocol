//! Borsh bundles for browser-generated native mental-poker proofs.
//!
//! These values are deliberately small, self-contained verifier inputs. They
//! are not a chain transaction ABI: Texas still derives the caller and seat
//! from the authenticated client session before constructing a VM command.

use borsh::{BorshDeserialize, BorshSerialize};

use crate::{
    crypto::{DefaultCurve, ECPoint, ElGamalCiphertext, N_CARDS},
    zk_shuffle::{
        error::VerificationError,
        reveal_token_proof::RevealTokenProof,
        transcript_ext::PoseidonFeltTranscript,
        ShuffleProof,
    },
};

use super::zk_shuffle::reconstruction::{ReconstructProof, ReconstructionStatement};

/// Browser-produced Bayer--Groth shuffle data plus every public verifier
/// input. The fixed transcript label matches `ClientPlayer::shuffle`.
#[derive(Debug, Clone, BorshSerialize, BorshDeserialize)]
pub struct BrowserShuffleV2Bundle {
    pub aggregate_pk: ECPoint,
    pub input_cards: Vec<ElGamalCiphertext>,
    pub output_cards: Vec<ElGamalCiphertext>,
    pub proof: ShuffleProof,
}

impl BrowserShuffleV2Bundle {
    /// Verify the complete shuffle bundle with the production V2 transcript.
    pub fn verify(&self) -> Result<(), VerificationError> {
        if self.input_cards.len() != N_CARDS || self.output_cards.len() != N_CARDS {
            return Err(VerificationError::LengthMismatch);
        }
        let mut transcript = PoseidonFeltTranscript::new_domain(crate::transcript_domains::SHUFFLE_V2_POSEIDON);
        self.proof.verify(
            &self.input_cards,
            &self.output_cards,
            &self.aggregate_pk.0,
            &mut transcript,
        )
    }
}

/// One browser-produced reveal token and its complete public verification
/// statement. `player_pk` is kept separately so decoding alone cannot turn a
/// proof-carried key into the trusted identity.
#[derive(Debug, Clone, BorshSerialize, BorshDeserialize)]
pub struct BrowserRevealTokenBundle {
    pub player_pk: ECPoint,
    pub encrypted_card: ElGamalCiphertext,
    pub reveal_token: ECPoint,
    pub proof: RevealTokenProof<DefaultCurve>,
}

impl BrowserRevealTokenBundle {
    /// Verify the token against the independently supplied player key.
    pub fn verify(&self) -> Result<(), VerificationError> {
        let mut transcript = PoseidonFeltTranscript::new_domain(
            crate::transcript_domains::REVEAL_TOKEN_V3_POSEIDON,
        );
        self.proof
            .verify(
                &self.encrypted_card,
                &self.reveal_token.0,
                &self.player_pk.0,
                &mut transcript,
            )
            .map_err(|_| VerificationError::InvalidRevealToken)
    }
}

/// Browser-produced reconstruction package plus its complete public verifier
/// statement. The bundle is a verifier input, not the authorization source:
/// the host still binds the state digests and owner key to authenticated game
/// state before calling `verify`.
#[derive(Debug, Clone, BorshSerialize, BorshDeserialize)]
pub struct BrowserReconstructionV3Bundle {
    pub statement: ReconstructionStatement<DefaultCurve>,
    pub proof: ReconstructProof<DefaultCurve>,
}

impl BrowserReconstructionV3Bundle {
    /// Verify with the same production reconstruction transcript domain used
    /// by the native client and precompile paths.
    pub fn verify(&self) -> Result<(), VerificationError> {
        let mut transcript =
            PoseidonFeltTranscript::new_domain(crate::transcript_domains::RECONSTRUCT_POSEIDON);
        self.proof.verify(&self.statement, &mut transcript)
    }
}

#[cfg(test)]
mod reconstruction_bundle_tests {
    use super::*;
    use crate::crypto::{Curve, CurveScalar, Scalar};
    use rand_core::OsRng;

    #[test]
    fn reconstruction_bundle_roundtrip_rejects_epoch_tampering() {
        let cards = (0..4)
            .map(|i| DefaultCurve::hash_to_curve(format!("bundle/card/{i}").as_bytes()))
            .collect::<Vec<_>>();
        let owner_sk = <Scalar as CurveScalar>::random(&mut OsRng);
        let aggregate_sk = <Scalar as CurveScalar>::random(&mut OsRng);
        let owner_pk = DefaultCurve::base_g() * owner_sk;
        let aggregate_pk = DefaultCurve::base_g() * aggregate_sk;
        let residual = ElGamalCiphertext::encrypt(&cards[1], &owner_pk, &Scalar::from_u64(7));

        let mut transcript =
            PoseidonFeltTranscript::new_domain(crate::transcript_domains::RECONSTRUCT_POSEIDON);
        let (statement, proof) = ReconstructProof::<DefaultCurve>::prove(
            [1; 32],
            9,
            [2; 32],
            cards,
            vec![residual],
            &owner_sk,
            &owner_pk,
            &aggregate_pk,
            &mut OsRng,
            &mut transcript,
        )
        .unwrap();
        let bundle = BrowserReconstructionV3Bundle { statement, proof };
        let bytes = borsh::to_vec(&bundle).unwrap();
        let decoded = BrowserReconstructionV3Bundle::try_from_slice(&bytes).unwrap();
        decoded.verify().unwrap();

        let mut changed = decoded;
        changed.statement.reconstruction_epoch += 1;
        assert!(changed.verify().is_err());
    }
}
