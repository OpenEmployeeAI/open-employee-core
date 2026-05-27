# Contributing

Thanks for helping build OpenEmployee.

## Development principles

- Keep core dependency-light.
- Prefer typed contracts over ad-hoc dictionaries.
- Do not introduce SPIFFE, OpenFGA, Infisical, Hydra, AWS, GCP, or Entra as hard v0 core dependencies; model extension points first.
- Preserve the invariant that every MCP tool selected by an LLM executes as a dedicated Temporal Activity boundary named `mcp__<server>__<tool>`.
- Never put raw secrets in Temporal workflow history. Use `auth_ref` and external secret resolution only.
- Use claim-check artifact references for large Activity outputs.

## Pull requests

1. Open an issue before substantial work.
2. Keep PRs small and composable.
3. Include tests or explain why tests do not apply.
4. Document contract changes.
5. End the PR description with the A2A handoff block.
