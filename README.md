# open-employee-core

Durable Temporal runtime core for MCP-backed AI employees.

OpenEmployee is an open-source, portable, durable runtime for AI employees.

## Core invariant

Every MCP tool selected by an LLM must execute as its own Temporal Activity boundary. Activity names must be deterministic and follow:

```text
mcp__<server>__<tool>
```

This follows the upstream `temporal-community/temporal-ai-agent` PR #61 pattern: typed `MCPToolInvocation`, `MCPToolResult`, `MCPToolError`, deterministic Activity names, retries, and structured errors.

## Scope for this repo

- Role: core
- Current phase (Phase 1): canonical contracts, naming, workflow skeleton, mock activities, safety guards, and a synchronous smoke API.
- Production connectors and real LLM providers come in later phases.

## Quickstart

```bash
pip install -e '.[dev]'
pytest -q

# Smoke API (synchronous simulator; not a substitute for the Temporal worker):
uvicorn openemployee_core.smoke.app:app --port 8080
curl -s localhost:8080/health | jq
```

## Layout

```
src/openemployee_core/
  contracts/   # Pydantic v2 models (MCPToolInvocation, ToolSelection*, PolicyDecision, ...)
  naming/      # build/parse mcp__<server>__<tool>, llm__<provider>__select_tool
  activities/  # Temporal Activity defns (mock LLM selector, mock MCP tools, policy)
  workflows/   # EmployeeWorkflow — only execute_activity boundaries, no LLM/MCP SDK imports
  policy/      # Pluggable policy evaluator
  safety/      # Identity / secret / claim-check guards
  smoke/       # FastAPI app for hosted smoke verification
```

See `docs/` for the full contract source map, PR #61 mapping, and AWS smoke instructions.

## Architecture anchors

- Temporal workflows orchestrate durable execution.
- Each MCP tool call is scheduled as a dedicated Temporal Activity.
- Raw secrets must never enter workflow history; use `auth_ref` only.
- Risky calls require policy checks and human approval before Activity scheduling.
- Large Activity outputs must use claim-check artifact references.
- FoundationAgents/OpenManus is the planned future computer/browser execution layer.
- Pipedream is the first-class SaaS connector layer.

## A2A handoff

Every agent thread must end with:

```yaml
from:
to:
repo:
branch:
pr:
status:
files_changed:
contracts_changed:
tests_run:
blockers:
risks:
next:
```
