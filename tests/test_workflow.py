"""End-to-end Temporal workflow tests using the in-process WorkflowEnvironment.

These prove the product invariants:
- LLM selection runs as an Activity (by name `llm__mock__select_tool`)
- MCP execution runs as an Activity (`mcp__mock__echo`)
- Unknown selector output is rejected
- High-risk path produces an approval pending state until signal
- Secret-shaped arguments are blocked with MCPToolError(secret_leak)
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from openemployee_core.activities import (
    MOCK_ECHO_NAME,
    MOCK_LLM_ACTIVITY_NAME,
    MOCK_SEARCH_NAME,
    POLICY_ACTIVITY_NAME,
    llm_mock_select_tool,
    mcp_mock_echo,
    mcp_mock_search,
    policy_evaluate,
)
from openemployee_core.workflows import EmployeeWorkflow, EmployeeWorkflowInput


SCHEDULED_ACTIVITIES: list[str] = []


@activity.defn(name=MOCK_LLM_ACTIVITY_NAME)
async def spy_llm_select(payload: dict) -> dict:
    SCHEDULED_ACTIVITIES.append(MOCK_LLM_ACTIVITY_NAME)
    from openemployee_core.activities import run_mock_selection

    return run_mock_selection(payload)


@activity.defn(name=MOCK_ECHO_NAME)
async def spy_mcp_echo(payload: dict) -> dict:
    SCHEDULED_ACTIVITIES.append(MOCK_ECHO_NAME)
    from openemployee_core.activities import run_mock_echo

    return run_mock_echo(payload)


@activity.defn(name=MOCK_SEARCH_NAME)
async def spy_mcp_search(payload: dict) -> dict:
    SCHEDULED_ACTIVITIES.append(MOCK_SEARCH_NAME)
    from openemployee_core.activities import run_mock_search

    return run_mock_search(payload)


@activity.defn(name=POLICY_ACTIVITY_NAME)
async def spy_policy(payload: dict) -> dict:
    SCHEDULED_ACTIVITIES.append(POLICY_ACTIVITY_NAME)
    from openemployee_core.activities import run_policy_evaluation

    return run_policy_evaluation(payload)


@activity.defn(name="llm__bad__select_tool")
async def bad_provider_select(payload: dict) -> dict:
    # Returns malformed output (missing server/tool) on purpose.
    SCHEDULED_ACTIVITIES.append("llm__bad__select_tool")
    return {"rationale": "no tool picked"}


@activity.defn(name="llm__rogue__select_tool")
async def rogue_provider_select(payload: dict) -> dict:
    # Picks a tool not in allowed_tools.
    SCHEDULED_ACTIVITIES.append("llm__rogue__select_tool")
    return {"server": "mock", "tool": "not_in_allowed_list", "arguments": {}}


@activity.defn(name="llm__secret__select_tool")
async def secret_provider_select(payload: dict) -> dict:
    SCHEDULED_ACTIVITIES.append("llm__secret__select_tool")
    return {
        "server": "mock",
        "tool": "echo",
        "arguments": {"token": "AKIAABCDEFGHIJKLMNOP"},
    }


def _allowed_mock_tools() -> list[dict]:
    return [
        {"server": "mock", "tool": "echo"},
        {"server": "mock", "tool": "search"},
    ]


def _input(**overrides) -> EmployeeWorkflowInput:
    return EmployeeWorkflowInput(
        org_id="org-1",
        employee_id="emp-1",
        correlation_id="corr-1",
        provider=overrides.pop("provider", "mock"),
        allowed_tools=overrides.pop("allowed_tools", _allowed_mock_tools()),
        messages=[{"role": "user", "content": "find the bug"}],
        risk=overrides.pop("risk", "low"),
        idempotency_key="idem-1",
        approval_timeout_seconds=overrides.pop("approval_timeout_seconds", 2),
        **overrides,
    )


@pytest.fixture
def reset_spy():
    SCHEDULED_ACTIVITIES.clear()
    yield
    SCHEDULED_ACTIVITIES.clear()


async def _run(env: WorkflowEnvironment, *, activities, wf_input):
    task_queue = f"tq-{uuid.uuid4().hex}"
    async with Worker(
        env.client,
        task_queue=task_queue,
        workflows=[EmployeeWorkflow],
        activities=activities,
    ):
        return await env.client.execute_workflow(
            EmployeeWorkflow.run,
            wf_input,
            id=f"wf-{uuid.uuid4().hex}",
            task_queue=task_queue,
        )


@pytest.mark.asyncio
async def test_llm_selection_runs_as_activity(reset_spy):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        out = await _run(
            env,
            activities=[spy_llm_select, spy_policy, spy_mcp_echo, spy_mcp_search],
            wf_input=_input(),
        )
    assert MOCK_LLM_ACTIVITY_NAME in SCHEDULED_ACTIVITIES
    assert out.ok is True
    assert out.stage == "mcp"


@pytest.mark.asyncio
async def test_mcp_execution_runs_as_activity(reset_spy):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        await _run(
            env,
            activities=[spy_llm_select, spy_policy, spy_mcp_echo, spy_mcp_search],
            wf_input=_input(),
        )
    assert MOCK_ECHO_NAME in SCHEDULED_ACTIVITIES


@pytest.mark.asyncio
async def test_invalid_selector_output_rejected(reset_spy):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        out = await _run(
            env,
            activities=[bad_provider_select, spy_policy, spy_mcp_echo],
            wf_input=_input(provider="bad"),
        )
    assert out.ok is False
    assert out.stage == "selection"
    assert out.result["error_type"] == "invalid_output"


@pytest.mark.asyncio
async def test_unknown_tool_rejected(reset_spy):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        out = await _run(
            env,
            activities=[rogue_provider_select, spy_policy, spy_mcp_echo],
            wf_input=_input(provider="rogue"),
        )
    assert out.ok is False
    assert out.stage == "selection"
    assert out.result["error_type"] == "unknown_tool"


@pytest.mark.asyncio
async def test_high_risk_blocks_until_signal(reset_spy):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"tq-{uuid.uuid4().hex}"
        wf_id = f"wf-{uuid.uuid4().hex}"

        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[EmployeeWorkflow],
            activities=[spy_llm_select, spy_policy, spy_mcp_echo, spy_mcp_search],
        ):
            handle = await env.client.start_workflow(
                EmployeeWorkflow.run,
                _input(risk="high", approval_timeout_seconds=30),
                id=wf_id,
                task_queue=task_queue,
            )
            # Give the workflow time to reach the wait_condition.
            await asyncio.sleep(0.5)
            assert POLICY_ACTIVITY_NAME in SCHEDULED_ACTIVITIES

            # Signal approval.
            await handle.signal(
                EmployeeWorkflow.on_approval_decided,
                {"state": "approved", "decision_by": "test-operator"},
            )
            out = await handle.result()
    assert out.ok is True
    assert out.stage == "mcp"
    assert MOCK_ECHO_NAME in SCHEDULED_ACTIVITIES


@pytest.mark.asyncio
async def test_high_risk_rejection_returns_approval_state(reset_spy):
    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"tq-{uuid.uuid4().hex}"
        wf_id = f"wf-{uuid.uuid4().hex}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[EmployeeWorkflow],
            activities=[spy_llm_select, spy_policy, spy_mcp_echo, spy_mcp_search],
        ):
            handle = await env.client.start_workflow(
                EmployeeWorkflow.run,
                _input(risk="high", approval_timeout_seconds=30),
                id=wf_id,
                task_queue=task_queue,
            )
            await asyncio.sleep(0.5)
            await handle.signal(
                EmployeeWorkflow.on_approval_decided,
                {"state": "rejected", "decision_by": "test-operator"},
            )
            out = await handle.result()
    assert out.ok is False
    assert out.stage == "approval"
    assert out.result["state"] == "rejected"


@pytest.mark.asyncio
async def test_secret_in_args_blocked_by_mcp_activity(reset_spy):
    """When the selector emits a raw-secret-shaped argument, the MCP Activity's
    safety guard returns an MCPToolError(secret_leak) instead of executing."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        out = await _run(
            env,
            activities=[secret_provider_select, spy_policy, spy_mcp_echo],
            wf_input=_input(provider="secret"),
        )
    assert out.ok is False
    assert out.stage == "mcp"
    assert out.result["error_type"] == "secret_leak"


@pytest.mark.asyncio
async def test_real_mcp_activity_returns_tool_result(reset_spy):
    """Smoke: with the real (non-spy) Activity functions wired in, workflow
    succeeds and returns an MCPToolResult with output."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        task_queue = f"tq-{uuid.uuid4().hex}"
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[EmployeeWorkflow],
            activities=[
                llm_mock_select_tool,
                mcp_mock_echo,
                mcp_mock_search,
                policy_evaluate,
            ],
        ):
            out = await env.client.execute_workflow(
                EmployeeWorkflow.run,
                _input(),
                id=f"wf-{uuid.uuid4().hex}",
                task_queue=task_queue,
            )
    assert out.ok is True
    assert out.result["ok"] is True
    assert out.result["output"]["echo"]["query"] == "find the bug"
