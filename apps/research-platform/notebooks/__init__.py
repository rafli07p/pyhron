"""Notebook Management for the Enthropy Research Platform.

Manages Jupyter-style research notebooks for interactive quantitative
analysis. Supports creating, listing, and executing notebooks
programmatically.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class NotebookMetadata:
    """Metadata for a research notebook."""

    notebook_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    kernel: str = "python3"
    cell_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    last_executed: datetime | None = None
    execution_status: str = "idle"  # idle, running, completed, failed
    file_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize notebook metadata to a dictionary."""
        return {
            "notebook_id": str(self.notebook_id),
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "kernel": self.kernel,
            "cell_count": self.cell_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "execution_status": self.execution_status,
            "file_path": self.file_path,
        }


class NotebookManager:
    """Manage Jupyter-style research notebooks.

    Provides programmatic creation, listing, and execution of Jupyter
    notebooks for quantitative research. Notebooks are stored as
    standard ``.ipynb`` files and can be executed via ``nbconvert``
    or ``papermill``.

    Parameters
    ----------
    notebooks_dir:
        Root directory for notebook storage.
    """

    def __init__(self, notebooks_dir: str | Path = "~/.enthropy/notebooks") -> None:
        self._notebooks_dir = Path(notebooks_dir).expanduser()
        self._registry: dict[str, NotebookMetadata] = {}
        logger.info("NotebookManager initialized (dir=%s)", self._notebooks_dir)

    def create_notebook(
        self,
        name: str,
        description: str = "",
        author: str = "",
        tags: list[str] | None = None,
        template: str | None = None,
        cells: list[dict[str, Any]] | None = None,
    ) -> NotebookMetadata:
        """Create a new Jupyter notebook.

        Parameters
        ----------
        name:
            Notebook name (used as the file stem).
        description:
            Human-readable description.
        author:
            Notebook author.
        tags:
            Tags for discoverability.
        template:
            Template name to use (``factor_research``, ``backtest``,
            ``model_training``). If ``None``, creates a blank notebook.
        cells:
            Custom cell definitions. Each dict should have ``cell_type``
            (``code`` or ``markdown``) and ``source`` keys.

        Returns
        -------
        NotebookMetadata
            Metadata for the created notebook.
        """
        self._notebooks_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._notebooks_dir / f"{name}.ipynb"

        # Build notebook structure
        nb_cells = []
        if cells:
            for cell_def in cells:
                nb_cells.append(self._make_cell(
                    cell_type=cell_def.get("cell_type", "code"),
                    source=cell_def.get("source", ""),
                ))
        elif template:
            nb_cells = self._get_template_cells(template, name)
        else:
            nb_cells = [
                self._make_cell("markdown", f"# {name}\n\n{description}"),
                self._make_cell("code", "# Start your research here\nimport pandas as pd\nimport numpy as np"),
            ]

        notebook = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.11.0"},
                "enthropy": {
                    "description": description,
                    "author": author,
                    "tags": tags or [],
                },
            },
            "cells": nb_cells,
        }

        with open(file_path, "w") as f:
            json.dump(notebook, f, indent=2)

        meta = NotebookMetadata(
            name=name,
            description=description,
            author=author,
            tags=tags or [],
            cell_count=len(nb_cells),
            file_path=str(file_path),
        )
        self._registry[name] = meta
        logger.info("Created notebook '%s' at %s (%d cells)", name, file_path, len(nb_cells))
        return meta

    def list_notebooks(
        self,
        tags: list[str] | None = None,
        author: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all available notebooks with optional filtering.

        Parameters
        ----------
        tags:
            Filter by tags (any match).
        author:
            Filter by author name.

        Returns
        -------
        list[dict[str, Any]]
            Notebook metadata dictionaries.
        """
        results: list[NotebookMetadata] = []

        # Scan filesystem for notebooks
        if self._notebooks_dir.exists():
            for nb_path in sorted(self._notebooks_dir.glob("*.ipynb")):
                name = nb_path.stem
                if name in self._registry:
                    results.append(self._registry[name])
                else:
                    # Parse notebook metadata
                    try:
                        with open(nb_path) as f:
                            nb_data = json.load(f)
                        enthropy_meta = nb_data.get("metadata", {}).get("enthropy", {})
                        meta = NotebookMetadata(
                            name=name,
                            description=enthropy_meta.get("description", ""),
                            author=enthropy_meta.get("author", ""),
                            tags=enthropy_meta.get("tags", []),
                            cell_count=len(nb_data.get("cells", [])),
                            file_path=str(nb_path),
                        )
                        results.append(meta)
                    except (json.JSONDecodeError, KeyError) as exc:
                        logger.warning("Failed to parse notebook %s: %s", nb_path, exc)

        # Include in-memory only entries
        for name, meta in self._registry.items():
            if meta not in results:
                results.append(meta)

        if tags:
            tag_set = set(tags)
            results = [m for m in results if tag_set & set(m.tags)]
        if author:
            results = [m for m in results if m.author == author]

        logger.info("Listed %d notebooks", len(results))
        return [m.to_dict() for m in results]

    def execute_notebook(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
        output_path: str | Path | None = None,
        timeout: int = 600,
    ) -> dict[str, Any]:
        """Execute a notebook programmatically.

        Uses ``papermill`` if available, falling back to ``nbconvert``.
        Parameters can be injected into a tagged parameters cell.

        Parameters
        ----------
        name:
            Notebook name to execute.
        parameters:
            Parameters to inject into the notebook.
        output_path:
            Path for the executed notebook output. Defaults to
            ``<name>_executed.ipynb``.
        timeout:
            Execution timeout in seconds per cell.

        Returns
        -------
        dict[str, Any]
            Execution result with status, duration, and output path.

        Raises
        ------
        FileNotFoundError
            If the notebook is not found.
        """
        source_path = self._notebooks_dir / f"{name}.ipynb"
        if not source_path.exists():
            raise FileNotFoundError(f"Notebook not found: {source_path}")

        if output_path is None:
            output_path = self._notebooks_dir / f"{name}_executed.ipynb"
        output_path = Path(output_path)

        meta = self._registry.get(name)
        if meta:
            meta.execution_status = "running"
            meta.last_executed = datetime.now(tz=UTC)

        start_time = datetime.now(tz=UTC)
        result: dict[str, Any] = {"name": name, "status": "completed"}

        try:
            # Try papermill first for parameterized execution
            import papermill as pm

            pm.execute_notebook(
                str(source_path),
                str(output_path),
                parameters=parameters or {},
                kernel_name="python3",
                request_save_on_cell_execute=True,
            )
        except ImportError:
            # Fall back to nbconvert
            logger.info("papermill not available, falling back to nbconvert")
            cmd = [
                "jupyter", "nbconvert",
                "--to", "notebook",
                "--execute",
                f"--ExecutePreprocessor.timeout={timeout}",
                "--output", str(output_path),
                str(source_path),
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
                if proc.returncode != 0:
                    result["status"] = "failed"
                    result["error"] = proc.stderr
            except subprocess.TimeoutExpired:
                result["status"] = "timeout"
        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
            logger.error("Notebook execution failed for '%s': %s", name, exc)

        duration = (datetime.now(tz=UTC) - start_time).total_seconds()
        result["duration_seconds"] = duration
        result["output_path"] = str(output_path)

        if meta:
            meta.execution_status = result["status"]
            meta.updated_at = datetime.now(tz=UTC)

        logger.info("Executed notebook '%s': %s (%.1fs)", name, result["status"], duration)
        return result

    @staticmethod
    def _make_cell(cell_type: str, source: str) -> dict[str, Any]:
        """Create a Jupyter notebook cell structure."""
        cell: dict[str, Any] = {
            "cell_type": cell_type,
            "source": source,
            "metadata": {},
        }
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        return cell

    @staticmethod
    def _get_template_cells(template: str, name: str) -> list[dict[str, Any]]:
        """Generate template cells for common research patterns."""
        templates: dict[str, list[dict[str, Any]]] = {
            "factor_research": [
                NotebookManager._make_cell("markdown", f"# Factor Research: {name}"),
                NotebookManager._make_cell("code", (
                    "import pandas as pd\n"
                    "import numpy as np\n"
                    "from shared.schemas.market_events import BarEvent\n"
                )),
                NotebookManager._make_cell("markdown", "## Data Loading"),
                NotebookManager._make_cell("code", "# Load price data and compute factor values\n"),
                NotebookManager._make_cell("markdown", "## Factor Analysis"),
                NotebookManager._make_cell("code", "# Compute IC, turnover, and quintile returns\n"),
            ],
            "backtest": [
                NotebookManager._make_cell("markdown", f"# Backtest: {name}"),
                NotebookManager._make_cell("code", (
                    "import pandas as pd\n"
                    "import numpy as np\n"
                )),
                NotebookManager._make_cell("markdown", "## Strategy Definition"),
                NotebookManager._make_cell("code", "# Define entry/exit rules\n"),
                NotebookManager._make_cell("markdown", "## Backtest Execution"),
                NotebookManager._make_cell("code", "# Run backtest and analyze results\n"),
            ],
            "model_training": [
                NotebookManager._make_cell("markdown", f"# Model Training: {name}"),
                NotebookManager._make_cell("code", (
                    "import pandas as pd\n"
                    "import numpy as np\n"
                    "import torch\n"
                    "import mlflow\n"
                )),
                NotebookManager._make_cell("markdown", "## Data Preparation"),
                NotebookManager._make_cell("code", "# Load and preprocess training data\n"),
                NotebookManager._make_cell("markdown", "## Model Architecture"),
                NotebookManager._make_cell("code", "# Define PyTorch model\n"),
                NotebookManager._make_cell("markdown", "## Training Loop"),
                NotebookManager._make_cell("code", "# Train with MLflow tracking\n"),
            ],
        }
        return templates.get(template, [
            NotebookManager._make_cell("markdown", f"# {name}"),
            NotebookManager._make_cell("code", "import pandas as pd\nimport numpy as np\n"),
        ])


__all__ = [
    "NotebookManager",
    "NotebookMetadata",
]
