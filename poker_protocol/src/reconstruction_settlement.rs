//! Settlement adapter boundary for reconstruction deposit policies.
//!
//! The submission policy emits a settlement proposal. A concrete host can use
//! this trait to put that proposal behind an escrow service or contract. The
//! in-memory implementation is a executable reference ledger: it is atomic,
//! idempotent for an identical proposal, and rejects replay of a different
//! proposal for the same reconstruction epoch.

use crate::reconstruction_policy::DeadlineSettlement;
use poker_protocol_core::tx_schnorr::{schnorr_challenge, sign as sign_schnorr};
use poker_protocol_core::{Curve, CurvePoint, CurveScalar, StarkCurve, StarkPoint, StarkScalar};
use std::collections::BTreeMap;

/// Receipt for a deposit lock.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DepositLockReceipt {
    pub reconstruction_epoch: u64,
    pub submitter: String,
    pub amount: u128,
}

/// Individual settlement event emitted by an adapter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SettlementEvent {
    Refund {
        reconstruction_epoch: u64,
        to: String,
        amount: u128,
    },
    Compensation {
        reconstruction_epoch: u64,
        to: String,
        amount: u128,
    },
    Burn {
        reconstruction_epoch: u64,
        amount: u128,
    },
}

/// Complete result of applying one settlement proposal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SettlementExecution {
    pub proposal: DeadlineSettlement,
    pub events: Vec<SettlementEvent>,
}

/// Cryptographically bound transaction digest used by the signed simulation
/// and reference adapter envelope. `PSTX` is not a public chain standard; a
/// production adapter must either bridge it explicitly or replace it with the
/// host chain's canonical signed-transaction identifier.
pub type SimulatedSettlementTxHash = [u8; 32];

/// Request submitted to the local chain simulator.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SettlementTransactionRequest {
    pub sender: String,
    pub deployment_digest: [u8; 32],
    pub nonce: u64,
    pub gas_limit: u128,
    pub proposal: DeadlineSettlement,
    pub public_key: [u8; 32],
    pub signature: [u8; 64],
}

/// Receipt for a simulated settlement transaction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SimulatedSettlementReceipt {
    pub transaction_hash: SimulatedSettlementTxHash,
    pub sender: String,
    pub nonce: u64,
    pub gas_limit: u128,
    pub gas_used: u128,
    pub included_block: u64,
    pub confirmations: u64,
    pub finalized: bool,
    pub execution: SettlementExecution,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SettlementError {
    ZeroEpoch,
    ZeroAmount,
    ProposalFinalizedAtZero,
    EmptySettlement,
    EpochAlreadySettled { reconstruction_epoch: u64 },
    SettlementConflict { reconstruction_epoch: u64 },
    DuplicateSubmitter { submitter: String },
    NonCanonicalSubmitterOrder,
    InvalidPlayerArithmetic { submitter: String },
    InvalidMissedSubmitterList,
    CompensationInvariant,
    LockedEscrowInvariant,
    MissingLockedDeposit { submitter: String },
    ExtraLockedDeposit { submitter: String },
    LockedAmountMismatch { submitter: String },
    DuplicateDepositWithDifferentAmount { submitter: String },
    EscrowOverflow,
    ReleaseOverflow,
    InvalidSender,
    InvalidNonce { expected: u64, supplied: u64 },
    NonceAlreadyUsed,
    GasLimitTooLow { required: u128, supplied: u128 },
    PendingTransactionExists,
    TransactionNotFound,
    TransactionAlreadyFinalized,
    InvalidTransactionSignature,
    InvalidSecretKey,
    DeploymentMismatch,
    InvalidDeploymentDigest,
    InvalidDeploymentIdentity,
    InvalidWireMagic,
    UnsupportedWireVersion(u8),
    InvalidWireLength,
    InvalidWireUtf8,
    ProposalTooLarge,
}

impl std::fmt::Display for SettlementError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ZeroEpoch => write!(f, "reconstruction epoch must be nonzero"),
            Self::ZeroAmount => write!(f, "deposit amount must be nonzero"),
            Self::ProposalFinalizedAtZero => {
                write!(f, "proposal finalization time must be nonzero")
            }
            Self::EmptySettlement => write!(f, "settlement has no participants"),
            Self::EpochAlreadySettled {
                reconstruction_epoch,
            } => write!(
                f,
                "reconstruction epoch {reconstruction_epoch} has already settled"
            ),
            Self::SettlementConflict {
                reconstruction_epoch,
            } => write!(
                f,
                "conflicting settlement for reconstruction epoch {reconstruction_epoch}"
            ),
            Self::DuplicateSubmitter { submitter } => {
                write!(f, "duplicate settlement submitter {submitter}")
            }
            Self::NonCanonicalSubmitterOrder => {
                write!(f, "settlement submitters are not in canonical order")
            }
            Self::InvalidPlayerArithmetic { submitter } => {
                write!(f, "invalid settlement arithmetic for submitter {submitter}")
            }
            Self::InvalidMissedSubmitterList => write!(f, "missed-submitter list is inexact"),
            Self::CompensationInvariant => write!(f, "compensation conservation failed"),
            Self::LockedEscrowInvariant => write!(f, "locked-escrow conservation failed"),
            Self::MissingLockedDeposit { submitter } => {
                write!(f, "missing locked deposit for submitter {submitter}")
            }
            Self::ExtraLockedDeposit { submitter } => {
                write!(f, "unexpected locked deposit for submitter {submitter}")
            }
            Self::LockedAmountMismatch { submitter } => {
                write!(f, "locked amount mismatch for submitter {submitter}")
            }
            Self::DuplicateDepositWithDifferentAmount { submitter } => write!(
                f,
                "duplicate deposit with a different amount for submitter {submitter}"
            ),
            Self::EscrowOverflow => write!(f, "escrow accounting overflow"),
            Self::ReleaseOverflow => write!(f, "release accounting overflow"),
            Self::InvalidSender => write!(f, "settlement sender is empty"),
            Self::InvalidNonce { expected, supplied } => write!(
                f,
                "invalid settlement nonce: expected {expected}, supplied {supplied}"
            ),
            Self::NonceAlreadyUsed => write!(f, "settlement nonce has already been used"),
            Self::GasLimitTooLow { required, supplied } => {
                write!(f, "gas limit {supplied} is below the required {required}")
            }
            Self::PendingTransactionExists => write!(f, "another settlement is pending finality"),
            Self::TransactionNotFound => write!(f, "pending settlement transaction not found"),
            Self::TransactionAlreadyFinalized => write!(f, "settlement transaction is final"),
            Self::InvalidTransactionSignature => {
                write!(f, "invalid settlement transaction signature")
            }
            Self::InvalidSecretKey => write!(f, "secret key cannot create a valid account"),
            Self::DeploymentMismatch => {
                write!(f, "settlement belongs to a different deployment")
            }
            Self::InvalidDeploymentDigest => write!(f, "deployment digest must be nonzero"),
            Self::InvalidDeploymentIdentity => {
                write!(f, "deployment identity parts must be nonempty")
            }
            Self::InvalidWireMagic => write!(f, "invalid PSTX wire magic"),
            Self::UnsupportedWireVersion(version) => {
                write!(f, "unsupported PSTX wire version {version}")
            }
            Self::InvalidWireLength => write!(f, "invalid PSTX wire length or trailing bytes"),
            Self::InvalidWireUtf8 => write!(f, "PSTX identity is not valid UTF-8"),
            Self::ProposalTooLarge => write!(f, "settlement proposal exceeds adapter limits"),
        }
    }
}

impl std::error::Error for SettlementError {}

/// Boundary implemented by an escrow service, contract adapter, or test
/// ledger. Implementations must be idempotent for an identical proposal and
/// fail closed if the same epoch has already settled differently.
pub trait ReconstructionSettlementAdapter {
    type Error: From<SettlementError>;

    fn lock_deposit(
        &mut self,
        reconstruction_epoch: u64,
        submitter: &str,
        amount: u128,
    ) -> Result<DepositLockReceipt, Self::Error>;

    fn apply_settlement(
        &mut self,
        proposal: &DeadlineSettlement,
    ) -> Result<SettlementExecution, Self::Error>;
}

/// Domain-separated canonical hash of the unsigned settlement transaction.
///
/// The encoding is local to this simulator. A production adapter must replace
/// it with the chain's canonical transaction RLP/calldata and signature hash.
#[must_use]
pub fn settlement_message_hash(request: &SettlementTransactionRequest) -> [u8; 32] {
    let mut buffer = Vec::new();
    buffer.extend_from_slice(b"poker.settlement.tx.v1");
    buffer.extend_from_slice(&request.deployment_digest);
    buffer.extend_from_slice(&request.public_key);
    buffer.extend_from_slice(&request.nonce.to_be_bytes());
    buffer.extend_from_slice(&request.gas_limit.to_be_bytes());
    buffer.extend_from_slice(&request.proposal.reconstruction_epoch.to_be_bytes());
    buffer.extend_from_slice(&request.proposal.finalized_at.to_be_bytes());

    let missed = &request.proposal.missed_submitters;
    buffer.extend_from_slice(&(missed.len() as u32).to_be_bytes());
    for submitter in missed {
        buffer.extend_from_slice(&(submitter.len() as u32).to_be_bytes());
        buffer.extend_from_slice(submitter.as_bytes());
    }

    let settlements = &request.proposal.settlements;
    buffer.extend_from_slice(&(settlements.len() as u32).to_be_bytes());
    for settlement in settlements {
        buffer.extend_from_slice(&(settlement.submitter.len() as u32).to_be_bytes());
        buffer.extend_from_slice(settlement.submitter.as_bytes());
        buffer.push(u8::from(settlement.submitted));
        buffer.extend_from_slice(&settlement.locked_deposit.to_be_bytes());
        buffer.extend_from_slice(&settlement.penalty.to_be_bytes());
        buffer.extend_from_slice(&settlement.refund.to_be_bytes());
        buffer.extend_from_slice(&settlement.compensation.to_be_bytes());
        buffer.extend_from_slice(&settlement.net_release.to_be_bytes());
    }
    buffer.extend_from_slice(&request.proposal.burned_penalty_remainder.to_be_bytes());

    StarkCurve::hash_to_scalar(&buffer).to_bytes_be()
}

