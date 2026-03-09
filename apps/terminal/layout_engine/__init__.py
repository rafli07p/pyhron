"""Layout Engine for the Enthropy Terminal.

Grid-based panel layout management system. Handles panel placement,
sizing, and serialization of layout configurations for workspace
persistence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class PanelSlot:
    """A panel's position and size within the layout grid."""

    panel_id: UUID = field(default_factory=uuid4)
    panel_type: str = ""
    row: int = 0
    col: int = 0
    width: int = 1
    height: int = 1
    min_width: int = 1
    min_height: int = 1
    visible: bool = True
    z_index: int = 0

    def overlaps(self, other: PanelSlot) -> bool:
        """Check if this slot overlaps with another."""
        return not (
            self.col + self.width <= other.col
            or other.col + other.width <= self.col
            or self.row + self.height <= other.row
            or other.row + other.height <= self.row
        )


@dataclass
class LayoutConfig:
    """Complete layout configuration with all panel slots."""

    layout_id: UUID = field(default_factory=uuid4)
    name: str = "Default"
    columns: int = 12
    rows: int = 8
    gap: int = 4
    panels: list[PanelSlot] = field(default_factory=list)


class LayoutEngine:
    """Grid-based panel layout management.

    Manages the placement, sizing, and arrangement of panels within a
    grid layout. Supports collision detection, panel resizing, and
    layout serialization for persistence.

    Parameters
    ----------
    columns:
        Number of grid columns. Defaults to 12.
    rows:
        Number of grid rows. Defaults to 8.
    """

    def __init__(self, columns: int = 12, rows: int = 8) -> None:
        self._columns = columns
        self._rows = rows
        self._layout = LayoutConfig(columns=columns, rows=rows)
        logger.info("LayoutEngine initialized (%dx%d grid)", columns, rows)

    @property
    def panel_count(self) -> int:
        """Number of panels in the current layout."""
        return len(self._layout.panels)

    def create_layout(
        self,
        name: str = "Default",
        columns: int | None = None,
        rows: int | None = None,
    ) -> LayoutConfig:
        """Create a new empty layout.

        Parameters
        ----------
        name:
            Layout name.
        columns:
            Grid columns (uses engine default if not specified).
        rows:
            Grid rows (uses engine default if not specified).

        Returns
        -------
        LayoutConfig
            The newly created layout.
        """
        self._layout = LayoutConfig(
            name=name,
            columns=columns or self._columns,
            rows=rows or self._rows,
        )
        logger.info("Created layout '%s' (%dx%d)", name, self._layout.columns, self._layout.rows)
        return self._layout

    def add_panel(
        self,
        panel_type: str,
        row: int = 0,
        col: int = 0,
        width: int = 3,
        height: int = 2,
        min_width: int = 1,
        min_height: int = 1,
    ) -> PanelSlot:
        """Add a panel to the layout at the specified grid position.

        Parameters
        ----------
        panel_type:
            Type identifier (e.g., ``chart``, ``orderbook``, ``execution``).
        row:
            Starting row in the grid.
        col:
            Starting column in the grid.
        width:
            Width in grid columns.
        height:
            Height in grid rows.
        min_width:
            Minimum allowed width for resizing.
        min_height:
            Minimum allowed height for resizing.

        Returns
        -------
        PanelSlot
            The created panel slot.

        Raises
        ------
        ValueError
            If the panel position is out of bounds or overlaps existing panels.
        """
        if col + width > self._layout.columns or row + height > self._layout.rows:
            raise ValueError(
                f"Panel ({row},{col}) size ({width}x{height}) exceeds grid "
                f"({self._layout.rows}x{self._layout.columns})"
            )

        slot = PanelSlot(
            panel_type=panel_type,
            row=row,
            col=col,
            width=width,
            height=height,
            min_width=min_width,
            min_height=min_height,
        )

        for existing in self._layout.panels:
            if existing.visible and slot.overlaps(existing):
                raise ValueError(
                    f"Panel at ({row},{col}) overlaps with '{existing.panel_type}' "
                    f"at ({existing.row},{existing.col})"
                )

        self._layout.panels.append(slot)
        logger.info("Added panel '%s' at (%d,%d) size %dx%d", panel_type, row, col, width, height)
        return slot

    def resize_panel(
        self,
        panel_id: UUID,
        width: int | None = None,
        height: int | None = None,
    ) -> PanelSlot:
        """Resize an existing panel.

        Parameters
        ----------
        panel_id:
            UUID of the panel to resize.
        width:
            New width in grid columns.
        height:
            New height in grid rows.

        Returns
        -------
        PanelSlot
            The updated panel slot.

        Raises
        ------
        KeyError
            If the panel is not found.
        ValueError
            If the new size violates constraints or causes overlaps.
        """
        slot = self._find_panel(panel_id)
        new_width = width if width is not None else slot.width
        new_height = height if height is not None else slot.height

        if new_width < slot.min_width or new_height < slot.min_height:
            raise ValueError(
                f"Size ({new_width}x{new_height}) is below minimum "
                f"({slot.min_width}x{slot.min_height})"
            )

        if slot.col + new_width > self._layout.columns or slot.row + new_height > self._layout.rows:
            raise ValueError(
                f"Resized panel exceeds grid bounds "
                f"({self._layout.rows}x{self._layout.columns})"
            )

        old_width, old_height = slot.width, slot.height
        slot.width = new_width
        slot.height = new_height

        for other in self._layout.panels:
            if other.panel_id != panel_id and other.visible and slot.overlaps(other):
                slot.width, slot.height = old_width, old_height
                raise ValueError(f"Resize causes overlap with '{other.panel_type}'")

        logger.info("Resized panel %s to %dx%d", panel_id, new_width, new_height)
        return slot

    def serialize_layout(self) -> dict[str, Any]:
        """Serialize the current layout to a dictionary.

        Returns
        -------
        dict[str, Any]
            Serialized layout configuration.
        """
        return {
            "layout_id": str(self._layout.layout_id),
            "name": self._layout.name,
            "columns": self._layout.columns,
            "rows": self._layout.rows,
            "gap": self._layout.gap,
            "panels": [
                {
                    "panel_id": str(p.panel_id),
                    "panel_type": p.panel_type,
                    "row": p.row,
                    "col": p.col,
                    "width": p.width,
                    "height": p.height,
                    "visible": p.visible,
                    "z_index": p.z_index,
                }
                for p in self._layout.panels
            ],
        }

    def deserialize_layout(self, data: dict[str, Any]) -> LayoutConfig:
        """Load a layout from a serialized dictionary.

        Parameters
        ----------
        data:
            Serialized layout data.

        Returns
        -------
        LayoutConfig
            The restored layout configuration.
        """
        self._layout = LayoutConfig(
            layout_id=UUID(data["layout_id"]) if "layout_id" in data else uuid4(),
            name=data.get("name", "Default"),
            columns=data.get("columns", self._columns),
            rows=data.get("rows", self._rows),
            gap=data.get("gap", 4),
            panels=[
                PanelSlot(
                    panel_id=UUID(p["panel_id"]) if "panel_id" in p else uuid4(),
                    panel_type=p.get("panel_type", ""),
                    row=p.get("row", 0),
                    col=p.get("col", 0),
                    width=p.get("width", 1),
                    height=p.get("height", 1),
                    visible=p.get("visible", True),
                    z_index=p.get("z_index", 0),
                )
                for p in data.get("panels", [])
            ],
        )
        return self._layout

    def _find_panel(self, panel_id: UUID) -> PanelSlot:
        """Find a panel by its UUID."""
        for panel in self._layout.panels:
            if panel.panel_id == panel_id:
                return panel
        raise KeyError(f"Panel not found: {panel_id}")


__all__ = [
    "LayoutConfig",
    "LayoutEngine",
    "PanelSlot",
]
