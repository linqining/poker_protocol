//! Pure deadline/deposit policy for reconstruction submissions.
//!
//! This module does not verify reconstruction proofs and does not settle funds.
//! The host records a submission only after the cryptographic verifier accepts
//! its statement/proof package. At the deadline it produces a deterministic
//! settlement proposal: missed submitters lose a capped deposit amount, timely
//! submitters share that penalty, and any non-distributable remainder is
//! burned rather than created as additional money.

use std::collections::{BTreeMap, BTreeSet};

/// Configuration for one reconstruction epoch.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReconstructionPolicyConfig {
    pub reconstruction_epoch: u64,
    pub submission_deadline: u64,
    /// Players required to submit one accepted reconstruction package.
    pub required_submitters: Vec<String>,
    /// Deposit locked by each required submitter.
    pub deposit_per_player: u128,
    /// Penalty charged for one missed package; it is capped by the deposit.
    pub penalty_per_missed_submission: u128,
}

/// Receipt for a cryptographically accepted submission.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubmissionReceipt {
    pub reconstruction_epoch: u64,
    pub submitter: String,
    pub proof_digest: [u8; 32],
    pub submitted_at: u64,
}

/// Per-player settlement proposed at the deadline.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlayerSettlement {
    pub submitter: String,
    pub submitted: bool,
    pub locked_deposit: u128,
    pub penalty: u128,
    pub refund: u128,
    pub compensation: u128,
    /// Refund plus compensation, excluding the originally locked deposit.
    pub net_release: u128,
}

/// Deterministic result of finalizing a reconstruction deadline.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeadlineSettlement {
    pub reconstruction_epoch: u64,
    pub finalized_at: u64,
    pub missed_submitters: Vec<String>,
    pub settlements: Vec<PlayerSettlement>,
    /// Penalty units that could not be divided evenly among timely submitters.
    pub burned_penalty_remainder: u128,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReconstructionPolicyError {
    EmptyRequiredSubmitterSet,
    DuplicateRequiredSubmitter(String),
    DeadlineNotAfterInitialization,
    ZeroDeposit,
    UnknownSubmitter(String),
    DuplicateSubmission(String),
    LateSubmission {
        submitter: String,
        submitted_at: u64,
        deadline: u64,
    },
    DeadlineNotReached {
        now: u64,
        deadline: u64,
    },
    InvalidProofDigest,
    WrongEpoch {
        expected: u64,
        supplied: u64,
    },
    PenaltyArithmeticOverflow,
    SettlementArithmeticOverflow,
}

impl std::fmt::Display for ReconstructionPolicyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyRequiredSubmitterSet => {
                write!(f, "required submitter set cannot be empty")
            }
            Self::DuplicateRequiredSubmitter(submitter) => {
                write!(f, "duplicate required submitter {submitter}")
            }
            Self::DeadlineNotAfterInitialization => {
                write!(f, "deadline must be after initialization")
            }
            Self::ZeroDeposit => write!(f, "deposit must be nonzero"),
            Self::UnknownSubmitter(submitter) => write!(f, "unknown submitter {submitter}"),
            Self::DuplicateSubmission(submitter) => {
                write!(f, "duplicate submission from {submitter}")
            }
            Self::LateSubmission {
                submitter,
                submitted_at,
                deadline,
            } => write!(
                f,
                "late submission from {submitter}: submitted at {submitted_at}, deadline {deadline}"
            ),
            Self::DeadlineNotReached { now, deadline } => {
                write!(f, "deadline not reached: now {now}, deadline {deadline}")
            }
            Self::InvalidProofDigest => write!(f, "proof digest must be nonzero"),
            Self::WrongEpoch { expected, supplied } => write!(
                f,
                "wrong reconstruction epoch: expected {expected}, supplied {supplied}"
            ),
            Self::PenaltyArithmeticOverflow => write!(f, "penalty arithmetic overflow"),
            Self::SettlementArithmeticOverflow => write!(f, "settlement arithmetic overflow"),
        }
    }
}

impl std::error::Error for ReconstructionPolicyError {}

/// Pure state machine for deadline and deposit accounting.
#[derive(Debug, Clone)]
pub struct ReconstructionSubmissionPolicy {
    reconstruction_epoch: u64,
    deadline: u64,
    required_submitters: BTreeSet<String>,
    deposit_per_player: u128,
    penalty_per_missed_submission: u128,
    receipts: BTreeMap<String, SubmissionReceipt>,
    settlement: Option<DeadlineSettlement>,
}

