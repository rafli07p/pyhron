"""Shared pytest fixtures and configuration for the Pyhron test suite."""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

# ── Make hyphenated directories importable ───────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _register_package(fs_path: Path, import_name: str) -> None:
    """Register a filesystem directory as an importable Python package."""
    if not fs_path.exists() or import_name in sys.modules:
        return
    init = fs_path / "__init__.py"
    if not init.exists():
        return
    spec = importlib.util.spec_from_file_location(
        import_name,
        init,
        submodule_search_locations=[str(fs_path)],
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[import_name] = mod
        spec.loader.exec_module(mod)


# data-platform → data_platform
_register_package(_PROJECT_ROOT / "data-platform", "data_platform")

# Ensure services package exists, then register risk-engine as services.risk_engine
_services_path = _PROJECT_ROOT / "services"
if _services_path.exists() and "services" not in sys.modules:
    _register_package(_services_path, "services")

_register_package(_services_path / "risk-engine", "services.risk_engine")


# ── Event Loop ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Pytest Configuration ────────────────────────────────────────────────────


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests requiring external services"
    )
    config.addinivalue_line(
        "markers", "e2e: marks end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "benchmark: marks performance benchmark tests"
    )
