"""Smoke FastAPI app.

IMPORTANT: This is a *synchronous simulator* intended for hosted verification
only (e.g. AWS App Runner). It is NOT a substitute for the Temporal worker.
The endpoints reuse the same Pydantic contracts, safety guards, and pure-
Python activity implementations as the durable runtime, so behavior matches.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .. import __version__
from ..activities import (
    MOCK_ECHO_NAME,
    MOCK_LLM_ACTIVITY_NAME,
    MOCK_SEARCH_NAME,
    dispatch_mock,
    run_mock_selection,
    run_policy_evaluation,
)
from ..contracts import (
    ApprovalRequest,
    ApprovalState,
    ApprovalSubject,
    ArtifactRef,
    MCPToolError,
    MCPToolInvocation,
    MCPToolResult,
    PolicyDecision,
    Risk,
    ToolSelectionError,
    ToolSelectionInput,
    ToolSelectionResult,
)
from ..naming import build_mcp_activity_name

app = FastAPI(
    title="OpenEmployee Core Smoke API",
    version=__version__,
    description=(
        "Synchronous simulator for the OpenEmployee Core runtime. Reuses the "
        "same contracts, safety guards, and mock activity implementations as "
        "the durable Temporal workflow. Not a replacement for Temporal tests."
    ),
)

_APPROVAL_STORE: dict[str, ApprovalRequest] = {}


def _git_commit() -> str:
    return os.environ.get("GIT_COMMIT", "unknown")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "commit": _git_commit(),
        "builder_check": build_mcp_activity_name("mock", "echo"),
        "llm_builder_check": MOCK_LLM_ACTIVITY_NAME,
    }


@app.get("/contracts")
def contracts() -> dict[str, Any]:
    return {
        "MCPToolInvocation": MCPToolInvocation.model_json_schema(),
        "MCPToolResult": MCPToolResult.model_json_schema(),
        "MCPToolError": MCPToolError.model_json_schema(),
        "ToolSelectionInput": ToolSelectionInput.model_json_schema(),
        "ToolSelectionResult": ToolSelectionResult.model_json_schema(),
        "ToolSelectionError": ToolSelectionError.model_json_schema(),
        "PolicyDecision": PolicyDecision.model_json_schema(),
        "ApprovalRequest": ApprovalRequest.model_json_schema(),
        "ArtifactRef": ArtifactRef.model_json_schema(),
    }


@app.post("/simulate/tool-selection")
def simulate_tool_selection(payload: dict[str, Any]) -> JSONResponse:
    try:
        ToolSelectionInput.model_validate(payload)
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"error_type": "invalid_output", "message": str(exc)},
        )
    out = run_mock_selection(payload)
    # Run policy to surface what would happen next.
    if "server" in out:
        decision = run_policy_evaluation(
            {
                "org_id": payload["org_id"],
                "employee_id": payload["employee_id"],
                "server": out["server"],
                "tool": out["tool"],
                "risk": payload.get("risk", Risk.LOW.value),
            }
        )
        out["_policy_preview"] = decision
    return JSONResponse(content=out)


@app.post("/simulate/approval")
def simulate_approval(payload: dict[str, Any]) -> JSONResponse:
    approval_id = payload.get("approval_id")
    decision = payload.get("decision")
    if not approval_id or decision not in {"approve", "reject"}:
        raise HTTPException(
            status_code=400,
            detail="approval_id and decision (approve|reject) are required",
        )

    existing = _APPROVAL_STORE.get(approval_id)
    if existing is None:
        # Allow first-touch creation so the smoke endpoint is self-contained.
        existing = ApprovalRequest(
            approval_id=approval_id,
            org_id=payload.get("org_id", "smoke-org"),
            employee_id=payload.get("employee_id", "smoke-employee"),
            subject=ApprovalSubject(
                server=payload.get("server", "mock"),
                tool=payload.get("tool", "echo"),
                arguments_digest="sha256:smoke",
            ),
            risk=Risk(payload.get("risk", Risk.HIGH.value)),
        )

    new_state = ApprovalState.APPROVED if decision == "approve" else ApprovalState.REJECTED
    from datetime import datetime, timezone

    updated = existing.model_copy(
        update={
            "state": new_state,
            "decision_by": payload.get("decision_by", "smoke-operator"),
            "decided_at": datetime.now(timezone.utc),
        }
    )
    _APPROVAL_STORE[approval_id] = updated
    return JSONResponse(content=updated.model_dump(mode="json"))


@app.post("/simulate/mcp-call")
def simulate_mcp_call(payload: dict[str, Any]) -> JSONResponse:
    server = payload.get("server")
    tool = payload.get("tool")
    if not server or not tool:
        raise HTTPException(status_code=400, detail="server and tool are required")
    activity_name = build_mcp_activity_name(server, tool)
    if activity_name not in {MOCK_ECHO_NAME, MOCK_SEARCH_NAME}:
        raise HTTPException(
            status_code=404, detail=f"no mock MCP activity registered as {activity_name!r}"
        )

    try:
        MCPToolInvocation.model_validate(payload)
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error_type": "validation",
                "message": str(exc),
                "retriable": False,
                "invocation_id": payload.get("invocation_id", "unknown"),
            },
        )
    return JSONResponse(content=dispatch_mock(activity_name, payload))
