"""Phase 00 health test: the package tree imports and exposes a version."""

import importlib

import agentic_qa

LAYER_PACKAGES = [
    "agentic_qa.domain",
    "agentic_qa.domain.projects",
    "agentic_qa.domain.runs",
    "agentic_qa.domain.agent",
    "agentic_qa.domain.browser",
    "agentic_qa.domain.qa",
    "agentic_qa.domain.inference",
    "agentic_qa.domain.knowledge",
    "agentic_qa.application",
    "agentic_qa.application.commands",
    "agentic_qa.application.queries",
    "agentic_qa.application.ports",
    "agentic_qa.application.services",
    "agentic_qa.infrastructure",
    "agentic_qa.interfaces",
    "agentic_qa.bootstrap",
]


def test_package_has_version() -> None:
    assert agentic_qa.__version__


def test_layer_packages_import() -> None:
    for name in LAYER_PACKAGES:
        assert importlib.import_module(name).__name__ == name
