"""Policy + approval contracts."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from .common import NonEmptyStr, Risk, StrictModel, utc_now


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyDecision(StrictModel):
    decision: PolicyOutcome
    reasons: list[str] = Field(default_factory=list)
    policy_version: NonEmptyStr
    evaluated_at: datetime = Field(default_factory=utc_now)


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalSubject(StrictModel):
    server: NonEmptyStr
    tool: NonEmptyStr
    arguments_digest: NonEmptyStr


class ApprovalRequest(StrictModel):
    approval_id: NonEmptyStr
    org_id: NonEmptyStr
    employee_id: NonEmptyStr
    actor_user_id: Optional[NonEmptyStr] = None
    subject: ApprovalSubject
    risk: Risk
    requested_at: datetime = Field(default_factory=utc_now)
    state: ApprovalState = ApprovalState.PENDING
    decision_by: Optional[NonEmptyStr] = None
    decided_at: Optional[datetime] = None
