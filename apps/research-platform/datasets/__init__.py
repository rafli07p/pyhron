"""Dataset Management for the Enthropy Research Platform.

Browse, load, create, and export datasets used in quantitative research.
Supports multiple storage backends and formats including Parquet, CSV,
and in-memory DataFrames.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


@dataclass
class DatasetMetadata:
    """Metadata describing a research dataset."""

    dataset_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    category: str = "general"  # equity, macro, alternative, factor, custom
    format: str = "parquet"
    row_count: int = 0
    column_count: int = 0
    columns: list[str] = field(default_factory=list)
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: list[str] = field(default_factory=list)
    source: str = ""
    tenant_id: str = "default"

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to a dictionary."""
        return {
            "dataset_id": str(self.dataset_id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "format": self.format,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": self.columns,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "source": self.source,
        }


class DatasetManager:
    """Browse, load, create, and export research datasets.

    Manages the lifecycle of research datasets including registration,
    discovery, loading into DataFrames, and exporting to various
    formats. Datasets are organized by category and tagged for
    discoverability.

    Parameters
    ----------
    storage_dir:
        Root directory for dataset storage.
    tenant_id:
        Tenant identifier for multi-tenancy.
    """

    def __init__(
        self,
        storage_dir: str | Path = "~/.enthropy/datasets",
        tenant_id: str = "default",
    ) -> None:
        self._storage_dir = Path(storage_dir).expanduser()
        self._tenant_id = tenant_id
        self._registry: dict[str, DatasetMetadata] = {}
        logger.info("DatasetManager initialized (storage_dir=%s)", self._storage_dir)

    def list_datasets(
        self,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """List available datasets with optional filtering.

        Parameters
        ----------
        category:
            Filter by category (``equity``, ``macro``, ``alternative``).
        tags:
            Filter by tags (any match).

        Returns
        -------
        list[dict[str, Any]]
            Dataset metadata dictionaries.
        """
        results: list[DatasetMetadata] = list(self._registry.values())

        # Also scan storage directory for unregistered datasets
        if self._storage_dir.exists():
            for path in self._storage_dir.rglob("*.parquet"):
                ds_id = path.stem
                if ds_id not in self._registry:
                    meta = DatasetMetadata(
                        name=path.stem,
                        category=path.parent.name if path.parent != self._storage_dir else "general",
                        format="parquet",
                        size_bytes=path.stat().st_size,
                    )
                    results.append(meta)

        if category:
            results = [d for d in results if d.category == category]
        if tags:
            tag_set = set(tags)
            results = [d for d in results if tag_set & set(d.tags)]

        logger.info("Listed %d datasets (category=%s, tags=%s)", len(results), category, tags)
        return [d.to_dict() for d in results]

    def load_dataset(
        self,
        name: str,
        format: str = "dataframe",
        columns: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> Any:
        """Load a dataset into memory.

        Parameters
        ----------
        name:
            Dataset name or ID.
        format:
            Return format: ``dataframe`` (pandas), ``dict``, or ``raw``.
        columns:
            Specific columns to load. ``None`` loads all.
        limit:
            Maximum number of rows to load.

        Returns
        -------
        Any
            Loaded dataset (pandas DataFrame, dict, or raw bytes
            depending on ``format``).

        Raises
        ------
        FileNotFoundError
            If the dataset is not found.
        """
        import pandas as pd

        # Search registry first
        meta = self._registry.get(name)
        file_path: Optional[Path] = None

        if meta:
            file_path = self._storage_dir / f"{name}.parquet"
        else:
            # Search filesystem
            candidates = list(self._storage_dir.rglob(f"{name}.*"))
            if candidates:
                file_path = candidates[0]

        if file_path is None or not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {name}")

        suffix = file_path.suffix.lower()
        if suffix == ".parquet":
            df = pd.read_parquet(file_path, columns=columns)
        elif suffix == ".csv":
            df = pd.read_csv(file_path, usecols=columns)
        else:
            with open(file_path, "rb") as f:
                return f.read()

        if limit is not None:
            df = df.head(limit)

        logger.info("Loaded dataset '%s': %d rows x %d cols", name, len(df), len(df.columns))

        if format == "dict":
            return df.to_dict(orient="records")
        if format == "raw":
            return df.to_parquet()
        return df

    def create_dataset(
        self,
        name: str,
        data: Any,
        description: str = "",
        category: str = "custom",
        tags: Optional[list[str]] = None,
        format: str = "parquet",
    ) -> DatasetMetadata:
        """Create and persist a new dataset.

        Parameters
        ----------
        name:
            Dataset name.
        data:
            Data to store. Accepts pandas DataFrame, list of dicts,
            or raw bytes.
        description:
            Human-readable description.
        category:
            Dataset category for organization.
        tags:
            Tags for discoverability.
        format:
            Storage format (``parquet`` or ``csv``).

        Returns
        -------
        DatasetMetadata
            Metadata for the created dataset.
        """
        import pandas as pd

        self._storage_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")

        if format == "parquet":
            file_path = self._storage_dir / f"{name}.parquet"
            df.to_parquet(file_path, index=False)
        elif format == "csv":
            file_path = self._storage_dir / f"{name}.csv"
            df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        meta = DatasetMetadata(
            name=name,
            description=description,
            category=category,
            format=format,
            row_count=len(df),
            column_count=len(df.columns),
            columns=list(df.columns),
            size_bytes=file_path.stat().st_size,
            tags=tags or [],
            tenant_id=self._tenant_id,
        )
        self._registry[name] = meta
        logger.info("Created dataset '%s': %d rows, %d cols (%s)", name, len(df), len(df.columns), format)
        return meta

    def export_dataset(
        self,
        name: str,
        output_path: str | Path,
        format: str = "csv",
        columns: Optional[list[str]] = None,
    ) -> Path:
        """Export a dataset to a specific format and location.

        Parameters
        ----------
        name:
            Dataset name to export.
        output_path:
            Destination file path.
        format:
            Export format (``csv``, ``parquet``, ``json``).
        columns:
            Specific columns to export. ``None`` exports all.

        Returns
        -------
        Path
            Path to the exported file.
        """
        import pandas as pd

        df = self.load_dataset(name, format="dataframe", columns=columns)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            df.to_csv(output, index=False)
        elif format == "parquet":
            df.to_parquet(output, index=False)
        elif format == "json":
            df.to_json(output, orient="records", indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info("Exported dataset '%s' to %s (%s)", name, output, format)
        return output


__all__ = [
    "DatasetManager",
    "DatasetMetadata",
]
