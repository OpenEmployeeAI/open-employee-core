"""Property-style tests for the naming module."""
from __future__ import annotations

import random
import string

import pytest

from openemployee_core.naming import (
    build_llm_selection_activity_name,
    build_mcp_activity_name,
    parse_mcp_activity_name,
)


def _rand_token(rng: random.Random) -> str:
    head_alphabet = string.ascii_lowercase + string.digits
    body_alphabet = string.ascii_lowercase + string.digits + "-"
    head = rng.choice(head_alphabet)
    tail = "".join(rng.choice(body_alphabet) for _ in range(rng.randint(0, 8)))
    # Optionally append zero or more single-underscore-separated chunks.
    parts = [head + tail]
    for _ in range(rng.randint(0, 3)):
        chunk_head = rng.choice(head_alphabet)
        chunk_tail = "".join(
            rng.choice(body_alphabet) for _ in range(rng.randint(0, 5))
        )
        parts.append(chunk_head + chunk_tail)
    return "_".join(parts)


def test_mcp_activity_name_round_trip_property():
    rng = random.Random(42)
    for _ in range(200):
        server = _rand_token(rng)
        tool = _rand_token(rng)
        name = build_mcp_activity_name(server, tool)
        assert name == f"mcp__{server}__{tool}"
        s2, t2 = parse_mcp_activity_name(name)
        assert (s2, t2) == (server, tool)


@pytest.mark.parametrize(
    "server,tool",
    [
        ("Mock", "echo"),
        ("mock", "Echo"),
        ("-bad", "echo"),
        ("mock", ""),
        ("", "echo"),
        ("mock", "echo!"),
        ("mock__bad", "echo"),  # consecutive underscores
    ],
)
def test_rejects_invalid_tokens(server, tool):
    with pytest.raises(ValueError):
        build_mcp_activity_name(server, tool)


@pytest.mark.parametrize(
    "name",
    [
        "mock__echo",  # missing mcp__ prefix
        "mcp_mockecho",
        "mcp__echo",  # missing tool
        "mcp__MOCK__echo",  # uppercase
        "",
    ],
)
def test_parse_rejects_malformed(name):
    with pytest.raises(ValueError):
        parse_mcp_activity_name(name)


def test_llm_selection_activity_name_smoke():
    assert build_llm_selection_activity_name("mock") == "llm__mock__select_tool"
    with pytest.raises(ValueError):
        build_llm_selection_activity_name("BadProvider")
