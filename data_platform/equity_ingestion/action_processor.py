"""Processes IDX corporate actions and adjusts historical prices.

Supported action types:
- Stock split (pemecahan saham): multiply shares, divide price
- Stock dividend (dividen saham): similar to split
- Cash dividend (dividen tunai): adjust close by dividend amount
- Rights issue (HMETD): adjust price by subscription ratio
- Reverse split (penggabungan saham): divide shares, multiply price

Price adjustment method: backward adjustment from most recent date.
Adjustment factor accumulates multiplicatively for split events.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from data_platform.adapters.eodhd_adapter import EODHDDividendRecord, EODHDSplitRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


class IDXCorporateActionProcessor:
    """Processes IDX corporate actions and adjusts historical prices."""

    def compute_adjustment_factor(
        self,
        action: EODHDSplitRecord | EODHDDividendRecord,
        close_before_action: Decimal,
    ) -> Decimal:
        """Returns the multiplicative factor to apply to all prices before the action date.

        For a 2-for-1 split: factor = 0.5 (prices halved backward)
        For a cash dividend of IDR 100 on close of IDR 5000:
            factor = (5000 - 100) / 5000 = 0.98
        """
        if isinstance(action, EODHDSplitRecord):
            if action.split_ratio == 0:
                return Decimal("1")
            return Decimal("1") / action.split_ratio

        if isinstance(action, EODHDDividendRecord):
            if close_before_action <= 0:
                return Decimal("1")
            return (close_before_action - action.dividend_idr) / close_before_action

        return Decimal("1")

    async def apply_adjustments(
        self,
        symbol: str,
        actions: list[EODHDSplitRecord | EODHDDividendRecord],
        db_session: AsyncSession,
    ) -> int:
        """Recompute adjusted_close for all historical OHLCV bars for symbol.

        Returns number of rows updated. Uses backward adjustment:
        first reset adjusted_close = close, then apply factors cumulatively.
        """
        if not actions:
            return 0

        # Reset adjusted_close to close for this symbol
        await db_session.execute(
            text("UPDATE ohlcv SET adjusted_close = close " "WHERE symbol = :symbol"),
            {"symbol": symbol},
        )

        # Sort actions by date descending (most recent first for backward adjustment)
        sorted_actions = sorted(
            actions, key=lambda a: a.date if isinstance(a, EODHDSplitRecord) else a.ex_date, reverse=True
        )

        total_updated = 0
        cumulative_factor = Decimal("1")

        for action in sorted_actions:
            action_date = action.date if isinstance(action, EODHDSplitRecord) else action.ex_date

            # Get close price on the day before the action
            result = await db_session.execute(
                text(
                    "SELECT close FROM ohlcv "
                    "WHERE symbol = :symbol AND time < :action_date "
                    "ORDER BY time DESC LIMIT 1"
                ),
                {"symbol": symbol, "action_date": action_date.isoformat()},
            )
            row = result.fetchone()
            if row is None:
                continue

            close_before = Decimal(str(row[0]))
            factor = self.compute_adjustment_factor(action, close_before)
            cumulative_factor *= factor

            # Apply factor to all bars before the action date
            result = await db_session.execute(
                text(
                    "UPDATE ohlcv SET adjusted_close = close * :factor "
                    "WHERE symbol = :symbol AND time < :action_date"
                ),
                {
                    "factor": float(cumulative_factor),
                    "symbol": symbol,
                    "action_date": action_date.isoformat(),
                },
            )
            total_updated += result.rowcount  # type: ignore[attr-defined]

        await db_session.flush()
        logger.info(
            "corporate_action_adjustments_applied",
            symbol=symbol,
            actions_count=len(actions),
            rows_updated=total_updated,
        )
        return total_updated

    async def detect_unprocessed_actions(
        self,
        symbol: str,
        db_session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Compare corporate actions in DB against price discontinuities.

        Returns list of actions not yet applied.
        """
        result = await db_session.execute(
            text(
                "SELECT action_type, ex_date, value, description "
                "FROM corporate_actions "
                "WHERE symbol = :symbol "
                "ORDER BY ex_date DESC"
            ),
            {"symbol": symbol},
        )
        actions_in_db = result.fetchall()

        unprocessed: list[dict[str, Any]] = []
        for row in actions_in_db:
            action_type, ex_date, value, description = row
            # Check if there's a price discontinuity at the ex_date
            prices = await db_session.execute(
                text(
                    "SELECT close, adjusted_close FROM ohlcv "
                    "WHERE symbol = :symbol AND time < :ex_date "
                    "ORDER BY time DESC LIMIT 1"
                ),
                {"symbol": symbol, "ex_date": ex_date.isoformat()},
            )
            price_row = prices.fetchone()
            if price_row and price_row[0] == price_row[1]:
                # adjusted_close == close means no adjustment applied
                unprocessed.append(
                    {
                        "action_type": action_type,
                        "ex_date": ex_date,
                        "value": value,
                        "description": description,
                    }
                )

        return unprocessed
