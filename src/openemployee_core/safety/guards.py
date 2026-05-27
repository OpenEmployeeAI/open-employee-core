"""Safety guards.

Two responsibilities:
- Block invocations that lack required identity / idempotency fields.
- Reject any argument value that looks like a raw secret.
- Spill oversized outputs into ``artifact_refs`` rather than inline.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from ..contracts import (
    ArtifactKind,
    ArtifactRef,
    MCPErrorType,
    MCPToolError,
    MCPToolInvocation,
    MCPToolResult,
)

MAX_INLINE_BYTES = 32 * 1024

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32,}(?![0-9a-fA-F])"),
]


class SafetyViolation(Exception):
    """Raised when a guard blocks an invocation. Wraps an MCPToolError."""

    def __init__(self, error: MCPToolError) -> None:
        super().__init__(error.message)
        self.error = error


def _looks_like_secret(value: str) -> bool:
    for pattern in _SECRET_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _scan_for_secrets(value: Any, path: str = "") -> None:
    if isinstance(value, str):
        if _looks_like_secret(value):
            raise _violation(
                invocation_id="pending",
                error_type=MCPErrorType.SECRET_LEAK,
                message=f"argument at {path or '<root>'} looks like a raw secret",
            )
    elif isinstance(value, dict):
        for k, v in value.items():
            _scan_for_secrets(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _scan_for_secrets(v, f"{path}[{i}]")


def _violation(
    *, invocation_id: str, error_type: MCPErrorType, message: str
) -> SafetyViolation:
    return SafetyViolation(
        MCPToolError(
            invocation_id=invocation_id,
            error_type=error_type,
            message=message,
            retriable=False,
        )
    )


def validate_invocation(invocation: MCPToolInvocation) -> None:
    """Raise SafetyViolation if the invocation is unsafe.

    Note: Pydantic already enforces that org_id/employee_id/idempotency_key are
    non-empty. This function additionally scans arguments for raw-secret shapes.
    """
    missing: list[str] = []
    if not invocation.org_id:
        missing.append("org_id")
    if not invocation.employee_id:
        missing.append("employee_id")
    if not invocation.idempotency_key:
        missing.append("idempotency_key")
    if missing:
        raise _violation(
            invocation_id=invocation.invocation_id,
            error_type=MCPErrorType.VALIDATION,
            message=f"missing required identity fields: {', '.join(missing)}",
        )

    try:
        _scan_for_secrets(invocation.arguments)
    except SafetyViolation as exc:
        # Re-emit with the real invocation_id.
        raise SafetyViolation(
            exc.error.model_copy(update={"invocation_id": invocation.invocation_id})
        ) from exc


def spill_large_output(
    invocation: MCPToolInvocation, output: dict[str, Any]
) -> MCPToolResult:
    """Return MCPToolResult. If the serialized output exceeds MAX_INLINE_BYTES,
    swap inline content for an ``artifact_refs`` claim-check entry.
    """
    payload = json.dumps(output, sort_keys=True, default=str).encode("utf-8")
    if len(payload) <= MAX_INLINE_BYTES:
        return MCPToolResult(invocation_id=invocation.invocation_id, output=output)

    checksum = hashlib.sha256(payload).hexdigest()
    artifact = ArtifactRef(
        uri=f"memory://artifacts/{invocation.invocation_id}",
        media_type="application/json",
        bytes=len(payload),
        checksum=f"sha256:{checksum}",
        kind=ArtifactKind.OUTPUT,
    )
    return MCPToolResult(
        invocation_id=invocation.invocation_id,
        output=None,
        artifact_refs=[artifact],
        provider_metadata={"spilled": True, "inline_limit_bytes": MAX_INLINE_BYTES},
    )
