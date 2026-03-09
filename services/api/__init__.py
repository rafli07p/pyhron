"""Enthropy API Service.

Provides REST and WebSocket gateways for the Enthropy quant research
platform.  The REST gateway exposes market data, order management,
portfolio, research, risk, and admin endpoints.  The WebSocket gateway
delivers real-time market data, order updates, and portfolio events.
"""

from __future__ import annotations

__all__ = [
    "configure_logging",
    "create_rest_app",
    "create_ws_app",
]


def __getattr__(name: str):
    """Lazy imports to avoid heavy startup cost."""
    if name == "create_rest_app":
        from services.api.rest_gateway import create_rest_app

        return create_rest_app
    if name == "create_ws_app":
        from services.api.websocket_gateway import create_ws_app

        return create_ws_app
    if name == "configure_logging":
        from services.api.logging import configure_logging

        return configure_logging
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
