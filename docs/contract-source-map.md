# Contract source map

How each canonical contract field traces back to its source. Three origins:

- **PR #61** — `temporal-community/temporal-ai-agent#61` (typed MCPToolInvocation /
  MCPToolResult / MCPToolError and deterministic Activity-name scheme).
- **tenuringai** — prior identity / approval / artifact conventions used in
  earlier internal repos, mapped to OpenEmployee canonical names.
- **OpenEmployee-original** — fields introduced in this repo because they are
  required by the OpenEmployee runtime invariants (multi-tenant identity,
  pluggable policy, secret-leak guard).

| Contract | Field | Origin | Notes |
|----------|-------|--------|-------|
| `MCPToolInvocation` | `invocation_id` | OpenEmployee-original | Stable handle for tracing / idempotency lookup. |
| `MCPToolInvocation` | `org_id`, `employee_id`, `actor_user_id` | tenuringai | Required multi-tenant identity triple. |
| `MCPToolInvocation` | `server`, `tool`, `arguments` | PR #61 | Same shape as upstream; here `arguments` is `dict[str, Any]`. |
| `MCPToolInvocation` | `auth_ref` | OpenEmployee-original | Opaque reference; raw secrets never enter workflow history. |
| `MCPToolInvocation` | `spiffe_id` | tenuringai | Optional; **no SPIFFE library dep**. |
| `MCPToolInvocation` | `idempotency_key` | tenuringai | Required for safe retry. |
| `MCPToolInvocation` | `risk` | OpenEmployee-original | Drives the policy / approval path. |
| `MCPToolInvocation` | `approval_ref` | OpenEmployee-original | Set after approval gate. |
| `MCPToolInvocation` | `artifact_refs` | OpenEmployee-original | Claim-check inputs. |
| `MCPToolInvocation` | `correlation_id`, `requested_at` | tenuringai | Tracing. |
| `MCPToolResult` | `ok=True`, `output` | PR #61 | Upstream used `success`/`content`; renamed to `ok`/`output` for symmetry with `MCPToolError`. |
| `MCPToolResult` | `artifact_refs` | OpenEmployee-original | Spilled outputs over `MAX_INLINE_BYTES`. |
| `MCPToolResult` | `latency_ms`, `provider_metadata` | OpenEmployee-original | Observability. |
| `MCPToolError` | `error_type` enum | PR #61 (extended) | Upstream string `error_type`; here a closed enum (validation, policy, approval_required, connector, timeout, secret_leak, unknown_tool, internal). |
| `MCPToolError` | `retriable` | PR #61 | Upstream `retryable`; renamed. |
| `ToolSelectionInput` | `messages`, `allowed_tools`, `provider`, `model_hint` | OpenEmployee-original | LLM selection lives in its own Activity boundary. |
| `ToolSelectionResult` | `server`, `tool`, `arguments`, `rationale`, `confidence` | OpenEmployee-original | Reflects what an LLM must return to be safely routed. |
| `ToolSelectionError` | `error_type` enum | OpenEmployee-original | `invalid_output`, `provider`, `policy`, `unknown_tool`. |
| `PolicyDecision` | `decision` enum, `reasons`, `policy_version` | OpenEmployee-original | Pluggable evaluator interface. |
| `ApprovalRequest` | `approval_id`, `subject{server,tool,arguments_digest}`, `state` enum | tenuringai | Approval gate before the MCP Activity. |
| `ArtifactRef` | `uri`, `media_type`, `bytes`, `checksum`, `kind` | OpenEmployee-original | Claim-check record. |
