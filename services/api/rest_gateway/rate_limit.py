"""Shared slowapi Limiter for the Pyhron REST gateway.

Lives in its own module so every route package can decorate endpoints
with ``@limiter.limit(...)`` without creating a circular dependency on
the app factory.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
