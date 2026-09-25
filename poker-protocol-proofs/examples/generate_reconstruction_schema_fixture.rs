//! Generate deterministic Rust--Lean reconstruction statement/proof schemas.

use poker_protocol_core::{
    Curve, CurveScalar, ElGamalCiphertextGeneric, StarkCurve, STARK_POINT_COMPRESSED_LEN,
    STARK_SCALAR_LEN,
};
use poker_protocol_proofs::reconstruction::{ReconstructProof, RECONSTRUCTION_PROOF_VERSION};
use poker_protocol_proofs::transcript_ext::{CryptoTranscript, FiatShamirTranscript};
use rand_chacha::ChaCha20Rng;
use rand_core::SeedableRng;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{env, fs, path::PathBuf};

type Ciphertext = ElGamalCiphertextGeneric<StarkCurve>;

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn scalar(value: u64) -> <StarkCurve as Curve>::Scalar {
    <StarkCurve as Curve>::Scalar::from_u64(value)
}

fn field_schema(bytes: &[u8], card_count: usize, carrier_count: usize) -> Vec<serde_json::Value> {
    let ciphertext_len = 2 * STARK_POINT_COMPRESSED_LEN;
    let fields = [
        ("version", 1usize),
        ("context_digest", 32),
        ("reconstruction_epoch", 8),
        ("prior_state_digest", 32),
        ("aggregate_pk", STARK_POINT_COMPRESSED_LEN),
        ("owner_pk", STARK_POINT_COMPRESSED_LEN),
        ("card_count", 4),
        ("cards", card_count * STARK_POINT_COMPRESSED_LEN),
        ("residual_carrier_count", 4),
        ("residual_carriers", carrier_count * ciphertext_len),
        ("contributions", card_count * ciphertext_len),
    ];
    let mut offset = 0usize;
    fields
        .iter()
        .map(|(name, length)| {
            let end = offset + length;
            let value = json!({
                "name": name,
                "offset": offset,
                "length": length,
                "hex": hex(&bytes[offset..end]),
            });
            offset = end;
            value
        })
        .collect()
}

fn fields_from_layout(bytes: &[u8], fields: &[(&str, usize)]) -> Vec<serde_json::Value> {
    let mut offset = 0usize;
    fields
        .iter()
        .map(|(name, length)| {
            let end = offset + length;
            let value = json!({
                "name": name,
                "offset": offset,
                "length": length,
                "hex": hex(&bytes[offset..end]),
            });
            offset = end;
            value
        })
        .collect()
}

