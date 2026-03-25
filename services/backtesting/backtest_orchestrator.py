"""Backtest orchestration service.

Connects the strategy engine, historical data loading, and result
persistence to run backtests end-to-end. Used by both the CLI script
and the REST API.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from sqlalchemy import text

from data_platform.database_models.backtest_run import BacktestRun, BacktestStatus
from shared.structured_json_logger import get_logger
from strategy_engine.backtesting.idx_transaction_cost_model import IDXTransactionCostModel
from strategy_engine.backtesting.idx_vectorbt_backtest_engine import (
    BacktestResult,
    run_momentum_backtest,
)
from strategy_engine.idx_momentum_cross_section_strategy import (
    IDXMomentumCrossSectionStrategy,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Strategies available for backtesting
STRATEGY_REGISTRY: dict[str, type] = {
    "momentum": IDXMomentumCrossSectionStrategy,
}


async def load_ohlcv_from_db(
    db_session: AsyncSession,
    symbols: list[str],
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load OHLCV data from TimescaleDB and return (prices, volumes, trading_values).

    Returns DataFrames with DatetimeIndex and symbol columns.
    """
    placeholders = ", ".join(f":sym_{i}" for i in range(len(symbols)))
    query = text(f"""
        SELECT time, symbol, open, high, low, close, volume,
               close * volume AS trading_value
        FROM market_data.idx_equity_ohlcv_tick
        WHERE symbol IN ({placeholders})
          AND time >= :start_date
          AND time <= :end_date
        ORDER BY time ASC, symbol ASC
    """)

    params: dict[str, Any] = {"start_date": start_date, "end_date": end_date}
    for i, sym in enumerate(symbols):
        params[f"sym_{i}"] = sym
    result = await db_session.execute(query, params)
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = pd.DataFrame(rows, columns=["time", "symbol", "open", "high", "low", "close", "volume", "trading_value"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time")

    prices = df.pivot_table(values="close", index=df.index, columns="symbol")
    volumes = df.pivot_table(values="volume", index=df.index, columns="symbol")
    trading_values = df.pivot_table(values="trading_value", index=df.index, columns="symbol")

    return prices.ffill(), volumes.fillna(0), trading_values.fillna(0)


async def load_instrument_metadata(
    db_session: AsyncSession,
    symbols: list[str],
) -> pd.DataFrame:
    """Load instrument metadata from the database."""
    placeholders = ", ".join(f":sym_{i}" for i in range(len(symbols)))
    query = text(f"""
        SELECT symbol, sector, lot_size, is_active
        FROM market_data.idx_equity_instrument
        WHERE symbol IN ({placeholders})
    """)  # noqa: S608
    params = {f"sym_{i}": sym for i, sym in enumerate(symbols)}
    result = await db_session.execute(query, params)
    rows = result.fetchall()

    if rows:
        return pd.DataFrame(rows, columns=["symbol", "sector", "lot_size", "is_active"])

    # Fallback: create default metadata
    return pd.DataFrame(
        {
            "symbol": symbols,
            "sector": ["Unknown"] * len(symbols),
            "lot_size": [100] * len(symbols),
            "is_active": [True] * len(symbols),
        }
    )


async def run_backtest(
    strategy_type: str,
    symbols: list[str],
    start_date: date,
    end_date: date,
    initial_capital_idr: Decimal,
    strategy_params: dict[str, Any] | None = None,
    slippage_bps: float = 5.0,
    db_session: AsyncSession | None = None,
) -> BacktestResult:
    """Run a backtest using historical data from the database.

    Parameters
    ----------
    strategy_type:
        Strategy name from STRATEGY_REGISTRY (e.g. "momentum").
    symbols:
        List of ticker symbols.
    start_date, end_date:
        Backtest date range.
    initial_capital_idr:
        Starting capital in IDR.
    strategy_params:
        Optional strategy-specific parameters.
    slippage_bps:
        Slippage in basis points.
    db_session:
        Database session for loading historical data. If None, uses
        synthetic data for testing.
    """
    if strategy_type not in STRATEGY_REGISTRY:
        msg = f"Unknown strategy: {strategy_type}. Available: {list(STRATEGY_REGISTRY.keys())}"
        raise ValueError(msg)

    # Initialize strategy
    params = strategy_params or {}
    strategy = IDXMomentumCrossSectionStrategy(
        universe=symbols,
        **{
            k: v
            for k, v in params.items()
            if k
            in {
                "formation_months",
                "skip_months",
                "holding_months",
                "top_pct",
                "max_position_pct",
                "max_sector_concentration",
            }
        },
    )

    cost_model = IDXTransactionCostModel(slippage_bps=slippage_bps)

    # Load data
    if db_session is not None:
        # Extend start date back for formation period lookback
        lookback_start = date(
            start_date.year - 2,
            start_date.month,
            start_date.day,
        )
        prices, volumes, trading_values = await load_ohlcv_from_db(
            db_session,
            symbols,
            lookback_start,
            end_date,
        )
        metadata = await load_instrument_metadata(db_session, symbols)
    else:
        # Generate synthetic data for testing
        prices, volumes, trading_values, metadata = _generate_synthetic_data(
            symbols,
            start_date,
            end_date,
        )

    if prices.empty:
        msg = "No historical data available for the specified symbols and date range"
        raise ValueError(msg)

    logger.info(
        "backtest_data_loaded",
        symbols=len(symbols),
        rows=len(prices),
        date_range=f"{prices.index[0]} to {prices.index[-1]}",
    )

    # Run the backtest
    result = run_momentum_backtest(
        strategy=strategy,
        prices=prices,
        volumes=volumes,
        trading_values=trading_values,
        instrument_metadata=metadata,
        initial_capital_idr=initial_capital_idr,
        start_date=start_date,
        end_date=end_date,
        cost_model=cost_model,
    )

    logger.info(
        "backtest_complete",
        strategy=result.strategy_name,
        total_return_pct=round(result.total_return_pct, 2),
        sharpe=round(result.sharpe_ratio, 4),
        max_dd=round(result.max_drawdown_pct, 2),
        trades=result.total_trades,
    )

    return result


async def persist_backtest_result(
    result: BacktestResult,
    strategy_id: str,
    user_id: str,
    db_session: AsyncSession,
) -> BacktestRun:
    """Save a backtest result to the database."""
    final_capital = result.initial_capital_idr * Decimal(str(1 + result.total_return_pct / 100))

    run = BacktestRun(
        strategy_id=uuid.UUID(strategy_id),
        user_id=uuid.UUID(user_id),
        status=BacktestStatus.COMPLETED,
        start_date=result.start_date,
        end_date=result.end_date,
        initial_capital_idr=result.initial_capital_idr,
        final_capital_idr=final_capital,
        total_return_pct=Decimal(str(round(result.total_return_pct, 4))),
        cagr_pct=Decimal(str(round(result.cagr_pct, 4))),
        sharpe_ratio=Decimal(str(round(result.sharpe_ratio, 4))),
        sortino_ratio=Decimal(str(round(result.sortino_ratio, 4))),
        calmar_ratio=Decimal(str(round(result.calmar_ratio, 4))),
        max_drawdown_pct=Decimal(str(round(result.max_drawdown_pct, 4))),
        max_drawdown_duration_days=result.max_drawdown_duration_days,
        total_trades=result.total_trades,
        win_rate_pct=Decimal(str(round(result.win_rate_pct, 4))),
        profit_factor=Decimal(str(round(result.profit_factor, 4))),
        omega_ratio=Decimal(str(round(result.omega_ratio, 4))),
        parameters_snapshot={
            "strategy_name": result.strategy_name,
            "initial_capital_idr": str(result.initial_capital_idr),
        },
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    db_session.add(run)
    await db_session.flush()

    logger.info(
        "backtest_result_persisted",
        backtest_id=str(run.id),
        total_return_pct=float(run.total_return_pct or 0),
    )
    return run


def _generate_synthetic_data(
    symbols: list[str],
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate synthetic market data for testing without a database."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range(
        start=date(start_date.year - 2, start_date.month, start_date.day),
        end=end_date,
        freq="B",
    )
    dates = dates.tz_localize("UTC")

    # Generate realistic IDX prices (1000-50000 IDR range)
    base_prices = rng.integers(2000, 15000, size=len(symbols)).astype(float)
    daily_returns = rng.normal(0.0005, 0.02, size=(len(dates), len(symbols)))
    cum_returns = np.cumprod(1 + daily_returns, axis=0)

    prices_data = cum_returns * base_prices
    prices = pd.DataFrame(prices_data, index=dates, columns=symbols)

    # Volumes: 1M-50M shares typical for IDX
    volumes_data = rng.integers(500_000, 20_000_000, size=(len(dates), len(symbols)))
    volumes = pd.DataFrame(volumes_data, index=dates, columns=symbols)

    # Trading values
    trading_values = prices * volumes

    metadata = pd.DataFrame(
        {
            "symbol": symbols,
            "sector": rng.choice(
                ["Financials", "Consumer", "Energy", "Telecom", "Infrastructure"],
                size=len(symbols),
            ),
            "lot_size": [100] * len(symbols),
            "is_active": [True] * len(symbols),
        }
    )

    return prices, volumes, trading_values, metadata


def format_result_summary(result: BacktestResult) -> str:
    """Format a backtest result as a human-readable summary."""
    lines = [
        "",
        "=" * 60,
        f"  Backtest Results: {result.strategy_name}",
        "=" * 60,
        f"  Period:           {result.start_date} to {result.end_date}",
        f"  Initial Capital:  IDR {result.initial_capital_idr:,.0f}",
        "",
        "  -- Returns --",
        f"  Total Return:     {result.total_return_pct:+.2f}%",
        f"  CAGR:             {result.cagr_pct:+.2f}%",
        "",
        "  -- Risk-Adjusted --",
        f"  Sharpe Ratio:     {result.sharpe_ratio:.4f}",
        f"  Sortino Ratio:    {result.sortino_ratio:.4f}",
        f"  Calmar Ratio:     {result.calmar_ratio:.4f}",
        f"  Omega Ratio:      {result.omega_ratio:.4f}",
        "",
        "  -- Drawdown --",
        f"  Max Drawdown:     {result.max_drawdown_pct:.2f}%",
        f"  Max DD Duration:  {result.max_drawdown_duration_days} days",
        f"  Avg Drawdown:     {result.avg_drawdown_pct:.2f}%",
        "",
        "  -- Trading Activity --",
        f"  Total Trades:     {result.total_trades}",
        f"  Win Rate:         {result.win_rate_pct:.1f}%",
        f"  Profit Factor:    {result.profit_factor:.2f}",
        f"  Avg Trades/Month: {result.avg_trades_per_month:.1f}",
        "",
        "  -- Costs --",
        f"  Commission Paid:  IDR {result.total_commission_paid_idr:,.0f}",
        f"  Levy Paid:        IDR {result.total_levy_paid_idr:,.0f}",
        f"  Cost Drag (ann.): {result.cost_drag_annualized_pct:.2f}%",
        "",
        "  -- Benchmark (IHSG) --",
        f"  Benchmark Return: {result.benchmark_total_return_pct:+.2f}%",
        f"  Alpha (ann.):     {result.alpha_annualized_pct:+.2f}%",
        f"  Beta:             {result.beta:.4f}",
        f"  Information Ratio:{result.information_ratio:.4f}",
        "=" * 60,
    ]
    return "\n".join(lines)
