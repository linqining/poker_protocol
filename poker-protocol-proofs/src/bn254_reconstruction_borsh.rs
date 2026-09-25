//! BN254 Borsh codecs for the curve-generic reconstruction package.

use borsh::{BorshDeserialize, BorshSerialize};
use poker_protocol_bg::BayerGrothShuffleProof;
use poker_protocol_core::{
    read_bn254_point, read_bn254_scalar, write_bn254_point, write_bn254_scalar, Bn254Curve,
    ElGamalCiphertextGeneric,
};

use crate::reconstruction::{
    CrossKeyNegationProof, ReconstructProof, ReconstructionStatement, SlotContributionOrProof,
    RECONSTRUCTION_PROOF_VERSION,
};

const MAX_RECONSTRUCTION_DECK_SIZE: usize = 1024;

fn write_len<W: borsh::io::Write>(len: usize, min: usize, w: &mut W) -> borsh::io::Result<()> {
    if !(min..=MAX_RECONSTRUCTION_DECK_SIZE).contains(&len) {
        return Err(borsh::io::Error::new(
            borsh::io::ErrorKind::InvalidData,
            "invalid reconstruction vector length",
        ));
    }
    let len = u32::try_from(len).map_err(|_| {
        borsh::io::Error::new(
            borsh::io::ErrorKind::InvalidData,
            "reconstruction vector too long",
        )
    })?;
    w.write_all(&len.to_le_bytes())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reconstruction::ReconstructProof;
    use crate::transcript_ext::{CryptoTranscript, FiatShamirTranscript};
    use poker_protocol_core::{Curve, CurveScalar};
    use rand_core::OsRng;

    #[test]
    fn bn254_reconstruction_statement_and_proof_borsh_roundtrip() {
        let cards = (0..8)
            .map(|index| Bn254Curve::hash_to_curve(format!("bn254-borsh/card/{index}").as_bytes()))
            .collect::<Vec<_>>();
        let owner_sk = <Bn254Curve as Curve>::Scalar::from_u64(73);
        let other_sk = <Bn254Curve as Curve>::Scalar::from_u64(29);
        let aggregate_sk = owner_sk + other_sk;
        let owner_pk = Bn254Curve::base_g() * owner_sk;
        let aggregate_pk = Bn254Curve::base_g() * aggregate_sk;
        let residual_carriers = [(0usize, 1000u64), (5, 1001)]
            .map(|(card, randomness)| {
                ElGamalCiphertextGeneric::encrypt(
                    &cards[card],
                    &owner_pk,
                    &<Bn254Curve as Curve>::Scalar::from_u64(randomness),
                )
            })
            .to_vec();
        let mut transcript = FiatShamirTranscript::new(b"bn254-reconstruction-borsh");
        let (statement, proof) = ReconstructProof::<Bn254Curve>::prove(
            [7u8; 32],
            11,
            [9u8; 32],
            cards,
            residual_carriers,
            &owner_sk,
            &owner_pk,
            &aggregate_pk,
            &mut OsRng,
            &mut transcript,
        )
        .unwrap();

        let statement_bytes = borsh::to_vec(&statement).unwrap();
        let proof_bytes = borsh::to_vec(&proof).unwrap();
        let recovered_statement =
            borsh::from_slice::<ReconstructionStatement<Bn254Curve>>(&statement_bytes).unwrap();
        let recovered_proof =
            borsh::from_slice::<ReconstructProof<Bn254Curve>>(&proof_bytes).unwrap();
        assert_eq!(statement, recovered_statement);
        assert!(recovered_proof
            .verify(
                &recovered_statement,
                &mut FiatShamirTranscript::new(b"bn254-reconstruction-borsh")
            )
            .is_ok());
        assert!(borsh::from_slice::<ReconstructionStatement<Bn254Curve>>(
            &statement_bytes[..statement_bytes.len() - 1]
        )
        .is_err());
        assert!(borsh::from_slice::<ReconstructProof<Bn254Curve>>(
            &proof_bytes[..proof_bytes.len() - 1]
        )
        .is_err());
    }
}

fn read_len<R: borsh::io::Read>(r: &mut R, min: usize) -> borsh::io::Result<usize> {
    let mut len_bytes = [0u8; 4];
    r.read_exact(&mut len_bytes)?;
    let len = u32::from_le_bytes(len_bytes) as usize;
    if !(min..=MAX_RECONSTRUCTION_DECK_SIZE).contains(&len) {
        return Err(borsh::io::Error::new(
            borsh::io::ErrorKind::InvalidData,
            "invalid reconstruction vector length",
        ));
    }
    Ok(len)
}

