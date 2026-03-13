"""Broadcasts IDX market status changes to all connected WebSocket clients.

IDX trading sessions (WIB = UTC+7)
-----------------------------------
Pre-opening:   08:45 – 09:00
Session 1:     09:00 – 12:00
Intermission:  12:00 – 13:30
Session 2:     13:30 – 16:00
Post-closing:  16:00 – 16:15
Closed:        16:15 – 08:45 next trading day

Uses ``strategy_engine.idx_trading_calendar`` for holiday logic.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from services.api.websocket_gateway.ws_message_protocol import MarketStatusMessage

if TYPE_CHECKING:
    from services.api.websocket_gateway.connection_manager import (
        WebSocketConnectionManager,
    )

logger = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")

# Session boundaries in WIB local time
_PRE_OPEN = time(8, 45)
_SESSION1_OPEN = time(9, 0)
_SESSION1_CLOSE = time(12, 0)
_SESSION2_OPEN = time(13, 30)
_SESSION2_CLOSE = time(16, 0)
_POST_CLOSE = time(16, 15)

# (start, end, status, session, next_event)
_SESSION_TABLE: list[tuple[time, time, str, str, str]] = [
    (_PRE_OPEN, _SESSION1_OPEN, "CLOSED", "PRE_OPENING", "SESSION_1_OPEN"),
    (_SESSION1_OPEN, _SESSION1_CLOSE, "OPEN", "SESSION_1", "INTERMISSION"),
    (_SESSION1_CLOSE, _SESSION2_OPEN, "CLOSED", "INTERMISSION", "SESSION_2_OPEN"),
    (_SESSION2_OPEN, _SESSION2_CLOSE, "OPEN", "SESSION_2", "POST_CLOSE"),
    (_POST_CLOSE, time(23, 59, 59), "CLOSED", "POST_CLOSING", "CLOSED"),
]


class MarketStatusBroadcaster:
    """Broadcasts ``MARKET_STATUS`` messages at session transitions and
    every 60 s during open sessions.
    """

    BROADCAST_INTERVAL_SECONDS = 60

    def get_current_status(self, now: datetime) -> MarketStatusMessage:
        """Compute current market status from a timezone-aware *now*."""
        wib_now = now.astimezone(WIB)
        local_time = wib_now.time()

        # Check if today is a trading day
        from strategy_engine.idx_trading_calendar import is_trading_day

        if not is_trading_day(wib_now.date()):
            return MarketStatusMessage(
                status="CLOSED",
                session="HOLIDAY",
                next_event="PRE_OPENING",
                next_event_at="",
                ihsg_last="",
                ihsg_change_pct="",
                server_time=now.isoformat(),
            )

        # Before market opens
        if local_time < _PRE_OPEN:
            next_at = wib_now.replace(hour=8, minute=45, second=0, microsecond=0)
            return MarketStatusMessage(
                status="CLOSED",
                session="CLOSED",
                next_event="PRE_OPENING",
                next_event_at=next_at.astimezone(UTC).isoformat(),
                ihsg_last="",
                ihsg_change_pct="",
                server_time=now.isoformat(),
            )

        for start, end, status, session, next_event in _SESSION_TABLE:
            if start <= local_time < end:
                # Compute next event time
                next_at = wib_now.replace(
                    hour=end.hour,
                    minute=end.minute,
                    second=0,
                    microsecond=0,
                )
                return MarketStatusMessage(
                    status=status,
                    session=session,
                    next_event=next_event,
                    next_event_at=next_at.astimezone(UTC).isoformat(),
                    ihsg_last="",
                    ihsg_change_pct="",
                    server_time=now.isoformat(),
                )

        # After post-closing (shouldn't reach due to 23:59:59 but be safe)
        return MarketStatusMessage(
            status="CLOSED",
            session="CLOSED",
            next_event="PRE_OPENING",
            next_event_at="",
            ihsg_last="",
            ihsg_change_pct="",
            server_time=now.isoformat(),
        )

    def time_until_next_event(self, now: datetime) -> timedelta:
        """Return time until the next session transition."""
        wib_now = now.astimezone(WIB)
        local_time = wib_now.time()

        boundaries = [_PRE_OPEN, _SESSION1_OPEN, _SESSION1_CLOSE, _SESSION2_OPEN, _SESSION2_CLOSE, _POST_CLOSE]
        for boundary in boundaries:
            if local_time < boundary:
                target = wib_now.replace(
                    hour=boundary.hour,
                    minute=boundary.minute,
                    second=0,
                    microsecond=0,
                )
                return target - wib_now

        # Past all boundaries today → next day pre-open
        tomorrow = (wib_now + timedelta(days=1)).replace(hour=8, minute=45, second=0, microsecond=0)
        return tomorrow - wib_now

    async def run(self, manager: WebSocketConnectionManager) -> None:
        """Main broadcast loop — runs as a background asyncio task."""
        try:
            while True:
                now = datetime.now(UTC)
                status = self.get_current_status(now)
                msg = status.to_dict()

                # Broadcast to pyhron:market:status channel
                await manager.broadcast_to_channel("pyhron:market:status", msg)

                # During open sessions, broadcast every 60s.
                # During closed sessions, sleep until next event.
                if status.status == "OPEN":
                    await asyncio.sleep(self.BROADCAST_INTERVAL_SECONDS)
                else:
                    wait = self.time_until_next_event(now)
                    sleep_secs = min(wait.total_seconds(), self.BROADCAST_INTERVAL_SECONDS)
                    await asyncio.sleep(max(sleep_secs, 1))
        except asyncio.CancelledError:
            logger.info("market_status_broadcaster.cancelled")
