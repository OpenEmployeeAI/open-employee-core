"""Skeleton for the feedback-to-roadmap workflow.

This module declares the *boundary* of the workflow: its input/output shapes,
the helper that enforces the ``mcp__<server>__<tool>`` Activity naming
invariant, and the ordered phases the concrete workflow will implement.

It intentionally does not import ``temporalio`` or perform any I/O. The goal
is to lock down contracts and naming before an implementation is wired up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from core.contracts import IssueCandidate, SignalSource

# Activity names must be deterministic and match the upstream
# temporal-community/temporal-ai-agent PR #61 pattern. The double-underscore
# separators are load-bearing — workers route on them, so segments must not
# contain ``__`` themselves.
ACTIVITY_NAME_RE = re.compile(r"^mcp__[a-z0-9][a-z0-9-]*(?:_[a-z0-9-]+)*__[a-z0-9][a-z0-9-]*(?:_[a-z0-9-]+)*$")

_SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(?:_[a-z0-9-]+)*$")


def mcp_activity_name(server: str, tool: str) -> str:
    """Return the canonical Activity name for an MCP tool invocation.

    Raises ``ValueError`` if either segment is empty, contains characters
    outside ``[a-z0-9_-]``, or contains ``__`` (which would collide with the
    Activity-name separator). Callers should treat the returned string as
    the only legal Temporal Activity name for that ``(server, tool)`` pair.
    """
    for label, value in (("server", server), ("tool", tool)):
        if not _SEGMENT_RE.match(value):
            raise ValueError(
                f"invalid MCP activity {label} segment {value!r}: "
                "must be lowercase [a-z0-9_-], non-empty, and contain no '__'"
            )
    return f"mcp__{server}__{tool}"


@dataclass(frozen=True)
class FeedbackToRoadmapWorkflowInput:
    """Inputs to one execution of the feedback-to-roadmap workflow."""

    sources: Sequence[SignalSource]
    since: str  # RFC 3339 timestamp; ingestion lower bound
    max_interactions: int = 500


@dataclass(frozen=True)
class FeedbackToRoadmapWorkflowResult:
    """Outputs of the workflow: candidates produced, not actions taken."""

    cluster_ids: Sequence[str] = field(default_factory=tuple)
    issue_candidates: Sequence[IssueCandidate] = field(default_factory=tuple)
    skipped_for_policy: int = 0


# Phases the concrete workflow will execute, each via its own Activity.
# Listed here so reviewers can see the boundary without reading an
# implementation. Risky public actions (e.g. filing an issue) must check
# ``IssueCandidate.policy`` before scheduling the corresponding Activity.
WORKFLOW_PHASES: Sequence[str] = (
    "ingest_interactions",
    "normalize_to_signals",
    "cluster_signals",
    "draft_issue_candidates",
    "policy_gate",
    "publish_or_handoff",
)