impl ReconstructionSubmissionPolicy {
    pub fn new(
        config: ReconstructionPolicyConfig,
        initialized_at: u64,
    ) -> Result<Self, ReconstructionPolicyError> {
        if config.reconstruction_epoch == 0 {
            return Err(ReconstructionPolicyError::WrongEpoch {
                expected: 1,
                supplied: 0,
            });
        }
        if config.required_submitters.is_empty() {
            return Err(ReconstructionPolicyError::EmptyRequiredSubmitterSet);
        }
        let required_submitters = config
            .required_submitters
            .iter()
            .cloned()
            .collect::<BTreeSet<_>>();
        if required_submitters.len() != config.required_submitters.len() {
            let mut seen = BTreeSet::new();
            for submitter in &config.required_submitters {
                if !seen.insert(submitter.clone()) {
                    return Err(ReconstructionPolicyError::DuplicateRequiredSubmitter(
                        submitter.clone(),
                    ));
                }
            }
        }
        if config.submission_deadline <= initialized_at {
            return Err(ReconstructionPolicyError::DeadlineNotAfterInitialization);
        }
        if config.deposit_per_player == 0 {
            return Err(ReconstructionPolicyError::ZeroDeposit);
        }

        Ok(Self {
            reconstruction_epoch: config.reconstruction_epoch,
            deadline: config.submission_deadline,
            required_submitters,
            deposit_per_player: config.deposit_per_player,
            penalty_per_missed_submission: config.penalty_per_missed_submission,
            receipts: BTreeMap::new(),
            settlement: None,
        })
    }

    /// Record an already verified package. Passing a proof digest makes the
    /// receipt audit trail explicit, but cryptographic verification itself is
    /// intentionally outside this policy module.
    pub fn record_accepted_submission(
        &mut self,
        submitter: &str,
        reconstruction_epoch: u64,
        proof_digest: [u8; 32],
        submitted_at: u64,
    ) -> Result<SubmissionReceipt, ReconstructionPolicyError> {
        if self.settlement.is_some() {
            return Err(ReconstructionPolicyError::LateSubmission {
                submitter: submitter.to_owned(),
                submitted_at,
                deadline: self.deadline,
            });
        }
        if reconstruction_epoch != self.reconstruction_epoch {
            return Err(ReconstructionPolicyError::WrongEpoch {
                expected: self.reconstruction_epoch,
                supplied: reconstruction_epoch,
            });
        }
        if !self.required_submitters.contains(submitter) {
            return Err(ReconstructionPolicyError::UnknownSubmitter(
                submitter.to_owned(),
            ));
        }
        if submitted_at > self.deadline {
            return Err(ReconstructionPolicyError::LateSubmission {
                submitter: submitter.to_owned(),
                submitted_at,
                deadline: self.deadline,
            });
        }
        if self.receipts.contains_key(submitter) {
            return Err(ReconstructionPolicyError::DuplicateSubmission(
                submitter.to_owned(),
            ));
        }
        if proof_digest == [0; 32] {
            return Err(ReconstructionPolicyError::InvalidProofDigest);
        }

        let receipt = SubmissionReceipt {
            reconstruction_epoch,
            submitter: submitter.to_owned(),
            proof_digest,
            submitted_at,
        };
        self.receipts.insert(submitter.to_owned(), receipt.clone());
        Ok(receipt)
    }

    pub fn has_submitted(&self, submitter: &str) -> bool {
        self.receipts.contains_key(submitter)
    }

    pub fn receipts(&self) -> impl Iterator<Item = &SubmissionReceipt> {
        self.receipts.values()
    }