impl BorshSerialize for CrossKeyNegationProof<Bn254Curve> {
    fn serialize<W: borsh::io::Write>(&self, w: &mut W) -> borsh::io::Result<()> {
        write_bn254_point(&self.commitment_owner_key, w)?;
        write_bn254_point(&self.commitment_contribution_c1, w)?;
        write_bn254_point(&self.commitment_joint_c2, w)?;
        write_bn254_scalar(&self.response_owner_sk, w)?;
        write_bn254_scalar(&self.response_contribution_randomness, w)
    }
}

impl BorshDeserialize for CrossKeyNegationProof<Bn254Curve> {
    fn deserialize_reader<R: borsh::io::Read>(r: &mut R) -> borsh::io::Result<Self> {
        Ok(Self {
            commitment_owner_key: read_bn254_point(r)?,
            commitment_contribution_c1: read_bn254_point(r)?,
            commitment_joint_c2: read_bn254_point(r)?,
            response_owner_sk: read_bn254_scalar(r)?,
            response_contribution_randomness: read_bn254_scalar(r)?,
        })
    }
}

impl BorshSerialize for SlotContributionOrProof<Bn254Curve> {
    fn serialize<W: borsh::io::Write>(&self, w: &mut W) -> borsh::io::Result<()> {
        for point in &self.commitment_g {
            write_bn254_point(point, w)?;
        }
        for point in &self.commitment_pk {
            write_bn254_point(point, w)?;
        }
        for challenge in &self.challenges {
            write_bn254_scalar(challenge, w)?;
        }
        for response in &self.responses {
            write_bn254_scalar(response, w)?;
        }
        Ok(())
    }
}

impl BorshDeserialize for SlotContributionOrProof<Bn254Curve> {
    fn deserialize_reader<R: borsh::io::Read>(r: &mut R) -> borsh::io::Result<Self> {
        Ok(Self {
            commitment_g: [read_bn254_point(r)?, read_bn254_point(r)?],
            commitment_pk: [read_bn254_point(r)?, read_bn254_point(r)?],
            challenges: [read_bn254_scalar(r)?, read_bn254_scalar(r)?],
            responses: [read_bn254_scalar(r)?, read_bn254_scalar(r)?],
        })
    }
}

impl BorshSerialize for ReconstructionStatement<Bn254Curve> {
    fn serialize<W: borsh::io::Write>(&self, w: &mut W) -> borsh::io::Result<()> {
        if self.version != RECONSTRUCTION_PROOF_VERSION
            || self.cards.len() != self.contributions.len()
            || self.residual_carriers.len() > self.cards.len()
        {
            return Err(borsh::io::Error::new(
                borsh::io::ErrorKind::InvalidData,
                "invalid reconstruction statement shape",
            ));
        }
        w.write_all(&[self.version])?;
        w.write_all(&self.context_digest)?;
        w.write_all(&self.reconstruction_epoch.to_le_bytes())?;
        w.write_all(&self.prior_state_digest)?;
        write_bn254_point(&self.aggregate_pk, w)?;
        write_bn254_point(&self.owner_pk, w)?;
        write_len(self.cards.len(), 2, w)?;
        for card in &self.cards {
            write_bn254_point(card, w)?;
        }
        write_len(self.residual_carriers.len(), 1, w)?;
        for ciphertext in &self.residual_carriers {
            BorshSerialize::serialize(ciphertext, w)?;
        }
        for ciphertext in &self.contributions {
            BorshSerialize::serialize(ciphertext, w)?;
        }
        Ok(())
    }
}

