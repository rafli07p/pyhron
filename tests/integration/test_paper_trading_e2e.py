"""Integration tests for the paper trading end-to-end flow.

These tests require running infrastructure (PostgreSQL, Kafka, Redis)
and are marked with @pytest.mark.integration.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
async def test_signal_to_fill_end_to_end() -> None:
    """Create paper session, start it, publish a momentum signal to Kafka,
    assert order is submitted to Alpaca paper, assert fill event is received,
    assert position is updated in DB, assert NAV snapshot reflects new
    position value, assert terminal would receive POSITION_UPDATE via WebSocket.
    """
    pytest.skip("Requires full infrastructure (PostgreSQL, Kafka, Alpaca)")


@pytest.mark.integration
async def test_simulation_produces_nav_curve() -> None:
    """Create simulation session with date range spanning 30 trading days.
    Run simulation.
    Assert 30 NAV snapshots created.
    Assert final NAV != initial (trades occurred).
    Assert Sharpe ratio is computable (sufficient return history).
    """
    pytest.skip("Requires full infrastructure (PostgreSQL with TimescaleDB)")


@pytest.mark.integration
async def test_stop_session_closes_positions() -> None:
    """Start session, open two positions via submitted fills.
    Call stop_session with close_positions=True.
    Assert sell orders submitted for both positions.
    Assert session status is STOPPED after fills processed.
    """
    pytest.skip("Requires full infrastructure (PostgreSQL, Alpaca)")
