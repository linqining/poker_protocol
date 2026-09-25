//! Self-contained BN254 reconstruction verifier input.
//!
//! This is a native host verifier for the BN254 Borsh wire bundle. It is not
//! a chain contract, transaction ABI, or consensus verifier; a concrete chain
//! adapter can use it as the reference semantics for an on-chain route.

use borsh::{BorshDeserialize, BorshSerialize};
use poker_protocol_core::Bn254Curve;
use poker_protocol_proofs::reconstruction::{ReconstructProof, ReconstructionStatement};
use poker_protocol_proofs::transcript_ext::{CryptoTranscript, FiatShamirTranscript};

/// SHA3 Fiat–Shamir domain for BN254 host-bundle verification.
pub const BN254_RECONSTRUCTION_BUNDLE_DOMAIN: &[u8] = b"bn254-reconstruction-bundle-v1";

/// Complete BN254 statement plus proof accepted by the reference host route.
#[derive(Debug, Clone, BorshSerialize, BorshDeserialize)]
pub struct Bn254ReconstructionV3Bundle {
    pub statement: ReconstructionStatement<Bn254Curve>,
    pub proof: ReconstructProof<Bn254Curve>,
}

impl Bn254ReconstructionV3Bundle {
    pub fn verify(&self) -> Result<(), poker_protocol_proofs::VerificationError> {
        self.statement.validate()?;
        let mut transcript = FiatShamirTranscript::new(BN254_RECONSTRUCTION_BUNDLE_DOMAIN);
        self.proof.verify(&self.statement, &mut transcript)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use poker_protocol_core::{Curve, CurveScalar};
    use rand_core::OsRng;

    #[test]
    fn bn254_bundle_roundtrip_verifies_and_rejects_epoch_tampering() {
        let cards = (0..4)
            .map(|index| Bn254Curve::hash_to_curve(format!("bn254-bundle/card/{index}").as_bytes()))
            .collect::<Vec<_>>();
        let owner_sk = <Bn254Curve as Curve>::Scalar::from_u64(83);
        let other_sk = <Bn254Curve as Curve>::Scalar::from_u64(41);
        let aggregate_sk = owner_sk + other_sk;
        let owner_pk = Bn254Curve::base_g() * owner_sk;
        let aggregate_pk = Bn254Curve::base_g() * aggregate_sk;
        let residual = poker_protocol_core::ElGamalCiphertextGeneric::encrypt(
            &cards[2],
            &owner_pk,
            &<Bn254Curve as Curve>::Scalar::from_u64(9001),
        );

        let mut prove_transcript = FiatShamirTranscript::new(BN254_RECONSTRUCTION_BUNDLE_DOMAIN);
        let (statement, proof) = ReconstructProof::<Bn254Curve>::prove(
            [8u8; 32],
            17,
            [11u8; 32],
            cards,
            vec![residual],
            &owner_sk,
            &owner_pk,
            &aggregate_pk,
            &mut OsRng,
            &mut prove_transcript,
        )
        .unwrap();
        let bundle = Bn254ReconstructionV3Bundle { statement, proof };
        let bytes = borsh::to_vec(&bundle).unwrap();
        let decoded = Bn254ReconstructionV3Bundle::try_from_slice(&bytes).unwrap();
        decoded.verify().unwrap();

        let mut tampered = decoded;
        tampered.statement.reconstruction_epoch += 1;
        assert!(tampered.verify().is_err());
        assert!(Bn254ReconstructionV3Bundle::try_from_slice(&bytes[..bytes.len() - 1]).is_err());
    }
}
