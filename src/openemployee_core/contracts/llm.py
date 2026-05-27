"""LLM tool-selection contracts.

The LLM does not execute tools. It returns a *selection* that the workflow then
schedules as a separate MCP Activity. This split is the product invariant.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import Field

from .common import NonEmptyStr, StrictModel


class AllowedTool(StrictModel):
    server: NonEmptyStr
    tool: NonEmptyStr


class ToolSelectionMessage(StrictModel):
    role: NonEmptyStr
    content: str


class ToolSelectionInput(StrictModel):
    org_id: NonEmptyStr
    employee_id: NonEmptyStr
    actor_user_id: Optional[NonEmptyStr] = None
    messages: list[ToolSelectionMessage] = Field(default_factory=list)
    allowed_tools: list[AllowedTool]
    provider: NonEmptyStr
    model_hint: Optional[NonEmptyStr] = None
    correlation_id: NonEmptyStr


class ToolSelectionResult(StrictModel):
    selection_id: NonEmptyStr = Field(default_factory=lambda: f"sel-{uuid4().hex}")
    server: NonEmptyStr
    tool: NonEmptyStr
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class ToolSelectionErrorType(str, Enum):
    INVALID_OUTPUT = "invalid_output"
    PROVIDER = "provider"
    POLICY = "policy"
    UNKNOWN_TOOL = "unknown_tool"


class ToolSelectionError(StrictModel):
    selection_id: NonEmptyStr = Field(default_factory=lambda: f"sel-{uuid4().hex}")
    error_type: ToolSelectionErrorType
    message: NonEmptyStr
    raw_output: Optional[dict[str, Any]] = None
