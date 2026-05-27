"""MCP tool invocation, result, and error contracts.

Derived from temporal-community/temporal-ai-agent PR #61 (typed MCPToolInvocation /
MCPToolResult / MCPToolError, deterministic Activity name, structured errors) and
mapped into OpenEmployee canonical fields (org_id, employee_id, auth_ref, ...).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import Field

from .common import ArtifactRef, NonEmptyStr, Risk, StrictModel, utc_now


class MCPErrorType(str, Enum):
    VALIDATION = "validation"
    POLICY = "policy"
    APPROVAL_REQUIRED = "approval_required"
    CONNECTOR = "connector"
    TIMEOUT = "timeout"
    SECRET_LEAK = "secret_leak"
    UNKNOWN_TOOL = "unknown_tool"
    INTERNAL = "internal"


class MCPToolInvocation(StrictModel):
    """An MCP tool call routed to a `mcp__<server>__<tool>` Activity boundary."""

    invocation_id: NonEmptyStr = Field(default_factory=lambda: f"mcp-{uuid4().hex}")
    org_id: NonEmptyStr
    employee_id: NonEmptyStr
    actor_user_id: Optional[NonEmptyStr] = None
    server: NonEmptyStr
    tool: NonEmptyStr
    arguments: dict[str, Any] = Field(default_factory=dict)
    auth_ref: Optional[NonEmptyStr] = None
    spiffe_id: Optional[NonEmptyStr] = None
    idempotency_key: NonEmptyStr
    risk: Risk = Risk.LOW
    approval_ref: Optional[NonEmptyStr] = None
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    correlation_id: NonEmptyStr
    requested_at: datetime = Field(default_factory=utc_now)


class MCPToolResult(StrictModel):
    invocation_id: NonEmptyStr
    ok: bool = True
    output: Optional[dict[str, Any]] = None
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    latency_ms: int = Field(ge=0, default=0)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class MCPToolError(StrictModel):
    invocation_id: NonEmptyStr
    ok: bool = False
    error_type: MCPErrorType
    message: NonEmptyStr
    retriable: bool = False
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