/// Sign a settlement transaction with the simulator's Stark Schnorr scheme.
///
/// This function canonicalizes `sender` to the lowercase compressed public-key
/// hex so a signature cannot be detached from the account identity. The caller
/// must set the request's deployment digest; the signature also binds it.
pub fn sign_settlement_transaction(
    secret_key: &StarkScalar,
    mut request: SettlementTransactionRequest,
) -> Result<SettlementTransactionRequest, SettlementError> {
    if *secret_key == StarkScalar::zero() {
        return Err(SettlementError::InvalidSecretKey);
    }
    if request.deployment_digest == [0u8; 32] {
        return Err(SettlementError::InvalidDeploymentDigest);
    }
    validate_settlement_proposal(&request.proposal)?;
    let public_key = StarkCurve::base_g() * secret_key;
    if public_key.is_identity() {
        return Err(SettlementError::InvalidSecretKey);
    }
    request.public_key = public_key.compress().as_ref().to_vec().try_into().unwrap();
    request.sender = hex::encode(request.public_key);
    let message_hash = settlement_message_hash(&request);
    request.signature = sign_schnorr(secret_key, &message_hash);
    Ok(request)
}

/// Verify the simulator's Stark Schnorr transaction signature.
///
/// The sender field must be the canonical lowercase hex of the compressed
/// public key, and identity public keys and identity Schnorr commitments are
/// not valid. Signature and proposal tampering therefore fail closed before
/// nonce or gas admission.
#[must_use]
pub fn verify_settlement_transaction_signature(request: &SettlementTransactionRequest) -> bool {
    if request.sender.len() != 64
        || request.signature.len() != 64
        || request.sender != request.sender.to_lowercase()
    {
        return false;
    }
    if request.deployment_digest == [0u8; 32] {
        return false;
    }
    let Ok(public_key_bytes) =
        <[u8; 32]>::try_from(hex::decode(&request.sender).unwrap_or_default())
    else {
        return false;
    };
    if public_key_bytes != request.public_key {
        return false;
    }
    let Some(public_key) = <StarkPoint as CurvePoint>::from_compressed(&request.public_key) else {
        return false;
    };
    if public_key.is_identity() {
        return false;
    }
    let Some(big_r) = <StarkPoint as CurvePoint>::from_compressed(&request.signature[..32]) else {
        return false;
    };
    if big_r.is_identity() {
        return false;
    }
    let Some(response) =
        <StarkScalar as CurveScalar>::from_canonical_bytes(&request.signature[32..])
    else {
        return false;
    };
    if response == StarkScalar::zero() {
        return false;
    }
    let message_hash = settlement_message_hash(request);
    let challenge = schnorr_challenge(&big_r, &public_key, &message_hash);
    StarkCurve::base_g() * response - public_key * challenge == big_r
}

const SETTLEMENT_TX_WIRE_MAGIC: [u8; 4] = *b"PSTX";
const SETTLEMENT_TX_WIRE_VERSION: u8 = 1;
const MAX_SETTLEMENT_PARTICIPANTS: usize = 1024;
const MAX_SETTLEMENT_IDENTITY_BYTES: usize = 256;

fn encode_length_prefixed_bytes(out: &mut Vec<u8>, bytes: &[u8]) -> Result<(), SettlementError> {
    let length = u32::try_from(bytes.len()).map_err(|_| SettlementError::ProposalTooLarge)?;
    out.extend_from_slice(&length.to_be_bytes());
    out.extend_from_slice(bytes);
    Ok(())
}

fn encode_settlement_string(out: &mut Vec<u8>, value: &str) -> Result<(), SettlementError> {
    if value.len() > MAX_SETTLEMENT_IDENTITY_BYTES {
        return Err(SettlementError::ProposalTooLarge);
    }
    encode_length_prefixed_bytes(out, value.as_bytes())
}

/// Derive a nonzero deployment binding digest from the deployment's canonical
/// label. A production adapter should derive this from its chain ID, contract
/// address, and adapter version rather than reusing the local label.
#[must_use]
pub fn settlement_deployment_digest(label: &[u8]) -> [u8; 32] {
    StarkCurve::hash_to_scalar(label).to_bytes_be()
}

/// Derive a deployment digest from canonical chain/contract/adapter identity.
///
/// Each part is domain-separated and length-prefixed so different part
/// boundaries cannot produce the same byte string. None may be empty; keep
/// addresses and versions in their canonical byte/text representation.
pub fn settlement_deployment_digest_from_parts(
    chain_id: &[u8],
    contract_address: &[u8],
    adapter_version: &[u8],
) -> Result<[u8; 32], SettlementError> {
    const MAX_PART_BYTES: usize = MAX_SETTLEMENT_IDENTITY_BYTES;
    const DEPLOYMENT_DOMAIN: &[u8] = b"poker.settlement.deployment.v1";

    for part in [chain_id, contract_address, adapter_version] {
        if part.is_empty() {
            return Err(SettlementError::InvalidDeploymentIdentity);
        }
        if part.len() > MAX_PART_BYTES {
            return Err(SettlementError::ProposalTooLarge);
        }
    }

    let mut encoded = Vec::from(DEPLOYMENT_DOMAIN);
    for part in [chain_id, contract_address, adapter_version] {
        encode_length_prefixed_bytes(&mut encoded, part)?;
    }
    let digest = StarkCurve::hash_to_scalar(&encoded).to_bytes_be();
    if digest == [0u8; 32] {
        return Err(SettlementError::InvalidDeploymentDigest);
    }
    Ok(digest)
}

/// Digest for the built-in local simulator only; it is not a deployment ID.
#[must_use]
pub fn local_settlement_deployment_digest() -> [u8; 32] {
    settlement_deployment_digest(b"poker.settlement.local.v1")
}

fn take_wire_bytes<'a>(bytes: &mut &'a [u8], length: usize) -> Result<&'a [u8], SettlementError> {
    if bytes.len() < length {
        return Err(SettlementError::InvalidWireLength);
    }
    let (value, rest) = bytes.split_at(length);
    *bytes = rest;
    Ok(value)
}

fn read_wire_u8(bytes: &mut &[u8]) -> Result<u8, SettlementError> {
    Ok(take_wire_bytes(bytes, 1)?
        .first()
        .copied()
        .unwrap_or_default())
}

fn read_wire_u32(bytes: &mut &[u8]) -> Result<u32, SettlementError> {
    let value = take_wire_bytes(bytes, 4)?;
    Ok(u32::from_be_bytes(value.try_into().expect("four bytes")))
}

fn read_wire_u64(bytes: &mut &[u8]) -> Result<u64, SettlementError> {
    let value = take_wire_bytes(bytes, 8)?;
    Ok(u64::from_be_bytes(value.try_into().expect("eight bytes")))
}

fn read_wire_count(bytes: &mut &[u8]) -> Result<usize, SettlementError> {
    let value = read_wire_u32(bytes)?;
    let value = usize::try_from(value).map_err(|_| SettlementError::ProposalTooLarge)?;
    if value > MAX_SETTLEMENT_PARTICIPANTS {
        return Err(SettlementError::ProposalTooLarge);
    }
    Ok(value)
}

fn read_wire_u128(bytes: &mut &[u8]) -> Result<u128, SettlementError> {
    let value = take_wire_bytes(bytes, 16)?;
    Ok(u128::from_be_bytes(value.try_into().expect("16 bytes")))
}

fn read_wire_string(bytes: &mut &[u8]) -> Result<String, SettlementError> {
    let length = read_wire_u32(bytes)?;
    let length = usize::try_from(length).map_err(|_| SettlementError::ProposalTooLarge)?;
    if length > MAX_SETTLEMENT_IDENTITY_BYTES {
        return Err(SettlementError::ProposalTooLarge);
    }
    let value = take_wire_bytes(bytes, length)?;
    String::from_utf8(value.to_vec()).map_err(|_| SettlementError::InvalidWireUtf8)
}

