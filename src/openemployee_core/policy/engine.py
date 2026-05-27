"""Simple in-process policy engine. Pluggable via the PolicyEvaluator protocol."""
from __future__ import annotations

from typing import Protocol

from ..contracts import PolicyDecision, PolicyOutcome, Risk

POLICY_VERSION = "0.1.0-inmemory"


class PolicyEvaluator(Protocol):
    def evaluate(
        self, *, org_id: str, employee_id: str, server: str, tool: str, risk: Risk
    ) -> PolicyDecision:  # pragma: no cover - protocol stub
        ...


class RiskBasedPolicy:
    """Default policy: high risk requires approval; everything else is allowed."""

    def __init__(self, version: str = POLICY_VERSION) -> None:
        self.version = version

    def evaluate(
        self,
        *,
        org_id: str,
        employee_id: str,
        server: str,
        tool: str,
        risk: Risk,
    ) -> PolicyDecision:
        if risk is Risk.HIGH:
            return PolicyDecision(
                decision=PolicyOutcome.REQUIRE_APPROVAL,
                reasons=[f"risk={risk.value} requires human approval"],
                policy_version=self.version,
            )
        return PolicyDecision(
            decision=PolicyOutcome.ALLOW,
            reasons=[f"risk={risk.value} is auto-allowed"],
            policy_version=self.version,
        )


DEFAULT_POLICY: PolicyEvaluator = RiskBasedPolicy()
