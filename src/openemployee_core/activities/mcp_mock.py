"""Mock MCP tools registered as Temporal Activities with canonical names.

Each function below is registered with the exact name produced by
``build_mcp_activity_name(server, tool)`` so the workflow's
``execute_activity(name)`` call resolves correctly.
"""
from __future__ import annotations

import time
from typing import Any

from temporalio import activity

from ..contracts import MCPToolError, MCPToolInvocation, MCPToolResult
from ..naming import build_mcp_activity_name
from ..safety import SafetyViolation, spill_large_output, validate_invocation

MOCK_SERVER = "mock"
MOCK_ECHO_NAME = build_mcp_activity_name(MOCK_SERVER, "echo")
MOCK_SEARCH_NAME = build_mcp_activity_name(MOCK_SERVER, "search")


def _run_safely(invocation: MCPToolInvocation, output: dict[str, Any]) -> dict:
    try:
        validate_invocation(invocation)
    except SafetyViolation as exc:
        return exc.error.model_dump(mode="json")

    start = time.monotonic()
    result = spill_large_output(invocation, output)
    latency_ms = int((time.monotonic() - start) * 1000)
    return result.model_copy(update={"latency_ms": latency_ms}).model_dump(mode="json")


def run_mock_echo(payload: dict) -> dict:
    """Synchronous reusable implementation for the smoke endpoint."""
    invocation = MCPToolInvocation.model_validate(payload)
    return _run_safely(invocation, {"echo": invocation.arguments})


def run_mock_search(payload: dict) -> dict:
    invocation = MCPToolInvocation.model_validate(payload)
    query = invocation.arguments.get("query", "")
    output = {
        "query": query,
        "hits": [
            {"id": "doc-1", "title": "Mock result 1", "snippet": f"about: {query}"},
            {"id": "doc-2", "title": "Mock result 2", "snippet": f"more on: {query}"},
        ],
    }
    return _run_safely(invocation, output)


@activity.defn(name=MOCK_ECHO_NAME)
async def mcp_mock_echo(payload: dict) -> dict:
    return run_mock_echo(payload)


@activity.defn(name=MOCK_SEARCH_NAME)
async def mcp_mock_search(payload: dict) -> dict:
    return run_mock_search(payload)


MOCK_DISPATCH: dict[str, callable] = {
    MOCK_ECHO_NAME: run_mock_echo,
    MOCK_SEARCH_NAME: run_mock_search,
}


def dispatch_mock(activity_name: str, payload: dict) -> dict:
    """Used by the smoke endpoint to route by canonical activity name."""
    if activity_name not in MOCK_DISPATCH:
        err = MCPToolError(
            invocation_id=str(payload.get("invocation_id", "unknown")) or "unknown",
            error_type="unknown_tool",  # type: ignore[arg-type]
            message=f"no mock MCP activity registered as {activity_name!r}",
            retriable=False,
        )
        return err.model_dump(mode="json")
    return MOCK_DISPATCH[activity_name](payload)
