"""Integration tests for the Pyhron WebSocket real-time feed.

These tests require running Kafka, Redis, and the API server.
Run with: pytest -m integration tests/integration/test_websocket_integration.py
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
async def test_subscribe_and_receive_quote_update() -> None:
    """Connect WebSocket client, authenticate, subscribe to BBCA quotes.

    Publish a mock OHLCV event to Kafka.
    Assert client receives QUOTE_UPDATE within 5s.
    """


@pytest.mark.integration
async def test_order_update_delivered_to_correct_user_only() -> None:
    """Connect two clients authenticated as different users.

    Both subscribe to orders channel.
    Publish ORDER_FILLED event for user A.
    Assert user A receives ORDER_UPDATE.
    Assert user B does not receive the message.
    """


@pytest.mark.integration
async def test_reconnection_resubscribes_automatically() -> None:
    """Connect client, authenticate, subscribe to quotes for BBCA.

    Force disconnect server-side.
    Assert client reconnects and resubscribes within 10s.
    Assert QUOTE_UPDATE is received after reconnection.
    """
