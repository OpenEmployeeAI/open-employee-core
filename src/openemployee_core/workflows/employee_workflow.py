"""EmployeeWorkflow — the durable orchestration boundary.

IMPORTANT: This module must not import any LLM SDK or MCP connector library.
It only reaches the outside world through ``workflow.execute_activity`` calls
addressed to canonical Activity names built via the ``naming`` module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

# NOTE: We deliberately do NOT import anything from
# ``openemployee_core.activities`` or any LLM/MCP library here. The workflow
# resolves Activities by canonical name only.
with workflow.unsafe.imports_passed_through():
    from ..naming import build_llm_selection_activity_name, build_mcp_activity_name


SELECTION_RETRY = RetryPolicy(
    initial_interval=timedelta(milliseconds=200),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)
POLICY_RETRY = RetryPolicy(
    initial_interval=timedelta(milliseconds=200),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)
MCP_RETRY = RetryPolicy(
    initial_interval=timedelta(milliseconds=500),
    maximum_attempts=5,
    backoff_coefficient=2.0,
)


@dataclass
class EmployeeWorkflowInput:
    org_id: str
    employee_id: str
    correlation_id: str
    provider: str
    allowed_tools: list[dict]  # [{server, tool}, ...]
    messages: list[dict] = field(default_factory=list)
    actor_user_id: Optional[str] = None
    risk: str = "low"
    idempotency_key: str = ""
    approval_timeout_seconds: int = 300


@dataclass
class EmployeeWorkflowOutput:
    ok: bool
    stage: str  # "selection" | "policy" | "approval" | "mcp"
    result: dict[str, Any]


@workflow.defn
class EmployeeWorkflow:
    """Picks a tool via an LLM Activity, runs policy, awaits approval if needed,
    then schedules the MCP tool as its own Activity boundary.
    """

    def __init__(self) -> None:
        self._approval_state: Optional[str] = None
        self._approval_decided_by: Optional[str] = None

    @workflow.signal(name="approval_decided")
    def on_approval_decided(self, decision: dict[str, Any]) -> None:
        # decision keys: state, decision_by
        state = decision.get("state")
        if state in {"approved", "rejected", "expired"}:
            self._approval_state = state
            self._approval_decided_by = decision.get("decision_by")

    @workflow.run
    async def run(self, payload: EmployeeWorkflowInput) -> EmployeeWorkflowOutput:
        # 1. LLM selection -> Activity boundary.
        selection_activity = build_llm_selection_activity_name(payload.provider)
        selection_payload = {
            "org_id": payload.org_id,
            "employee_id": payload.employee_id,
            "actor_user_id": payload.actor_user_id,
            "messages": payload.messages,
            "allowed_tools": payload.allowed_tools,
            "provider": payload.provider,
            "correlation_id": payload.correlation_id,
        }
        selection = await workflow.execute_activity(
            selection_activity,
            selection_payload,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=SELECTION_RETRY,
        )

        # Validate selector output shape.
        server = selection.get("server")
        tool = selection.get("tool")
        if not server or not tool:
            return EmployeeWorkflowOutput(
                ok=False,
                stage="selection",
                result={
                    "error_type": "invalid_output",
                    "message": "selector did not return server/tool",
                    "raw_output": selection,
                },
            )

        # Validate that the selection is in the allowed tools.
        allowed_pairs = {(t["server"], t["tool"]) for t in payload.allowed_tools}
        if (server, tool) not in allowed_pairs:
            return EmployeeWorkflowOutput(
                ok=False,
                stage="selection",
                result={
                    "error_type": "unknown_tool",
                    "message": f"selector picked {server}.{tool} which is not in allowed_tools",
                    "raw_output": selection,
                },
            )

        # 2. Policy -> Activity boundary.
        policy_decision = await workflow.execute_activity(
            "policy__evaluate",
            {
                "org_id": payload.org_id,
                "employee_id": payload.employee_id,
                "server": server,
                "tool": tool,
                "risk": payload.risk,
            },
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=POLICY_RETRY,
        )
        decision = policy_decision.get("decision")
        if decision == "deny":
            return EmployeeWorkflowOutput(
                ok=False, stage="policy", result=policy_decision
            )
        if decision == "require_approval":
            approval_id = f"appr-{workflow.info().workflow_id}"
            approval_request = {
                "approval_id": approval_id,
                "org_id": payload.org_id,
                "employee_id": payload.employee_id,
                "actor_user_id": payload.actor_user_id,
                "subject": {
                    "server": server,
                    "tool": tool,
                    "arguments_digest": "sha256:pending",
                },
                "risk": payload.risk,
                "state": "pending",
            }
            workflow.logger.info("approval pending", extra={"approval": approval_id})
            try:
                await workflow.wait_condition(
                    lambda: self._approval_state is not None,
                    timeout=timedelta(seconds=payload.approval_timeout_seconds),
                )
            except TimeoutError:
                self._approval_state = "expired"
            approval_request["state"] = self._approval_state
            approval_request["decision_by"] = self._approval_decided_by
            if self._approval_state != "approved":
                return EmployeeWorkflowOutput(
                    ok=False, stage="approval", result=approval_request
                )
            approval_ref: Optional[str] = approval_id
        else:
            approval_ref = None

        # 3. MCP execution -> Activity boundary with deterministic name.
        invocation = {
            "org_id": payload.org_id,
            "employee_id": payload.employee_id,
            "actor_user_id": payload.actor_user_id,
            "server": server,
            "tool": tool,
            "arguments": selection.get("arguments", {}),
            "idempotency_key": payload.idempotency_key or workflow.info().workflow_id,
            "risk": payload.risk,
            "approval_ref": approval_ref,
            "correlation_id": payload.correlation_id,
        }
        mcp_activity = build_mcp_activity_name(server, tool)
        mcp_result = await workflow.execute_activity(
            mcp_activity,
            invocation,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=MCP_RETRY,
        )
        ok = bool(mcp_result.get("ok", True))
        return EmployeeWorkflowOutput(ok=ok, stage="mcp", result=mcp_result)
