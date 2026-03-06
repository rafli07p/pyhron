"""CLI script to run a sample backtest."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date

from services.research.backtesting import BacktestEngine


async def main(
    symbols: list[str],
    start: str,
    end: str,
    initial_capital: float,
    tenant_id: str,
) -> None:
    engine = BacktestEngine()
    result = await engine.run_backtest(
        symbols=symbols,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end),
        initial_capital=initial_capital,
        tenant_id=tenant_id,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a sample backtest")
    parser.add_argument(
        "--symbols", nargs="+", default=["AAPL", "MSFT"],
        help="Symbols to backtest",
    )
    parser.add_argument("--start", default="2024-01-01", help="Start date")
    parser.add_argument("--end", default="2025-12-31", help="End date")
    parser.add_argument("--capital", type=float, default=1_000_000.0)
    parser.add_argument("--tenant", default="dev")

    args = parser.parse_args()
    asyncio.run(main(args.symbols, args.start, args.end, args.capital, args.tenant))
