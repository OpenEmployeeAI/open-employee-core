"""Tests for the smoke FastAPI app."""
from __future__ import annotations

from fastapi.testclient import TestClient

from openemployee_core.smoke.app import app

client = TestClient(app)


def _invocation() -> dict:
    return {
        "org_id": "org-1",
        "employee_id": "emp-1",
        "server": "mock",
        "tool": "echo",
        "arguments": {"query": "hi"},
        "idempotency_key": "idem-1",
        "correlation_id": "corr-1",
    }


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["builder_check"] == "mcp__mock__echo"
    assert body["llm_builder_check"] == "llm__mock__select_tool"


def test_contracts_returns_schemas():
    r = client.get("/contracts")
    assert r.status_code == 200
    body = r.json()
    assert "MCPToolInvocation" in body
    assert "ToolSelectionInput" in body


def test_simulate_tool_selection_ok():
    payload = {
        "org_id": "org-1",
        "employee_id": "emp-1",
        "messages": [{"role": "user", "content": "ping"}],
        "allowed_tools": [{"server": "mock", "tool": "echo"}],
        "provider": "mock",
        "correlation_id": "corr-1",
    }
    r = client.post("/simulate/tool-selection", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["server"] == "mock"
    assert body["tool"] == "echo"
    assert body["arguments"] == {"query": "ping"}
    assert body["_policy_preview"]["decision"] == "allow"


def test_simulate_tool_selection_invalid():
    r = client.post("/simulate/tool-selection", json={"org_id": ""})
    assert r.status_code == 400


def test_simulate_approval():
    r = client.post(
        "/simulate/approval",
        json={"approval_id": "appr-1", "decision": "approve"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "approved"
    assert body["decision_by"] == "smoke-operator"


def test_simulate_mcp_call_echo():
    r = client.post("/simulate/mcp-call", json=_invocation())
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["output"]["echo"]["query"] == "hi"


def test_simulate_mcp_call_unknown_tool():
    payload = _invocation()
    payload["tool"] = "nonexistent"
    r = client.post("/simulate/mcp-call", json=payload)
    assert r.status_code == 404


def test_simulate_mcp_call_blocks_secret():
    payload = _invocation()
    payload["arguments"] = {"token": "AKIAABCDEFGHIJKLMNOP"}
    r = client.post("/simulate/mcp-call", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["error_type"] == "secret_leak"
