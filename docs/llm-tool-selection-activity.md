# Why LLM tool selection is its own Activity

## The invariant

> Every LLM-selected tool call must become a Temporal Activity boundary.
> LLM tool selection itself runs as Activity `llm__<provider>__select_tool`.
> MCP tool execution runs as Activity `mcp__<server>__<tool>`.

## Why selection must be an Activity (not inline workflow code)

Temporal workflows are deterministic replay. If LLM selection ran inline:

- The LLM call would re-execute on every workflow replay, producing a different
  answer each time → non-determinism → corrupted history.
- Provider failures would not be retried by Temporal's RetryPolicy; we would
  have to hand-roll retry inside the workflow, which is exactly what the
  Activity boundary already gives us.
- Workflow history would not contain the selection input/output, so we could
  not audit "which tool did the model pick and why."

Putting the selector behind `workflow.execute_activity(llm__<provider>__select_tool, ...)`:

- Records the chosen `(server, tool, arguments)` once in workflow history.
- Replays from history without re-calling the model.
- Gets retries, timeouts, and structured failure for free.

## Contract

Input (`ToolSelectionInput`):
- `org_id`, `employee_id`, optional `actor_user_id` — identity triple.
- `messages` — chat context; provider-agnostic shape.
- `allowed_tools` — the closed set the model is allowed to pick from.
- `provider` — drives the Activity name (`llm__<provider>__select_tool`).
- `model_hint` — optional; opaque to the workflow.
- `correlation_id` — propagated for tracing.

Output, on success (`ToolSelectionResult`):
- `selection_id`, `server`, `tool`, `arguments`, optional `rationale` and
  `confidence`, `provider_metadata`.

Output, on failure (`ToolSelectionError`):
- `error_type ∈ {invalid_output, provider, policy, unknown_tool}`.

## Workflow-side validation

After the selection Activity returns, the workflow:

1. Verifies `server` and `tool` are present (else `invalid_output`).
2. Verifies `(server, tool)` is in `allowed_tools` (else `unknown_tool`).
3. Calls `policy__evaluate` (another Activity) for `allow` / `deny` /
   `require_approval`.
4. If `require_approval`, waits on the `approval_decided` signal.
5. Schedules the MCP Activity by canonical name.

The workflow imports neither LLM SDKs nor MCP connector libraries; it only
imports `naming` helpers and the `workflow` runtime. This is enforced by
`tests/test_workflow_imports.py`.

## Retry / timeout policy (Phase 1)

| Stage | start_to_close | retries | backoff |
|-------|----------------|---------|---------|
| `llm__<provider>__select_tool` | 30 s | 3 | exponential, base 200 ms |
| `policy__evaluate` | 10 s | 3 | exponential, base 200 ms |
| `mcp__<server>__<tool>` | 60 s | 5 | exponential, base 500 ms |

## Determinism rules

- The selector Activity must be a pure function of `ToolSelectionInput`. Any
  randomness, temperature, or system clock dependency must be captured inside
  the Activity body so the result becomes part of workflow history.
- The mock selector (`run_mock_selection`) is fully deterministic: it picks
  the first entry of `allowed_tools` and copies the last user message into
  `arguments.query`. This makes it suitable for CI without a real model.