impl SettlementTransactionRequest {
    /// Canonical reference-adapter encoding for a signed settlement request.
    ///
    /// The account is not encoded separately: decoding derives the lowercase
    /// sender from the compressed public key and requires a valid Stark
    /// Schnorr signature over the complete proposal.
    pub fn encode(&self) -> Result<Vec<u8>, SettlementError> {
        validate_settlement_proposal(&self.proposal)?;
        if self.sender != hex::encode(self.public_key)
            || !verify_settlement_transaction_signature(self)
        {
            return Err(SettlementError::InvalidTransactionSignature);
        }
        if self.proposal.missed_submitters.len() > MAX_SETTLEMENT_PARTICIPANTS
            || self.proposal.settlements.len() > MAX_SETTLEMENT_PARTICIPANTS
        {
            return Err(SettlementError::ProposalTooLarge);
        }

        let mut out = Vec::new();
        out.extend_from_slice(&SETTLEMENT_TX_WIRE_MAGIC);
        out.push(SETTLEMENT_TX_WIRE_VERSION);
        out.extend_from_slice(&self.deployment_digest);
        out.extend_from_slice(&self.nonce.to_be_bytes());
        out.extend_from_slice(&self.gas_limit.to_be_bytes());
        out.extend_from_slice(&self.public_key);
        out.extend_from_slice(&self.proposal.reconstruction_epoch.to_be_bytes());
        out.extend_from_slice(&self.proposal.finalized_at.to_be_bytes());

        out.extend_from_slice(
            &(u32::try_from(self.proposal.missed_submitters.len())
                .map_err(|_| SettlementError::ProposalTooLarge)?
                .to_be_bytes()),
        );
        for submitter in &self.proposal.missed_submitters {
            encode_settlement_string(&mut out, submitter)?;
        }
        out.extend_from_slice(
            &(u32::try_from(self.proposal.settlements.len())
                .map_err(|_| SettlementError::ProposalTooLarge)?
                .to_be_bytes()),
        );
        for settlement in &self.proposal.settlements {
            encode_settlement_string(&mut out, &settlement.submitter)?;
            out.push(u8::from(settlement.submitted));
            out.extend_from_slice(&settlement.locked_deposit.to_be_bytes());
            out.extend_from_slice(&settlement.penalty.to_be_bytes());
            out.extend_from_slice(&settlement.refund.to_be_bytes());
            out.extend_from_slice(&settlement.compensation.to_be_bytes());
            out.extend_from_slice(&settlement.net_release.to_be_bytes());
        }
        out.extend_from_slice(&self.proposal.burned_penalty_remainder.to_be_bytes());
        out.extend_from_slice(&self.signature);
        Ok(out)
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, SettlementError> {
        let mut bytes = bytes;
        if take_wire_bytes(&mut bytes, 4)? != SETTLEMENT_TX_WIRE_MAGIC {
            return Err(SettlementError::InvalidWireMagic);
        }
        let version = read_wire_u8(&mut bytes)?;
        if version != SETTLEMENT_TX_WIRE_VERSION {
            return Err(SettlementError::UnsupportedWireVersion(version));
        }
        let deployment_digest = take_wire_bytes(&mut bytes, 32)?
            .try_into()
            .expect("32-byte deployment digest");
        let nonce = read_wire_u64(&mut bytes)?;
        let gas_limit = read_wire_u128(&mut bytes)?;
        let public_key = take_wire_bytes(&mut bytes, 32)?
            .try_into()
            .expect("32-byte public key");
        let reconstruction_epoch = read_wire_u64(&mut bytes)?;
        let finalized_at = read_wire_u64(&mut bytes)?;

        let missed_count = read_wire_count(&mut bytes)?;
        let mut missed_submitters = Vec::with_capacity(missed_count);
        for _ in 0..missed_count {
            missed_submitters.push(read_wire_string(&mut bytes)?);
        }
        let settlement_count = read_wire_count(&mut bytes)?;
        let mut settlements = Vec::with_capacity(settlement_count);
        for _ in 0..settlement_count {
            let submitter = read_wire_string(&mut bytes)?;
            let submitted = read_wire_u8(&mut bytes)?;
            if submitted > 1 {
                return Err(SettlementError::InvalidWireLength);
            }
            settlements.push(crate::reconstruction_policy::PlayerSettlement {
                submitter,
                submitted: submitted == 1,
                locked_deposit: read_wire_u128(&mut bytes)?,
                penalty: read_wire_u128(&mut bytes)?,
                refund: read_wire_u128(&mut bytes)?,
                compensation: read_wire_u128(&mut bytes)?,
                net_release: read_wire_u128(&mut bytes)?,
            });
        }
        let burned_penalty_remainder = read_wire_u128(&mut bytes)?;
        let signature = take_wire_bytes(&mut bytes, 64)?
            .try_into()
            .expect("64-byte signature");
        if !bytes.is_empty() {
            return Err(SettlementError::InvalidWireLength);
        }

        let request = Self {
            sender: hex::encode(public_key),
            deployment_digest,
            nonce,
            gas_limit,
            proposal: DeadlineSettlement {
                reconstruction_epoch,
                finalized_at,
                missed_submitters,
                settlements,
                burned_penalty_remainder,
            },
            public_key,
            signature,
        };
        validate_settlement_proposal(&request.proposal)?;
        if !verify_settlement_transaction_signature(&request) {
            return Err(SettlementError::InvalidTransactionSignature);
        }
        Ok(request)
    }
}

/// Validate the proposal semantics that every settlement adapter must enforce
/// before applying events. This function does not verify escrow balances; the
/// adapter's committed state must do that separately.
pub fn validate_settlement_proposal(proposal: &DeadlineSettlement) -> Result<(), SettlementError> {
    InMemorySettlementLedger::validate_proposal(proposal)
}

/// Deterministic reference ledger for tests and off-chain prototypes.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct InMemorySettlementLedger {
    escrow_by_epoch: BTreeMap<u64, BTreeMap<String, u128>>,
    escrow_total_by_epoch: BTreeMap<u64, u128>,
    settled_by_epoch: BTreeMap<u64, SettlementExecution>,
    released_by_submitter: BTreeMap<String, u128>,
    burned_total: u128,
}

impl InMemorySettlementLedger {
    pub fn outstanding_escrow(&self, reconstruction_epoch: u64) -> u128 {
        self.escrow_total_by_epoch
            .get(&reconstruction_epoch)
            .copied()
            .unwrap_or(0)
    }

    pub fn locked_amount(&self, reconstruction_epoch: u64, submitter: &str) -> u128 {
        self.escrow_by_epoch
            .get(&reconstruction_epoch)
            .and_then(|players| players.get(submitter))
            .copied()
            .unwrap_or(0)
    }

    pub fn released_to(&self, submitter: &str) -> u128 {
        self.released_by_submitter
            .get(submitter)
            .copied()
            .unwrap_or(0)
    }

    pub fn burned_total(&self) -> u128 {
        self.burned_total
    }

    pub fn settlement_execution(&self, reconstruction_epoch: u64) -> Option<&SettlementExecution> {
        self.settled_by_epoch.get(&reconstruction_epoch)
    }

    fn validate_locked_escrow(
        &self,
        proposal: &DeadlineSettlement,
    ) -> Result<BTreeMap<String, u128>, SettlementError> {
        let locked = self
            .escrow_by_epoch
            .get(&proposal.reconstruction_epoch)
            .cloned()
            .unwrap_or_default();
        for player in &proposal.settlements {
            let actual = locked.get(&player.submitter).copied().unwrap_or(0);
            if actual == 0 {
                return Err(SettlementError::MissingLockedDeposit {
                    submitter: player.submitter.clone(),
                });
            }
            if actual != player.locked_deposit {
                return Err(SettlementError::LockedAmountMismatch {
                    submitter: player.submitter.clone(),
                });
            }
        }
        if locked.len() != proposal.settlements.len() {
            let expected: Vec<_> = proposal
                .settlements
                .iter()
                .map(|item| &item.submitter)
                .collect();
            let extra = locked
                .keys()
                .find(|submitter| !expected.contains(submitter))
                .cloned();
            if let Some(submitter) = extra {
                return Err(SettlementError::ExtraLockedDeposit { submitter });
            }
            return Err(SettlementError::LockedEscrowInvariant);
        }
        Ok(locked)
    }

    pub fn validate_proposal(proposal: &DeadlineSettlement) -> Result<(), SettlementError> {
        if proposal.reconstruction_epoch == 0 {
            return Err(SettlementError::ZeroEpoch);
        }
        if proposal.finalized_at == 0 {
            return Err(SettlementError::ProposalFinalizedAtZero);
        }
        if proposal.settlements.is_empty() {
            return Err(SettlementError::EmptySettlement);
        }

        let mut previous_submitter: Option<String> = None;
        for player in &proposal.settlements {
            if player.submitter.is_empty() || player.locked_deposit == 0 {
                return Err(SettlementError::InvalidPlayerArithmetic {
                    submitter: player.submitter.clone(),
                });
            }
            if let Some(previous) = previous_submitter.as_deref() {
                if player.submitter.as_str() <= previous {
                    if player.submitter == previous {
                        return Err(SettlementError::DuplicateSubmitter {
                            submitter: player.submitter.clone(),
                        });
                    }
                    return Err(SettlementError::NonCanonicalSubmitterOrder);
                }
            }
            previous_submitter = Some(player.submitter.clone());

            let refund_plus_penalty = player
                .refund
                .checked_add(player.penalty)
                .filter(|total| *total == player.locked_deposit);
            let release = player
                .refund
                .checked_add(player.compensation)
                .filter(|total| *total == player.net_release);
            let penalty_in_range = player.penalty <= player.locked_deposit;
            let branch_is_consistent = (!player.submitted || player.penalty == 0)
                && (player.submitted || player.compensation == 0);
            if refund_plus_penalty.is_none()
                || release.is_none()
                || !penalty_in_range
                || !branch_is_consistent
            {
                return Err(SettlementError::InvalidPlayerArithmetic {
                    submitter: player.submitter.clone(),
                });
            }
        }

        let expected_missed: Vec<_> = proposal
            .settlements
            .iter()
            .filter(|player| !player.submitted)
            .map(|player| player.submitter.clone())
            .collect();
        if proposal.missed_submitters != expected_missed {
            return Err(SettlementError::InvalidMissedSubmitterList);
        }

        let total_penalty = proposal
            .settlements
            .iter()
            .map(|player| player.penalty)
            .try_fold(0u128, |total, value| total.checked_add(value))
            .ok_or(SettlementError::CompensationInvariant)?;
        let total_compensation = proposal
            .settlements
            .iter()
            .map(|player| player.compensation)
            .try_fold(0u128, |total, value| total.checked_add(value))
            .ok_or(SettlementError::CompensationInvariant)?;
        if total_penalty
            != total_compensation
                .checked_add(proposal.burned_penalty_remainder)
                .ok_or(SettlementError::CompensationInvariant)?
        {
            return Err(SettlementError::CompensationInvariant);
        }

        let total_locked = proposal
            .settlements
            .iter()
            .map(|player| player.locked_deposit)
            .try_fold(0u128, |total, value| total.checked_add(value))
            .ok_or(SettlementError::LockedEscrowInvariant)?;
        let total_refund = proposal
            .settlements
            .iter()
            .map(|player| player.refund)
            .try_fold(0u128, |total, value| total.checked_add(value))
            .ok_or(SettlementError::LockedEscrowInvariant)?;
        if total_locked
            != total_refund
                .checked_add(total_compensation)
                .and_then(|value| value.checked_add(proposal.burned_penalty_remainder))
                .ok_or(SettlementError::LockedEscrowInvariant)?
        {
            return Err(SettlementError::LockedEscrowInvariant);
        }
        Ok(())
    }
}

