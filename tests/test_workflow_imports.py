"""Static check: workflow module must not transitively import LLM/MCP SDKs."""
from __future__ import annotations

import ast
import pathlib


WORKFLOW_FILE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "openemployee_core"
    / "workflows"
    / "employee_workflow.py"
)

# These are libraries that, if imported at workflow module load time, would
# violate the product invariant.
FORBIDDEN_MODULE_PREFIXES = {
    "openai",
    "anthropic",
    "google.generativeai",
    "ollama",
    "mcp",  # the python MCP SDK package
    "httpx",
    "requests",
    "boto3",
    "botocore",
}


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_workflow_does_not_import_forbidden_modules():
    imports = _imported_modules(WORKFLOW_FILE)
    offenders: list[str] = []
    for imp in imports:
        for forbidden in FORBIDDEN_MODULE_PREFIXES:
            if imp == forbidden or imp.startswith(forbidden + "."):
                offenders.append(imp)
    assert not offenders, f"workflow imports forbidden modules: {offenders}"


def test_workflow_does_not_import_activities_module():
    """Workflow resolves activities by canonical name only."""
    imports = _imported_modules(WORKFLOW_FILE)
    offenders = [
        imp
        for imp in imports
        if "openemployee_core.activities" in imp
        or imp.endswith(".activities")
    ]
    assert not offenders, f"workflow imports activities directly: {offenders}"
