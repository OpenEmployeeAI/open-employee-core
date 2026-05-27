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
- Current phase: scaffold and coordination only.
- Production implementation is intentionally out of scope until issues are claimed.

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
