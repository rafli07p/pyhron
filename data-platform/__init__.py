"""
Enthropy Data Platform
======================

Bloomberg-style quant trading data infrastructure providing tick
storage, historical bars, corporate actions, news ingestion, dataset
cataloging, backup management, and encryption services.

All modules enforce multi-tenant isolation via ``tenant_id``.

Note: Sub-packages use hyphenated directory names (e.g. ``tick-storage/``).
Python cannot import hyphenated names directly, so this root ``__init__``
uses ``importlib`` to bridge the gap transparently.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import helper for hyphenated sub-package directories
# ---------------------------------------------------------------------------
_PACKAGE_DIR = Path(__file__).resolve().parent

_MODULE_MAP = {
    "encryption": "encryption",
    "tick_storage": "tick-storage",
    "historical_storage": "historical-storage",
    "dataset_index": "dataset-index",
    "corporate_actions": "corporate-actions",
    "news_ingestion": "news-ingestion",
    "backup": "backup",
}


def _import_subpackage(python_name: str):
    """Import a sub-package whose directory is hyphenated."""
    dir_name = _MODULE_MAP[python_name]
    full_path = _PACKAGE_DIR / dir_name / "__init__.py"

    spec = importlib.util.spec_from_file_location(
        f"data_platform.{python_name}",
        str(full_path),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Lazy-load and re-export
# ---------------------------------------------------------------------------

_encryption = _import_subpackage("encryption")
_tick_storage = _import_subpackage("tick_storage")
_historical_storage = _import_subpackage("historical_storage")
_dataset_index = _import_subpackage("dataset_index")
_corporate_actions = _import_subpackage("corporate_actions")
_news_ingestion = _import_subpackage("news_ingestion")
_backup = _import_subpackage("backup")

# Encryption
EncryptionService = _encryption.EncryptionService
EncryptionError = _encryption.EncryptionError
KeyManagementError = _encryption.KeyManagementError

# Tick storage
Tick = _tick_storage.Tick
TickStorageEngine = _tick_storage.TickStorageEngine

# Historical storage
Base = _historical_storage.Base
OHLCVRecord = _historical_storage.OHLCVRecord
TradeRecord = _historical_storage.TradeRecord
CorporateAction = _historical_storage.CorporateAction
HistoricalStorageEngine = _historical_storage.HistoricalStorageEngine

# Dataset index
DatasetIndex = _dataset_index.DatasetIndex
DatasetMetadata = _dataset_index.DatasetMetadata

# Corporate actions
CorporateActionsEngine = _corporate_actions.CorporateActionsEngine

# News ingestion
NewsIngestionEngine = _news_ingestion.NewsIngestionEngine
NewsArticle = _news_ingestion.NewsArticle

# Backup
BackupManager = _backup.BackupManager
BackupError = _backup.BackupError

__all__ = [
    # Encryption
    "EncryptionService",
    "EncryptionError",
    "KeyManagementError",
    # Tick storage
    "Tick",
    "TickStorageEngine",
    # Historical storage
    "Base",
    "OHLCVRecord",
    "TradeRecord",
    "CorporateAction",
    "HistoricalStorageEngine",
    # Dataset index
    "DatasetIndex",
    "DatasetMetadata",
    # Corporate actions
    "CorporateActionsEngine",
    # News ingestion
    "NewsIngestionEngine",
    "NewsArticle",
    # Backup
    "BackupManager",
    "BackupError",
]
