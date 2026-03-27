from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass
class EquityPoint:
    date: date
    value: Decimal


@dataclass
class TradeRecord:
    symbol: str
    direction: str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime


@dataclass
class BacktestResult:
    start_date: date
    end_date: date
    initial_capital: Decimal
    total_return: Decimal
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    equity_curve: list[EquityPoint] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    risk_violations: list = field(default_factory=list)
    benchmark_return: Decimal | None = None
    alpha: float | None = None
    beta: float | None = None
    information_ratio: float | None = None

    def to_html(self) -> str:
        return (
            f"<html><body>"
            f"<h1>Backtest Result</h1>"
            f"<p>Return: {self.total_return}</p>"
            f"<p>Sharpe: {self.sharpe_ratio}</p>"
            f"<p>Max Drawdown: {self.max_drawdown}</p>"
            f"</body></html>"
        )

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": str(self.initial_capital),
            "total_return": str(self.total_return),
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "equity_curve": [{"date": p.date.isoformat(), "value": str(p.value)} for p in self.equity_curve],
            "trades": [
                {
                    "symbol": t.symbol,
                    "direction": t.direction,
                    "quantity": str(t.quantity),
                    "price": str(t.price),
                    "commission": str(t.commission),
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in self.trades
            ],
            "risk_violations": self.risk_violations,
            "benchmark_return": str(self.benchmark_return) if self.benchmark_return is not None else None,
            "alpha": self.alpha,
            "beta": self.beta,
            "information_ratio": self.information_ratio,
        }
