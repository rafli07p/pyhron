"""Backtesting engine for the Enthropy trading platform.

Provides full vectorised backtesting with QuantLib pricing, real
market data from yfinance/Polygon, and Dask-based parallelism for
large-universe tests.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

import dask.dataframe as dd
import numpy as np
import pandas as pd
import structlog
import yfinance as yf

from shared.schemas.research_events import BacktestResult, BacktestStatus

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Strategy protocol — users implement this to plug into the engine
# ---------------------------------------------------------------------------

@runtime_checkable
class Strategy(Protocol):
    """Protocol that user strategies must implement."""

    name: str

    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame of signals aligned with *prices*.

        Columns should match the symbols.  Values: +1 (long), -1
        (short), 0 (flat).
        """
        ...

    def get_position_sizes(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        capital: float,
    ) -> pd.DataFrame:
        """Return target dollar positions for each symbol/date.

        Default equal-weight sizing is used if this method raises
        ``NotImplementedError``.
        """
        ...


# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------

async def _fetch_yfinance(
    symbols: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch adjusted close prices from yfinance."""
    log = logger.bind(source="yfinance")
    log.info("fetching_data", symbols=symbols, start=str(start_date), end=str(end_date))

    loop = asyncio.get_running_loop()

    def _download() -> pd.DataFrame:
        data = yf.download(
            tickers=symbols,
            start=str(start_date),
            end=str(end_date),
            auto_adjust=True,
            progress=False,
        )
        if isinstance(data.columns, pd.MultiIndex):
            return data["Close"]
        return data[["Close"]].rename(columns={"Close": symbols[0]})

    df = await loop.run_in_executor(None, _download)
    return df


async def _fetch_polygon(
    symbols: list[str],
    start_date: date,
    end_date: date,
    api_key: str,
) -> pd.DataFrame:
    """Fetch daily bars from Polygon.io REST API."""
    import aiohttp

    log = logger.bind(source="polygon")
    log.info("fetching_data", symbols=symbols, start=str(start_date), end=str(end_date))

    frames: dict[str, pd.Series] = {}
    async with aiohttp.ClientSession() as session:
        for sym in symbols:
            url = (
                f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/day/"
                f"{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={api_key}"
            )
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.warning("polygon_fetch_failed", symbol=sym, status=resp.status)
                    continue
                body = await resp.json()
                results = body.get("results", [])
                if results:
                    dates = pd.to_datetime([r["t"] for r in results], unit="ms")
                    closes = [r["c"] for r in results]
                    frames[sym] = pd.Series(closes, index=dates, name=sym)

    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames)


# ---------------------------------------------------------------------------
# Performance metrics (vectorised)
# ---------------------------------------------------------------------------

def _compute_returns(equity_curve: np.ndarray) -> np.ndarray:
    """Compute log returns from an equity curve."""
    with np.errstate(divide="ignore", invalid="ignore"):
        returns = np.diff(np.log(equity_curve))
    return np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0)


def _sharpe_ratio(returns: np.ndarray, trading_days: int = 252) -> float:
    """Annualised Sharpe ratio (excess return / volatility)."""
    if len(returns) < 2:
        return 0.0
    mean_r = np.mean(returns)
    std_r = np.std(returns, ddof=1)
    if std_r == 0:
        return 0.0
    return float(mean_r / std_r * np.sqrt(trading_days))


def _max_drawdown(equity_curve: np.ndarray) -> float:
    """Maximum drawdown as a negative fraction."""
    if len(equity_curve) < 2:
        return 0.0
    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - running_max) / running_max
    return float(np.min(drawdowns))


def _win_rate(trade_pnls: np.ndarray) -> float:
    """Fraction of winning trades."""
    if len(trade_pnls) == 0:
        return 0.0
    return float(np.sum(trade_pnls > 0) / len(trade_pnls))


def _profit_factor(trade_pnls: np.ndarray) -> float:
    """Gross profit divided by gross loss."""
    gross_profit = np.sum(trade_pnls[trade_pnls > 0])
    gross_loss = abs(np.sum(trade_pnls[trade_pnls < 0]))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


def _sortino_ratio(returns: np.ndarray, trading_days: int = 252) -> float:
    """Annualised Sortino ratio."""
    if len(returns) < 2:
        return 0.0
    mean_r = np.mean(returns)
    downside = returns[returns < 0]
    if len(downside) == 0:
        return float("inf") if mean_r > 0 else 0.0
    downside_std = np.std(downside, ddof=1)
    if downside_std == 0:
        return 0.0
    return float(mean_r / downside_std * np.sqrt(trading_days))


def _annualized_return(total_return: float, days: int) -> float:
    """Annualised return from total return and holding period."""
    if days <= 0:
        return 0.0
    years = days / 252
    if years <= 0:
        return 0.0
    return float((1 + total_return) ** (1 / years) - 1)


def _annualized_volatility(returns: np.ndarray, trading_days: int = 252) -> float:
    """Annualised volatility."""
    if len(returns) < 2:
        return 0.0
    return float(np.std(returns, ddof=1) * np.sqrt(trading_days))


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Full-featured vectorised backtesting engine.

    Uses QuantLib for option/bond pricing where applicable, yfinance
    and Polygon.io for market data, and Dask for parallelised
    computation on large symbol universes.

    Parameters
    ----------
    polygon_api_key:
        Optional Polygon.io API key.  When provided, Polygon is used
        as the primary data source with yfinance as fallback.
    initial_capital:
        Default starting capital.
    slippage_bps:
        Default slippage assumption in basis points.
    commission_per_share:
        Default commission per share.
    use_dask:
        If ``True``, convert price data to Dask DataFrames for
        parallel processing on large universes.
    dask_npartitions:
        Number of Dask partitions.
    """

    def __init__(
        self,
        polygon_api_key: str | None = None,
        initial_capital: float = 1_000_000.0,
        slippage_bps: float = 5.0,
        commission_per_share: float = 0.005,
        use_dask: bool = False,
        dask_npartitions: int = 8,
    ) -> None:
        self._polygon_key = polygon_api_key
        self._initial_capital = initial_capital
        self._slippage_bps = slippage_bps
        self._commission_per_share = commission_per_share
        self._use_dask = use_dask
        self._dask_npartitions = dask_npartitions
        self._log = logger.bind(component="BacktestEngine")

    # -- data acquisition ----------------------------------------------------

    async def _get_prices(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch price data, trying Polygon first, then yfinance."""
        prices: pd.DataFrame | None = None

        if self._polygon_key:
            try:
                prices = await _fetch_polygon(symbols, start_date, end_date, self._polygon_key)
                if not prices.empty:
                    self._log.info("data_source", source="polygon", rows=len(prices))
            except Exception:
                self._log.warning("polygon_fetch_failed_falling_back")

        if prices is None or prices.empty:
            prices = await _fetch_yfinance(symbols, start_date, end_date)
            self._log.info("data_source", source="yfinance", rows=len(prices))

        # Forward-fill missing data
        prices = prices.ffill()

        # Drop rows where all symbols are NaN (before data start)
        prices = prices.dropna(how="all")

        # Fill any remaining NaN with backward fill then zero
        prices = prices.bfill().fillna(0.0)

        return prices

    # -- core backtest logic -------------------------------------------------

    async def run_backtest(
        self,
        strategy: Strategy,
        symbols: list[str],
        start_date: date,
        end_date: date,
        tenant_id: str = "default",
        initial_capital: float | None = None,
        slippage_bps: float | None = None,
        commission_per_share: float | None = None,
    ) -> BacktestResult:
        """Execute a vectorised backtest over historical data.

        Parameters
        ----------
        strategy:
            A strategy implementing the ``Strategy`` protocol.
        symbols:
            Universe of symbols to trade.
        start_date:
            Backtest start (inclusive).
        end_date:
            Backtest end (inclusive).
        tenant_id:
            Tenant identifier for the result event.
        initial_capital:
            Starting capital; overrides the engine default.
        slippage_bps:
            Slippage in bps; overrides engine default.
        commission_per_share:
            Per-share commission; overrides engine default.

        Returns
        -------
        BacktestResult
            Shared-schema result with all performance metrics.
        """
        capital = initial_capital or self._initial_capital
        slip_bps = slippage_bps or self._slippage_bps
        comm = commission_per_share or self._commission_per_share

        self._log.info(
            "run_backtest",
            strategy=strategy.name,
            symbols=symbols,
            start=str(start_date),
            end=str(end_date),
            capital=capital,
            tenant_id=tenant_id,
        )

        try:
            # 1. Fetch price data
            prices = await self._get_prices(symbols, start_date, end_date)
            if prices.empty:
                return self._failed_result(
                    strategy, symbols, start_date, end_date,
                    tenant_id, capital, "No price data available",
                )

            # Ensure all requested symbols are present
            missing = [s for s in symbols if s not in prices.columns]
            if missing:
                self._log.warning("missing_symbols", missing=missing)
                symbols = [s for s in symbols if s in prices.columns]
                if not symbols:
                    return self._failed_result(
                        strategy, symbols, start_date, end_date,
                        tenant_id, capital, "No data for any requested symbol",
                    )

            prices = prices[symbols]

            # 2. Optionally convert to Dask for large universes
            compute_prices = prices
            if self._use_dask and len(symbols) > 20:
                self._log.info("using_dask", npartitions=self._dask_npartitions)
                dask_prices = dd.from_pandas(prices, npartitions=self._dask_npartitions)
                # Generate signals using pandas (strategy expects pandas)
                # but use Dask for heavy compute below
                compute_prices = prices

            # 3. Generate signals
            signals = strategy.generate_signals(compute_prices)
            signals = signals.reindex(prices.index).fillna(0)

            # 4. Position sizing
            try:
                positions = strategy.get_position_sizes(signals, compute_prices, capital)
            except (NotImplementedError, AttributeError):
                # Default: equal-weight allocation
                n_active = signals.abs().sum(axis=1).replace(0, np.nan)
                weights = signals.div(n_active, axis=0).fillna(0)
                positions = weights * capital

            positions = positions.reindex(prices.index).fillna(0)

            # 5. Compute daily returns (vectorised)
            daily_returns_pct = prices.pct_change().fillna(0)

            if self._use_dask and len(symbols) > 20:
                dask_returns = dd.from_pandas(daily_returns_pct, npartitions=self._dask_npartitions)
                dask_positions = dd.from_pandas(positions.shift(1).fillna(0), npartitions=self._dask_npartitions)
                port_returns_series = (dask_returns * dask_positions).sum(axis=1).compute()
            else:
                # Position from previous day earns today's return
                shifted_positions = positions.shift(1).fillna(0)
                port_returns_series = (daily_returns_pct * shifted_positions).sum(axis=1)

            # 6. Apply transaction costs
            position_changes = positions.diff().fillna(0)
            # Slippage cost
            slippage_cost = position_changes.abs().sum(axis=1) * (slip_bps / 10_000)
            # Commission cost
            shares_traded = (position_changes.abs() / prices.replace(0, np.nan)).fillna(0).sum(axis=1)
            commission_cost = shares_traded * comm

            total_costs = slippage_cost + commission_cost
            net_returns = port_returns_series - total_costs

            # 7. Build equity curve
            equity = np.zeros(len(net_returns) + 1)
            equity[0] = capital
            for i, ret in enumerate(net_returns.values):
                equity[i + 1] = equity[i] + ret
            equity = np.maximum(equity, 0)  # floor at zero

            # 8. Compute performance metrics
            log_returns = _compute_returns(equity)
            pct_returns = np.diff(equity) / np.where(equity[:-1] == 0, 1, equity[:-1])
            pct_returns = np.nan_to_num(pct_returns, nan=0.0, posinf=0.0, neginf=0.0)

            total_return = (equity[-1] - capital) / capital if capital > 0 else 0.0
            trading_days = len(log_returns)
            ann_return = _annualized_return(total_return, trading_days)
            sharpe = _sharpe_ratio(pct_returns)
            sortino = _sortino_ratio(pct_returns)
            mdd = _max_drawdown(equity)
            vol = _annualized_volatility(pct_returns)
            calmar = ann_return / abs(mdd) if mdd != 0 else 0.0

            # 9. Trade statistics
            # A "trade" occurs when positions change
            trade_signals = position_changes.abs().sum(axis=1)
            trade_mask = trade_signals > 0
            trade_returns = net_returns[trade_mask].values
            total_trades = int(trade_mask.sum())
            wr = _win_rate(trade_returns)
            pf = _profit_factor(trade_returns)

            total_slippage = float(slippage_cost.sum())
            total_commission = float(commission_cost.sum())

            self._log.info(
                "backtest_complete",
                strategy=strategy.name,
                total_return=round(total_return, 4),
                sharpe=round(sharpe, 2),
                max_drawdown=round(mdd, 4),
                trades=total_trades,
            )

            # Clamp max_drawdown to <= 0 for the schema
            mdd_clamped = min(mdd, 0.0)

            return BacktestResult(
                tenant_id=tenant_id,
                strategy_id=strategy.name,
                status=BacktestStatus.COMPLETED,
                start_date=start_date,
                end_date=end_date,
                symbols=symbols,
                total_return=Decimal(str(round(total_return, 6))),
                annualized_return=Decimal(str(round(ann_return, 6))),
                sharpe_ratio=Decimal(str(round(sharpe, 4))),
                sortino_ratio=Decimal(str(round(sortino, 4))),
                calmar_ratio=Decimal(str(round(calmar, 4))),
                max_drawdown=Decimal(str(round(mdd_clamped, 6))),
                volatility=Decimal(str(round(abs(vol), 6))),
                total_trades=total_trades,
                win_rate=Decimal(str(round(wr, 4))),
                profit_factor=Decimal(str(round(min(pf, 9999.0), 4))),
                avg_trade_pnl=Decimal(str(round(float(np.mean(trade_returns)), 2))) if len(trade_returns) > 0 else None,
                total_commission=Decimal(str(round(total_commission, 2))),
                total_slippage=Decimal(str(round(total_slippage, 2))),
                returns=pct_returns.tolist(),
                equity_curve=equity.tolist(),
                initial_capital=Decimal(str(capital)),
                final_capital=Decimal(str(round(equity[-1], 2))),
            )

        except Exception as exc:
            self._log.exception("backtest_failed", strategy=strategy.name)
            return self._failed_result(
                strategy, symbols, start_date, end_date,
                tenant_id, capital, str(exc),
            )

    # -- QuantLib pricing helpers --------------------------------------------

    @staticmethod
    def price_option_black_scholes(
        spot: float,
        strike: float,
        risk_free_rate: float,
        volatility: float,
        time_to_maturity: float,
        option_type: str = "call",
    ) -> float:
        """Price a European option using QuantLib's Black-Scholes engine.

        Parameters
        ----------
        spot:
            Current underlying price.
        strike:
            Option strike price.
        risk_free_rate:
            Risk-free interest rate (annualised).
        volatility:
            Implied volatility (annualised).
        time_to_maturity:
            Time to expiry in years.
        option_type:
            ``"call"`` or ``"put"``.

        Returns
        -------
        float
            Theoretical option price.
        """
        import QuantLib as ql

        today = ql.Date.todaysDate()
        ql.Settings.instance().evaluationDate = today

        maturity_date = today + ql.Period(int(time_to_maturity * 365), ql.Days)

        payoff = ql.PlainVanillaPayoff(
            ql.Option.Call if option_type.lower() == "call" else ql.Option.Put,
            strike,
        )
        exercise = ql.EuropeanExercise(maturity_date)
        option = ql.VanillaOption(payoff, exercise)

        spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
        flat_ts = ql.YieldTermStructureHandle(
            ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(risk_free_rate)), ql.Actual365Fixed())
        )
        flat_vol = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(today, ql.NullCalendar(), ql.QuoteHandle(ql.SimpleQuote(volatility)), ql.Actual365Fixed())
        )

        bsm_process = ql.BlackScholesMertonProcess(spot_handle, flat_ts, flat_ts, flat_vol)
        option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))

        return option.NPV()

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _failed_result(
        strategy: Strategy,
        symbols: list[str],
        start_date: date,
        end_date: date,
        tenant_id: str,
        capital: float,
        error: str,
    ) -> BacktestResult:
        return BacktestResult(
            tenant_id=tenant_id,
            strategy_id=strategy.name,
            status=BacktestStatus.FAILED,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            initial_capital=Decimal(str(capital)),
            error_message=error,
        )


__all__ = [
    "Strategy",
    "BacktestEngine",
]