    /// Finalize at the first observed time at or after the deadline. Calling
    /// again returns the identical settlement proposal.
    pub fn finalize_at(
        &mut self,
        now: u64,
    ) -> Result<DeadlineSettlement, ReconstructionPolicyError> {
        if let Some(settlement) = &self.settlement {
            return Ok(settlement.clone());
        }
        if now < self.deadline {
            return Err(ReconstructionPolicyError::DeadlineNotReached {
                now,
                deadline: self.deadline,
            });
        }

        let mut missed_submitters = Vec::new();
        let mut total_penalty = 0u128;
        let mut penalties = BTreeMap::<String, u128>::new();
        for submitter in &self.required_submitters {
            if self.receipts.contains_key(submitter) {
                continue;
            }
            let penalty = self
                .penalty_per_missed_submission
                .min(self.deposit_per_player);
            penalties.insert(submitter.clone(), penalty);
            total_penalty = total_penalty
                .checked_add(penalty)
                .ok_or(ReconstructionPolicyError::PenaltyArithmeticOverflow)?;
            missed_submitters.push(submitter.clone());
        }

        let timely: Vec<_> = self
            .required_submitters
            .iter()
            .filter(|submitter| self.receipts.contains_key(*submitter))
            .cloned()
            .collect();
        let share = if timely.is_empty() {
            0
        } else {
            total_penalty / timely.len() as u128
        };
        let mut remainder = if timely.is_empty() {
            total_penalty
        } else {
            total_penalty % timely.len() as u128
        };

        let mut settlements = Vec::with_capacity(self.required_submitters.len());
        for submitter in &self.required_submitters {
            let submitted = self.receipts.contains_key(submitter);
            let penalty = penalties.get(submitter).copied().unwrap_or(0);
            let refund = self.deposit_per_player - penalty;
            let mut compensation = if submitted { share } else { 0 };
            // Give each non-distributable unit to the earliest timely submitter
            // in deterministic canonical order, then burn any excess.
            if submitted && remainder > 0 {
                compensation += 1;
                remainder -= 1;
            }
            let net_release = refund
                .checked_add(compensation)
                .ok_or(ReconstructionPolicyError::SettlementArithmeticOverflow)?;
            settlements.push(PlayerSettlement {
                submitter: submitter.clone(),
                submitted,
                locked_deposit: self.deposit_per_player,
                penalty,
                refund,
                compensation,
                net_release,
            });
        }

        let settlement = DeadlineSettlement {
            reconstruction_epoch: self.reconstruction_epoch,
            finalized_at: now,
            missed_submitters,
            settlements,
            burned_penalty_remainder: remainder,
        };
        self.settlement = Some(settlement.clone());
        Ok(settlement)
    }

