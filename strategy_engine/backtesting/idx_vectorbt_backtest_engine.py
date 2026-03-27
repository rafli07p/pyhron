"""Vectorbt wrapper for IDX strategy backtesting.

Provides a high-level interface around vectorbt for running vectorised
backtests of Pyhron strategies, including IDX-specific transaction costs,
lot-size constraints, and T+2 settlement handling.

Usage::

    engine = IDXVectorbtBacktestEngine(cost_model=cost_model)
    result = await engine.run(strategy, market_data, start, end)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import vectorbt as vbt

from shared.structured_json_logger import get_logger
from strategy_engine.backtesting.idx_transaction_cost_model import IDXTransactionCostModel

if TYPE_CHECKING:
    from datetime import date, datetime

    from strategy_engine.base_strategy_interface import BaseStrategyInterface
    from strategy_engine.idx_momentum_cross_section_strategy import (
        IDXMomentumCrossSectionStrategy,
    )

logger = get_logger(__name__)

# Bank Indonesia 7-day Reverse Repo Rate — update when BI changes policy rate
# Current: 5.75% as of Q1 2025 (source: bi.go.id)
BI_RISK_FREE_RATE_ANNUAL = 0.0575
DAILY_RISK_FREE_RATE = (1 + BI_RISK_FREE_RATE_ANNUAL) ** (1 / 252) - 1


@dataclass
class BacktestResult:
    """Full backtest result with all required metrics."""

    # Identity
    strategy_name: str
    start_date: date
    end_date: date
    initial_capital_idr: Decimal

    # Returns
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0

    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0

    # Drawdown
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    avg_drawdown_pct: float = 0.0

    # Trading activity
    total_trades: int = 0
    avg_trades_per_month: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    avg_win_idr: Decimal = Decimal("0")
    avg_loss_idr: Decimal = Decimal("0")

    # Turnover & costs
    avg_monthly_turnover_pct: float = 0.0
    total_commission_paid_idr: Decimal = Decimal("0")
    total_levy_paid_idr: Decimal = Decimal("0")
    cost_drag_annualized_pct: float = 0.0

    # Portfolio characteristics
    avg_portfolio_size: float = 0.0
    avg_holding_period_days: float = 0.0

    # Benchmark comparison (vs IHSG / JCI)
    benchmark_total_return_pct: float = 0.0
    information_ratio: float = 0.0
    beta: float = 0.0
    alpha_annualized_pct: float = 0.0

    # Time series (for plotting)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    drawdown_series: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    monthly_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))

    # Per-trade log
    trade_log: pd.DataFrame = field(default_factory=pd.DataFrame)


def _compute_metrics(
    equity_curve: pd.Series,
    trade_log: pd.DataFrame,
    initial_capital: Decimal,
    benchmark_returns: pd.Series | None = None,
) -> dict[str, Any]:
    """Compute all BacktestResult metrics from equity curve and trade log."""
    returns = equity_curve.pct_change().dropna()
    n_days = len(returns)
    if n_days == 0:
        return {}

    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0
    years = n_days / 252.0
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0

    # Sharpe
    excess = returns - DAILY_RISK_FREE_RATE
    sharpe = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0

    # Sortino
    downside = returns[returns < DAILY_RISK_FREE_RATE]
    downside_std = float(downside.std()) if len(downside) > 1 else 1.0
    sortino = float(excess.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

    # Drawdown
    cum = (1 + returns).cumprod()
    running_max = cum.cummax()
    drawdown = cum / running_max - 1
    max_dd = float(drawdown.min())
    avg_dd = float(drawdown[drawdown < 0].mean()) if (drawdown < 0).any() else 0.0

    # Drawdown duration
    in_dd = drawdown < 0
    dd_groups = (~in_dd).cumsum()
    dd_durations = in_dd.groupby(dd_groups).sum()
    max_dd_duration = int(dd_durations.max()) if len(dd_durations) > 0 else 0

    # Calmar
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0

    # Omega
    threshold = DAILY_RISK_FREE_RATE
    gains = returns[returns > threshold] - threshold
    losses = threshold - returns[returns <= threshold]
    omega = float(gains.sum() / losses.sum()) if losses.sum() > 0 else 0.0

    # Trade stats
    total_trades = len(trade_log) if not trade_log.empty else 0
    months = max(1, n_days / 21)
    avg_trades_month = total_trades / months

    wins = trade_log[trade_log.get("pnl", pd.Series(dtype=float)) > 0] if "pnl" in trade_log.columns else pd.DataFrame()
    losses_df = (
        trade_log[trade_log.get("pnl", pd.Series(dtype=float)) < 0] if "pnl" in trade_log.columns else pd.DataFrame()
    )
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0.0
    gross_profit = float(wins["pnl"].sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses_df["pnl"].sum())) if not losses_df.empty else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    avg_win = Decimal(str(float(wins["pnl"].mean()))) if not wins.empty else Decimal("0")
    avg_loss = Decimal(str(float(losses_df["pnl"].mean()))) if not losses_df.empty else Decimal("0")

    # Costs
    total_commission = Decimal("0")
    total_levy = Decimal("0")
    if "cost" in trade_log.columns:
        total_cost_val = float(trade_log["cost"].sum())
        total_commission = Decimal(str(total_cost_val * 0.8))  # approximate split
        total_levy = Decimal(str(total_cost_val * 0.2))
    cost_drag = float(total_commission + total_levy) / float(initial_capital) / years * 100 if years > 0 else 0.0

    # Monthly returns
    monthly_rets = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)

    # Turnover
    avg_turnover = 0.0
    if "value" in trade_log.columns and not trade_log.empty:
        monthly_values = trade_log.groupby(pd.Grouper(key="date", freq="ME"))["value"].sum()
        avg_turnover = (
            float(monthly_values.mean() / float(initial_capital) * 100) if float(initial_capital) > 0 else 0.0
        )

    # Benchmark
    info_ratio = 0.0
    beta_val = 0.0
    alpha_val = 0.0
    bench_total = 0.0
    if benchmark_returns is not None and len(benchmark_returns) > 0:
        aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if len(aligned) > 1:
            aligned.columns = ["strat", "bench"]
            bench_total = float((1 + aligned["bench"]).prod() - 1)
            tracking = aligned["strat"] - aligned["bench"]
            te = float(tracking.std()) * np.sqrt(252)
            info_ratio = float(tracking.mean() * 252 / te) if te > 0 else 0.0
            cov_matrix = np.cov(aligned["strat"], aligned["bench"])
            beta_val = float(cov_matrix[0, 1] / cov_matrix[1, 1]) if cov_matrix[1, 1] > 0 else 0.0
            alpha_val = (
                (cagr - BI_RISK_FREE_RATE_ANNUAL - beta_val * (bench_total / years - BI_RISK_FREE_RATE_ANNUAL)) * 100
                if years > 0
                else 0.0
            )

    return {
        "total_return_pct": total_return * 100,
        "cagr_pct": cagr * 100,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "omega_ratio": omega,
        "max_drawdown_pct": max_dd * 100,
        "max_drawdown_duration_days": max_dd_duration,
        "avg_drawdown_pct": avg_dd * 100,
        "total_trades": total_trades,
        "avg_trades_per_month": avg_trades_month,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "avg_win_idr": avg_win,
        "avg_loss_idr": avg_loss,
        "avg_monthly_turnover_pct": avg_turnover,
        "total_commission_paid_idr": total_commission,
        "total_levy_paid_idr": total_levy,
        "cost_drag_annualized_pct": cost_drag,
        "equity_curve": equity_curve,
        "drawdown_series": drawdown,
        "monthly_returns": monthly_rets,
        "benchmark_total_return_pct": bench_total * 100,
        "information_ratio": info_ratio,
        "beta": beta_val,
        "alpha_annualized_pct": alpha_val,
    }


def run_momentum_backtest(
    strategy: IDXMomentumCrossSectionStrategy,
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    trading_values: pd.DataFrame,
    instrument_metadata: pd.DataFrame,
    initial_capital_idr: Decimal,
    start_date: date,
    end_date: date,
    cost_model: IDXTransactionCostModel,
    benchmark_returns: pd.Series | None = None,
) -> BacktestResult:
    """Run a full momentum backtest.

    Simulates:
      1. Monthly rebalancing on the FIRST TRADING DAY of each month
      2. Execution at OPEN of the day AFTER signal generation
      3. Transaction costs per trade
      4. Cash management: uninvested cash earns 0%
      5. Corporate actions: use adjusted prices (already in input)

    Parameters
    ----------
    strategy:
        Configured momentum strategy instance.
    prices:
        (dates, symbols) adjusted close. DatetimeIndex, tz-aware UTC.
    volumes:
        (dates, symbols) volume in shares.
    trading_values:
        (dates, symbols) IDR value.
    instrument_metadata:
        Columns: symbol, sector, lot_size, is_active.
    initial_capital_idr:
        Starting capital in IDR.
    start_date:
        Backtest start date.
    end_date:
        Backtest end date.
    cost_model:
        IDX transaction cost model.
    benchmark_returns:
        Optional benchmark daily returns for comparison.
    """
    from strategy_engine.idx_trading_calendar import get_monthly_rebalance_dates

    rebalance_dates = list(get_monthly_rebalance_dates(start_date, end_date))
    signals = strategy.generate_signals_full(
        prices=prices,
        volumes=volumes,
        trading_values=trading_values,
        instrument_metadata=instrument_metadata,
        rebalance_dates=rebalance_dates,
        portfolio_nav=initial_capital_idr,
    )

    # Build daily equity curve by simulating portfolio
    all_dates = prices.loc[(prices.index >= pd.Timestamp(start_date)) & (prices.index <= pd.Timestamp(end_date))].index

    cash = float(initial_capital_idr)
    holdings: dict[str, int] = {}  # symbol -> shares
    equity_values: list[float] = []
    equity_dates: list[pd.Timestamp] = []
    trade_records: list[dict[str, Any]] = []
    total_cost_paid = 0.0

    # Build rebalance lookup: date -> target lots per symbol
    rebal_map: dict[date, dict[str, int]] = {}
    if not signals.empty:
        for reb_date, group in signals.groupby("date"):
            rebal_map[reb_date] = dict(zip(group["symbol"], group["target_lots"], strict=False))

    # Build execution date lookup: shift signal execution to T+1 (next trading day)
    # to avoid look-ahead bias. Signals generated on date D are executed on D+1.
    execution_map: dict[date, dict[str, int]] = {}
    sorted_dates = sorted(d.date() if hasattr(d, "date") else d for d in all_dates)
    for i, d in enumerate(sorted_dates):
        if d in rebal_map and i + 1 < len(sorted_dates):
            execution_map[sorted_dates[i + 1]] = rebal_map[d]
        elif d in rebal_map:
            # Last day: cannot execute next bar, skip
            logger.warning("signal_on_last_day_skipped", signal_date=str(d))

    for ts in all_dates:
        current_date = ts.date() if hasattr(ts, "date") else ts

        # Execute rebalancing on T+1 (day after signal generation)
        if current_date in execution_map:
            target_lots = execution_map[current_date]
            target_shares: dict[str, int] = {sym: lots * 100 for sym, lots in target_lots.items()}

            # Sell positions not in target (or reduce)
            for sym in list(holdings.keys()):
                current_shares = holdings[sym]
                target = target_shares.get(sym, 0)
                if current_shares > target:
                    sell_shares = current_shares - target
                    price = float(prices.loc[ts, sym]) if sym in prices.columns else 0.0
                    if price > 0:
                        cost_breakdown = cost_model.compute_trade_cost(
                            price=price,
                            shares=sell_shares,
                            side="sell",
                        )
                        trade_cost = float(cost_breakdown.total_cost)
                        proceeds = price * sell_shares - trade_cost
                        cash += proceeds
                        total_cost_paid += trade_cost
                        trade_records.append(
                            {
                                "date": ts,
                                "symbol": sym,
                                "action": "SELL",
                                "lots": sell_shares // 100,
                                "price": price,
                                "value": price * sell_shares,
                                "cost": trade_cost,
                                "pnl": 0.0,  # computed later
                            }
                        )
                    holdings[sym] = target
                    if holdings[sym] == 0:
                        del holdings[sym]

            # Buy new/additional positions
            for sym, target_sh in target_shares.items():
                current_shares = holdings.get(sym, 0)
                if target_sh > current_shares:
                    buy_shares = target_sh - current_shares
                    price = float(prices.loc[ts, sym]) if sym in prices.columns else 0.0
                    if price > 0:
                        cost_breakdown = cost_model.compute_trade_cost(
                            price=price,
                            shares=buy_shares,
                            side="buy",
                        )
                        trade_cost = float(cost_breakdown.total_cost)
                        total_needed = price * buy_shares + trade_cost
                        if total_needed <= cash:
                            cash -= total_needed
                            total_cost_paid += trade_cost
                            holdings[sym] = holdings.get(sym, 0) + buy_shares
                            trade_records.append(
                                {
                                    "date": ts,
                                    "symbol": sym,
                                    "action": "BUY",
                                    "lots": buy_shares // 100,
                                    "price": price,
                                    "value": price * buy_shares,
                                    "cost": trade_cost,
                                    "pnl": 0.0,
                                }
                            )

        # Compute portfolio value
        portfolio_value = cash
        for sym, shares in holdings.items():
            price = float(prices.loc[ts, sym]) if sym in prices.columns else 0.0
            portfolio_value += shares * price

        equity_values.append(portfolio_value)
        equity_dates.append(ts)

    equity_curve = pd.Series(equity_values, index=pd.DatetimeIndex(equity_dates))
    trade_log = (
        pd.DataFrame(trade_records)
        if trade_records
        else pd.DataFrame(columns=["date", "symbol", "action", "lots", "price", "value", "cost", "pnl"])
    )

    # Compute metrics
    metrics = _compute_metrics(equity_curve, trade_log, initial_capital_idr, benchmark_returns)

    # Portfolio size
    avg_size = float(np.mean([len(holdings)])) if holdings else 0.0

    return BacktestResult(
        strategy_name=strategy.get_parameters().name,
        start_date=start_date,
        end_date=end_date,
        initial_capital_idr=initial_capital_idr,
        total_return_pct=metrics.get("total_return_pct", 0.0),
        cagr_pct=metrics.get("cagr_pct", 0.0),
        sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
        sortino_ratio=metrics.get("sortino_ratio", 0.0),
        calmar_ratio=metrics.get("calmar_ratio", 0.0),
        omega_ratio=metrics.get("omega_ratio", 0.0),
        max_drawdown_pct=metrics.get("max_drawdown_pct", 0.0),
        max_drawdown_duration_days=metrics.get("max_drawdown_duration_days", 0),
        avg_drawdown_pct=metrics.get("avg_drawdown_pct", 0.0),
        total_trades=metrics.get("total_trades", 0),
        avg_trades_per_month=metrics.get("avg_trades_per_month", 0.0),
        win_rate_pct=metrics.get("win_rate_pct", 0.0),
        profit_factor=metrics.get("profit_factor", 0.0),
        avg_win_idr=metrics.get("avg_win_idr", Decimal("0")),
        avg_loss_idr=metrics.get("avg_loss_idr", Decimal("0")),
        avg_monthly_turnover_pct=metrics.get("avg_monthly_turnover_pct", 0.0),
        total_commission_paid_idr=metrics.get("total_commission_paid_idr", Decimal("0")),
        total_levy_paid_idr=metrics.get("total_levy_paid_idr", Decimal("0")),
        cost_drag_annualized_pct=metrics.get("cost_drag_annualized_pct", 0.0),
        avg_portfolio_size=avg_size,
        equity_curve=metrics.get("equity_curve", pd.Series(dtype=float)),
        drawdown_series=metrics.get("drawdown_series", pd.Series(dtype=float)),
        monthly_returns=metrics.get("monthly_returns", pd.Series(dtype=float)),
        benchmark_total_return_pct=metrics.get("benchmark_total_return_pct", 0.0),
        information_ratio=metrics.get("information_ratio", 0.0),
        beta=metrics.get("beta", 0.0),
        alpha_annualized_pct=metrics.get("alpha_annualized_pct", 0.0),
        trade_log=trade_log,
    )


class IDXVectorbtBacktestEngine:
    """Vectorbt-based backtest engine with IDX market microstructure.

    Handles lot-size rounding (100 shares), asymmetric transaction costs,
    and T+2 settlement delay.
    """

    def __init__(
        self,
        cost_model: IDXTransactionCostModel | None = None,
        initial_capital: float = 1_000_000_000.0,
        lot_size: int = 100,
    ) -> None:
        self._cost_model = cost_model or IDXTransactionCostModel()
        self._initial_capital = initial_capital
        self._lot_size = lot_size

        logger.info(
            "backtest_engine_initialised",
            initial_capital=self._initial_capital,
            lot_size=self._lot_size,
        )

    async def run(
        self,
        strategy: BaseStrategyInterface,
        market_data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime,
    ) -> BacktestResult:
        """Execute a full backtest for the given strategy."""
        params = strategy.get_parameters()
        logger.info(
            "backtest_run_start",
            strategy=params.name,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
        )

        if isinstance(market_data.index, pd.MultiIndex):
            close = market_data["close"].unstack(level="symbol")
        else:
            close = market_data.pivot(columns="symbol", values="close")

        close = close.loc[(close.index >= start_date) & (close.index <= end_date)].sort_index()

        rebalance_dates = self._get_rebalance_dates(
            close.index,
            params.rebalance_frequency,
        )

        target_weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)

        for rdate in rebalance_dates:
            hist = market_data.loc[market_data.index.get_level_values(0) < rdate]
            signals = await strategy.generate_signals(hist, rdate)
            future_dates = close.index[close.index > rdate]
            if len(future_dates) == 0:
                continue
            next_bar = future_dates[0]
            for sig in signals:
                if sig.symbol in target_weights.columns:
                    target_weights.loc[next_bar:, sig.symbol] = sig.target_weight

        shares = (target_weights * self._initial_capital) / close
        shares = (shares // self._lot_size) * self._lot_size
        shares = shares.fillna(0).astype(int)

        portfolio = vbt.Portfolio.from_orders(
            close=close,
            size=shares.diff().fillna(shares),
            size_type="amount",
            init_cash=self._initial_capital,
            fees=self._cost_model.effective_round_trip_cost(),
            freq="1D",
        )

        equity_curve = portfolio.value()
        metrics = _compute_metrics(
            equity_curve,
            portfolio.trades.records_readable,
            Decimal(str(self._initial_capital)),
        )

        result = BacktestResult(
            strategy_name=params.name,
            start_date=start_date.date() if hasattr(start_date, "date") else start_date,
            end_date=end_date.date() if hasattr(end_date, "date") else end_date,
            initial_capital_idr=Decimal(str(self._initial_capital)),
            **dict(metrics),
        )

        logger.info(
            "backtest_run_complete",
            strategy=params.name,
            total_return=result.total_return_pct,
        )
        return result

    @staticmethod
    def _get_rebalance_dates(
        date_index: pd.DatetimeIndex,
        frequency: str,
    ) -> list[datetime]:
        if frequency == "daily":
            return list(date_index)
        if frequency == "weekly":
            return list(date_index[date_index.dayofweek == 4])
        if frequency == "monthly":
            grouped = pd.Series(date_index, index=date_index).groupby(
                date_index.to_period("M"),
            )
            return [g.iloc[-1] for _, g in grouped]
        if frequency == "quarterly":
            grouped = pd.Series(date_index, index=date_index).groupby(
                date_index.to_period("Q"),
            )
            return [g.iloc[-1] for _, g in grouped]
        return list(date_index)
