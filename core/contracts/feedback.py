"""Contracts for the feedback-to-roadmap loop.

The feedback-to-roadmap loop ingests inbound interactions (support emails,
community posts, social mentions), normalizes them into community signals,
clusters them, and surfaces candidate issues for the product roadmap.

Design rules enforced by these contracts (see SECURITY.md and CONTRIBUTING.md):

* Secrets never appear inline. Use ``AuthRef`` to point at an external secret.
* Large payloads (long transcripts, attachments, raw HTML) are referenced via
  ``ArtifactRef`` claim-checks rather than embedded in workflow history.
* Anything that may trigger an externally visible action carries a
  ``PolicyDecision`` so a workflow can gate Activity scheduling on policy
  evaluation and, when required, human approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Sequence


class SignalSource(str, Enum):
    """Where an inbound interaction originated."""

    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    GITHUB = "github"
    LINEAR = "linear"
    SOCIAL = "social"
    SUPPORT_TICKET = "support_ticket"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk class used by policy gates before scheduling Activities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class AuthRef:
    """Opaque reference to a credential held by an external secret resolver.

    The workflow history must never contain the secret material itself —
    only this reference. The Activity worker resolves ``ref`` at call time.
    """

    provider: str
    ref: str
    scope: Optional[str] = None


@dataclass(frozen=True)
class ArtifactRef:
    """Claim-check reference to a large payload stored outside workflow history."""

    uri: str
    media_type: str
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None


@dataclass(frozen=True)
class InboundInteraction:
    """A single raw inbound message from a user or community member."""

    id: str
    source: SignalSource
    received_at: str  # RFC 3339 timestamp
    author_handle: str
    subject: Optional[str] = None
    body_excerpt: Optional[str] = None
    body_artifact: Optional[ArtifactRef] = None
    locale: Optional[str] = None
    tags: Sequence[str] = field(default_factory=tuple)
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CommunitySignal:
    """Normalized, deduplicated signal derived from one or more interactions."""

    id: str
    interaction_ids: Sequence[str]
    summary: str
    sentiment: Optional[str] = None  # "positive" | "neutral" | "negative"
    topics: Sequence[str] = field(default_factory=tuple)
    confidence: float = 0.0
    detected_at: Optional[str] = None


@dataclass(frozen=True)
class SignalCluster:
    """A group of related community signals representing one underlying theme."""

    id: str
    signal_ids: Sequence[str]
    label: str
    description: Optional[str] = None
    size: int = 0
    representative_signal_id: Optional[str] = None


@dataclass(frozen=True)
class PolicyDecision:
    """Outcome of a policy check, required before any risky public Activity."""

    allowed: bool
    risk: RiskLevel
    requires_human_approval: bool = False
    approver: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class IssueCandidate:
    """Proposed roadmap issue derived from a signal cluster.

    ``policy`` is required: anything that may be filed publicly (e.g. a GitHub
    issue) must carry an evaluated ``PolicyDecision`` so the workflow can gate
    Activity scheduling. ``draft_body_artifact`` keeps long-form draft text
    out of workflow history.
    """

    id: str
    cluster_id: str
    title: str
    rationale: str
    policy: PolicyDecision
    target_repo: Optional[str] = None
    labels: Sequence[str] = field(default_factory=tuple)
    draft_body_artifact: Optional[ArtifactRef] = None
