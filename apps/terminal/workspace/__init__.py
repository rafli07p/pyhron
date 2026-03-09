"""Workspace management for the Enthropy Terminal.

Manages multi-panel layouts with save/load support and per-user settings.
Workspaces define which panels are visible, their positions, and user
preferences for each panel configuration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class PanelConfig:
    """Configuration for a single panel within a workspace."""

    panel_type: str
    position: dict[str, int] = field(default_factory=lambda: {"row": 0, "col": 0, "width": 1, "height": 1})
    settings: dict[str, Any] = field(default_factory=dict)
    visible: bool = True


@dataclass
class WorkspaceConfig:
    """Full workspace configuration including all panels and user settings."""

    workspace_id: UUID = field(default_factory=uuid4)
    name: str = "Default"
    user_id: str = "default"
    panels: list[PanelConfig] = field(default_factory=list)
    grid_columns: int = 12
    grid_rows: int = 8
    theme: str = "dark"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Serialize workspace configuration to a dictionary."""
        return {
            "workspace_id": str(self.workspace_id),
            "name": self.name,
            "user_id": self.user_id,
            "panels": [
                {
                    "panel_type": p.panel_type,
                    "position": p.position,
                    "settings": p.settings,
                    "visible": p.visible,
                }
                for p in self.panels
            ],
            "grid_columns": self.grid_columns,
            "grid_rows": self.grid_rows,
            "theme": self.theme,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceConfig:
        """Deserialize workspace configuration from a dictionary."""
        panels = [
            PanelConfig(
                panel_type=p["panel_type"],
                position=p.get("position", {}),
                settings=p.get("settings", {}),
                visible=p.get("visible", True),
            )
            for p in data.get("panels", [])
        ]
        return cls(
            workspace_id=UUID(data["workspace_id"]) if "workspace_id" in data else uuid4(),
            name=data.get("name", "Default"),
            user_id=data.get("user_id", "default"),
            panels=panels,
            grid_columns=data.get("grid_columns", 12),
            grid_rows=data.get("grid_rows", 8),
            theme=data.get("theme", "dark"),
        )


class WorkspaceManager:
    """Manage multi-panel workspace layouts with per-user persistence.

    Supports creating, loading, saving, and listing workspaces. Each
    workspace is stored as a JSON file keyed by user and workspace ID.

    Parameters
    ----------
    storage_dir:
        Directory for persisting workspace JSON files.
    """

    def __init__(self, storage_dir: str | Path = "~/.enthropy/workspaces") -> None:
        self._storage_dir = Path(storage_dir).expanduser()
        self._workspaces: dict[str, WorkspaceConfig] = {}
        logger.info("WorkspaceManager initialized with storage_dir=%s", self._storage_dir)

    def create_workspace(
        self,
        name: str,
        user_id: str,
        panels: list[PanelConfig] | None = None,
        theme: str = "dark",
    ) -> WorkspaceConfig:
        """Create a new workspace configuration.

        Parameters
        ----------
        name:
            Human-readable workspace name.
        user_id:
            Owner of the workspace.
        panels:
            Initial panel configurations. Defaults to empty.
        theme:
            UI theme (``dark`` or ``light``).

        Returns
        -------
        WorkspaceConfig
            The newly created workspace.
        """
        config = WorkspaceConfig(
            name=name,
            user_id=user_id,
            panels=panels or [],
            theme=theme,
        )
        key = f"{user_id}/{config.workspace_id}"
        self._workspaces[key] = config
        logger.info("Created workspace '%s' for user=%s (id=%s)", name, user_id, config.workspace_id)
        return config

    def load_workspace(self, user_id: str, workspace_id: str) -> WorkspaceConfig:
        """Load a workspace configuration from disk or cache.

        Parameters
        ----------
        user_id:
            Owner of the workspace.
        workspace_id:
            UUID string of the workspace to load.

        Returns
        -------
        WorkspaceConfig
            The loaded workspace.

        Raises
        ------
        FileNotFoundError
            If the workspace file does not exist.
        """
        key = f"{user_id}/{workspace_id}"
        if key in self._workspaces:
            return self._workspaces[key]

        filepath = self._storage_dir / user_id / f"{workspace_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Workspace not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        config = WorkspaceConfig.from_dict(data)
        self._workspaces[key] = config
        logger.info("Loaded workspace '%s' from %s", config.name, filepath)
        return config

    def save_workspace(self, config: WorkspaceConfig) -> Path:
        """Persist a workspace configuration to disk.

        Parameters
        ----------
        config:
            Workspace configuration to save.

        Returns
        -------
        Path
            Path to the saved JSON file.
        """
        user_dir = self._storage_dir / config.user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        filepath = user_dir / f"{config.workspace_id}.json"

        config.updated_at = datetime.utcnow()
        with open(filepath, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

        key = f"{config.user_id}/{config.workspace_id}"
        self._workspaces[key] = config
        logger.info("Saved workspace '%s' to %s", config.name, filepath)
        return filepath

    def list_workspaces(self, user_id: str) -> list[WorkspaceConfig]:
        """List all workspaces belonging to a user.

        Parameters
        ----------
        user_id:
            Owner whose workspaces to list.

        Returns
        -------
        list[WorkspaceConfig]
            All workspace configurations for the user.
        """
        user_dir = self._storage_dir / user_id
        results: list[WorkspaceConfig] = []

        if user_dir.exists():
            for filepath in sorted(user_dir.glob("*.json")):
                with open(filepath) as f:
                    data = json.load(f)
                config = WorkspaceConfig.from_dict(data)
                results.append(config)

        # Include in-memory workspaces not yet persisted
        for key, config in self._workspaces.items():
            if key.startswith(f"{user_id}/") and config not in results:
                results.append(config)

        return results


__all__ = [
    "PanelConfig",
    "WorkspaceConfig",
    "WorkspaceManager",
]
