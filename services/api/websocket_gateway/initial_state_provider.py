"""Provides initial state when a client subscribes to a channel.

Fetches current data from Redis cache or the database so the terminal
does not display empty panels after subscribing.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as aioredis
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.api.websocket_gateway.connection_manager import (
        WebSocketConnectionManager,
    )

logger = logging.getLogger(__name__)


class InitialStateProvider:
    """Fetches current state from cache/DB for newly subscribed connections."""

    QUOTE_CACHE_TTL = 60  # seconds

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis: aioredis.Redis = redis_client

    async def send_initial_quote(
        self,
        connection_id: str,
        symbol: str,
        manager: WebSocketConnectionManager,
        db_session: AsyncSession,
    ) -> None:
        """Send latest OHLCV bar for *symbol* to the connection."""
        cache_key = f"pyhron:initial:quote:{symbol}"

        # Try cache first
        cached = await self._redis.get(cache_key)
        if cached:
            msg = json.loads(cached)
            await manager.send_to_connection(connection_id, msg)
            return

        # Query DB
        try:
            from sqlalchemy import text

            row = (
                await db_session.execute(
                    text(
                        "SELECT time, symbol, open, high, low, close, volume, bid, ask "
                        "FROM ohlcv WHERE symbol = :symbol "
                        "ORDER BY time DESC LIMIT 1"
                    ),
                    {"symbol": symbol},
                )
            ).first()

            if row is None:
                return

            msg = {
                "type": "QUOTE_UPDATE",
                "symbol": str(row.symbol),
                "timestamp": row.time.isoformat() if row.time else "",
                "open": str(row.open) if row.open is not None else "",
                "high": str(row.high) if row.high is not None else "",
                "low": str(row.low) if row.low is not None else "",
                "close": str(row.close) if row.close is not None else "",
                "volume": str(row.volume) if row.volume is not None else "",
                "value_idr": "",
                "change": "",
                "change_pct": "",
                "prev_close": "",
                "bid": str(row.bid) if row.bid is not None else "",
                "ask": str(row.ask) if row.ask is not None else "",
                "bid_volume": "",
                "ask_volume": "",
            }

            await self._redis.setex(cache_key, self.QUOTE_CACHE_TTL, json.dumps(msg))
            await manager.send_to_connection(connection_id, msg)
        except Exception:
            logger.exception("initial_state.quote_error symbol=%s", symbol)

    async def send_initial_positions(
        self,
        connection_id: str,
        user_id: str,
        manager: WebSocketConnectionManager,
        db_session: AsyncSession,
    ) -> None:
        """Send all open positions for *user_id*."""
        try:
            from sqlalchemy import text

            rows = (
                await db_session.execute(
                    text(
                        "SELECT symbol, quantity, avg_entry_price, current_price, "
                        "unrealized_pnl, realized_pnl, last_updated "
                        "FROM positions WHERE quantity > 0 "
                        "AND strategy_id IN ("
                        "  SELECT DISTINCT strategy_id FROM orders WHERE user_id = :user_id"
                        ")"
                    ),
                    {"user_id": user_id},
                )
            ).fetchall()

            for row in rows:
                qty = int(row.quantity) if row.quantity else 0
                avg_cost = float(row.avg_entry_price) if row.avg_entry_price else 0.0
                last_price = float(row.current_price) if row.current_price else 0.0
                unrealized = float(row.unrealized_pnl) if row.unrealized_pnl else 0.0
                pct = (unrealized / (avg_cost * qty) * 100) if avg_cost and qty else 0.0

                msg = {
                    "type": "POSITION_UPDATE",
                    "symbol": str(row.symbol),
                    "quantity_lots": qty // 100,
                    "avg_cost_idr": str(avg_cost),
                    "last_price": str(last_price),
                    "unrealized_pnl_idr": str(unrealized),
                    "unrealized_pnl_pct": f"{pct:.2f}",
                    "realized_pnl_idr": str(row.realized_pnl) if row.realized_pnl else "0",
                    "updated_at": row.last_updated.isoformat() if row.last_updated else "",
                }
                await manager.send_to_connection(connection_id, msg)
        except Exception:
            logger.exception("initial_state.positions_error user_id=%s", user_id)

    async def send_initial_orders(
        self,
        connection_id: str,
        user_id: str,
        manager: WebSocketConnectionManager,
        db_session: AsyncSession,
    ) -> None:
        """Send today's orders for *user_id*."""
        try:
            from sqlalchemy import text

            today = datetime.now(UTC).date().isoformat()
            rows = (
                await db_session.execute(
                    text(
                        "SELECT client_order_id, broker_order_id, symbol, side, "
                        "order_type, status, quantity, filled_quantity, "
                        "limit_price, avg_fill_price, commission, "
                        "submitted_at, filled_at, updated_at "
                        "FROM orders WHERE user_id = :user_id "
                        "AND created_at::date = :today "
                        "ORDER BY created_at DESC"
                    ),
                    {"user_id": user_id, "today": today},
                )
            ).fetchall()

            for row in rows:
                lot_size = 100
                msg = {
                    "type": "ORDER_UPDATE",
                    "order_id": str(row.broker_order_id or ""),
                    "client_order_id": str(row.client_order_id),
                    "symbol": str(row.symbol),
                    "side": str(row.side).upper() if row.side else "",
                    "order_type": str(row.order_type).upper() if row.order_type else "",
                    "status": str(row.status).upper() if row.status else "",
                    "quantity_lots": int(row.quantity) // lot_size if row.quantity else 0,
                    "filled_quantity_lots": int(row.filled_quantity) // lot_size if row.filled_quantity else 0,
                    "limit_price": str(row.limit_price) if row.limit_price else "",
                    "avg_fill_price": str(row.avg_fill_price) if row.avg_fill_price else "",
                    "commission_idr": str(row.commission) if row.commission else "0",
                    "submitted_at": row.submitted_at.isoformat() if row.submitted_at else "",
                    "filled_at": row.filled_at.isoformat() if row.filled_at else "",
                    "updated_at": row.updated_at.isoformat() if row.updated_at else "",
                }
                await manager.send_to_connection(connection_id, msg)
        except Exception:
            logger.exception("initial_state.orders_error user_id=%s", user_id)

    async def send_market_status(
        self,
        connection_id: str,
        manager: WebSocketConnectionManager,
    ) -> None:
        """Send current IDX market status."""
        from services.api.websocket_gateway.market_status_broadcaster import (
            MarketStatusBroadcaster,
        )

        broadcaster = MarketStatusBroadcaster()
        now = datetime.now(UTC)
        status = broadcaster.get_current_status(now)
        await manager.send_to_connection(connection_id, status.to_dict())
