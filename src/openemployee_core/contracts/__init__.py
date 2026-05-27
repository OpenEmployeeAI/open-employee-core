"""OpenEmployee Core canonical contracts."""
from .common import ArtifactKind, ArtifactRef, Risk
from .llm import (
    AllowedTool,
    ToolSelectionError,
    ToolSelectionErrorType,
    ToolSelectionInput,
    ToolSelectionMessage,
    ToolSelectionResult,
)
from .mcp import MCPErrorType, MCPToolError, MCPToolInvocation, MCPToolResult
from .policy import (
    ApprovalRequest,
    ApprovalState,
    ApprovalSubject,
    PolicyDecision,
    PolicyOutcome,
)

__all__ = [
    "AllowedTool",
    "ApprovalRequest",
    "ApprovalState",
    "ApprovalSubject",
    "ArtifactKind",
    "ArtifactRef",
    "MCPErrorType",
    "MCPToolError",
    "MCPToolInvocation",
    "MCPToolResult",
    "PolicyDecision",
    "PolicyOutcome",
    "Risk",
    "ToolSelectionError",
    "ToolSelectionErrorType",
    "ToolSelectionInput",
    "ToolSelectionMessage",
    "ToolSelectionResult",
]
