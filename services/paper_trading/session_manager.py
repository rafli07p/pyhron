"""Paper trading session lifecycle manager.

Manages creation, start, pause, resume, stop of paper trading sessions
and NAV snapshots for equity curve tracking.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from data_platform.database_models.paper_trading_session import (
    PaperNavSnapshot,
    PaperTradingSession,
)
from data_platform.database_models.strategy import Strategy
from data_platform.database_models.strategy_position_snapshot import StrategyPositionSnapshot
from shared.kafka_topics import KafkaTopic
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

MIN_CAPITAL_IDR = Decimal("10_000_000")
MIN_DAILY_RETURNS_FOR_METRICS = 20


@dataclass
class PaperSessionSummary:
    """Final summary of a paper trading session."""

    session_id: str
    name: str
    initial_capital_idr: Decimal
    final_nav_idr: Decimal
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None
    total_trades: int
    winning_trades: int
    win_rate_pct: float
    total_commission_idr: Decimal
    net_return_after_costs_pct: float
    duration_days: int
    started_at: datetime | None
    stopped_at: datetime | None


class PaperTradingSessionManager:
    """Manages paper trading session lifecycle.

    Only one session per strategy may be in RUNNING state at a time.
    """

    def __init__(
        self,
        kafka_producer: Any = None,
    ) -> None:
        self._kafka_producer = kafka_producer

    async def create_session(
        self,
        name: str,
        strategy_id: str,
        initial_capital_idr: Decimal,
        mode: str,
        created_by: str,
        db_session: AsyncSession,
    ) -> PaperTradingSession:
        """Create a new session in INITIALIZING status."""
        if initial_capital_idr < MIN_CAPITAL_IDR:
            msg = f"Initial capital IDR {initial_capital_idr} below minimum IDR {MIN_CAPITAL_IDR}"
            raise ValueError(msg)

        if mode not in ("LIVE_HOURS", "SIMULATION"):
            msg = f"Invalid mode: {mode}"
            raise ValueError(msg)

        # Validate strategy exists and is active
        result = await db_session.execute(select(Strategy).where(Strategy.id == strategy_id))
        strategy = result.scalar_one_or_none()
        if strategy is None:
            msg = f"Strategy {strategy_id} not found"
            raise ValueError(msg)
        if not strategy.is_active:
            msg = f"Strategy {strategy_id} is not active"
            raise ValueError(msg)

        # Check no other session for this strategy is RUNNING or PAUSED
        existing = await db_session.execute(
            select(PaperTradingSession).where(
                PaperTradingSession.strategy_id == strategy_id,
                PaperTradingSession.status.in_(["RUNNING", "PAUSED"]),
            )
        )
        if existing.scalar_one_or_none() is not None:
            msg = f"Strategy {strategy_id} already has a running or paused session"
            raise ValueError(msg)

        session = PaperTradingSession(
            name=name,
            strategy_id=strategy_id,
            status="INITIALIZING",
            mode=mode,
            initial_capital_idr=initial_capital_idr,
            current_nav_idr=initial_capital_idr,
            peak_nav_idr=initial_capital_idr,
            cash_idr=initial_capital_idr,
            unsettled_cash_idr=Decimal("0"),
            created_by=created_by,
        )
        db_session.add(session)
        await db_session.flush()

        logger.info(
            "paper_session_created",
            session_id=str(session.id),
            name=name,
            strategy_id=strategy_id,
            initial_capital=str(initial_capital_idr),
        )
        return session

    async def start_session(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> None:
        """Transition INITIALIZING -> RUNNING."""
        session = await self._get_session(session_id, db_session)
        if session.status != "INITIALIZING":
            msg = f"Cannot start session in {session.status} state"
            raise ValueError(msg)

        session.status = "RUNNING"
        session.started_at = datetime.now(UTC)
        session.cash_idr = session.initial_capital_idr
        session.updated_at = datetime.now(UTC)
        await db_session.flush()

        if self._kafka_producer:
            await self._kafka_producer.send(
                KafkaTopic.PAPER_SESSION_STARTED,
                json.dumps(
                    {
                        "session_id": str(session.id),
                        "name": session.name,
                        "strategy_id": str(session.strategy_id),
                        "initial_capital_idr": str(session.initial_capital_idr),
                        "mode": session.mode,
                        "started_at": session.started_at.isoformat(),
                    }
                ).encode(),
            )

        logger.info("paper_session_started", session_id=session_id)

    async def pause_session(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> None:
        """Transition RUNNING -> PAUSED."""
        session = await self._get_session(session_id, db_session)
        if session.status != "RUNNING":
            msg = f"Cannot pause session in {session.status} state"
            raise ValueError(msg)

        session.status = "PAUSED"
        session.paused_at = datetime.now(UTC)
        session.updated_at = datetime.now(UTC)
        await db_session.flush()

        logger.info("paper_session_paused", session_id=session_id)

    async def resume_session(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> None:
        """Transition PAUSED -> RUNNING."""
        session = await self._get_session(session_id, db_session)
        if session.status != "PAUSED":
            msg = f"Cannot resume session in {session.status} state"
            raise ValueError(msg)

        session.status = "RUNNING"
        session.paused_at = None
        session.updated_at = datetime.now(UTC)
        await db_session.flush()

        logger.info("paper_session_resumed", session_id=session_id)

    async def stop_session(
        self,
        session_id: str,
        db_session: AsyncSession,
        close_positions: bool = True,
    ) -> PaperSessionSummary:
        """Transition RUNNING or PAUSED -> STOPPED."""
        session = await self._get_session(session_id, db_session)
        if session.status not in ("RUNNING", "PAUSED"):
            msg = f"Cannot stop session in {session.status} state"
            raise ValueError(msg)

        now = datetime.now(UTC)
        session.status = "STOPPED"
        session.stopped_at = now
        session.updated_at = now
        await db_session.flush()

        summary = await self._compute_summary(session, db_session)

        if self._kafka_producer:
            await self._kafka_producer.send(
                KafkaTopic.PAPER_SESSION_STOPPED,
                json.dumps(
                    {
                        "session_id": str(session.id),
                        "name": session.name,
                        "final_nav_idr": str(session.current_nav_idr),
                        "total_return_pct": summary.total_return_pct,
                        "stopped_at": now.isoformat(),
                    }
                ).encode(),
            )

        logger.info(
            "paper_session_stopped",
            session_id=session_id,
            total_return_pct=summary.total_return_pct,
        )
        return summary

    async def snapshot_nav(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> PaperNavSnapshot:
        """Compute current NAV and write snapshot row."""
        session = await self._get_session(session_id, db_session)

        # Fetch positions for this session's strategy
        positions_result = await db_session.execute(
            select(StrategyPositionSnapshot).where(
                StrategyPositionSnapshot.strategy_id == str(session.strategy_id),
                StrategyPositionSnapshot.quantity > 0,
            )
        )
        positions = positions_result.scalars().all()

        # Compute gross exposure
        gross_exposure = Decimal("0")
        for pos in positions:
            if pos.market_value is not None:
                gross_exposure += pos.market_value

        nav = session.cash_idr + session.unsettled_cash_idr + gross_exposure

        # Update peak and drawdown
        if nav > session.peak_nav_idr:
            session.peak_nav_idr = nav

        drawdown_pct = Decimal("0")
        if session.peak_nav_idr > 0:
            drawdown_pct = ((session.peak_nav_idr - nav) / session.peak_nav_idr * 100).quantize(Decimal("0.0001"))

        if drawdown_pct > session.max_drawdown_pct:
            session.max_drawdown_pct = drawdown_pct

        # Get previous NAV for daily P&L
        prev_result = await db_session.execute(
            select(PaperNavSnapshot)
            .where(PaperNavSnapshot.session_id == session.id)
            .order_by(PaperNavSnapshot.timestamp.desc())
            .limit(1)
        )
        prev_snap = prev_result.scalar_one_or_none()

        prev_nav = prev_snap.nav_idr if prev_snap else session.initial_capital_idr
        daily_pnl = nav - prev_nav
        daily_return_pct = Decimal("0")
        if prev_nav > 0:
            daily_return_pct = (daily_pnl / prev_nav * 100).quantize(Decimal("0.000001"))

        now = datetime.now(UTC)
        snapshot = PaperNavSnapshot(
            session_id=session.id,
            timestamp=now,
            nav_idr=nav,
            cash_idr=session.cash_idr,
            gross_exposure_idr=gross_exposure,
            drawdown_pct=drawdown_pct,
            daily_pnl_idr=daily_pnl,
            daily_return_pct=daily_return_pct,
        )
        db_session.add(snapshot)

        session.current_nav_idr = nav
        session.updated_at = now
        await db_session.flush()

        if self._kafka_producer:
            await self._kafka_producer.send(
                KafkaTopic.PAPER_NAV_SNAPSHOT,
                json.dumps(
                    {
                        "session_id": str(session.id),
                        "timestamp": now.isoformat(),
                        "nav_idr": str(nav),
                        "cash_idr": str(session.cash_idr),
                        "gross_exposure_idr": str(gross_exposure),
                        "drawdown_pct": str(drawdown_pct),
                        "daily_pnl_idr": str(daily_pnl),
                    }
                ).encode(),
            )

        return snapshot

    async def _get_session(
        self,
        session_id: str,
        db_session: AsyncSession,
    ) -> PaperTradingSession:
        result = await db_session.execute(select(PaperTradingSession).where(PaperTradingSession.id == session_id))
        session = result.scalar_one_or_none()
        if session is None:
            msg = f"Paper trading session {session_id} not found"
            raise ValueError(msg)
        return session

    async def _compute_summary(
        self,
        session: PaperTradingSession,
        db_session: AsyncSession,
    ) -> PaperSessionSummary:
        initial = session.initial_capital_idr
        final = session.current_nav_idr
        total_return_pct = float((final - initial) / initial * 100) if initial > 0 else 0.0
        net_return = float((final - initial - session.total_commission_idr) / initial * 100) if initial > 0 else 0.0

        win_rate = 0.0
        if session.total_trades > 0:
            win_rate = session.winning_trades / session.total_trades * 100

        duration_days = 0
        if session.started_at and session.stopped_at:
            duration_days = (session.stopped_at - session.started_at).days

        # Compute risk metrics from NAV snapshots
        sharpe, sortino, calmar = await self._compute_risk_metrics(session, db_session)

        return PaperSessionSummary(
            session_id=str(session.id),
            name=session.name,
            initial_capital_idr=initial,
            final_nav_idr=final,
            total_return_pct=round(total_return_pct, 4),
            max_drawdown_pct=float(session.max_drawdown_pct),
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            total_trades=session.total_trades,
            winning_trades=session.winning_trades,
            win_rate_pct=round(win_rate, 2),
            total_commission_idr=session.total_commission_idr,
            net_return_after_costs_pct=round(net_return, 4),
            duration_days=duration_days,
            started_at=session.started_at,
            stopped_at=session.stopped_at,
        )

    async def _compute_risk_metrics(
        self,
        session: PaperTradingSession,
        db_session: AsyncSession,
    ) -> tuple[float | None, float | None, float | None]:
        """Compute Sharpe, Sortino, Calmar from daily NAV returns."""
        result = await db_session.execute(
            select(PaperNavSnapshot.daily_return_pct)
            .where(PaperNavSnapshot.session_id == session.id)
            .order_by(PaperNavSnapshot.timestamp.asc())
        )
        returns = [float(r[0]) for r in result.all()]

        if len(returns) < MIN_DAILY_RETURNS_FOR_METRICS:
            return None, None, None

        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_ret = math.sqrt(variance) if variance > 0 else 0.0

        # Sharpe: annualized
        sharpe = (mean_ret / std_ret * math.sqrt(252)) if std_ret > 0 else None

        # Sortino: use downside deviation
        downside = [r for r in returns if r < 0]
        if downside:
            downside_var = sum(r**2 for r in downside) / len(returns)
            downside_std = math.sqrt(downside_var)
            sortino = (mean_ret / downside_std * math.sqrt(252)) if downside_std > 0 else None
        else:
            sortino = None

        # Calmar: annualized return / max drawdown
        max_dd = float(session.max_drawdown_pct)
        if max_dd > 0:
            annualized_return = mean_ret * 252
            calmar = annualized_return / max_dd
        else:
            calmar = None

        return (
            round(sharpe, 4) if sharpe is not None else None,
            round(sortino, 4) if sortino is not None else None,
            round(calmar, 4) if calmar is not None else None,
        )