impl ReconstructionSettlementAdapter for InMemorySettlementLedger {
    type Error = SettlementError;

    fn lock_deposit(
        &mut self,
        reconstruction_epoch: u64,
        submitter: &str,
        amount: u128,
    ) -> Result<DepositLockReceipt, Self::Error> {
        if reconstruction_epoch == 0 {
            return Err(SettlementError::ZeroEpoch);
        }
        if submitter.is_empty() {
            return Err(SettlementError::InvalidPlayerArithmetic {
                submitter: submitter.to_owned(),
            });
        }
        if amount == 0 {
            return Err(SettlementError::ZeroAmount);
        }
        if self.settled_by_epoch.contains_key(&reconstruction_epoch) {
            return Err(SettlementError::EpochAlreadySettled {
                reconstruction_epoch,
            });
        }
        let receipt = DepositLockReceipt {
            reconstruction_epoch,
            submitter: submitter.to_owned(),
            amount,
        };
        if self
            .escrow_by_epoch
            .get(&reconstruction_epoch)
            .and_then(|players| players.get(submitter))
            .is_some()
        {
            return if self.locked_amount(reconstruction_epoch, submitter) == amount {
                Ok(receipt)
            } else {
                Err(SettlementError::DuplicateDepositWithDifferentAmount {
                    submitter: submitter.to_owned(),
                })
            };
        }

        let total = self
            .escrow_total_by_epoch
            .get(&reconstruction_epoch)
            .copied()
            .unwrap_or(0);
        self.escrow_total_by_epoch.insert(
            reconstruction_epoch,
            total
                .checked_add(amount)
                .ok_or(SettlementError::EscrowOverflow)?,
        );
        self.escrow_by_epoch
            .entry(reconstruction_epoch)
            .or_default()
            .insert(submitter.to_owned(), amount);
        Ok(receipt)
    }

    fn apply_settlement(
        &mut self,
        proposal: &DeadlineSettlement,
    ) -> Result<SettlementExecution, Self::Error> {
        if let Some(previous) = self.settled_by_epoch.get(&proposal.reconstruction_epoch) {
            return if &previous.proposal == proposal {
                Ok(previous.clone())
            } else {
                Err(SettlementError::SettlementConflict {
                    reconstruction_epoch: proposal.reconstruction_epoch,
                })
            };
        }
        Self::validate_proposal(proposal)?;
        let locked = self.validate_locked_escrow(proposal)?;
        let locked_total = self
            .escrow_total_by_epoch
            .get(&proposal.reconstruction_epoch)
            .copied()
            .unwrap_or(0);
        let summed_locks = locked
            .values()
            .copied()
            .try_fold(0u128, |total, value| total.checked_add(value))
            .ok_or(SettlementError::LockedEscrowInvariant)?;
        if locked_total != summed_locks {
            return Err(SettlementError::LockedEscrowInvariant);
        }

        let mut releases = self.released_by_submitter.clone();
        let mut events = Vec::new();
        for player in &proposal.settlements {
            if player.refund > 0 {
                events.push(SettlementEvent::Refund {
                    reconstruction_epoch: proposal.reconstruction_epoch,
                    to: player.submitter.clone(),
                    amount: player.refund,
                });
            }
            if player.compensation > 0 {
                events.push(SettlementEvent::Compensation {
                    reconstruction_epoch: proposal.reconstruction_epoch,
                    to: player.submitter.clone(),
                    amount: player.compensation,
                });
            }
            let release = releases
                .get(&player.submitter)
                .copied()
                .unwrap_or(0)
                .checked_add(player.net_release)
                .ok_or(SettlementError::ReleaseOverflow)?;
            releases.insert(player.submitter.clone(), release);
        }
        if proposal.burned_penalty_remainder > 0 {
            events.push(SettlementEvent::Burn {
                reconstruction_epoch: proposal.reconstruction_epoch,
                amount: proposal.burned_penalty_remainder,
            });
        }
        let new_burned_total = self
            .burned_total
            .checked_add(proposal.burned_penalty_remainder)
            .ok_or(SettlementError::ReleaseOverflow)?;

        let execution = SettlementExecution {
            proposal: proposal.clone(),
            events,
        };
        self.escrow_by_epoch.remove(&proposal.reconstruction_epoch);
        self.escrow_total_by_epoch
            .remove(&proposal.reconstruction_epoch);
        self.released_by_submitter = releases;
        self.burned_total = new_burned_total;
        self.settled_by_epoch
            .insert(proposal.reconstruction_epoch, execution.clone());
        Ok(execution)
    }
}

/// A deliberately explicit model of the transaction boundary that a real
/// settlement adapter must face.
///
/// The simulator separates a candidate ledger state from the committed ledger
/// state. A transaction applies against a clone; only after the configured
/// confirmation depth does that candidate become committed. A reorg before
/// finality drops the candidate, restores the sender nonce, and leaves the
/// original escrow untouched.
///
/// This is not a blockchain and does not model mempool propagation, signature
/// execution gas refunds, or consensus-specific probabilistic finality. It
/// verifies signatures and binds them to a deployment digest so nonce replay,
/// gas admission, cross-deployment replay, and reorg rollback are explicit
/// before integrating a concrete chain SDK.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SimulatedChainSettlementHost {
    deployment_digest: [u8; 32],
    committed_ledger: InMemorySettlementLedger,
    candidate_ledger: Option<InMemorySettlementLedger>,
    candidate_receipt: Option<SimulatedSettlementReceipt>,
    expected_nonce_by_sender: BTreeMap<String, u64>,
    finalized_receipts: BTreeMap<SimulatedSettlementTxHash, SimulatedSettlementReceipt>,
    block_height: u64,
    required_confirmations: u64,
}

impl SimulatedChainSettlementHost {
    pub const BASE_GAS: u128 = 21_000;
    pub const GAS_PER_EVENT: u128 = 35_000;

    pub fn new(required_confirmations: u64) -> Self {
        Self {
            deployment_digest: local_settlement_deployment_digest(),
            committed_ledger: InMemorySettlementLedger::default(),
            candidate_ledger: None,
            candidate_receipt: None,
            expected_nonce_by_sender: BTreeMap::new(),
            finalized_receipts: BTreeMap::new(),
            block_height: 0,
            required_confirmations,
        }
    }

    /// Construct a host bound to a deployment-derived nonzero digest.
    pub fn new_for_deployment(
        required_confirmations: u64,
        deployment_digest: [u8; 32],
    ) -> Result<Self, SettlementError> {
        if deployment_digest == [0u8; 32] {
            return Err(SettlementError::InvalidDeploymentDigest);
        }
        Ok(Self {
            deployment_digest,
            committed_ledger: InMemorySettlementLedger::default(),
            candidate_ledger: None,
            candidate_receipt: None,
            expected_nonce_by_sender: BTreeMap::new(),
            finalized_receipts: BTreeMap::new(),
            block_height: 0,
            required_confirmations,
        })
    }

    pub fn deployment_digest(&self) -> [u8; 32] {
        self.deployment_digest
    }

    pub fn required_confirmations(&self) -> u64 {
        self.required_confirmations
    }

    pub fn block_height(&self) -> u64 {
        self.block_height
    }

    pub fn outstanding_escrow(&self, reconstruction_epoch: u64) -> u128 {
        self.committed_ledger
            .outstanding_escrow(reconstruction_epoch)
    }

    pub fn locked_amount(&self, reconstruction_epoch: u64, submitter: &str) -> u128 {
        self.committed_ledger
            .locked_amount(reconstruction_epoch, submitter)
    }

    pub fn released_to(&self, submitter: &str) -> u128 {
        self.committed_ledger.released_to(submitter)
    }

    pub fn burned_total(&self) -> u128 {
        self.committed_ledger.burned_total()
    }

