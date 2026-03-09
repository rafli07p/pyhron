"""Backward-compatibility shim.

Re-exports ``get_config`` from :mod:`shared.configuration_settings` as
``get_settings`` so existing imports continue to work.
"""

from shared.configuration_settings import Config as Settings
from shared.configuration_settings import get_config as get_settings

__all__ = ["Settings", "get_settings"]
