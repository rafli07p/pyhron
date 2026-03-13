"""P&L attribution engine for paper trading.

Computes realized and unrealized P&L with attribution to signal sources
(momentum vs ML). Uses FIFO cost basis for IDX standard accounting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from data_platform.database_models.paper_trading_session import (
    PaperNavSnapshot,
    PaperPnlAttribution,
    PaperTradingSession,
)
from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

MIN_DAILY_RETURNS_FOR_METRICS = 20


@dataclass
class PaperSessionMetrics:
    """Risk-adjusted performance metrics for a paper session."""

    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None
    max_drawdown_pct: float
    annualized_return_pct: float
    daily_returns: list[float] = field(default_factory=list)
    nav_series: list[tuple[datetime, Decimal]] = field(default_factory=list)


@dataclass
class AttributionReport:
    """Aggregated P&L attribution report."""

    session_id: str
    date_from: date
    date_to: date
    total_realized_pnl_idr: Decimal
    total_unrealized_pnl_idr: Decimal
    total_commission_idr: Decimal
    total_turnover_idr: Decimal
    total_trades: int
    by_symbol: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_signal_source: dict[str, dict[str, Any]] = field(default_factory=dict)


class PnLAttributionEngine:
    """Computes realized and unrealized P&L with signal attribution.

    Uses FIFO cost basis matching for IDX standard accounting.
    """

    async def record_fill_attribution(
        self,
        session_id: str,
        fill_event: dict[str, Any],
        db_session: AsyncSession,
    ) -> None:
        """Record attribution for a fill event.

        On each fill:
        1. Extract signal metadata from order tags
        2. Update paper_pnl_attribution for (session, symbol, date)
        3. Update session totals
        """
        symbol = fill_event.get("symbol", "")
        fill_qty = int(fill_event.get("filled_qty", fill_event.get("fill_quantity_lots", 0)))
        fill_price = Decimal(str(fill_event.get("fill_price", fill_event.get("filled_avg_price", "0"))))
        commission = Decimal(str(fill_event.get("commission_idr", fill_event.get("commission", "0"))))
        signal_source = fill_event.get("signal_source", "unknown")
        alpha_score = fill_event.get("alpha_score")
        realized_pnl = Decimal(str(fill_event.get("realized_pnl_idr", "0")))

        today = date.today()
        trade_value = fill_price * fill_qty

        # Upsert attribution record
        stmt = (
            pg_insert(PaperPnlAttribution)
            .values(
                session_id=session_id,
                symbol=symbol,
                date=today,
                realized_pnl_idr=realized_pnl,
                commission_idr=commission,
                turnover_idr=trade_value,
                trades_count=1,
                signal_source=signal_source,
                alpha_score=Decimal(str(alpha_score)) if alpha_score is not None else None,
            )
            .on_conflict_do_update(
                constraint="uq_paper_pnl_session_symbol_date",
                set_={
                    "realized_pnl_idr": PaperPnlAttribution.realized_pnl_idr + realized_pnl,
                    "commission_idr": PaperPnlAttribution.commission_idr + commission,
                    "turnover_idr": PaperPnlAttribution.turnover_idr + trade_value,
                    "trades_count": PaperPnlAttribution.trades_count + 1,
                },
            )
        )
        await db_session.execute(stmt)

        # Update session totals
        session_result = await db_session.execute(
            select(PaperTradingSession).where(PaperTradingSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if session:
            session.total_trades += 1
            session.total_commission_idr += commission
            session.realized_pnl_idr += realized_pnl
            if realized_pnl > 0:
                session.winning_trades += 1

        await db_session.flush()

    async def compute_unrealized_pnl(
        self,
        session_id: str,
        last_prices: dict[str, Decimal],
        db_session: AsyncSession,
    ) -> dict[str, Decimal]:
        """Compute unrealized P&L for all open positions."""
        session_result = await db_session.execute(
            select(PaperTradingSession).where(PaperTradingSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if session is None:
            return {}

        positions_result = await db_session.execute(
            select(StrategyPositionSnapshot).where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                StrategyPositionSnapshot.quantity > 0,
            )
        )
        positions = positions_result.scalars().all()

        unrealized: dict[str, Decimal] = {}
        for pos in positions:
            price = last_prices.get(pos.symbol, Decimal("0"))
            if price > 0 and pos.avg_entry_price is not None:
                pnl = (price - pos.avg_entry_price) * pos.quantity
                unrealized[pos.symbol] = pnl

        return unrealized

    async def compute_session_metrics(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> PaperSessionMetrics:
        """Compute Sharpe, Sortino, Calmar from NAV snapshot series."""
        result = await db_session.execute(
            select(PaperNavSnapshot.timestamp, PaperNavSnapshot.nav_idr, PaperNavSnapshot.daily_return_pct)
            .where(PaperNavSnapshot.session_id == session_id)
            .order_by(PaperNavSnapshot.timestamp.asc())
        )
        rows = result.all()

        daily_returns = [float(r[2]) for r in rows]
        nav_series = [(r[0], r[1]) for r in rows]

        # Get session for max drawdown
        session_result = await db_session.execute(
            select(PaperTradingSession).where(PaperTradingSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        max_dd = float(session.max_drawdown_pct) if session else 0.0

        sharpe = None
        sortino = None
        calmar = None
        annualized_return = 0.0

        if len(daily_returns) >= MIN_DAILY_RETURNS_FOR_METRICS:
            mean_ret = sum(daily_returns) / len(daily_returns)
            annualized_return = mean_ret * 252

            variance = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)
            std_ret = math.sqrt(variance) if variance > 0 else 0.0

            if std_ret > 0:
                sharpe = round(mean_ret / std_ret * math.sqrt(252), 4)

            downside = [r for r in daily_returns if r < 0]
            if downside:
                downside_var = sum(r**2 for r in downside) / len(daily_returns)
                downside_std = math.sqrt(downside_var)
                if downside_std > 0:
                    sortino = round(mean_ret / downside_std * math.sqrt(252), 4)

            if max_dd > 0:
                calmar = round(annualized_return / max_dd, 4)

        return PaperSessionMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown_pct=max_dd,
            annualized_return_pct=round(annualized_return, 4),
            daily_returns=daily_returns,
            nav_series=nav_series,
        )

    async def get_attribution_report(
        self,
        session_id: str,
        date_from: date,
        date_to: date,
        db_session: AsyncSession,
    ) -> AttributionReport:
        """Aggregate daily attribution records into a report."""
        result = await db_session.execute(
            select(PaperPnlAttribution).where(
                PaperPnlAttribution.session_id == session_id,
                PaperPnlAttribution.date >= date_from,
                PaperPnlAttribution.date <= date_to,
            )
        )
        records = result.scalars().all()

        total_realized = Decimal("0")
        total_unrealized = Decimal("0")
        total_commission = Decimal("0")
        total_turnover = Decimal("0")
        total_trades = 0

        by_symbol: dict[str, dict[str, Any]] = {}
        by_signal_source: dict[str, dict[str, Any]] = {}

        for rec in records:
            total_realized += rec.realized_pnl_idr
            total_unrealized += rec.unrealized_pnl_idr
            total_commission += rec.commission_idr
            total_turnover += rec.turnover_idr
            total_trades += rec.trades_count

            # By symbol
            if rec.symbol not in by_symbol:
                by_symbol[rec.symbol] = {
                    "realized_pnl_idr": Decimal("0"),
                    "unrealized_pnl_idr": Decimal("0"),
                    "commission_idr": Decimal("0"),
                    "turnover_idr": Decimal("0"),
                    "trades_count": 0,
                }
            by_symbol[rec.symbol]["realized_pnl_idr"] += rec.realized_pnl_idr
            by_symbol[rec.symbol]["unrealized_pnl_idr"] += rec.unrealized_pnl_idr
            by_symbol[rec.symbol]["commission_idr"] += rec.commission_idr
            by_symbol[rec.symbol]["turnover_idr"] += rec.turnover_idr
            by_symbol[rec.symbol]["trades_count"] += rec.trades_count

            # By signal source
            source = rec.signal_source or "unknown"
            if source not in by_signal_source:
                by_signal_source[source] = {
                    "realized_pnl_idr": Decimal("0"),
                    "commission_idr": Decimal("0"),
                    "turnover_idr": Decimal("0"),
                    "trades_count": 0,
                }
            by_signal_source[source]["realized_pnl_idr"] += rec.realized_pnl_idr
            by_signal_source[source]["commission_idr"] += rec.commission_idr
            by_signal_source[source]["turnover_idr"] += rec.turnover_idr
            by_signal_source[source]["trades_count"] += rec.trades_count

        return AttributionReport(
            session_id=session_id,
            date_from=date_from,
            date_to=date_to,
            total_realized_pnl_idr=total_realized,
            total_unrealized_pnl_idr=total_unrealized,
            total_commission_idr=total_commission,
            total_turnover_idr=total_turnover,
            total_trades=total_trades,
            by_symbol=by_symbol,
            by_signal_source=by_signal_source,
        )
