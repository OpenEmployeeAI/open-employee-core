"""Tests for safety guards (secret rejection, large-output spill)."""
from __future__ import annotations

import pytest

from openemployee_core.contracts import MCPErrorType, MCPToolInvocation
from openemployee_core.safety import (
    MAX_INLINE_BYTES,
    SafetyViolation,
    spill_large_output,
    validate_invocation,
)


def _base_invocation(**overrides) -> MCPToolInvocation:
    defaults = dict(
        org_id="org-1",
        employee_id="emp-1",
        server="mock",
        tool="echo",
        idempotency_key="idem-1",
        correlation_id="corr-1",
        arguments={"q": "hello"},
    )
    defaults.update(overrides)
    return MCPToolInvocation(**defaults)


def test_validate_accepts_normal_invocation():
    validate_invocation(_base_invocation())


@pytest.mark.parametrize(
    "secret",
    [
        "AKIAABCDEFGHIJKLMNOP",  # AWS key shape
        "ghp_" + "a" * 36,  # GitHub PAT shape
        "eyJabc.def123.ghi456",  # JWT-ish
        "0123456789abcdef0123456789abcdef",  # 32 hex
    ],
)
def test_rejects_secret_in_arguments(secret):
    invocation = _base_invocation(arguments={"token": secret})
    with pytest.raises(SafetyViolation) as ei:
        validate_invocation(invocation)
    assert ei.value.error.error_type == MCPErrorType.SECRET_LEAK
    assert ei.value.error.invocation_id == invocation.invocation_id


def test_rejects_secret_nested():
    invocation = _base_invocation(
        arguments={"deep": {"list": ["AKIAABCDEFGHIJKLMNOP"]}}
    )
    with pytest.raises(SafetyViolation):
        validate_invocation(invocation)


def test_small_output_returned_inline():
    invocation = _base_invocation()
    result = spill_large_output(invocation, {"a": 1})
    assert result.output == {"a": 1}
    assert result.artifact_refs == []


def test_large_output_spills_to_artifact():
    invocation = _base_invocation()
    big = {"blob": "x" * (MAX_INLINE_BYTES + 1024)}
    result = spill_large_output(invocation, big)
    assert result.output is None
    assert len(result.artifact_refs) == 1
    artifact = result.artifact_refs[0]
    assert artifact.bytes > MAX_INLINE_BYTES
    assert artifact.checksum.startswith("sha256:")
    assert result.provider_metadata.get("spilled") is True
