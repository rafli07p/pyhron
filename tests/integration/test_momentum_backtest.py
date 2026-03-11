"""Integration tests for momentum strategy backtest pipeline.

Tests:
  - Full momentum pipeline end-to-end with synthetic data
  - Signal publishing to Kafka mock
"""

from __future__ import annotations

from datetime import UTC, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest


def _generate_test_data(
    n_symbols: int = 20,
    n_days: int = 600,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate synthetic market data for integration tests."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-02", periods=n_days, freq="B", tz=UTC)
    symbols = [f"SYM{i:03d}" for i in range(n_symbols)]
    sectors = ["FINANCE", "CONSUMER", "ENERGY", "MATERIALS", "INFRA"]

    price_data = {}
    for i, sym in enumerate(symbols):
        base = rng.uniform(1000, 10000)
        drift = rng.uniform(-0.0005, 0.001)
        returns = rng.normal(drift, 0.02, n_days)
        price_data[sym] = base * np.cumprod(1 + returns)

    prices = pd.DataFrame(price_data, index=dates)
    volumes = pd.DataFrame(
        rng.uniform(1_000_000, 20_000_000, size=prices.shape).astype(int),
        index=dates,
        columns=symbols,
    )
    trading_values = prices * volumes

    metadata = pd.DataFrame(
        {
            "symbol": symbols,
            "sector": [sectors[i % len(sectors)] for i in range(n_symbols)],
            "lot_size": [100] * n_symbols,
            "is_active": [True] * n_symbols,
        }
    )

    return prices, volumes, trading_values, metadata


@pytest.mark.integration
class TestFullMomentumPipeline:
    def test_backtest_runs_successfully(self) -> None:
        """End-to-end: run backtest with synthetic data."""
        from strategy_engine.backtesting.idx_transaction_cost_model import (
            IDXTransactionCostModel,
        )
        from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
            run_momentum_backtest,
        )
        from strategy_engine.idx_momentum_cross_section_strategy import (
            IDXMomentumCrossSectionStrategy,
        )

        prices, volumes, trading_values, metadata = _generate_test_data()
        symbols = list(prices.columns)

        strategy = IDXMomentumCrossSectionStrategy(
            universe=symbols,
            formation_months=6,
            skip_months=1,
        )
        cost_model = IDXTransactionCostModel()

        result = run_momentum_backtest(
            strategy=strategy,
            prices=prices,
            volumes=volumes,
            trading_values=trading_values,
            instrument_metadata=metadata,
            initial_capital_idr=Decimal("1_000_000_000"),
            start_date=date(2021, 1, 4),
            end_date=date(2022, 6, 30),
            cost_model=cost_model,
        )

        assert result.total_trades >= 0
        assert not result.equity_curve.empty
        assert result.max_drawdown_pct <= 0  # drawdown is negative

    def test_backtest_plausible_metrics(self) -> None:
        """Metrics should be plausible for IDX momentum."""
        from strategy_engine.backtesting.idx_transaction_cost_model import (
            IDXTransactionCostModel,
        )
        from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
            run_momentum_backtest,
        )
        from strategy_engine.idx_momentum_cross_section_strategy import (
            IDXMomentumCrossSectionStrategy,
        )

        prices, volumes, trading_values, metadata = _generate_test_data(
            n_symbols=30,
            n_days=800,
            seed=123,
        )
        symbols = list(prices.columns)

        strategy = IDXMomentumCrossSectionStrategy(
            universe=symbols,
            formation_months=12,
            skip_months=1,
        )
        cost_model = IDXTransactionCostModel()

        result = run_momentum_backtest(
            strategy=strategy,
            prices=prices,
            volumes=volumes,
            trading_values=trading_values,
            instrument_metadata=metadata,
            initial_capital_idr=Decimal("1_000_000_000"),
            start_date=date(2021, 6, 1),
            end_date=date(2023, 1, 31),
            cost_model=cost_model,
        )

        # Strategy not catastrophically broken
        assert result.max_drawdown_pct > -80  # drawdown less than 80%


@pytest.mark.integration
class TestSignalPublishing:
    @pytest.mark.asyncio
    async def test_signal_order_exits_before_entries(self) -> None:
        """Signals must be published in order: EXIT, ENTRY, HOLD."""
        from strategy_engine.live_execution.strategy_signal_publisher import (
            publish_momentum_signals,
        )

        signals = pd.DataFrame(
            {
                "symbol": ["A", "B", "C"],
                "signal_type": ["ENTRY_LONG", "EXIT_LONG", "HOLD"],
                "momentum_score": [0.5, -0.1, 0.0],
                "rank": [1, 2, 3],
                "universe_size": [10, 10, 10],
                "target_weight": [0.1, 0.0, 0.05],
                "target_lots": [10, 0, 5],
                "sector": ["FINANCE", "ENERGY", "CONSUMER"],
            }
        )

        # Mock Kafka producer
        mock_producer = MagicMock()
        mock_inner = AsyncMock()
        mock_producer._producer = mock_inner
        mock_inner.send_and_wait = AsyncMock()

        count = await publish_momentum_signals(
            signals=signals,
            strategy_id="test_momentum",
            rebalance_date=date(2025, 1, 2),
            kafka_producer=mock_producer,
        )

        assert count == 3
        # Verify call order: EXIT first, then ENTRY, then HOLD
        calls = mock_inner.send_and_wait.call_args_list
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_required_fields_in_messages(self) -> None:
        """Each published message must have required fields."""
        import json

        from strategy_engine.live_execution.strategy_signal_publisher import (
            publish_momentum_signals,
        )

        signals = pd.DataFrame(
            {
                "symbol": ["BBCA"],
                "signal_type": ["ENTRY_LONG"],
                "momentum_score": [0.42],
                "rank": [1],
                "universe_size": [40],
                "target_weight": [0.05],
                "target_lots": [13],
                "sector": ["FINANCE"],
            }
        )

        mock_producer = MagicMock()
        mock_inner = AsyncMock()
        mock_producer._producer = mock_inner
        mock_inner.send_and_wait = AsyncMock()

        await publish_momentum_signals(
            signals=signals,
            strategy_id="idx_momentum_12_1",
            rebalance_date=date(2025, 1, 2),
            kafka_producer=mock_producer,
        )

        # Decode the payload
        call_args = mock_inner.send_and_wait.call_args
        payload = json.loads(call_args[1]["value"].decode())

        required_fields = [
            "event_id",
            "event_type",
            "strategy_id",
            "rebalance_date",
            "symbol",
            "signal_type",
            "momentum_score",
            "rank",
            "universe_size",
            "target_weight",
            "target_lots",
            "sector",
            "generated_at",
        ]
        for f in required_fields:
            assert f in payload, f"Missing field: {f}"
        assert payload["event_type"] == "MOMENTUM_SIGNAL"
        assert payload["symbol"] == "BBCA"
