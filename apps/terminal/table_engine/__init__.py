"""Table Engine for the Enthropy Terminal.

Data table rendering with sorting, filtering, pagination, and CSV
export capabilities. Used by panels that display tabular data such
as order blotters, position lists, and dataset previews.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ColumnDef:
    """Column definition for a table."""

    key: str
    label: str
    sortable: bool = True
    filterable: bool = True
    width: Optional[int] = None
    align: str = "left"  # left, right, center
    formatter: Optional[Callable[[Any], str]] = None


@dataclass
class TableState:
    """Internal state of a rendered table."""

    columns: list[ColumnDef] = field(default_factory=list)
    data: list[dict[str, Any]] = field(default_factory=list)
    filtered_data: list[dict[str, Any]] = field(default_factory=list)
    sort_key: Optional[str] = None
    sort_ascending: bool = True
    filters: dict[str, Any] = field(default_factory=dict)
    page: int = 0
    page_size: int = 50


class TableEngine:
    """Data table rendering engine with sorting, filtering, and pagination.

    Provides a reusable table engine for displaying structured data with
    column sorting, value-based filtering, pagination, and CSV export.

    Parameters
    ----------
    page_size:
        Default number of rows per page.
    """

    def __init__(self, page_size: int = 50) -> None:
        self._state = TableState(page_size=page_size)
        logger.info("TableEngine initialized (page_size=%d)", page_size)

    @property
    def total_rows(self) -> int:
        """Total number of rows after filtering."""
        return len(self._state.filtered_data)

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        if self._state.page_size <= 0:
            return 1
        return max(1, (self.total_rows + self._state.page_size - 1) // self._state.page_size)

    @property
    def current_page(self) -> int:
        """Current page index (0-based)."""
        return self._state.page

    def create_table(
        self,
        columns: list[dict[str, Any]],
        data: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Create a new table with column definitions.

        Parameters
        ----------
        columns:
            List of column definition dictionaries with keys ``key``,
            ``label``, and optional ``sortable``, ``filterable``, ``width``,
            ``align``.
        data:
            Initial data rows. Can also be set later via ``set_data``.

        Returns
        -------
        dict[str, Any]
            Table metadata including column count and row count.
        """
        self._state.columns = [
            ColumnDef(
                key=c["key"],
                label=c.get("label", c["key"]),
                sortable=c.get("sortable", True),
                filterable=c.get("filterable", True),
                width=c.get("width"),
                align=c.get("align", "left"),
            )
            for c in columns
        ]
        if data is not None:
            self._state.data = list(data)
            self._state.filtered_data = list(data)
        else:
            self._state.data = []
            self._state.filtered_data = []

        self._state.page = 0
        self._state.sort_key = None
        self._state.filters = {}

        logger.info("Created table with %d columns, %d rows", len(self._state.columns), len(self._state.data))
        return {
            "columns": len(self._state.columns),
            "rows": len(self._state.data),
            "page_size": self._state.page_size,
        }

    def set_data(self, data: list[dict[str, Any]]) -> int:
        """Set or replace the table data.

        Parameters
        ----------
        data:
            List of row dictionaries.

        Returns
        -------
        int
            Number of rows loaded.
        """
        self._state.data = list(data)
        self._apply_filters()
        self._apply_sort()
        self._state.page = 0
        logger.info("Set table data: %d rows", len(data))
        return len(data)

    def sort_by(self, column_key: str, ascending: bool = True) -> list[dict[str, Any]]:
        """Sort the table by a column.

        Parameters
        ----------
        column_key:
            Column key to sort by.
        ascending:
            Sort direction. ``True`` for ascending, ``False`` for descending.

        Returns
        -------
        list[dict[str, Any]]
            Current page of sorted data.
        """
        self._state.sort_key = column_key
        self._state.sort_ascending = ascending
        self._apply_sort()
        self._state.page = 0
        logger.info("Sorted by '%s' (%s)", column_key, "asc" if ascending else "desc")
        return self._get_page()

    def filter_by(self, column_key: str, value: Any) -> list[dict[str, Any]]:
        """Filter the table by a column value.

        Parameters
        ----------
        column_key:
            Column key to filter on.
        value:
            Value to match. Use ``None`` to remove the filter for this column.

        Returns
        -------
        list[dict[str, Any]]
            Current page of filtered data.
        """
        if value is None:
            self._state.filters.pop(column_key, None)
        else:
            self._state.filters[column_key] = value

        self._apply_filters()
        self._apply_sort()
        self._state.page = 0
        logger.info("Filter applied: %s=%s (%d rows match)", column_key, value, self.total_rows)
        return self._get_page()

    def get_page(self, page: int = 0) -> list[dict[str, Any]]:
        """Get a specific page of data.

        Parameters
        ----------
        page:
            Page index (0-based).

        Returns
        -------
        list[dict[str, Any]]
            Rows for the requested page.
        """
        self._state.page = max(0, min(page, self.total_pages - 1))
        return self._get_page()

    def export_csv(self) -> str:
        """Export the current filtered/sorted data as CSV.

        Returns
        -------
        str
            CSV-formatted string of all filtered data.
        """
        output = io.StringIO()
        if not self._state.columns:
            return ""

        writer = csv.DictWriter(
            output,
            fieldnames=[c.key for c in self._state.columns],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(self._state.filtered_data)

        csv_string = output.getvalue()
        logger.info("Exported %d rows to CSV (%d bytes)", len(self._state.filtered_data), len(csv_string))
        return csv_string

    def _apply_filters(self) -> None:
        """Apply all active filters to the base data."""
        if not self._state.filters:
            self._state.filtered_data = list(self._state.data)
            return

        result = []
        for row in self._state.data:
            match = True
            for key, value in self._state.filters.items():
                row_val = row.get(key)
                if isinstance(value, str) and isinstance(row_val, str):
                    if value.lower() not in row_val.lower():
                        match = False
                        break
                elif row_val != value:
                    match = False
                    break
            if match:
                result.append(row)

        self._state.filtered_data = result

    def _apply_sort(self) -> None:
        """Apply the current sort to filtered data."""
        if self._state.sort_key is None:
            return

        key = self._state.sort_key
        self._state.filtered_data.sort(
            key=lambda row: (row.get(key) is None, row.get(key, "")),
            reverse=not self._state.sort_ascending,
        )

    def _get_page(self) -> list[dict[str, Any]]:
        """Return rows for the current page."""
        start = self._state.page * self._state.page_size
        end = start + self._state.page_size
        return self._state.filtered_data[start:end]


__all__ = [
    "TableEngine",
    "TableState",
    "ColumnDef",
]