    pub fn lock_deposit(
        &mut self,
        reconstruction_epoch: u64,
        submitter: &str,
        amount: u128,
    ) -> Result<DepositLockReceipt, SettlementError> {
        if self.candidate_receipt.is_some() {
            return Err(SettlementError::PendingTransactionExists);
        }
        self.committed_ledger
            .lock_deposit(reconstruction_epoch, submitter, amount)
    }

    pub fn estimate_gas(proposal: &DeadlineSettlement) -> u128 {
        let events = proposal
            .settlements
            .iter()
            .map(|player| usize::from(player.refund > 0) + usize::from(player.compensation > 0))
            .sum::<usize>()
            + usize::from(proposal.burned_penalty_remainder > 0);
        Self::BASE_GAS + Self::GAS_PER_EVENT * events as u128
    }

    pub fn transaction_hash(request: &SettlementTransactionRequest) -> SimulatedSettlementTxHash {
        let message_hash = settlement_message_hash(request);
        let mut buffer = Vec::with_capacity(32 + 32 + 64);
        buffer.extend_from_slice(&message_hash);
        buffer.extend_from_slice(&request.public_key);
        buffer.extend_from_slice(&request.signature);
        StarkCurve::hash_to_scalar(&buffer).to_bytes_be()
    }

    pub fn submit_transaction(
        &mut self,
        request: &SettlementTransactionRequest,
    ) -> Result<SimulatedSettlementReceipt, SettlementError> {
        if request.sender.is_empty() {
            return Err(SettlementError::InvalidSender);
        }
        if request.deployment_digest != self.deployment_digest {
            return Err(SettlementError::DeploymentMismatch);
        }
        if !verify_settlement_transaction_signature(request) {
            return Err(SettlementError::InvalidTransactionSignature);
        }
        let hash = Self::transaction_hash(request);
        if let Some(receipt) = self.finalized_receipts.get(&hash) {
            return Ok(receipt.clone());
        }
        if let Some(pending) = &self.candidate_receipt {
            return if pending.transaction_hash == hash {
                Ok(pending.clone())
            } else {
                Err(SettlementError::PendingTransactionExists)
            };
        }

        let expected = self
            .expected_nonce_by_sender
            .get(&request.sender)
            .copied()
            .unwrap_or(0);
        if request.nonce != expected {
            if request.nonce < expected {
                return Err(SettlementError::NonceAlreadyUsed);
            }
            return Err(SettlementError::InvalidNonce {
                expected,
                supplied: request.nonce,
            });
        }
        let required_gas = Self::estimate_gas(&request.proposal);
        if request.gas_limit < required_gas {
            return Err(SettlementError::GasLimitTooLow {
                required: required_gas,
                supplied: request.gas_limit,
            });
        }

        let mut candidate = self.committed_ledger.clone();
        let execution = candidate.apply_settlement(&request.proposal)?;
        let receipt = SimulatedSettlementReceipt {
            transaction_hash: hash,
            sender: request.sender.clone(),
            nonce: request.nonce,
            gas_limit: request.gas_limit,
            gas_used: required_gas,
            included_block: self.block_height.saturating_add(1),
            confirmations: 0,
            finalized: false,
            execution,
        };
        self.expected_nonce_by_sender
            .insert(request.sender.clone(), expected.saturating_add(1));
        self.candidate_ledger = Some(candidate);
        self.candidate_receipt = Some(receipt.clone());
        Ok(receipt)
    }

    pub fn pending_receipt(&self) -> Option<&SimulatedSettlementReceipt> {
        self.candidate_receipt.as_ref()
    }

    pub fn finalized_receipt(
        &self,
        transaction_hash: SimulatedSettlementTxHash,
    ) -> Option<&SimulatedSettlementReceipt> {
        self.finalized_receipts.get(&transaction_hash)
    }

    /// Advance one block. When the required confirmation count is reached, the
    /// candidate ledger becomes the committed ledger atomically.
    pub fn advance_block(&mut self) -> Result<Option<SimulatedSettlementReceipt>, SettlementError> {
        self.block_height = self
            .block_height
            .checked_add(1)
            .ok_or(SettlementError::ReleaseOverflow)?;
        let Some(receipt) = self.candidate_receipt.as_mut() else {
            return Ok(None);
        };
        receipt.confirmations = self
            .block_height
            .checked_sub(receipt.included_block)
            .and_then(|depth| depth.checked_add(1))
            .ok_or(SettlementError::ReleaseOverflow)?;
        if receipt.confirmations < self.required_confirmations {
            return Ok(None);
        }

        let receipt = receipt.clone();
        let candidate = self
            .candidate_ledger
            .take()
            .ok_or(SettlementError::LockedEscrowInvariant)?;
        self.committed_ledger = candidate;
        self.candidate_receipt = None;
        let mut finalized = receipt;
        finalized.finalized = true;
        self.finalized_receipts
            .insert(finalized.transaction_hash, finalized.clone());
        Ok(Some(finalized))
    }

