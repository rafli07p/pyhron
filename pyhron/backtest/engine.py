"""Backtest engine for the Pyhron trading platform.

Runs a strategy against historical data with risk checks and
P&L tracking. Produces a BacktestResult with equity curve,
trade log, and performance metrics.
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from decimal import Decimal

from pyhron.backtest.config import BacktestConfig
from pyhron.backtest.result import BacktestResult, EquityPoint, TradeRecord
from pyhron.market_data.historical import HistoricalDataLoader

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Event-driven backtest engine.

    Parameters
    ----------
    config:
        Backtest configuration (dates, symbols, capital, costs).
    risk_engine:
        Optional risk engine for pre-trade checks during simulation.
    pnl_engine:
        Optional P&L engine for attribution.
    data_loader:
        Historical data loader instance.
    """

    def __init__(self, config: BacktestConfig, risk_engine=None, pnl_engine=None, data_loader=None) -> None:
        self.config = config
        self.risk_engine = risk_engine
        self.pnl_engine = pnl_engine
        self.data_loader = data_loader or HistoricalDataLoader()
        self._strategy_name: str | None = None
        self._strategy_params: dict | None = None

    def run(self, strategy) -> BacktestResult:
        """Run backtest for the given strategy.

        The strategy must expose:
        - ``name: str`` property
        - ``parameters: dict`` property
        - ``generate_signals(bars) -> list[Signal]`` method

        Each Signal must have: symbol, direction ("BUY"/"SELL"),
        quantity (Decimal), and optionally price (Decimal).

        Returns a BacktestResult with equity curve and trade log.
        """
        self._strategy_name = strategy.name
        self._strategy_params = strategy.parameters

        # Load historical data
        data = self.data_loader.load(
            self.config.symbols,
            self.config.start_date,
            self.config.end_date,
        )

        # State tracking
        cash = self.config.initial_capital
        positions: dict[str, Decimal] = {}
        avg_costs: dict[str, Decimal] = {}
        equity_curve: list[EquityPoint] = []
        trades: list[TradeRecord] = []
        risk_violations: list[str] = []

        # Collect all trading dates across symbols
        all_dates: set = set()
        for bars in data.values():
            for bar in bars:
                all_dates.add(bar.date)
        sorted_dates = sorted(all_dates)

        # Build price lookup: date -> symbol -> close
        price_map: dict = {}
        for symbol, bars in data.items():
            for bar in bars:
                price_map.setdefault(bar.date, {})[symbol] = bar.close

        # Simulate day by day
        for trade_date in sorted_dates:
            day_prices = price_map.get(trade_date, {})

            # Build bars dict for signal generation
            day_bars = {}
            for symbol, bars in data.items():
                symbol_bars = [b for b in bars if b.date <= trade_date]
                if symbol_bars:
                    day_bars[symbol] = symbol_bars

            # Generate signals from strategy
            try:
                signals = strategy.generate_signals(day_bars)
            except Exception:
                signals = []

            # Execute signals
            for signal in signals:
                sym = signal.symbol if hasattr(signal, "symbol") else str(signal.get("symbol", ""))
                direction = signal.direction if hasattr(signal, "direction") else str(signal.get("direction", ""))
                qty = Decimal(str(signal.quantity if hasattr(signal, "quantity") else signal.get("quantity", 0)))
                sig_price = day_prices.get(sym)

                if sig_price is None or qty <= 0:
                    continue

                # Apply slippage
                slippage_factor = Decimal(str(self.config.slippage_bps)) / Decimal("10000")
                if direction == "BUY":
                    exec_price = sig_price * (1 + slippage_factor)
                else:
                    exec_price = sig_price * (1 - slippage_factor)

                notional = qty * exec_price
                commission = notional * self.config.commission_rate

                # Risk check
                if self.risk_engine is not None:
                    try:
                        check = self.risk_engine.check_order_size_value(notional)
                        if hasattr(check, "passed") and not check.passed:
                            risk_violations.append(f"{trade_date}: {sym} {direction} rejected by risk")
                            continue
                    except Exception:
                        logger.debug("risk_check_skipped", extra={"symbol": sym})

                # Execute
                if direction == "BUY":
                    if cash >= notional + commission:
                        cash -= notional + commission
                        old_qty = positions.get(sym, Decimal("0"))
                        old_cost = avg_costs.get(sym, Decimal("0"))
                        new_qty = old_qty + qty
                        if new_qty > 0:
                            avg_costs[sym] = (old_cost * old_qty + exec_price * qty) / new_qty
                        positions[sym] = new_qty
                    else:
                        continue
                elif direction == "SELL":
                    held = positions.get(sym, Decimal("0"))
                    sell_qty = min(qty, held)
                    if sell_qty <= 0:
                        continue
                    cash += sell_qty * exec_price - commission
                    positions[sym] = held - sell_qty
                    if positions[sym] == 0:
                        avg_costs.pop(sym, None)

                trades.append(TradeRecord(
                    symbol=sym,
                    direction=direction,
                    quantity=qty,
                    price=exec_price,
                    commission=commission,
                    timestamp=datetime(trade_date.year, trade_date.month, trade_date.day, tzinfo=UTC),
                ))

            # Mark-to-market
            portfolio_value = cash
            for sym, qty in positions.items():
                mkt_price = day_prices.get(sym, avg_costs.get(sym, Decimal("0")))
                portfolio_value += qty * mkt_price

            equity_curve.append(EquityPoint(date=trade_date, value=portfolio_value))

        # Compute metrics
        total_return = Decimal("0")
        if equity_curve and self.config.initial_capital > 0:
            total_return = (equity_curve[-1].value - self.config.initial_capital) / self.config.initial_capital

        daily_returns = self._compute_daily_returns(equity_curve)
        sharpe = self._compute_sharpe(daily_returns)
        max_dd = self._compute_max_drawdown(equity_curve)
        winning = sum(1 for t in trades if self._is_winning_trade(t, trades))
        win_rate = winning / len(trades) if trades else 0.0

        return BacktestResult(
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            initial_capital=self.config.initial_capital,
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            total_trades=len(trades),
            win_rate=win_rate,
            equity_curve=equity_curve,
            trades=trades,
            risk_violations=risk_violations,
        )

    @staticmethod
    def _compute_daily_returns(equity_curve: list[EquityPoint]) -> list[float]:
        """Compute daily returns from the equity curve."""
        if len(equity_curve) < 2:
            return []
        returns = []
        for i in range(1, len(equity_curve)):
            prev = float(equity_curve[i - 1].value)
            curr = float(equity_curve[i].value)
            if prev > 0:
                returns.append((curr - prev) / prev)
        return returns

    @staticmethod
    def _compute_sharpe(daily_returns: list[float], risk_free_rate: float = 0.0) -> float:
        """Annualized Sharpe ratio from daily returns."""
        if len(daily_returns) < 2:
            return 0.0
        mean_ret = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.0
        if std == 0:
            return 0.0
        excess = mean_ret - risk_free_rate / 252
        return round((excess / std) * math.sqrt(252), 4)

    @staticmethod
    def _compute_max_drawdown(equity_curve: list[EquityPoint]) -> float:
        """Maximum drawdown as a fraction (0.0 to 1.0)."""
        if not equity_curve:
            return 0.0
        peak = float(equity_curve[0].value)
        max_dd = 0.0
        for point in equity_curve:
            val = float(point.value)
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 6)

    @staticmethod
    def _is_winning_trade(trade: TradeRecord, all_trades: list[TradeRecord]) -> bool:
        """Heuristic: a sell at price > avg buy price for the same symbol."""
        if trade.direction != "SELL":
            return False
        buys = [t for t in all_trades if t.symbol == trade.symbol and t.direction == "BUY" and t.timestamp <= trade.timestamp]
        if not buys:
            return False
        avg_buy = sum(t.price * t.quantity for t in buys) / sum(t.quantity for t in buys)
        return trade.price > avg_buy
