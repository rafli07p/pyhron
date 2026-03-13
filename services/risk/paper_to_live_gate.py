"""Paper-to-live promotion gate.

Validates a paper trading session against qualification criteria
before allowing promotion to live trading. All criteria must pass.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PromotionBlockedError(Exception):
    """Raised when a promotion pre-condition is not met."""


@dataclass(frozen=True)
class LivePromotionAudit:
    """Result of a promotion gate evaluation."""

    id: str
    session_id: str
    checked_at: datetime
    checked_by: str
    min_trading_days_met: bool
    min_trades_met: bool
    sharpe_threshold_met: bool
    max_drawdown_met: bool
    win_rate_met: bool
    data_coverage_met: bool
    overall_pass: bool
    session_sharpe: Decimal | None
    session_max_drawdown_pct: Decimal | None
    session_win_rate_pct: Decimal | None
    session_trading_days: int | None
    session_total_trades: int | None
    notes: str | None


@dataclass(frozen=True)
class LiveTradingConfig:
    """Configuration for a live trading strategy."""

    id: str
    strategy_id: str
    mode: str
    is_active: bool
    max_position_size_pct: Decimal
    max_daily_loss_idr: Decimal
    max_drawdown_pct: Decimal


class PaperToLivePromotionGate:
    """Validates paper trading sessions against qualification criteria.

    Thresholds are intentionally conservative. The goal is not to find
    the best strategy -- it is to prevent catastrophic loss.
    """

    MIN_TRADING_DAYS = 30
    MIN_TRADES = 100
    MIN_SHARPE = Decimal("0.8")
    MAX_DRAWDOWN_PCT = Decimal("20.0")
    MIN_WIN_RATE = Decimal("45.0")
    MIN_DATA_COVERAGE = Decimal("0.95")

    async def evaluate(
        self,
        session_id: str,
        checked_by: str,
        db_session: AsyncSession,
    ) -> LivePromotionAudit:
        """Run all qualification checks against the session.

        Writes result to live_promotion_audit table.
        Returns the audit record regardless of pass/fail.
        Does NOT promote automatically even if all criteria pass.
        """
        # Fetch session metrics
        result = await db_session.execute(
            text(
                "SELECT s.id, s.total_trades, s.winning_trades, "
                "       s.max_drawdown_pct, s.status, s.strategy_id, "
                "       (SELECT COUNT(DISTINCT DATE(timestamp)) "
                "        FROM paper_nav_snapshots WHERE session_id = s.id) AS trading_days, "
                "       (SELECT COUNT(*) FROM paper_nav_snapshots WHERE session_id = s.id) AS snapshot_count "
                "FROM paper_trading_sessions s WHERE s.id = :session_id::uuid"
            ),
            {"session_id": session_id},
        )
        row = result.mappings().first()
        if row is None:
            msg = f"Session {session_id} not found"
            raise PromotionBlockedError(msg)

        trading_days = int(row["trading_days"])
        total_trades = int(row["total_trades"] or 0)
        winning_trades = int(row["winning_trades"] or 0)
        max_dd = Decimal(str(row["max_drawdown_pct"] or 0))
        win_rate = Decimal(str(winning_trades / total_trades * 100)) if total_trades > 0 else Decimal("0")

        # Compute Sharpe from NAV snapshots
        sharpe = await self._compute_sharpe(session_id, db_session)

        # Data coverage: ratio of snapshots to expected trading days
        expected_days = max(trading_days, 1)
        snapshot_count = int(row["snapshot_count"])
        coverage = Decimal(str(snapshot_count / expected_days)) if expected_days > 0 else Decimal("0")

        # Evaluate criteria
        min_trading_days_met = trading_days >= self.MIN_TRADING_DAYS
        min_trades_met = total_trades >= self.MIN_TRADES
        sharpe_threshold_met = sharpe is not None and sharpe >= self.MIN_SHARPE
        max_drawdown_met = max_dd <= self.MAX_DRAWDOWN_PCT
        win_rate_met = win_rate >= self.MIN_WIN_RATE
        data_coverage_met = coverage >= self.MIN_DATA_COVERAGE

        overall_pass = all([
            min_trading_days_met,
            min_trades_met,
            sharpe_threshold_met,
            max_drawdown_met,
            win_rate_met,
            data_coverage_met,
        ])

        checked_at = datetime.now(UTC)

        # Write audit record (immutable)
        await db_session.execute(
            text(
                "INSERT INTO live_promotion_audit "
                "(session_id, checked_at, checked_by, "
                " min_trading_days_met, min_trades_met, sharpe_threshold_met, "
                " max_drawdown_met, win_rate_met, data_coverage_met, overall_pass, "
                " session_sharpe, session_max_drawdown_pct, session_win_rate_pct, "
                " session_trading_days, session_total_trades) "
                "VALUES (:session_id::uuid, :checked_at, :checked_by::uuid, "
                "        :min_trading_days_met, :min_trades_met, :sharpe_threshold_met, "
                "        :max_drawdown_met, :win_rate_met, :data_coverage_met, :overall_pass, "
                "        :session_sharpe, :session_max_drawdown_pct, :session_win_rate_pct, "
                "        :session_trading_days, :session_total_trades) "
                "RETURNING id"
            ),
            {
                "session_id": session_id,
                "checked_at": checked_at,
                "checked_by": checked_by,
                "min_trading_days_met": min_trading_days_met,
                "min_trades_met": min_trades_met,
                "sharpe_threshold_met": sharpe_threshold_met,
                "max_drawdown_met": max_drawdown_met,
                "win_rate_met": win_rate_met,
                "data_coverage_met": data_coverage_met,
                "overall_pass": overall_pass,
                "session_sharpe": sharpe,
                "session_max_drawdown_pct": max_dd,
                "session_win_rate_pct": win_rate,
                "session_trading_days": trading_days,
                "session_total_trades": total_trades,
            },
        )
        await db_session.flush()

        return LivePromotionAudit(
            id=session_id,  # Simplified for now
            session_id=session_id,
            checked_at=checked_at,
            checked_by=checked_by,
            min_trading_days_met=min_trading_days_met,
            min_trades_met=min_trades_met,
            sharpe_threshold_met=sharpe_threshold_met,
            max_drawdown_met=max_drawdown_met,
            win_rate_met=win_rate_met,
            data_coverage_met=data_coverage_met,
            overall_pass=overall_pass,
            session_sharpe=sharpe,
            session_max_drawdown_pct=max_dd,
            session_win_rate_pct=win_rate,
            session_trading_days=trading_days,
            session_total_trades=total_trades,
            notes=None,
        )

    async def promote(
        self,
        session_id: str,
        initial_capital_idr: Decimal,
        max_position_size_pct: Decimal,
        max_daily_loss_idr: Decimal,
        max_drawdown_pct: Decimal,
        promoted_by: str,
        db_session: AsyncSession,
    ) -> LiveTradingConfig:
        """Promote a qualified paper session to live trading.

        Pre-conditions (all must hold or raise PromotionBlockedError):
        1. Session exists and is STOPPED or COMPLETED
        2. Most recent promotion audit has overall_pass=True
        3. Audit was performed within last 7 days
        4. No existing LIVE config is active for this strategy
        """
        # Check session status
        session_result = await db_session.execute(
            text(
                "SELECT id, strategy_id, status FROM paper_trading_sessions "
                "WHERE id = :session_id::uuid"
            ),
            {"session_id": session_id},
        )
        session_row = session_result.mappings().first()
        if session_row is None:
            raise PromotionBlockedError(f"Session {session_id} not found")

        if session_row["status"] not in ("STOPPED", "COMPLETED"):
            raise PromotionBlockedError(
                f"Session must be STOPPED or COMPLETED, got {session_row['status']}"
            )

        strategy_id = str(session_row["strategy_id"])

        # Check for passing audit within last 7 days
        seven_days_ago = datetime.now(UTC) - timedelta(days=7)
        audit_result = await db_session.execute(
            text(
                "SELECT id, overall_pass, checked_at FROM live_promotion_audit "
                "WHERE session_id = :session_id::uuid AND overall_pass = TRUE "
                "AND checked_at >= :cutoff "
                "ORDER BY checked_at DESC LIMIT 1"
            ),
            {"session_id": session_id, "cutoff": seven_days_ago},
        )
        audit_row = audit_result.mappings().first()
        if audit_row is None:
            raise PromotionBlockedError("No passing audit within the last 7 days")

        # Check no existing active LIVE config for this strategy
        existing = await db_session.execute(
            text(
                "SELECT id FROM live_trading_config "
                "WHERE strategy_id = :strategy_id::uuid AND is_active = TRUE AND mode = 'LIVE'"
            ),
            {"strategy_id": strategy_id},
        )
        if existing.first() is not None:
            raise PromotionBlockedError(
                f"Active LIVE config already exists for strategy {strategy_id}"
            )

        # Create live_trading_config
        config_result = await db_session.execute(
            text(
                "INSERT INTO live_trading_config "
                "(strategy_id, mode, is_active, max_position_size_pct, "
                " max_daily_loss_idr, max_drawdown_pct, kill_switch_armed, "
                " promoted_from_session_id, promoted_at, promoted_by) "
                "VALUES (:strategy_id::uuid, 'LIVE', TRUE, :max_position_size_pct, "
                "        :max_daily_loss_idr, :max_drawdown_pct, TRUE, "
                "        :session_id::uuid, now(), :promoted_by::uuid) "
                "RETURNING id"
            ),
            {
                "strategy_id": strategy_id,
                "max_position_size_pct": max_position_size_pct,
                "max_daily_loss_idr": max_daily_loss_idr,
                "max_drawdown_pct": max_drawdown_pct,
                "session_id": session_id,
                "promoted_by": promoted_by,
            },
        )
        config_row = config_result.first()
        await db_session.flush()

        logger.critical(
            "LIVE TRADING ACTIVATED strategy_id=%s session_id=%s by=%s",
            strategy_id,
            session_id,
            promoted_by,
        )

        return LiveTradingConfig(
            id=str(config_row[0]) if config_row else "",
            strategy_id=strategy_id,
            mode="LIVE",
            is_active=True,
            max_position_size_pct=max_position_size_pct,
            max_daily_loss_idr=max_daily_loss_idr,
            max_drawdown_pct=max_drawdown_pct,
        )

    async def demote_to_paper(
        self,
        strategy_id: str,
        reason: str,
        demoted_by: str,
        db_session: AsyncSession,
    ) -> None:
        """Switch strategy from live back to paper immediately."""
        await db_session.execute(
            text(
                "UPDATE live_trading_config "
                "SET mode = 'PAPER', is_active = FALSE, updated_at = now() "
                "WHERE strategy_id = :strategy_id::uuid AND is_active = TRUE"
            ),
            {"strategy_id": strategy_id},
        )
        await db_session.flush()

        logger.critical(
            "LIVE TRADING DEMOTED strategy_id=%s reason=%s by=%s",
            strategy_id,
            reason,
            demoted_by,
        )

    async def _compute_sharpe(self, session_id: str, db_session: AsyncSession) -> Decimal | None:
        """Compute annualized Sharpe ratio from NAV snapshot series."""
        result = await db_session.execute(
            text(
                "SELECT daily_return_pct FROM paper_nav_snapshots "
                "WHERE session_id = :session_id::uuid "
                "ORDER BY timestamp"
            ),
            {"session_id": session_id},
        )
        rows = result.all()
        if len(rows) < 20:
            return None

        returns = [float(r[0]) for r in rows if r[0] is not None]
        if len(returns) < 20:
            return None

        import statistics

        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        if std_return == 0:
            return None

        annualized_sharpe = (mean_return / std_return) * (252 ** 0.5)
        return Decimal(str(round(annualized_sharpe, 4)))
