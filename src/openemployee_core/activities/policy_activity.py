"""Policy evaluation Activity. Workflow calls this as a boundary, never inline."""
from __future__ import annotations

from temporalio import activity

from ..contracts import PolicyDecision, Risk
from ..policy import DEFAULT_POLICY

POLICY_ACTIVITY_NAME = "policy__evaluate"


def run_policy_evaluation(payload: dict) -> dict:
    risk = Risk(payload.get("risk", Risk.LOW.value))
    decision = DEFAULT_POLICY.evaluate(
        org_id=payload["org_id"],
        employee_id=payload["employee_id"],
        server=payload["server"],
        tool=payload["tool"],
        risk=risk,
    )
    return decision.model_dump(mode="json")


@activity.defn(name=POLICY_ACTIVITY_NAME)
async def policy_evaluate(payload: dict) -> dict:
    return run_policy_evaluation(payload)


__all__ = ["POLICY_ACTIVITY_NAME", "policy_evaluate", "run_policy_evaluation"]
