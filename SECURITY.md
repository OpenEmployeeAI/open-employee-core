# Security Policy

OpenEmployee treats agent actions as auditable, policy-controlled operations.

## Required boundaries

- Raw secrets must not enter Temporal workflow history.
- Secret references must use `auth_ref`.
- Risky MCP tool calls require a policy check and, when required, human approval before Activity scheduling.
- Each selected MCP tool must execute as its own Temporal Activity named `mcp__<server>__<tool>`.
- Large outputs should use claim-check references instead of raw workflow payloads.

## Reporting vulnerabilities

Please do not open public issues for sensitive vulnerabilities. Contact the maintainers privately through GitHub Security Advisories when enabled for this repository.
