# Upstream PR #61 — what it introduced, what we kept

Reference: `temporal-community/temporal-ai-agent#61` —
"Route every MCP tool call through a typed Temporal Activity dispatcher".

## What the PR introduced upstream

| Area | File | Summary |
|------|------|---------|
| Types | `models/mcp_types.py` | `MCPToolInvocation`, `MCPToolResult`, `MCPToolError` dataclasses. |
| Activity dispatcher | `activities/mcp_dispatcher.py` | `@activity.defn(dynamic=True)` dispatcher; parses activity-type name back to `(server, tool)`. |
| Naming | (in dispatcher) | Activities are named `mcp__<server>__<tool>` so each MCP call shows up distinctly in workflow history. |
| Retry semantics | `workflows/mcp_dispatcher_helpers.py` | `mcp_retry_policy()` + 5-attempt exponential backoff; non-retryable on `MCPInvalidArgumentError`. |
| Structured error | `MCPToolResult(success=False, error=MCPToolError(...))` | Folds logical failures into the typed result instead of raising. |
| Workflow integration | `workflows/mcp_agent_chain_workflow.py` | Sample chain workflow that runs LLM-selected MCP tools durably. |

## What we adopted in OpenEmployee Core (Phase 1)

- **Activity-name scheme** — kept verbatim (`mcp__<server>__<tool>`).
  Implemented in `naming/activity_names.py` with strict token validation
  (`^[a-z0-9][a-z0-9-]*(_[a-z0-9-]+)*$`) so that the name parses back to
  exactly one `(server, tool)` pair.
- **Typed invocation / result / error** — adopted, refactored as Pydantic v2
  models with `extra='forbid'`. Field names harmonized:
  - upstream `success` → `ok`
  - upstream `content` → `output`
  - upstream `retryable` → `retriable`
- **Structured error type** — `MCPToolError.error_type` is now a closed enum
  (`validation`, `policy`, `approval_required`, `connector`, `timeout`,
  `secret_leak`, `unknown_tool`, `internal`).
- **Workflow / Activity boundary discipline** — every MCP execution is
  scheduled with `workflow.execute_activity(build_mcp_activity_name(...))`.
  LLM selection itself is also an Activity (`llm__<provider>__select_tool`)
  — that is OpenEmployee-specific, not upstream.

## What we deliberately did NOT take

- No dynamic dispatcher Activity in Phase 1. Each mock MCP tool is registered
  by its canonical name (`@activity.defn(name=...)`). A dynamic dispatcher is
  a Phase 2 concern for real MCP servers.
- No `MCPClientManager` / pooled connection logic. The Phase 1 activities are
  pure-Python mocks.
- No automatic forwarding to legacy non-MCP tool handlers. OpenEmployee has no
  legacy path to be backwards-compatible with.