fn proof_schema(
    bytes: &[u8],
    card_count: usize,
    carrier_count: usize,
) -> (Vec<serde_json::Value>, Vec<serde_json::Value>) {
    let ciphertext_len = 2 * STARK_POINT_COMPRESSED_LEN;
    let cross_key_len = 3 * STARK_POINT_COMPRESSED_LEN + 2 * STARK_SCALAR_LEN;
    let slot_or_len = 4 * STARK_POINT_COMPRESSED_LEN + 4 * STARK_SCALAR_LEN;
    let scalar_vector_len = 4 + card_count * STARK_SCALAR_LEN;
    let multi_exponentiation_len = 2 * STARK_POINT_COMPRESSED_LEN
        + 2 * ciphertext_len
        + scalar_vector_len
        + 4 * STARK_SCALAR_LEN;
    let product_len = 3 * STARK_POINT_COMPRESSED_LEN + 2 * scalar_vector_len + 2 * STARK_SCALAR_LEN;
    let shuffle_len = 2 * STARK_POINT_COMPRESSED_LEN + multi_exponentiation_len + product_len;
    let top_level = fields_from_layout(
        bytes,
        &[
            ("version", 1),
            ("negative_contribution_count", 4),
            ("negative_contributions", carrier_count * ciphertext_len),
            ("cross_key_proofs", carrier_count * cross_key_len),
            ("contribution_shuffle_proof", shuffle_len),
            ("slot_membership_proof_count", 4),
            ("slot_membership_proofs", card_count * slot_or_len),
        ],
    );

    let mut nested = Vec::new();
    let mut offset = 5usize;
    for carrier in 0..carrier_count {
        nested.push(json!({
            "name": format!("negative_contributions[{carrier}]"),
            "offset": offset,
            "length": ciphertext_len,
            "hex": hex(&bytes[offset..offset + ciphertext_len]),
        }));
        offset += ciphertext_len;
    }
    for carrier in 0..carrier_count {
        nested.push(json!({
            "name": format!("cross_key_proofs[{carrier}]"),
            "offset": offset,
            "length": cross_key_len,
            "hex": hex(&bytes[offset..offset + cross_key_len]),
        }));
        offset += cross_key_len;
    }

    let shuffle_start = offset;
    let shuffle_fields = vec![
        (
            "contribution_shuffle_proof.c_permutation",
            STARK_POINT_COMPRESSED_LEN,
        ),
        (
            "contribution_shuffle_proof.c_permuted_powers",
            STARK_POINT_COMPRESSED_LEN,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.c_alpha",
            STARK_POINT_COMPRESSED_LEN,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.c_beta",
            STARK_POINT_COMPRESSED_LEN,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.ciphertext_0",
            ciphertext_len,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.ciphertext_1",
            ciphertext_len,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.alpha_response",
            scalar_vector_len,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.commitment_response",
            STARK_SCALAR_LEN,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.beta",
            STARK_SCALAR_LEN,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.beta_blinding_response",
            STARK_SCALAR_LEN,
        ),
        (
            "contribution_shuffle_proof.multi_exponentiation.rerandomization_response",
            STARK_SCALAR_LEN,
        ),
        (
            "contribution_shuffle_proof.product.c_d",
            STARK_POINT_COMPRESSED_LEN,
        ),
        (
            "contribution_shuffle_proof.product.c_delta",
            STARK_POINT_COMPRESSED_LEN,
        ),
        (
            "contribution_shuffle_proof.product.c_capital_delta",
            STARK_POINT_COMPRESSED_LEN,
        ),
        (
            "contribution_shuffle_proof.product.a_response",
            scalar_vector_len,
        ),
        (
            "contribution_shuffle_proof.product.b_response",
            scalar_vector_len,
        ),
        (
            "contribution_shuffle_proof.product.r_response",
            STARK_SCALAR_LEN,
        ),
        (
            "contribution_shuffle_proof.product.s_response",
            STARK_SCALAR_LEN,
        ),
    ];
    let mut nested_shuffle = fields_from_layout(
        &bytes[shuffle_start..shuffle_start + shuffle_len],
        &shuffle_fields,
    );
    for (index, field) in nested_shuffle.iter_mut().enumerate() {
        field["offset"] = json!(field["offset"].as_u64().unwrap() + shuffle_start as u64);
        field["name"] = json!(shuffle_fields[index].0);
    }
    nested.extend(nested_shuffle);
    offset += shuffle_len;

    offset += 4;
    for slot in 0..card_count {
        nested.push(json!({
            "name": format!("slot_membership_proofs[{slot}]"),
            "offset": offset,
            "length": slot_or_len,
            "hex": hex(&bytes[offset..offset + slot_or_len]),
        }));
        offset += slot_or_len;
    }
    assert_eq!(offset, bytes.len());
    (top_level, nested)
}

