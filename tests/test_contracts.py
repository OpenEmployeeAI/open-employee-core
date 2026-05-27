"""Tests for the feedback-to-roadmap contracts."""

import unittest
from dataclasses import FrozenInstanceError

from core.contracts import (
    ArtifactRef,
    AuthRef,
    CommunitySignal,
    InboundInteraction,
    IssueCandidate,
    PolicyDecision,
    RiskLevel,
    SignalCluster,
    SignalSource,
)


class ContractsTest(unittest.TestCase):
    def test_inbound_interaction_round_trip(self):
        ix = InboundInteraction(
            id="ix-1",
            source=SignalSource.EMAIL,
            received_at="2026-05-27T12:00:00Z",
            author_handle="alice@example.com",
            subject="Bug report",
            body_excerpt="It crashes when I…",
        )
        self.assertEqual(ix.source, SignalSource.EMAIL)
        self.assertEqual(ix.tags, ())
        self.assertEqual(ix.metadata, {})

    def test_contracts_are_frozen(self):
        # Frozen dataclasses are required so workflow inputs/outputs can be
        # treated as immutable values in Temporal history.
        auth = AuthRef(provider="pipedream", ref="conn_123")
        with self.assertRaises(FrozenInstanceError):
            auth.ref = "other"  # type: ignore[misc]

    def test_artifact_ref_is_claim_check_shape(self):
        art = ArtifactRef(uri="s3://bucket/key", media_type="text/plain", size_bytes=42)
        self.assertEqual(art.uri, "s3://bucket/key")
        self.assertEqual(art.media_type, "text/plain")

    def test_issue_candidate_requires_policy(self):
        # Policy must be present on every IssueCandidate so the workflow can
        # gate Activity scheduling. Constructing without it should fail.
        with self.assertRaises(TypeError):
            IssueCandidate(  # type: ignore[call-arg]
                id="ic-1",
                cluster_id="cl-1",
                title="Add export",
                rationale="users keep asking",
            )

    def test_issue_candidate_with_policy_decision(self):
        decision = PolicyDecision(
            allowed=True,
            risk=RiskLevel.LOW,
            requires_human_approval=False,
        )
        ic = IssueCandidate(
            id="ic-1",
            cluster_id="cl-1",
            title="Add export",
            rationale="users keep asking",
            policy=decision,
        )
        self.assertTrue(ic.policy.allowed)
        self.assertEqual(ic.policy.risk, RiskLevel.LOW)

    def test_signal_and_cluster_defaults(self):
        sig = CommunitySignal(id="s-1", interaction_ids=("ix-1",), summary="ask")
        self.assertEqual(sig.topics, ())
        self.assertEqual(sig.confidence, 0.0)

        cl = SignalCluster(id="cl-1", signal_ids=("s-1",), label="export-requests")
        self.assertEqual(cl.size, 0)
        self.assertIsNone(cl.representative_signal_id)


if __name__ == "__main__":
    unittest.main()
