"""The dependency rule is a test, not a review habit.

    Interfaces/Delivery ----> Application ----> Domain
    Infrastructure ---------> Application ----> Domain

Domain stays framework-free and Application depends on ports, never on adapters
(CLAUDE.md invariants, docs/03-clean-architecture.md). Absolute imports are required
inside these layers so the check cannot be bypassed by a relative path.
"""

import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "agentic_qa"

INFRASTRUCTURE_PACKAGES = (
    "sqlalchemy",
    "alembic",
    "asyncpg",
    "psycopg",
    "fastapi",
    "starlette",
    "redis",
    "temporalio",
    "langgraph",
    "langchain",
    "playwright",
    "httpx",
    "graphiti",
    "falkordb",
)

FORBIDDEN_BY_LAYER = {
    "domain": (
        "agentic_qa.application",
        "agentic_qa.infrastructure",
        "agentic_qa.interfaces",
        "agentic_qa.bootstrap",
        *INFRASTRUCTURE_PACKAGES,
    ),
    "application": (
        "agentic_qa.infrastructure",
        "agentic_qa.interfaces",
        "agentic_qa.bootstrap",
        *INFRASTRUCTURE_PACKAGES,
    ),
}


def imported_modules(source_file: Path) -> list[str]:
    tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, f"{source_file}: use absolute imports inside layered code"
            if node.module:
                modules.append(node.module)
    return modules


def forbidden_imports(source_file: Path, forbidden: tuple[str, ...]) -> list[str]:
    return [
        module
        for module in imported_modules(source_file)
        if module.split(".")[0] in forbidden or module.startswith(tuple(f"{f}." for f in forbidden))
    ]


def layer_files(layer: str) -> list[Path]:
    files = sorted((SOURCE_ROOT / layer).rglob("*.py"))
    assert files, f"no source files found for layer {layer}"
    return files


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_BY_LAYER))
def test_layer_has_no_forbidden_dependencies(layer: str) -> None:
    forbidden = FORBIDDEN_BY_LAYER[layer]
    violations = [
        f"{source_file.relative_to(SOURCE_ROOT)} imports {module}"
        for source_file in layer_files(layer)
        for module in forbidden_imports(source_file, forbidden)
    ]

    assert not violations, f"{layer} layer violates the dependency rule:\n" + "\n".join(violations)


@pytest.mark.parametrize(
    "line",
    [
        "from sqlalchemy.orm import Session",
        "import sqlalchemy",
        "from agentic_qa.infrastructure.persistence.postgres.models import Base",
        "from fastapi import APIRouter",
    ],
)
def test_guard_catches_a_planted_violation(tmp_path: Path, line: str) -> None:
    """A guard that cannot fail proves nothing: plant a violation and expect a catch."""
    planted = tmp_path / "leaky_entity.py"
    planted.write_text(f"{line}\n", encoding="utf-8")

    assert forbidden_imports(planted, FORBIDDEN_BY_LAYER["domain"])


def test_guard_allows_stdlib_and_own_layer(tmp_path: Path) -> None:
    clean = tmp_path / "clean_entity.py"
    clean.write_text(
        "from dataclasses import dataclass\nfrom agentic_qa.domain.errors import DomainError\n",
        encoding="utf-8",
    )

    assert not forbidden_imports(clean, FORBIDDEN_BY_LAYER["domain"])
