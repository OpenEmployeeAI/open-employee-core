"""Deterministic Activity name builders / parsers.

Every MCP tool the LLM selects becomes an Activity named exactly
``mcp__<server>__<tool>``. LLM selection itself is an Activity named
``llm__<provider>__select_tool``. These names are the contract between
workflow code and registered Activity functions.
"""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(_[a-z0-9-]+)*$")
_MCP_PREFIX = "mcp__"
_LLM_PREFIX = "llm__"
_LLM_SUFFIX = "__select_tool"


def _check_token(name: str, label: str) -> None:
    if not isinstance(name, str) or not _TOKEN_RE.match(name):
        raise ValueError(
            f"invalid {label} token {name!r}: must match {_TOKEN_RE.pattern}"
        )


def build_mcp_activity_name(server: str, tool: str) -> str:
    _check_token(server, "server")
    _check_token(tool, "tool")
    return f"{_MCP_PREFIX}{server}__{tool}"


def parse_mcp_activity_name(name: str) -> tuple[str, str]:
    if not isinstance(name, str) or not name.startswith(_MCP_PREFIX):
        raise ValueError(f"not an MCP activity name: {name!r}")
    body = name[len(_MCP_PREFIX) :]
    if "__" not in body:
        raise ValueError(f"malformed MCP activity name: {name!r}")
    server, tool = body.split("__", 1)
    _check_token(server, "server")
    _check_token(tool, "tool")
    return server, tool


def build_llm_selection_activity_name(provider: str) -> str:
    _check_token(provider, "provider")
    return f"{_LLM_PREFIX}{provider}{_LLM_SUFFIX}"