fn main() {
    let output = env::args()
        .nth(1)
        .map(PathBuf::from)
        .expect("usage: generate_reconstruction_schema_fixture OUTPUT_JSON");
    let card_count = 8usize;
    let carrier_count = 2usize;
    let selected_slots = [1usize, 4];

    let cards = (0..card_count)
        .map(|index| {
            StarkCurve::hash_to_curve(format!("schema/reconstruction/card/{index}").as_bytes())
        })
        .collect::<Vec<_>>();
    let owner_sk = scalar(73);
    let other_sk = scalar(29);
    let aggregate_sk = owner_sk + other_sk;
    let owner_pk = StarkCurve::base_g() * owner_sk;
    let aggregate_pk = StarkCurve::base_g() * aggregate_sk;

    let residual_carriers = selected_slots
        .iter()
        .enumerate()
        .map(|(carrier, slot)| {
            Ciphertext::encrypt(&cards[*slot], &owner_pk, &scalar(1000 + carrier as u64))
        })
        .collect::<Vec<_>>();
    let mut deterministic_rng = ChaCha20Rng::seed_from_u64(0x726563_6f6e5f76_33);
    let (statement, proof) = ReconstructProof::<StarkCurve>::prove(
        [0x07; 32],
        11,
        [0x09; 32],
        cards,
        residual_carriers,
        &owner_sk,
        &owner_pk,
        &aggregate_pk,
        &mut deterministic_rng,
        &mut FiatShamirTranscript::new(b"reconstruction-schema-v3"),
    )
    .expect("deterministic fixture proof generation");
    statement
        .validate()
        .expect("fixture statement must validate");
    proof
        .verify(
            &statement,
            &mut FiatShamirTranscript::new(b"reconstruction-schema-v3"),
        )
        .expect("deterministic fixture proof verification");
    let bytes = borsh::to_vec(&statement).expect("statement Borsh encoding");
    let fields = field_schema(&bytes, card_count, carrier_count);
    let expected_length = 1
        + 32
        + 8
        + 32
        + 2 * STARK_POINT_COMPRESSED_LEN
        + 4
        + card_count * STARK_POINT_COMPRESSED_LEN
        + 4
        + carrier_count * 2 * STARK_POINT_COMPRESSED_LEN
        + card_count * 2 * STARK_POINT_COMPRESSED_LEN;
    assert_eq!(bytes.len(), expected_length);

    let prefix_length = 1 + 32 + 8 + 32 + 2 * STARK_POINT_COMPRESSED_LEN + 4;
    let sha256 = Sha256::digest(&bytes);
    let proof_bytes = borsh::to_vec(&proof).expect("proof Borsh encoding");
    let (proof_fields, proof_nested_fields) = proof_schema(&proof_bytes, card_count, carrier_count);
    let proof_sha256 = Sha256::digest(&proof_bytes);
    let payload = json!({
        "schema_version": 4,
        "encoding": "ReconstructionStatement<StarkCurve> Borsh v3",
        "version": RECONSTRUCTION_PROOF_VERSION,
        "reconstruction_epoch": 11,
        "card_count": card_count,
        "residual_carrier_count": carrier_count,
        "removed_bitmap": "01001000",
        "context_digest_hex": hex(&statement.context_digest),
        "prior_state_digest_hex": hex(&statement.prior_state_digest),
        "point_encoding": "32-byte compressed Stark point",
        "scalar_encoding": format!("{STARK_SCALAR_LEN}-byte big-endian Stark scalar"),
        "length_encoding": "u32 little-endian with protocol bounds",
        "byte_length": bytes.len(),
        "field_count": fields.len(),
        "sha256": hex(&sha256),
        "prefix_length": prefix_length,
        "prefix_hex": hex(&bytes[..prefix_length]),
        "bytes_hex": hex(&bytes),
        "fields": fields,
        "scope": "deterministic full-field statement wire schema; proof encoding remains separately versioned and randomized",
        "proof": {
            "schema_version": 1,
            "encoding": "ReconstructProof<StarkCurve> Borsh v3",
            "deterministic_rng": "ChaCha20 seed 0x7265636f6e5f7633",
            "transcript": "FiatShamirTranscript(b'reconstruction-schema-v3')",
            "byte_length": proof_bytes.len(),
            "field_count": proof_fields.len(),
            "nested_field_count": proof_nested_fields.len(),
            "prefix_length": 5,
            "sha256": hex(&proof_sha256),
            "prefix_hex": hex(&proof_bytes[..5]),
            "bytes_hex": hex(&proof_bytes),
            "fields": proof_fields,
            "nested_fields": proof_nested_fields,
            "scope": "deterministic full proof wire schema for this frozen randomized proof instance",
        },
    });
    fs::write(output, serde_json::to_vec_pretty(&payload).unwrap()).unwrap();
}
