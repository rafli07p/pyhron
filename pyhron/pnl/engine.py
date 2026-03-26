from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from pyhron.pnl.models import (
    FillRecord,
    PnLReport,
    PnLSummary,
    RealizedPnLResult,
    TradeDirection,
)


@dataclass
class _OpenLot:
    direction: TradeDirection
    quantity: Decimal
    price: Decimal
    strategy_id: str


class PnLEngine:
    def __init__(self) -> None:
        self._positions: dict[str, list[_OpenLot]] = defaultdict(list)
        self._seen_fills: set[UUID] = set()
        self._realized_gross: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        self._commissions: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        self._fills: list[FillRecord] = []
        self._closed_trades: list[dict] = []

    def process_fill(self, fill: FillRecord) -> None:
        if fill.fill_id in self._seen_fills:
            raise ValueError("Duplicate fill")
        self._seen_fills.add(fill.fill_id)
        self._fills.append(fill)
        self._commissions[fill.symbol] += fill.commission

        lots = self._positions[fill.symbol]

        # Determine if this fill opens or closes position
        if lots and lots[0].direction != fill.direction:
            # Closing direction: match against existing lots FIFO
            remaining = fill.quantity
            while remaining > Decimal("0") and lots:
                lot = lots[0]
                matched = min(remaining, lot.quantity)

                if lot.direction == TradeDirection.BUY:
                    # Long lot being closed by a sell
                    gross = (fill.price - lot.price) * matched
                else:
                    # Short lot being closed by a buy
                    gross = (lot.price - fill.price) * matched

                self._realized_gross[fill.symbol] += gross
                self._closed_trades.append({
                    "symbol": fill.symbol,
                    "quantity": matched,
                    "gross_pnl": gross,
                    "strategy_id": fill.strategy_id,
                })

                lot.quantity -= matched
                remaining -= matched
                if lot.quantity == Decimal("0"):
                    lots.pop(0)

            # If there's remaining quantity, it opens a new position in the fill's direction
            if remaining > Decimal("0"):
                lots.append(_OpenLot(
                    direction=fill.direction,
                    quantity=remaining,
                    price=fill.price,
                    strategy_id=fill.strategy_id,
                ))
        else:
            # Same direction or no existing position: add new lot
            lots.append(_OpenLot(
                direction=fill.direction,
                quantity=fill.quantity,
                price=fill.price,
                strategy_id=fill.strategy_id,
            ))

    def get_realized_pnl(self, symbol: str) -> RealizedPnLResult:
        gross = self._realized_gross[symbol]
        commissions = self._commissions[symbol]
        return RealizedPnLResult(
            gross_pnl=gross,
            total_commissions=commissions,
            net_pnl=gross - commissions,
        )

    def get_open_quantity(self, symbol: str) -> Decimal:
        total = Decimal("0")
        for lot in self._positions[symbol]:
            total += lot.quantity
        return total

    def calculate_unrealized_pnl(self, symbol: str, current_price: Decimal) -> Decimal:
        lots = self._positions.get(symbol, [])
        if not lots:
            return Decimal("0")

        unrealized = Decimal("0")
        for lot in lots:
            if lot.direction == TradeDirection.BUY:
                unrealized += (current_price - lot.price) * lot.quantity
            else:
                unrealized += (lot.price - current_price) * lot.quantity
        return unrealized

    def generate_daily_report(
        self, report_date: date, current_prices: dict[str, Decimal]
    ) -> PnLReport:
        all_symbols: set[str] = set()
        all_symbols.update(self._realized_gross.keys())
        all_symbols.update(self._positions.keys())

        by_symbol: dict[str, dict[str, Decimal]] = {}
        total_realized = Decimal("0")
        total_unrealized = Decimal("0")

        for symbol in all_symbols:
            pnl = self.get_realized_pnl(symbol)
            current_price = current_prices.get(symbol, Decimal("0"))
            unrealized = self.calculate_unrealized_pnl(symbol, current_price)

            by_symbol[symbol] = {
                "realized_gross": pnl.gross_pnl,
                "realized_net": pnl.net_pnl,
                "unrealized": unrealized,
                "commissions": pnl.total_commissions,
            }
            total_realized += pnl.net_pnl
            total_unrealized += unrealized

        return PnLReport(
            report_date=report_date,
            total_realized_pnl=total_realized,
            total_unrealized_pnl=total_unrealized,
            by_symbol=by_symbol,
        )

    def get_summary(self, strategy_id: str) -> PnLSummary:
        trades = [t for t in self._closed_trades if t["strategy_id"] == strategy_id]
        total_trades = len(trades)
        winning = sum(1 for t in trades if t["gross_pnl"] > Decimal("0"))
        win_rate = winning / total_trades if total_trades > 0 else 0.0

        total_gross = sum((t["gross_pnl"] for t in trades), Decimal("0"))

        # Sum commissions for fills matching this strategy
        strategy_commissions = Decimal("0")
        for fill in self._fills:
            if fill.strategy_id == strategy_id:
                strategy_commissions += fill.commission

        return PnLSummary(
            total_trades=total_trades,
            win_rate=win_rate,
            total_net_pnl=total_gross - strategy_commissions,
            total_gross_pnl=total_gross,
            total_commissions=strategy_commissions,
        )
