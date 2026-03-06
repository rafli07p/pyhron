"""Enthropy Strategy Runtime.

Orchestrates the full strategy lifecycle in live or paper trading
mode.  Receives market data, generates alpha signals, constructs
portfolios, and submits orders to the execution service.  Provides
start/stop control, performance monitoring, and connects all
strategy components.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional
from uuid import UUID, uuid4

import numpy as np
import pandas as pd
import structlog

from shared.schemas.order_events import OrderFill, OrderRequest, OrderSide, OrderType, TimeInForce
from strategies.alpha_models import BaseAlphaModel
from strategies.portfolio_construction import PortfolioAllocation, PortfolioConstructor, PortfolioConstraints
from strategies.signal_generation import SignalGenerator

logger = structlog.stdlib.get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums & data structures
# ---------------------------------------------------------------------------

class RuntimeMode(StrEnum):
    LIVE = "live"
    PAPER = "paper"


class RuntimeStatus(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class PerformanceMetrics:
    """Running performance statistics for the strategy."""

    start_time: Optional[datetime] = None
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_volume: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    signals_generated: int = 0
    orders_submitted: int = 0
    fills_received: int = 0
    errors: int = 0
    _equity_curve: list[float] = field(default_factory=list)
    _peak_equity: float = 0.0

    def record_equity(self, equity: float) -> None:
        self._equity_curve.append(equity)
        if equity > self._peak_equity:
            self._peak_equity = equity
        if self._peak_equity > 0:
            dd = (self._peak_equity - equity) / self._peak_equity
            if dd > self.max_drawdown:
                self.max_drawdown = dd

    def compute_sharpe(self, risk_free_rate: float = 0.05) -> float:
        if len(self._equity_curve) < 2:
            return 0.0
        returns = np.diff(self._equity_curve) / (np.array(self._equity_curve[:-1]) + 1e-12)
        if len(returns) == 0 or np.std(returns) < 1e-12:
            return 0.0
        daily_rf = risk_free_rate / 252
        self.sharpe_ratio = float(
            (np.mean(returns) - daily_rf) / np.std(returns, ddof=1) * np.sqrt(252)
        )
        return self.sharpe_ratio

    @property
    def win_rate(self) -> float:
        total = self.winning_trades + self.losing_trades
        return self.winning_trades / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "total_pnl": self.total_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "signals_generated": self.signals_generated,
            "orders_submitted": self.orders_submitted,
            "fills_received": self.fills_received,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Strategy runtime
# ---------------------------------------------------------------------------

class StrategyRuntime:
    """Run a complete strategy pipeline in live or paper mode.

    Connects alpha models, signal generation, portfolio construction,
    and order execution into a cohesive event-driven loop.

    Parameters
    ----------
    strategy_id:
        Unique identifier for this strategy instance.
    tenant_id:
        Tenant owning this strategy.
    mode:
        ``"live"`` or ``"paper"``.
    universe:
        List of symbols to trade.
    alpha_models:
        List of ``(model, weight)`` tuples for signal generation.
    portfolio_constructor:
        ``PortfolioConstructor`` instance (or None to use defaults).
    initial_capital:
        Starting capital for the strategy.
    rebalance_interval_seconds:
        How often to recompute signals and rebalance (default 300 = 5min).
    """

    def __init__(
        self,
        strategy_id: str,
        tenant_id: str,
        mode: RuntimeMode = RuntimeMode.PAPER,
        universe: Optional[list[str]] = None,
        alpha_models: Optional[list[tuple[BaseAlphaModel, float]]] = None,
        portfolio_constructor: Optional[PortfolioConstructor] = None,
        initial_capital: float = 1_000_000.0,
        rebalance_interval_seconds: int = 300,
    ) -> None:
        self.strategy_id = strategy_id
        self.tenant_id = tenant_id
        self.mode = mode
        self.universe = universe or []
        self.initial_capital = initial_capital
        self.rebalance_interval_seconds = rebalance_interval_seconds

        # Components
        self.signal_generator = SignalGenerator(models=alpha_models)
        self.portfolio_constructor = portfolio_constructor or PortfolioConstructor()

        # State
        self._status = RuntimeStatus.STOPPED
        self._task: Optional[asyncio.Task[None]] = None
        self._market_data: dict[str, pd.DataFrame] = {}
        self._current_weights: dict[str, float] = {}
        self._current_positions: dict[str, float] = {}  # symbol -> qty
        self._pending_orders: dict[UUID, dict[str, Any]] = {}
        self.metrics = PerformanceMetrics()
        self._equity = initial_capital
        self._stop_event = asyncio.Event()

        self._log = logger.bind(strategy_id=strategy_id, tenant_id=tenant_id, mode=mode)

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Start the strategy runtime event loop."""
        if self._status == RuntimeStatus.RUNNING:
            self._log.warning("already_running")
            return

        self._status = RuntimeStatus.STARTING
        self._stop_event.clear()
        self.metrics.start_time = datetime.now(tz=timezone.utc)

        self._log.info("strategy_starting", universe=self.universe)

        # Start market data feed
        self._task = asyncio.create_task(self._run_loop())
        self._status = RuntimeStatus.RUNNING
        self._log.info("strategy_running")

    async def stop(self) -> None:
        """Gracefully stop the strategy runtime."""
        if self._status not in (RuntimeStatus.RUNNING, RuntimeStatus.STARTING):
            return

        self._status = RuntimeStatus.STOPPING
        self._stop_event.set()
        self._log.info("strategy_stopping")

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.metrics.compute_sharpe()
        self._status = RuntimeStatus.STOPPED
        self._log.info("strategy_stopped", metrics=self.metrics.to_dict())

    def get_status(self) -> dict[str, Any]:
        """Return current runtime status and performance metrics."""
        return {
            "strategy_id": self.strategy_id,
            "tenant_id": self.tenant_id,
            "mode": self.mode,
            "status": self._status,
            "universe": self.universe,
            "current_weights": self._current_weights,
            "positions": self._current_positions,
            "equity": self._equity,
            "metrics": self.metrics.to_dict(),
        }

    # -- event handlers ------------------------------------------------------

    async def on_market_data(self, symbol: str, data: pd.DataFrame) -> None:
        """Handle incoming market data update for a symbol.

        Called by the market data streaming service when new bars or
        ticks arrive.  Updates internal state and may trigger a
        rebalance if the rebalance interval has elapsed.
        """
        self._market_data[symbol] = data
        self._log.debug("market_data_received", symbol=symbol, rows=len(data))

    async def on_fill(self, fill: OrderFill) -> None:
        """Handle an order fill event from the execution service.

        Updates positions, P&L, and performance metrics.
        """
        symbol = fill.symbol
        side_mult = 1.0 if fill.side.value == "BUY" else -1.0
        fill_qty = float(fill.fill_qty) * side_mult
        fill_price = float(fill.fill_price)

        prev_qty = self._current_positions.get(symbol, 0.0)
        new_qty = prev_qty + fill_qty
        self._current_positions[symbol] = new_qty

        # Simplified P&L tracking
        cost = abs(float(fill.fill_qty)) * fill_price
        self.metrics.fills_received += 1
        self.metrics.total_trades += 1
        self.metrics.total_volume += cost

        # Track wins/losses based on fill direction vs position
        if abs(new_qty) < abs(prev_qty):
            # Reducing position — realised PnL would be computed here
            self.metrics.winning_trades += 1  # placeholder
        else:
            self.metrics.losing_trades += 0  # placeholder

        self._log.info(
            "fill_processed",
            symbol=symbol,
            fill_qty=str(fill.fill_qty),
            fill_price=str(fill.fill_price),
            position=new_qty,
        )

    # -- main loop -----------------------------------------------------------

    async def _run_loop(self) -> None:
        """Core event loop: fetch data -> signals -> portfolio -> execute."""
        while not self._stop_event.is_set():
            cycle_start = time.perf_counter()
            try:
                # 1. Fetch / update market data
                await self._fetch_market_data()

                # 2. Generate signals
                signals = self._generate_signals()
                self.metrics.signals_generated += len(signals)

                # 3. Construct portfolio
                if signals:
                    allocation = self._construct_portfolio(signals)
                    self._current_weights = allocation.weights

                    # 4. Generate and submit orders
                    await self._execute_rebalance(allocation)

                # 5. Update equity and metrics
                self._update_equity()
                self.metrics.record_equity(self._equity)

                elapsed = time.perf_counter() - cycle_start
                self._log.info(
                    "strategy_cycle_complete",
                    elapsed_ms=round(elapsed * 1000, 2),
                    signals=len(signals) if signals else 0,
                    equity=self._equity,
                )

            except asyncio.CancelledError:
                raise
            except Exception:
                self.metrics.errors += 1
                self._log.exception("strategy_cycle_error")

            # Wait for next rebalance
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.rebalance_interval_seconds,
                )
                break  # stop_event was set
            except asyncio.TimeoutError:
                continue

    async def _fetch_market_data(self) -> None:
        """Fetch latest OHLCV data for all universe symbols.

        Uses yfinance for historical data in paper mode, or Polygon
        REST API in live mode.
        """
        import os

        for symbol in self.universe:
            try:
                if self.mode == RuntimeMode.LIVE:
                    polygon_key = os.environ.get("POLYGON_API_KEY", "")
                    if polygon_key:
                        import httpx

                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await client.get(
                                f"https://api.polygon.io/v2/aggs/ticker/{symbol}"
                                f"/range/1/day/{_days_ago(60)}/{_today()}",
                                params={"adjusted": "true", "sort": "asc", "limit": 60, "apiKey": polygon_key},
                            )
                            if resp.status_code == 200:
                                results = resp.json().get("results", [])
                                if results:
                                    df = pd.DataFrame(results).rename(columns={
                                        "o": "open", "h": "high", "l": "low",
                                        "c": "close", "v": "volume", "t": "timestamp",
                                    })
                                    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
                                    df = df.set_index("date")
                                    self._market_data[symbol] = df
                                    continue

                # Fallback / paper mode: yfinance
                import yfinance as yf

                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="3mo", interval="1d")
                if not hist.empty:
                    hist.columns = [c.lower() for c in hist.columns]
                    self._market_data[symbol] = hist

            except Exception:
                self._log.exception("market_data_fetch_error", symbol=symbol)

    def _generate_signals(self) -> dict[str, float]:
        """Run signal generator across the universe."""
        if not self._market_data:
            return {}

        composite_signals = self.signal_generator.generate_signals(
            symbols=self.universe,
            data=self._market_data,
        )
        return {s.symbol: s.composite_score for s in composite_signals}

    def _construct_portfolio(self, signals: dict[str, float]) -> PortfolioAllocation:
        """Run portfolio optimisation on current signals."""
        # Build returns DataFrame from market data
        returns_data: dict[str, pd.Series] = {}
        for symbol in signals:
            df = self._market_data.get(symbol)
            if df is not None and "close" in df.columns and len(df) > 1:
                returns_data[symbol] = df["close"].astype(float).pct_change().dropna()

        if not returns_data:
            return self.portfolio_constructor.equal_weight(list(signals.keys()))

        returns_df = pd.DataFrame(returns_data).dropna()
        if len(returns_df) < 5:
            return self.portfolio_constructor.equal_weight(list(signals.keys()))

        try:
            allocation = self.portfolio_constructor.optimize_portfolio(
                signals=signals,
                returns=returns_df,
                current_weights=self._current_weights,
            )
        except Exception:
            self._log.exception("portfolio_optimization_fallback")
            allocation = self.portfolio_constructor.equal_weight(list(signals.keys()))

        # Apply sector constraints
        allocation = PortfolioAllocation(
            weights=self.portfolio_constructor.apply_sector_constraints(allocation.weights),
            expected_return=allocation.expected_return,
            expected_volatility=allocation.expected_volatility,
            sharpe_ratio=allocation.sharpe_ratio,
            turnover=allocation.turnover,
            method=allocation.method,
        )

        return allocation

    async def _execute_rebalance(self, allocation: PortfolioAllocation) -> None:
        """Compute order deltas and submit to execution service.

        In paper mode, orders are simulated locally.  In live mode,
        orders are submitted via the Alpaca API.
        """
        import os

        for symbol, target_weight in allocation.weights.items():
            target_value = self._equity * target_weight
            current_qty = self._current_positions.get(symbol, 0.0)

            # Get latest price
            df = self._market_data.get(symbol)
            if df is None or df.empty:
                continue
            last_price = float(df["close"].iloc[-1])
            if last_price <= 0:
                continue

            current_value = current_qty * last_price
            delta_value = target_value - current_value
            delta_qty = int(delta_value / last_price)

            if abs(delta_qty) < 1:
                continue

            side = OrderSide.BUY if delta_qty > 0 else OrderSide.SELL
            qty = abs(delta_qty)

            if self.mode == RuntimeMode.PAPER:
                # Simulate fill
                self._current_positions[symbol] = current_qty + delta_qty
                self.metrics.orders_submitted += 1
                self.metrics.fills_received += 1
                self.metrics.total_trades += 1
                self.metrics.total_volume += qty * last_price
                self._log.info(
                    "paper_order_filled",
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    price=last_price,
                )

            elif self.mode == RuntimeMode.LIVE:
                alpaca_key = os.environ.get("ALPACA_API_KEY", "")
                alpaca_secret = os.environ.get("ALPACA_SECRET_KEY", "")
                if alpaca_key and alpaca_secret:
                    try:
                        import httpx

                        base_url = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await client.post(
                                f"{base_url}/v2/orders",
                                headers={
                                    "APCA-API-KEY-ID": alpaca_key,
                                    "APCA-API-SECRET-KEY": alpaca_secret,
                                },
                                json={
                                    "symbol": symbol,
                                    "qty": str(qty),
                                    "side": side.value.lower(),
                                    "type": "market",
                                    "time_in_force": "day",
                                },
                            )
                            if resp.status_code in (200, 201):
                                order_data = resp.json()
                                order_id = UUID(order_data["id"])
                                self._pending_orders[order_id] = order_data
                                self.metrics.orders_submitted += 1
                                self._log.info(
                                    "live_order_submitted",
                                    symbol=symbol,
                                    side=side,
                                    qty=qty,
                                    order_id=str(order_id),
                                )
                            else:
                                self._log.error(
                                    "live_order_failed",
                                    symbol=symbol,
                                    status=resp.status_code,
                                    body=resp.text[:200],
                                )
                    except Exception:
                        self.metrics.errors += 1
                        self._log.exception("live_order_error", symbol=symbol)

    def _update_equity(self) -> None:
        """Recompute total equity from positions and cash."""
        position_value = 0.0
        for symbol, qty in self._current_positions.items():
            df = self._market_data.get(symbol)
            if df is not None and not df.empty:
                price = float(df["close"].iloc[-1])
                position_value += qty * price

        # Cash = initial - cost of positions (simplified)
        self._equity = self.initial_capital + position_value - sum(
            abs(q) * float(self._market_data.get(s, pd.DataFrame({"close": [0]}))["close"].iloc[-1])
            for s, q in self._current_positions.items()
            if s in self._market_data
        ) + position_value
        # Simplified: equity ~ initial_capital + unrealised pnl
        # A proper implementation tracks cash separately
        self.metrics.unrealized_pnl = position_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    from datetime import timedelta

    return (datetime.now(tz=timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


__all__ = [
    "RuntimeMode",
    "RuntimeStatus",
    "PerformanceMetrics",
    "StrategyRuntime",
]
