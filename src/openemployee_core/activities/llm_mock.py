"""Mock LLM tool-selection Activity.

Deterministic: picks the first entry of ``allowed_tools`` and copies
``arguments`` from input metadata when present. Used by tests and the smoke
endpoint. No real model providers are imported here.
"""
from __future__ import annotations

from temporalio import activity

from ..contracts import ToolSelectionError, ToolSelectionErrorType, ToolSelectionInput, ToolSelectionResult
from ..naming import build_llm_selection_activity_name

MOCK_PROVIDER = "mock"
MOCK_LLM_ACTIVITY_NAME = build_llm_selection_activity_name(MOCK_PROVIDER)


def run_mock_selection(payload: dict) -> dict:
    """Pure-Python implementation, reused by the synchronous smoke endpoint."""
    selection_input = ToolSelectionInput.model_validate(payload)
    if not selection_input.allowed_tools:
        err = ToolSelectionError(
            error_type=ToolSelectionErrorType.INVALID_OUTPUT,
            message="allowed_tools is empty; mock selector cannot pick a tool",
        )
        return err.model_dump(mode="json")

    chosen = selection_input.allowed_tools[0]
    # Last user message becomes the argument payload, if any.
    args: dict = {}
    for msg in reversed(selection_input.messages):
        if msg.role == "user":
            args = {"query": msg.content}
            break

    result = ToolSelectionResult(
        server=chosen.server,
        tool=chosen.tool,
        arguments=args,
        rationale="mock selector: first allowed tool",
        confidence=1.0,
        provider_metadata={"provider": "mock"},
    )
    return result.model_dump(mode="json")


@activity.defn(name=MOCK_LLM_ACTIVITY_NAME)
async def llm_mock_select_tool(payload: dict) -> dict:
    return run_mock_selection(payload)
