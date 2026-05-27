"""Typed contracts for OpenEmployee core.

These are dependency-light dataclasses that describe the shapes that flow
through workflows and activities. They are not implementations.
"""

from .feedback import (
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

__all__ = [
    "ArtifactRef",
    "AuthRef",
    "CommunitySignal",
    "InboundInteraction",
    "IssueCandidate",
    "PolicyDecision",
    "RiskLevel",
    "SignalCluster",
    "SignalSource",
]
