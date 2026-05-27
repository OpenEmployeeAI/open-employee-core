# AWS App Runner smoke test

A FastAPI app exposing the OpenEmployee Core contracts and mock activities
synchronously, for hosted verification (e.g. Perplexity Computer or any
external prober). **Not** a substitute for the Temporal worker — the durable
runtime is still required for real workflows. The smoke API only proves the
contracts and safety guards behave identically when wired through HTTP.

## Region

Default AWS region: `us-east-1`. App Runner spec lives in `apprunner.yaml`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + builder check. |
| GET | `/contracts` | Returns JSON Schemas for every contract via `model_json_schema()`. |
| POST | `/simulate/tool-selection` | Runs mock LLM selector + a policy preview. |
| POST | `/simulate/approval` | Updates an in-memory approval record. |
| POST | `/simulate/mcp-call` | Runs `mcp__mock__echo` / `mcp__mock__search` through the same safety guards. |

## curl samples

```bash
BASE=https://<app-runner-host>

# 1. Health
curl -s "$BASE/health" | jq

# 2. Contracts
curl -s "$BASE/contracts" | jq 'keys'

# 3. Tool selection
curl -s -X POST "$BASE/simulate/tool-selection" \
  -H 'content-type: application/json' \
  -d '{
        "org_id": "org-1",
        "employee_id": "emp-1",
        "messages": [{"role": "user", "content": "find the bug"}],
        "allowed_tools": [{"server": "mock", "tool": "echo"}],
        "provider": "mock",
        "correlation_id": "corr-1"
      }' | jq

# 4. Approval
curl -s -X POST "$BASE/simulate/approval" \
  -H 'content-type: application/json' \
  -d '{"approval_id": "appr-1", "decision": "approve"}' | jq

# 5. MCP call (echo)
curl -s -X POST "$BASE/simulate/mcp-call" \
  -H 'content-type: application/json' \
  -d '{
        "org_id": "org-1",
        "employee_id": "emp-1",
        "server": "mock",
        "tool": "echo",
        "arguments": {"query": "ping"},
        "idempotency_key": "idem-1",
        "correlation_id": "corr-1"
      }' | jq

# 6. MCP call with raw secret → must return secret_leak
curl -s -X POST "$BASE/simulate/mcp-call" \
  -H 'content-type: application/json' \
  -d '{
        "org_id": "org-1",
        "employee_id": "emp-1",
        "server": "mock",
        "tool": "echo",
        "arguments": {"token": "AKIAABCDEFGHIJKLMNOP"},
        "idempotency_key": "idem-1",
        "correlation_id": "corr-1"
      }' | jq
```

Expected: the secret-bearing payload returns
`{"ok": false, "error_type": "secret_leak", ...}` with HTTP 200 (the request
is well-formed; the safety guard rejects it inside the activity).

## What Perplexity Computer should verify once deployed

1. `GET /health` returns `status: ok` and `builder_check == "mcp__mock__echo"`.
2. `GET /contracts` returns a JSON object containing the keys `MCPToolInvocation`,
   `MCPToolResult`, `MCPToolError`, `ToolSelectionInput`, `ToolSelectionResult`,
   `ToolSelectionError`, `PolicyDecision`, `ApprovalRequest`, `ArtifactRef`.
3. `POST /simulate/tool-selection` with the sample payload echoes a selection
   of `server=mock`, `tool=echo`, `arguments.query=find the bug`, plus a
   `_policy_preview.decision=allow` field.
4. `POST /simulate/mcp-call` echoes the arguments back inside
   `output.echo` and reports `ok=true`.
5. The secret-bearing call returns `error_type=secret_leak`.

These five checks are sufficient for the orchestrator to fill the
`## AWS hosted smoke URL` slot in the PR.