    /// Drop the unfinalized candidate and restore the sender's nonce.
    pub fn reorg_pending(&mut self) -> Result<SimulatedSettlementReceipt, SettlementError> {
        let Some(receipt) = self.candidate_receipt.clone() else {
            return Err(SettlementError::TransactionNotFound);
        };
        if receipt.finalized {
            return Err(SettlementError::TransactionAlreadyFinalized);
        }
        let expected = self
            .expected_nonce_by_sender
            .get(&receipt.sender)
            .copied()
            .ok_or(SettlementError::LockedEscrowInvariant)?;
        self.expected_nonce_by_sender
            .insert(receipt.sender.clone(), expected.saturating_sub(1));
        self.candidate_ledger = None;
        self.candidate_receipt = None;
        Ok(receipt)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reconstruction_policy::{
        ReconstructionPolicyConfig, ReconstructionSubmissionPolicy,
    };

    const PSTX_KAT_WIRE_HEX: &str = "505354580106f794050c4ae9f3e8595445a38829403d545eb7efa44ea7d764c9fe51ae6aab000000000000002a0000000000000000000000000002fda082a7fe26deaa8ccaa56d78e73717d7424839e74934e50043bca1f33c7886826b000000000000000b000000000000006400000001000000056361726f6c0000000300000005616c696365010000000000000000000000000000006400000000000000000000000000000000000000000000000000000000000000640000000000000000000000000000000f0000000000000000000000000000007300000003626f62010000000000000000000000000000006400000000000000000000000000000000000000000000000000000000000000640000000000000000000000000000000f00000000000000000000000000000073000000056361726f6c00000000000000000000000000000000640000000000000000000000000000001e0000000000000000000000000000004600000000000000000000000000000000000000000000000000000000000000460000000000000000000000000000000004dad1e8b5b893b5cac4b596542aad86adad7f9447ded20d77bc2285b0d3675e0416ed46ba156f2d4353eb252ea3e82d6584151b829567bd0293a80054f453f7";
    const PSTX_KAT_TX_HASH_HEX: &str =
        "05d05f4ea9918adedb43e3d392402eca70bbd262dfa90b06d52ab730c10e4a58";

    #[test]
    fn settlement_errors_are_standard_errors_with_details() {
        fn assert_standard_error<E: std::error::Error>(error: &E) {
            assert!(!error.to_string().is_empty());
        }

        assert_standard_error(&SettlementError::InvalidNonce {
            expected: 7,
            supplied: 8,
        });
        assert_standard_error(&SettlementError::UnsupportedWireVersion(2));
        assert_eq!(
            SettlementError::GasLimitTooLow {
                required: 30,
                supplied: 20
            }
            .to_string(),
            "gas limit 20 is below the required 30"
        );
    }

    fn policy_with_one_miss() -> DeadlineSettlement {
        let config = ReconstructionPolicyConfig {
            reconstruction_epoch: 11,
            submission_deadline: 100,
            required_submitters: vec!["alice".into(), "bob".into(), "carol".into()],
            deposit_per_player: 100,
            penalty_per_missed_submission: 30,
        };
        let mut policy = ReconstructionSubmissionPolicy::new(config, 10).unwrap();
        policy
            .record_accepted_submission("alice", 11, [1; 32], 20)
            .unwrap();
        policy
            .record_accepted_submission("bob", 11, [2; 32], 30)
            .unwrap();
        policy.finalize_at(100).unwrap()
    }

    fn lock_required(ledger: &mut InMemorySettlementLedger, proposal: &DeadlineSettlement) {
        for player in &proposal.settlements {
            ReconstructionSettlementAdapter::lock_deposit(
                ledger,
                proposal.reconstruction_epoch,
                &player.submitter,
                player.locked_deposit,
            )
            .unwrap();
        }
    }

    fn settlement_request(
        proposal: &DeadlineSettlement,
        nonce: u64,
        gas_limit: u128,
    ) -> SettlementTransactionRequest {
        let request = SettlementTransactionRequest {
            sender: "settlement-operator".into(),
            deployment_digest: local_settlement_deployment_digest(),
            nonce,
            gas_limit,
            proposal: proposal.clone(),
            public_key: [0u8; 32],
            signature: [0u8; 64],
        };
        let secret_key = StarkCurve::hash_to_scalar(b"settlement-simulator-operator");
        sign_settlement_transaction(&secret_key, request).expect("valid signing request")
    }

    #[test]
    fn simulated_chain_admits_nonce_and_gas_then_finalizes_candidate() {
        let proposal = policy_with_one_miss();
        let mut host = SimulatedChainSettlementHost::new(2);
        for player in &proposal.settlements {
            host.lock_deposit(11, &player.submitter, player.locked_deposit)
                .unwrap();
        }
        let gas = SimulatedChainSettlementHost::estimate_gas(&proposal);
        let request = settlement_request(&proposal, 0, gas);
        let pending = host.submit_transaction(&request).unwrap();
        assert_eq!(pending.nonce, 0);
        assert_eq!(pending.gas_used, gas);
        assert_eq!(pending.included_block, 1);
        assert_eq!(pending.confirmations, 0);
        assert!(!pending.finalized);

        // Until finality, the visible committed escrow is unchanged.
        assert_eq!(host.outstanding_escrow(11), 300);
        assert_eq!(host.block_height(), 0);
        assert_eq!(host.advance_block().unwrap(), None);
        assert_eq!(host.pending_receipt().unwrap().confirmations, 1);
        assert_eq!(host.outstanding_escrow(11), 300);

        let identical = host.submit_transaction(&request).unwrap();
        assert_eq!(identical.transaction_hash, pending.transaction_hash);
        assert_eq!(identical.nonce, pending.nonce);
        assert_eq!(identical.execution, pending.execution);
        assert_eq!(identical.confirmations, 1);
        let finalized = host.advance_block().unwrap().unwrap();
        assert!(finalized.finalized);
        assert_eq!(finalized.confirmations, 2);
        assert_eq!(host.outstanding_escrow(11), 0);
        assert_eq!(host.released_to("alice"), 115);
        assert_eq!(host.burned_total(), 0);
        assert_eq!(
            host.finalized_receipt(finalized.transaction_hash),
            Some(&finalized)
        );

        // The finalized transaction remains idempotent, but its nonce cannot
        // be reused for a different proposal.
        assert_eq!(host.submit_transaction(&request).unwrap(), finalized);
        let settlement_secret = StarkCurve::hash_to_scalar(b"settlement-simulator-operator");
        let mut conflict_request = request.clone();
        conflict_request.nonce = 0;
        conflict_request.proposal.reconstruction_epoch = 12;
        let conflict_request = sign_settlement_transaction(&settlement_secret, conflict_request)
            .expect("valid signing request");
        assert!(matches!(
            host.submit_transaction(&conflict_request),
            Err(SettlementError::NonceAlreadyUsed)
        ));
    }

    #[test]
    fn simulated_chain_rejects_bad_nonce_and_insufficient_gas_without_mutation() {
        let proposal = policy_with_one_miss();
        let mut host = SimulatedChainSettlementHost::new(2);
        for player in &proposal.settlements {
            host.lock_deposit(11, &player.submitter, player.locked_deposit)
                .unwrap();
        }
        let required = SimulatedChainSettlementHost::estimate_gas(&proposal);
        assert!(required > SimulatedChainSettlementHost::BASE_GAS);

        let stale = settlement_request(&proposal, 0, required - 1);
        assert!(matches!(
            host.submit_transaction(&stale),
            Err(SettlementError::GasLimitTooLow { required: value, supplied })
                if value == required && supplied == required - 1
        ));
        assert!(host.pending_receipt().is_none());
        assert_eq!(host.outstanding_escrow(11), 300);

        let future = settlement_request(&proposal, 1, required);
        assert!(matches!(
            host.submit_transaction(&future),
            Err(SettlementError::InvalidNonce {
                expected: 0,
                supplied: 1
            })
        ));
        assert!(host.pending_receipt().is_none());
    }

    #[test]
    fn simulated_chain_reorg_drops_candidate_and_restores_nonce() {
        let proposal = policy_with_one_miss();
        let mut host = SimulatedChainSettlementHost::new(3);
        for player in &proposal.settlements {
            host.lock_deposit(11, &player.submitter, player.locked_deposit)
                .unwrap();
        }
        let request = settlement_request(
            &proposal,
            0,
            SimulatedChainSettlementHost::estimate_gas(&proposal),
        );
        let first = host.submit_transaction(&request).unwrap();
        assert_eq!(host.outstanding_escrow(11), 300);

        let dropped = host.reorg_pending().unwrap();
        assert_eq!(dropped, first);
        assert!(host.pending_receipt().is_none());
        assert_eq!(host.outstanding_escrow(11), 300);
        assert_eq!(host.released_to("alice"), 0);

        // The nonce rolled back with the dropped transaction, so the same
        // request can be replayed after re-submission.
        let replay = host.submit_transaction(&request).unwrap();
        assert_eq!(replay.transaction_hash, first.transaction_hash);
        assert!(matches!(host.reorg_pending(), Ok(_)));
        assert!(matches!(
            host.reorg_pending(),
            Err(SettlementError::TransactionNotFound)
        ));
    }

    #[test]
    fn simulated_transaction_hash_binds_public_key_nonce_gas_and_proposal() {
        let proposal = policy_with_one_miss();
        let gas = SimulatedChainSettlementHost::estimate_gas(&proposal);
        let request = settlement_request(&proposal, 7, gas);
        let baseline = SimulatedChainSettlementHost::transaction_hash(&request);

        let mut changed_public_key = request.clone();
        changed_public_key.public_key = [1u8; 32];
        let mut changed_nonce = request.clone();
        changed_nonce.nonce = 8;
        let mut changed_gas = request.clone();
        changed_gas.gas_limit += 1;
        let mut changed_proposal = request.clone();
        changed_proposal.proposal.reconstruction_epoch += 1;

        for changed in [
            changed_public_key,
            changed_nonce,
            changed_gas,
            changed_proposal,
        ] {
            assert_ne!(
                SimulatedChainSettlementHost::transaction_hash(&changed),
                baseline
            );
        }
    }

    #[test]
    fn simulated_chain_rejects_invalid_transaction_signature() {
        let proposal = policy_with_one_miss();
        let mut host = SimulatedChainSettlementHost::new(2);
        for player in &proposal.settlements {
            host.lock_deposit(11, &player.submitter, player.locked_deposit)
                .unwrap();
        }
        let gas = SimulatedChainSettlementHost::estimate_gas(&proposal);
        let request = settlement_request(&proposal, 0, gas);

        let mut wrong_public_key = request.clone();
        wrong_public_key.public_key = [1u8; 32];
        assert!(!verify_settlement_transaction_signature(&wrong_public_key));
        assert!(matches!(
            host.submit_transaction(&wrong_public_key),
            Err(SettlementError::InvalidTransactionSignature)
        ));

        let mut noncanonical_sender = request.clone();
        noncanonical_sender.sender.make_ascii_uppercase();
        assert!(!verify_settlement_transaction_signature(
            &noncanonical_sender
        ));
        assert!(matches!(
            host.submit_transaction(&noncanonical_sender),
            Err(SettlementError::InvalidTransactionSignature)
        ));

        let zero_secret = StarkScalar::zero();
        let identity_sign_request = SettlementTransactionRequest {
            sender: hex::encode([0u8; 32]),
            deployment_digest: local_settlement_deployment_digest(),
            nonce: request.nonce,
            gas_limit: request.gas_limit,
            proposal: request.proposal.clone(),
            public_key: [0u8; 32],
            signature: [0u8; 64],
        };
        assert_eq!(
            sign_settlement_transaction(&zero_secret, identity_sign_request.clone()),
            Err(SettlementError::InvalidSecretKey)
        );
        assert!(!verify_settlement_transaction_signature(
            &identity_sign_request
        ));
        assert!(matches!(
            host.submit_transaction(&identity_sign_request),
            Err(SettlementError::InvalidTransactionSignature)
        ));

        let zero_domain_request = SettlementTransactionRequest {
            deployment_digest: [0u8; 32],
            ..identity_sign_request.clone()
        };
        assert_eq!(
            sign_settlement_transaction(
                &StarkCurve::hash_to_scalar(b"settlement-simulator-operator"),
                zero_domain_request.clone(),
            ),
            Err(SettlementError::InvalidDeploymentDigest)
        );
        assert!(!verify_settlement_transaction_signature(
            &zero_domain_request
        ));

        let mut tampered_signature = request.clone();
        tampered_signature.signature[0] ^= 1;
        assert!(!verify_settlement_transaction_signature(
            &tampered_signature
        ));
        assert!(matches!(
            host.submit_transaction(&tampered_signature),
            Err(SettlementError::InvalidTransactionSignature)
        ));

        let mut tampered_proposal = request.clone();
        tampered_proposal.proposal.burned_penalty_remainder += 1;
        assert!(!verify_settlement_transaction_signature(&tampered_proposal));
        assert!(matches!(
            host.submit_transaction(&tampered_proposal),
            Err(SettlementError::InvalidTransactionSignature)
        ));
        assert!(host.pending_receipt().is_none());
    }

    #[test]
    fn settlement_proposal_rejects_zero_finalized_at() {
        let mut proposal = policy_with_one_miss();
        proposal.finalized_at = 0;
        assert!(matches!(
            validate_settlement_proposal(&proposal),
            Err(SettlementError::ProposalFinalizedAtZero)
        ));
    }

    #[test]
    fn verifier_rejects_zero_schnorr_response() {
        let proposal = policy_with_one_miss();
        let request = settlement_request(&proposal, 0, 196_000);
        let mut zero_response = request.clone();
        zero_response.signature[32..].fill(0);
        assert!(!verify_settlement_transaction_signature(&zero_response));
    }

    #[test]
    fn verifier_rejects_identity_schnorr_commitment() {
        let proposal = policy_with_one_miss();
        let gas = SimulatedChainSettlementHost::estimate_gas(&proposal);
        let secret_key = StarkCurve::hash_to_scalar(b"settlement-simulator-operator");
        let mut request = settlement_request(&proposal, 0, gas);
        let public_key = StarkCurve::base_g() * secret_key;
        let message_hash = settlement_message_hash(&request);
        let identity = StarkPoint::identity();
        let challenge = schnorr_challenge(&identity, &public_key, &message_hash);
        let response = challenge * secret_key;

        request.signature[..32].copy_from_slice(identity.compress().as_ref());
        request.signature[32..].copy_from_slice(&response.to_bytes_be());

        // The scalar equation can be made to hold for R = identity when the
        // signer is known. The canonical verifier must still reject identity
        // commitments before transaction admission.
        assert!(!verify_settlement_transaction_signature(&request));
        let mut host = SimulatedChainSettlementHost::new(2);
        assert!(matches!(
            host.submit_transaction(&request),
            Err(SettlementError::InvalidTransactionSignature)
        ));
    }

    #[test]
    fn simulated_transaction_hash_binds_signature_and_message() {
        let proposal = policy_with_one_miss();
        let gas = SimulatedChainSettlementHost::estimate_gas(&proposal);
        let request = settlement_request(&proposal, 7, gas);
        assert!(verify_settlement_transaction_signature(&request));
        assert_eq!(request.sender, hex::encode(request.public_key));

        let baseline = SimulatedChainSettlementHost::transaction_hash(&request);
        let mut alternate_key = StarkCurve::hash_to_scalar(b"settlement-simulator-other");
        if alternate_key == StarkCurve::hash_to_scalar(b"settlement-simulator-operator") {
            alternate_key = StarkCurve::hash_to_scalar(b"settlement-simulator-other-2");
        }
        let other = sign_settlement_transaction(
            &alternate_key,
            SettlementTransactionRequest {
                sender: String::new(),
                deployment_digest: local_settlement_deployment_digest(),
                nonce: request.nonce,
                gas_limit: request.gas_limit,
                proposal: request.proposal.clone(),
                public_key: [0u8; 32],
                signature: [0u8; 64],
            },
        )
        .expect("valid alternate signing request");
        assert_ne!(other.public_key, request.public_key);
        assert_ne!(
            SimulatedChainSettlementHost::transaction_hash(&other),
            baseline
        );

        let mut detached = request.clone();
        detached.signature = sign_schnorr(&alternate_key, &settlement_message_hash(&detached));
        assert_ne!(
            SimulatedChainSettlementHost::transaction_hash(&detached),
            baseline
        );
        assert!(!verify_settlement_transaction_signature(&detached));
    }

    #[test]
    fn signed_settlement_wire_roundtrips_and_fails_closed() {
        let proposal = policy_with_one_miss();
        let gas = SimulatedChainSettlementHost::estimate_gas(&proposal);
        let request = settlement_request(&proposal, 8, gas);
        let encoded = request.encode().expect("signed request encodes");
        let decoded =
            SettlementTransactionRequest::decode(&encoded).expect("signed request decodes");
        assert_eq!(decoded, request);
        assert_eq!(
            SimulatedChainSettlementHost::transaction_hash(&decoded),
            SimulatedChainSettlementHost::transaction_hash(&request)
        );

        let mut bad_magic = encoded.clone();
        bad_magic[0] = b'X';
        assert_eq!(
            SettlementTransactionRequest::decode(&bad_magic),
            Err(SettlementError::InvalidWireMagic)
        );

        let mut bad_version = encoded.clone();
        bad_version[4] = 2;
        assert_eq!(
            SettlementTransactionRequest::decode(&bad_version),
            Err(SettlementError::UnsupportedWireVersion(2))
        );

        let mut truncated = encoded.clone();
        truncated.pop();
        assert_eq!(
            SettlementTransactionRequest::decode(&truncated),
            Err(SettlementError::InvalidWireLength)
        );

        let mut trailing = encoded.clone();
        trailing.push(0);
        assert_eq!(
            SettlementTransactionRequest::decode(&trailing),
            Err(SettlementError::InvalidWireLength)
        );

        let mut tampered_signature = encoded.clone();
        let signature_start = encoded.len() - 64;
        tampered_signature[signature_start] ^= 1;
        assert_eq!(
            SettlementTransactionRequest::decode(&tampered_signature),
            Err(SettlementError::InvalidTransactionSignature)
        );

        let unsigned = SettlementTransactionRequest {
            sender: "not-derived".into(),
            deployment_digest: local_settlement_deployment_digest(),
            nonce: 8,
            gas_limit: gas,
            proposal: proposal,
            public_key: [9u8; 32],
            signature: [0u8; 64],
        };
        assert_eq!(
            unsigned.encode(),
            Err(SettlementError::InvalidTransactionSignature)
        );
    }

    #[test]
    fn signer_and_wire_reject_semantically_invalid_proposals() {
        let mut invalid_proposal = policy_with_one_miss();
        invalid_proposal.burned_penalty_remainder += 1;
        assert_eq!(
            validate_settlement_proposal(&invalid_proposal),
            Err(SettlementError::CompensationInvariant)
        );

        let secret_key = StarkCurve::hash_to_scalar(b"settlement-simulator-operator");
        let signing_request = SettlementTransactionRequest {
            sender: String::new(),
            deployment_digest: local_settlement_deployment_digest(),
            nonce: 9,
            gas_limit: SimulatedChainSettlementHost::estimate_gas(&invalid_proposal),
            proposal: invalid_proposal.clone(),
            public_key: [0u8; 32],
            signature: [0u8; 64],
        };
        assert_eq!(
            sign_settlement_transaction(&secret_key, signing_request),
            Err(SettlementError::CompensationInvariant)
        );

        let public_key = StarkCurve::base_g() * secret_key;
        let mut wire_request = SettlementTransactionRequest {
            sender: hex::encode(public_key.compress().as_ref()),
            deployment_digest: local_settlement_deployment_digest(),
            nonce: 9,
            gas_limit: SimulatedChainSettlementHost::estimate_gas(&invalid_proposal),
            proposal: invalid_proposal,
            public_key: public_key.compress().as_ref().to_vec().try_into().unwrap(),
            signature: [0u8; 64],
        };
        wire_request.signature = sign_schnorr(&secret_key, &settlement_message_hash(&wire_request));
        assert!(verify_settlement_transaction_signature(&wire_request));
        assert_eq!(
            wire_request.encode(),
            Err(SettlementError::CompensationInvariant)
        );
    }

    #[test]
    fn settlement_signature_binds_deployment_and_rejects_cross_domain() {
        let proposal = policy_with_one_miss();
        let gas = SimulatedChainSettlementHost::estimate_gas(&proposal);
        let local_request = settlement_request(&proposal, 0, gas);
        let local_domain = local_request.deployment_digest;
        let other_domain =
            settlement_deployment_digest_from_parts(b"test-chain-2", b"0xdead", b"adapter-v1")
                .expect("canonical deployment identity");
        assert_ne!(local_domain, other_domain);
        assert_ne!(
            settlement_message_hash(&local_request),
            settlement_message_hash(&SettlementTransactionRequest {
                deployment_digest: other_domain,
                ..local_request.clone()
            })
        );

        let mut host = SimulatedChainSettlementHost::new_for_deployment(2, other_domain)
            .expect("nonzero deployment");
        for player in &proposal.settlements {
            host.lock_deposit(11, &player.submitter, player.locked_deposit)
                .unwrap();
        }
        assert!(matches!(
            host.submit_transaction(&local_request),
            Err(SettlementError::DeploymentMismatch)
        ));

        let other_request = sign_settlement_transaction(
            &StarkCurve::hash_to_scalar(b"settlement-simulator-operator"),
            SettlementTransactionRequest {
                sender: String::new(),
                deployment_digest: other_domain,
                nonce: 0,
                gas_limit: gas,
                proposal: proposal.clone(),
                public_key: [0u8; 32],
                signature: [0u8; 64],
            },
        )
        .expect("valid other-domain signing request");
        assert!(verify_settlement_transaction_signature(&other_request));
        let receipt = host.submit_transaction(&other_request).unwrap();
        assert_eq!(receipt.nonce, 0);

        assert!(matches!(
            SimulatedChainSettlementHost::new_for_deployment(2, [0u8; 32]),
            Err(SettlementError::InvalidDeploymentDigest)
        ));
    }

    #[test]
    fn deployment_digest_parts_are_domain_separated_and_validated() {
        let first = settlement_deployment_digest_from_parts(b"1", b"23", b"v1")
            .expect("valid first identity");
        let repeated = settlement_deployment_digest_from_parts(b"1", b"23", b"v1")
            .expect("valid repeated identity");
        let shifted = settlement_deployment_digest_from_parts(b"12", b"3", b"v1")
            .expect("valid shifted identity");
        let different_version = settlement_deployment_digest_from_parts(b"1", b"23", b"v2")
            .expect("valid different version");

        assert_eq!(first, repeated);
        assert_ne!(first, shifted, "part boundaries must be length-separated");
        assert_ne!(first, different_version);
        assert_ne!(first, [0u8; 32]);

        for parts in [
            [&b""[..], &b"address"[..], &b"v1"[..]],
            [&b"1"[..], &b""[..], &b"v1"[..]],
            [&b"1"[..], &b"address"[..], &b""[..]],
        ] {
            assert_eq!(
                settlement_deployment_digest_from_parts(parts[0], parts[1], parts[2]),
                Err(SettlementError::InvalidDeploymentIdentity)
            );
        }

        let long_address = [7u8; MAX_SETTLEMENT_IDENTITY_BYTES + 1];
        assert_eq!(
            settlement_deployment_digest_from_parts(b"chain", &long_address, b"v1"),
            Err(SettlementError::ProposalTooLarge)
        );
    }

    fn pstx_v1_known_answer_request() -> Result<SettlementTransactionRequest, SettlementError> {
        let deployment_digest = settlement_deployment_digest_from_parts(
            b"test-chain-42",
            b"0xpstxcontract",
            b"pstx-adapter-v1",
        )?;
        let proposal = DeadlineSettlement {
            reconstruction_epoch: 11,
            finalized_at: 100,
            missed_submitters: vec!["carol".into()],
            settlements: vec![
                crate::reconstruction_policy::PlayerSettlement {
                    submitter: "alice".into(),
                    submitted: true,
                    locked_deposit: 100,
                    penalty: 0,
                    refund: 100,
                    compensation: 15,
                    net_release: 115,
                },
                crate::reconstruction_policy::PlayerSettlement {
                    submitter: "bob".into(),
                    submitted: true,
                    locked_deposit: 100,
                    penalty: 0,
                    refund: 100,
                    compensation: 15,
                    net_release: 115,
                },
                crate::reconstruction_policy::PlayerSettlement {
                    submitter: "carol".into(),
                    submitted: false,
                    locked_deposit: 100,
                    penalty: 30,
                    refund: 70,
                    compensation: 0,
                    net_release: 70,
                },
            ],
            burned_penalty_remainder: 0,
        };
        let secret_key = StarkCurve::hash_to_scalar(b"poker.settlement.pstx-v1.kat.secret");
        sign_settlement_transaction(
            &secret_key,
            SettlementTransactionRequest {
                sender: String::new(),
                deployment_digest,
                nonce: 42,
                gas_limit: 196_000,
                proposal,
                public_key: [0u8; 32],
                signature: [0u8; 64],
            },
        )
    }

    #[test]
    fn pstx_v1_known_answer_vector_is_stable() -> Result<(), SettlementError> {
        let request = pstx_v1_known_answer_request().expect("valid KAT signing request");
        let encoded = request.encode().expect("KAT encodes");
        let transaction_hash = SimulatedChainSettlementHost::transaction_hash(&request);
        let wire_hex = hex::encode(&encoded);
        let transaction_hash_hex = hex::encode(transaction_hash);
        assert_eq!(wire_hex, PSTX_KAT_WIRE_HEX);
        let decoded = SettlementTransactionRequest::decode(&encoded)?;
        assert_eq!(decoded, request);
        assert_eq!(request.encode()?, encoded);
        assert_eq!(transaction_hash_hex, PSTX_KAT_TX_HASH_HEX);
        Ok(())
    }

    #[test]
    fn reference_ledger_applies_policy_and_conserves_value() {
        let proposal = policy_with_one_miss();
        let mut ledger = InMemorySettlementLedger::default();
        lock_required(&mut ledger, &proposal);
        let execution = ledger.apply_settlement(&proposal).unwrap();
        assert_eq!(ledger.outstanding_escrow(11), 0);
        assert_eq!(ledger.locked_amount(11, "alice"), 0);
        assert_eq!(ledger.released_to("alice"), 115);
        assert_eq!(ledger.released_to("bob"), 115);
        assert_eq!(ledger.released_to("carol"), 70);
        assert_eq!(ledger.burned_total(), 0);
        assert_eq!(execution.events.len(), 5);
        assert_eq!(
            ledger.settlement_execution(11).map(|item| item.clone()),
            Some(execution.clone())
        );
    }

    #[test]
    fn identical_settlement_is_idempotent_and_conflicting_settlement_is_rejected() {
        let proposal = policy_with_one_miss();
        let mut conflicting = proposal.clone();
        conflicting.burned_penalty_remainder += 1;
        let mut ledger = InMemorySettlementLedger::default();
        lock_required(&mut ledger, &proposal);
        let first = ledger.apply_settlement(&proposal).unwrap();
        let second = ledger.apply_settlement(&proposal).unwrap();
        assert_eq!(first, second);
        assert!(matches!(
            ledger.apply_settlement(&conflicting),
            Err(SettlementError::SettlementConflict {
                reconstruction_epoch: 11
            })
        ));
    }

    #[test]
    fn locks_are_idempotent_but_amount_changes_are_rejected() {
        let mut ledger = InMemorySettlementLedger::default();
        let first = ledger.lock_deposit(11, "alice", 100).unwrap();
        let second = ledger.lock_deposit(11, "alice", 100).unwrap();
        assert_eq!(first, second);
        assert_eq!(ledger.outstanding_escrow(11), 100);
        assert!(matches!(
            ledger.lock_deposit(11, "alice", 101),
            Err(SettlementError::DuplicateDepositWithDifferentAmount { submitter })
                if submitter == "alice"
        ));
        assert_eq!(ledger.outstanding_escrow(11), 100);
    }

    #[test]
    fn missing_extra_and_mismatched_escrow_fail_closed() {
        let proposal = policy_with_one_miss();
        let mut missing = InMemorySettlementLedger::default();
        missing.lock_deposit(11, "alice", 100).unwrap();
        assert!(matches!(
            missing.apply_settlement(&proposal),
            Err(SettlementError::MissingLockedDeposit { submitter })
                if submitter == "bob"
        ));

        let mut extra = InMemorySettlementLedger::default();
        lock_required(&mut extra, &proposal);
        extra.lock_deposit(11, "dave", 100).unwrap();
        assert!(matches!(
            extra.apply_settlement(&proposal),
            Err(SettlementError::ExtraLockedDeposit { submitter })
                if submitter == "dave"
        ));

        let mut mismatch = InMemorySettlementLedger::default();
        mismatch.lock_deposit(11, "alice", 101).unwrap();
        mismatch.lock_deposit(11, "bob", 100).unwrap();
        mismatch.lock_deposit(11, "carol", 100).unwrap();
        assert!(matches!(
            mismatch.apply_settlement(&proposal),
            Err(SettlementError::LockedAmountMismatch { submitter })
                if submitter == "alice"
        ));
    }

    #[test]
    fn malformed_player_math_and_compensation_are_rejected() {
        let mut compensation = policy_with_one_miss();
        compensation.settlements[0].compensation += 1;
        compensation.settlements[0].net_release += 1;
        let mut ledger = InMemorySettlementLedger::default();
        lock_required(&mut ledger, &compensation);
        assert!(matches!(
            ledger.apply_settlement(&compensation),
            Err(SettlementError::CompensationInvariant)
        ));

        let mut player_math = policy_with_one_miss();
        player_math.settlements[0].refund -= 1;
        player_math.settlements[0].net_release -= 1;
        let mut ledger = InMemorySettlementLedger::default();
        lock_required(&mut ledger, &player_math);
        assert!(matches!(
            ledger.apply_settlement(&player_math),
            Err(SettlementError::InvalidPlayerArithmetic { submitter })
                if submitter == "alice"
        ));
    }

    #[test]
    fn malformed_metadata_and_order_are_rejected_before_ledger_mutation() {
        let mut duplicate = policy_with_one_miss();
        duplicate.settlements[1].submitter = duplicate.settlements[0].submitter.clone();
        let mut ledger = InMemorySettlementLedger::default();
        lock_required(&mut ledger, &policy_with_one_miss());
        assert!(matches!(
            ledger.apply_settlement(&duplicate),
            Err(SettlementError::DuplicateSubmitter { .. })
        ));
        assert_eq!(ledger.outstanding_escrow(11), 300);

        let mut missed = policy_with_one_miss();
        missed.missed_submitters.push("alice".into());
        assert!(matches!(
            ledger.apply_settlement(&missed),
            Err(SettlementError::InvalidMissedSubmitterList)
        ));
        assert_eq!(ledger.outstanding_escrow(11), 300);
    }

    #[test]
    fn escrow_and_release_overflow_fail_closed() {
        let mut ledger = InMemorySettlementLedger::default();
        ledger.lock_deposit(11, "alice", u128::MAX).unwrap();
        assert!(matches!(
            ledger.lock_deposit(11, "bob", 1),
            Err(SettlementError::EscrowOverflow)
        ));

        fn max_refund_proposal(epoch: u64) -> DeadlineSettlement {
            let config = ReconstructionPolicyConfig {
                reconstruction_epoch: epoch,
                submission_deadline: 100,
                required_submitters: vec!["alice".into()],
                deposit_per_player: u128::MAX,
                penalty_per_missed_submission: 1,
            };
            let mut policy = ReconstructionSubmissionPolicy::new(config, 10).unwrap();
            policy
                .record_accepted_submission("alice", epoch, [7; 32], 20)
                .unwrap();
            policy.finalize_at(100).unwrap()
        }

        let first = max_refund_proposal(21);
        let second = max_refund_proposal(22);
        let mut ledger = InMemorySettlementLedger::default();
        ledger.lock_deposit(21, "alice", u128::MAX).unwrap();
        ledger.apply_settlement(&first).unwrap();
        ledger.lock_deposit(22, "alice", u128::MAX).unwrap();
        assert!(matches!(
            ledger.apply_settlement(&second),
            Err(SettlementError::ReleaseOverflow)
        ));
    }
}