    pub fn settlement(&self) -> Option<&DeadlineSettlement> {
        self.settlement.as_ref()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn policy_errors_are_standard_errors_with_details() {
        let error = ReconstructionPolicyError::LateSubmission {
            submitter: "alice".into(),
            submitted_at: 101,
            deadline: 100,
        };
        let _: &dyn std::error::Error = &error;
        assert!(error.to_string().contains("alice"));
        assert!(error.to_string().contains("101"));
    }

    fn config(deadline: u64) -> ReconstructionPolicyConfig {
        ReconstructionPolicyConfig {
            reconstruction_epoch: 11,
            submission_deadline: deadline,
            required_submitters: vec!["alice".into(), "bob".into(), "carol".into()],
            deposit_per_player: 100,
            penalty_per_missed_submission: 30,
        }
    }

    fn digest(value: u8) -> [u8; 32] {
        [value; 32]
    }

    #[test]
    fn all_timely_submissions_refund_all_deposits() {
        let mut policy = ReconstructionSubmissionPolicy::new(config(100), 10).unwrap();
        policy
            .record_accepted_submission("alice", 11, digest(1), 20)
            .unwrap();
        policy
            .record_accepted_submission("bob", 11, digest(2), 30)
            .unwrap();
        policy
            .record_accepted_submission("carol", 11, digest(3), 40)
            .unwrap();
        let settlement = policy.finalize_at(100).unwrap();
        assert!(settlement.missed_submitters.is_empty());
        assert_eq!(settlement.burned_penalty_remainder, 0);
        for player in settlement.settlements {
            assert_eq!(player.penalty, 0);
            assert_eq!(player.refund, 100);
            assert_eq!(player.compensation, 0);
            assert_eq!(player.net_release, 100);
        }
    }

    #[test]
    fn missed_deposit_is_capped_and_shared_with_timely_submitters() {
        let mut policy = ReconstructionSubmissionPolicy::new(
            ReconstructionPolicyConfig {
                penalty_per_missed_submission: 250,
                ..config(100)
            },
            10,
        )
        .unwrap();
        policy
            .record_accepted_submission("alice", 11, digest(1), 20)
            .unwrap();
        policy
            .record_accepted_submission("bob", 11, digest(2), 30)
            .unwrap();
        let settlement = policy.finalize_at(100).unwrap();
        assert_eq!(settlement.missed_submitters, vec!["carol".to_string()]);
        let by_name: BTreeMap<_, _> = settlement
            .settlements
            .iter()
            .map(|item| (item.submitter.as_str(), item))
            .collect();
        assert_eq!(by_name["carol"].penalty, 100);
        assert_eq!(by_name["carol"].refund, 0);
        assert_eq!(by_name["alice"].compensation, 50);
        assert_eq!(by_name["bob"].compensation, 50);
        assert_eq!(settlement.burned_penalty_remainder, 0);

        let penalties: u128 = settlement.settlements.iter().map(|item| item.penalty).sum();
        let compensation: u128 = settlement
            .settlements
            .iter()
            .map(|item| item.compensation)
            .sum();
        assert_eq!(
            penalties,
            compensation + settlement.burned_penalty_remainder
        );
    }

    #[test]
    fn duplicate_late_unknown_and_wrong_epoch_submissions_are_rejected() {
        let mut policy = ReconstructionSubmissionPolicy::new(config(100), 10).unwrap();
        policy
            .record_accepted_submission("alice", 11, digest(1), 20)
            .unwrap();
        assert!(matches!(
            policy.record_accepted_submission("alice", 11, digest(1), 21),
            Err(ReconstructionPolicyError::DuplicateSubmission(_))
        ));
        assert!(matches!(
            policy.record_accepted_submission("dave", 11, digest(4), 21),
            Err(ReconstructionPolicyError::UnknownSubmitter(_))
        ));
        assert!(matches!(
            policy.record_accepted_submission("bob", 12, digest(2), 21),
            Err(ReconstructionPolicyError::WrongEpoch {
                expected: 11,
                supplied: 12
            })
        ));
        assert!(matches!(
            policy.record_accepted_submission("bob", 11, digest(2), 101),
            Err(ReconstructionPolicyError::LateSubmission {
                submitted_at: 101,
                deadline: 100,
                ..
            })
        ));
        assert!(!policy.has_submitted("bob"));
    }

    #[test]
    fn finalization_is_idempotent_and_late_submissions_cannot_change_it() {
        let mut policy = ReconstructionSubmissionPolicy::new(config(100), 10).unwrap();
        policy
            .record_accepted_submission("alice", 11, digest(1), 20)
            .unwrap();
        let first = policy.finalize_at(100).unwrap();
        assert!(matches!(
            policy.record_accepted_submission("bob", 11, digest(2), 100),
            Err(ReconstructionPolicyError::LateSubmission { .. })
        ));
        let second = policy.finalize_at(200).unwrap();
        assert_eq!(first, second);
        assert_eq!(policy.settlement(), Some(&first));
    }

    #[test]
    fn all_missed_submissions_burn_penalty_without_creating_compensation() {
        let mut policy = ReconstructionSubmissionPolicy::new(config(100), 10).unwrap();
        let settlement = policy.finalize_at(100).unwrap();
        assert_eq!(settlement.missed_submitters.len(), 3);
        assert_eq!(settlement.burned_penalty_remainder, 90);
        assert!(settlement
            .settlements
            .iter()
            .all(|item| item.compensation == 0));
        assert!(settlement.settlements.iter().all(|item| item.penalty == 30));
        assert!(settlement.settlements.iter().all(|item| item.refund == 70));
    }

    #[test]
    fn configuration_and_proof_digest_inputs_are_validated() {
        assert!(matches!(
            ReconstructionSubmissionPolicy::new(
                ReconstructionPolicyConfig {
                    required_submitters: vec![],
                    ..config(100)
                },
                10,
            ),
            Err(ReconstructionPolicyError::EmptyRequiredSubmitterSet)
        ));
        assert!(matches!(
            ReconstructionSubmissionPolicy::new(
                ReconstructionPolicyConfig {
                    required_submitters: vec!["alice".into(), "alice".into()],
                    ..config(100)
                },
                10,
            ),
            Err(ReconstructionPolicyError::DuplicateRequiredSubmitter(_))
        ));
        assert!(matches!(
            ReconstructionSubmissionPolicy::new(config(10), 10),
            Err(ReconstructionPolicyError::DeadlineNotAfterInitialization)
        ));
        assert!(matches!(
            ReconstructionSubmissionPolicy::new(
                ReconstructionPolicyConfig {
                    deposit_per_player: 0,
                    ..config(100)
                },
                10,
            ),
            Err(ReconstructionPolicyError::ZeroDeposit)
        ));
        let mut policy = ReconstructionSubmissionPolicy::new(config(100), 10).unwrap();
        assert!(matches!(
            policy.record_accepted_submission("alice", 11, [0; 32], 20),
            Err(ReconstructionPolicyError::InvalidProofDigest)
        ));
    }

    #[test]
    fn settlement_rejects_u128_release_overflow() {
        let mut policy = ReconstructionSubmissionPolicy::new(
            ReconstructionPolicyConfig {
                required_submitters: vec!["alice".into(), "bob".into()],
                deposit_per_player: u128::MAX,
                penalty_per_missed_submission: u128::MAX,
                ..config(100)
            },
            10,
        )
        .unwrap();
        policy
            .record_accepted_submission("alice", 11, digest(1), 20)
            .unwrap();
        assert!(matches!(
            policy.finalize_at(100),
            Err(ReconstructionPolicyError::SettlementArithmeticOverflow)
        ));
    }
}
