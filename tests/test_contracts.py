"""Test contract validation and JSON-schema generation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from openemployee_core.contracts import (
    MCPToolInvocation,
    PolicyDecision,
    PolicyOutcome,
    Risk,
    ToolSelectionInput,
)


def test_mcp_invocation_rejects_extra_fields():
    with pytest.raises(ValidationError):
        MCPToolInvocation(
            org_id="o",
            employee_id="e",
            server="mock",
            tool="echo",
            idempotency_key="i",
            correlation_id="c",
            mystery="boom",  # type: ignore[call-arg]
        )


def test_mcp_invocation_requires_identity_fields():
    with pytest.raises(ValidationError):
        MCPToolInvocation(
            org_id="",
            employee_id="e",
            server="mock",
            tool="echo",
            idempotency_key="i",
            correlation_id="c",
        )


def test_policy_decision_schema():
    schema = PolicyDecision.model_json_schema()
    assert "decision" in schema["properties"]
    decision = PolicyDecision(
        decision=PolicyOutcome.ALLOW, policy_version="v1"
    )
    assert decision.evaluated_at.tzinfo is not None


def test_tool_selection_input_validates():
    payload = ToolSelectionInput(
        org_id="o",
        employee_id="e",
        allowed_tools=[{"server": "mock", "tool": "echo"}],
        provider="mock",
        correlation_id="c",
    )
    assert payload.provider == "mock"
    assert payload.allowed_tools[0].server == "mock"


def test_risk_enum_round_trip():
    assert Risk("high") is Risk.HIGH
