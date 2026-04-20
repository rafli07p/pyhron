"""Seed demo portfolio data for Pyhron demo environment.

Creates a demo strategy owned by the demo user and 7 IDX blue-chip positions.
Safe to re-run — strategy insert is idempotent, positions use UPSERT.

Usage:
    poetry run python scripts/seed_demo_portfolio.py
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import text

from shared.async_database_session import get_session

DEMO_USER_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
STRATEGY_ID = uuid.UUID("660e8400-e29b-41d4-a716-446655440001")

DEMO_POSITIONS = [
    {"symbol": "BBCA", "quantity": 50_000, "avg_entry_price": 8500.0},
    {"symbol": "BBRI", "quantity": 80_000, "avg_entry_price": 4200.0},
    {"symbol": "BMRI", "quantity": 60_000, "avg_entry_price": 5800.0},
    {"symbol": "TLKM", "quantity": 100_000, "avg_entry_price": 3200.0},
    {"symbol": "ASII", "quantity": 40_000, "avg_entry_price": 4800.0},
    {"symbol": "UNVR", "quantity": 30_000, "avg_entry_price": 2900.0},
    {"symbol": "GOTO", "quantity": 500_000, "avg_entry_price": 68.0},
]


async def seed() -> None:
    async with get_session() as session:
        existing = await session.execute(
            text("SELECT id FROM strategies WHERE id = :id"),
            {"id": str(STRATEGY_ID)},
        )
        if existing.scalar_one_or_none() is None:
            await session.execute(
                text(
                    """
                    INSERT INTO strategies
                      (id, user_id, name, strategy_type, parameters,
                       is_active, is_live, universe, risk_config, created_at, updated_at)
                    VALUES
                      (:id, :user_id, :name, :stype, CAST(:params AS jsonb),
                       true, false, CAST(:universe AS jsonb), CAST(:risk AS jsonb), now(), now())
                    """
                ),
                {
                    "id": str(STRATEGY_ID),
                    "user_id": str(DEMO_USER_ID),
                    "name": "Demo IDX Blue Chip Portfolio",
                    "stype": "long_only",
                    "params": "{}",
                    "universe": '["BBCA","BBRI","BMRI","TLKM","ASII","UNVR","GOTO"]',
                    "risk": '{"max_drawdown": 0.15, "position_limit": 0.25}',
                },
            )
            print("Strategy seeded.")
        else:
            print("Strategy already exists.")

        for pos in DEMO_POSITIONS:
            mkt_val = pos["quantity"] * pos["avg_entry_price"]
            await session.execute(
                text(
                    """
                    INSERT INTO positions
                      (id, strategy_id, symbol, exchange, quantity,
                       avg_entry_price, current_price, market_value,
                       unrealized_pnl, realized_pnl, updated_at)
                    VALUES
                      (:id, :strategy_id, :symbol, 'IDX', :qty,
                       :avg_price, :avg_price, :mkt_val,
                       0, 0, now())
                    ON CONFLICT (strategy_id, symbol)
                    DO UPDATE SET
                      quantity = EXCLUDED.quantity,
                      avg_entry_price = EXCLUDED.avg_entry_price,
                      current_price = EXCLUDED.current_price,
                      market_value = EXCLUDED.market_value,
                      updated_at = now()
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "strategy_id": str(STRATEGY_ID),
                    "symbol": pos["symbol"],
                    "qty": pos["quantity"],
                    "avg_price": pos["avg_entry_price"],
                    "mkt_val": mkt_val,
                },
            )
            print(f"  Position seeded: {pos['symbol']}")

        await session.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