impl BorshDeserialize for ReconstructionStatement<Bn254Curve> {
    fn deserialize_reader<R: borsh::io::Read>(r: &mut R) -> borsh::io::Result<Self> {
        let mut version = [0u8; 1];
        r.read_exact(&mut version)?;
        if version[0] != RECONSTRUCTION_PROOF_VERSION {
            return Err(borsh::io::Error::new(
                borsh::io::ErrorKind::InvalidData,
                "unsupported reconstruction statement version",
            ));
        }
        let mut context_digest = [0u8; 32];
        r.read_exact(&mut context_digest)?;
        let mut epoch_bytes = [0u8; 8];
        r.read_exact(&mut epoch_bytes)?;
        let reconstruction_epoch = u64::from_le_bytes(epoch_bytes);
        let mut prior_state_digest = [0u8; 32];
        r.read_exact(&mut prior_state_digest)?;
        let aggregate_pk = read_bn254_point(r)?;
        let owner_pk = read_bn254_point(r)?;
        let n = read_len(r, 2)?;
        let cards = (0..n)
            .map(|_| read_bn254_point(r))
            .collect::<Result<_, _>>()?;
        let k = read_len(r, 1)?;
        if k > n {
            return Err(borsh::io::Error::new(
                borsh::io::ErrorKind::InvalidData,
                "more residual carriers than reconstruction slots",
            ));
        }
        let residual_carriers = (0..k)
            .map(|_| BorshDeserialize::deserialize_reader(r))
            .collect::<Result<Vec<ElGamalCiphertextGeneric<Bn254Curve>>, _>>()?;
        let contributions = (0..n)
            .map(|_| BorshDeserialize::deserialize_reader(r))
            .collect::<Result<Vec<ElGamalCiphertextGeneric<Bn254Curve>>, _>>()?;
        let statement = Self {
            version: version[0],
            context_digest,
            reconstruction_epoch,
            prior_state_digest,
            aggregate_pk,
            owner_pk,
            cards,
            residual_carriers,
            contributions,
        };
        statement.validate().map_err(|_| {
            borsh::io::Error::new(
                borsh::io::ErrorKind::InvalidData,
                "invalid reconstruction statement",
            )
        })?;
        Ok(statement)
    }
}

impl BorshSerialize for ReconstructProof<Bn254Curve> {
    fn serialize<W: borsh::io::Write>(&self, w: &mut W) -> borsh::io::Result<()> {
        let k = self.negative_contributions.len();
        let n = self.slot_membership_proofs.len();
        if self.cross_key_proofs.len() != k || k == 0 || k > n {
            return Err(borsh::io::Error::new(
                borsh::io::ErrorKind::InvalidData,
                "invalid reconstruction proof shape",
            ));
        }
        w.write_all(&[RECONSTRUCTION_PROOF_VERSION])?;
        write_len(k, 1, w)?;
        for ciphertext in &self.negative_contributions {
            BorshSerialize::serialize(ciphertext, w)?;
        }
        for proof in &self.cross_key_proofs {
            BorshSerialize::serialize(proof, w)?;
        }
        BorshSerialize::serialize(&self.contribution_shuffle_proof, w)?;
        write_len(n, 2, w)?;
        for proof in &self.slot_membership_proofs {
            BorshSerialize::serialize(proof, w)?;
        }
        Ok(())
    }
}

impl BorshDeserialize for ReconstructProof<Bn254Curve> {
    fn deserialize_reader<R: borsh::io::Read>(r: &mut R) -> borsh::io::Result<Self> {
        let mut version = [0u8; 1];
        r.read_exact(&mut version)?;
        if version[0] != RECONSTRUCTION_PROOF_VERSION {
            return Err(borsh::io::Error::new(
                borsh::io::ErrorKind::InvalidData,
                "unsupported reconstruction proof version",
            ));
        }
        let k = read_len(r, 1)?;
        let negative_contributions = (0..k)
            .map(|_| BorshDeserialize::deserialize_reader(r))
            .collect::<Result<Vec<ElGamalCiphertextGeneric<Bn254Curve>>, _>>(
        )?;
        let cross_key_proofs = (0..k)
            .map(|_| BorshDeserialize::deserialize_reader(r))
            .collect::<Result<Vec<CrossKeyNegationProof<Bn254Curve>>, _>>()?;
        let contribution_shuffle_proof =
            BayerGrothShuffleProof::<Bn254Curve>::deserialize_reader(r)?;
        let n = read_len(r, 2)?;
        if k > n
            || contribution_shuffle_proof
                .multi_exponentiation
                .alpha_response
                .len()
                != n
        {
            return Err(borsh::io::Error::new(
                borsh::io::ErrorKind::InvalidData,
                "reconstruction proof vector lengths disagree",
            ));
        }
        let slot_membership_proofs = (0..n)
            .map(|_| BorshDeserialize::deserialize_reader(r))
            .collect::<Result<Vec<SlotContributionOrProof<Bn254Curve>>, _>>(
        )?;
        Ok(Self {
            negative_contributions,
            cross_key_proofs,
            contribution_shuffle_proof,
            slot_membership_proofs,
        })
    }
}
