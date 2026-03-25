#!/usr/bin/env python3
"""CLI script to run IDX strategy backtests.

Uses the Pyhron backtesting engine with IDX-specific transaction costs,
lot-size constraints, and cross-sectional momentum strategy.

Usage::

    python scripts/run_backtest.py
    python scripts/run_backtest.py --symbols BBCA BBRI TLKM --start 2023-01-01
    python scripts/run_backtest.py --capital 5000000000 --output results.json
    python scripts/run_backtest.py --use-db  # load data from TimescaleDB
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pyhron.run_backtest")

DEFAULT_SYMBOLS = [
    "BBCA",
    "BBRI",
    "BMRI",
    "BBNI",
    "TLKM",
    "ASII",
    "UNVR",
    "HMSP",
    "GGRM",
    "KLBF",
    "ICBP",
    "INDF",
    "SMGR",
    "PTBA",
    "ADRO",
    "ITMG",
    "UNTR",
    "PGAS",
    "JSMR",
    "CPIN",
]


async def run_backtest(args: argparse.Namespace) -> None:
    """Execute the backtest."""
    from services.backtesting.backtest_orchestrator import (
        format_result_summary,
    )
    from services.backtesting.backtest_orchestrator import (
        run_backtest as execute_backtest,
    )

    if args.use_db:
        from shared.async_database_session import get_async_session

        async with get_async_session() as session:
            result = await execute_backtest(
                strategy_type=args.strategy,
                symbols=args.symbols,
                start_date=date.fromisoformat(args.start),
                end_date=date.fromisoformat(args.end),
                initial_capital_idr=Decimal(str(args.capital)),
                strategy_params=json.loads(args.strategy_params) if args.strategy_params else None,
                slippage_bps=args.slippage,
                db_session=session,
            )
    else:
        result = await execute_backtest(
            strategy_type=args.strategy,
            symbols=args.symbols,
            start_date=date.fromisoformat(args.start),
            end_date=date.fromisoformat(args.end),
            initial_capital_idr=Decimal(str(args.capital)),
            strategy_params=json.loads(args.strategy_params) if args.strategy_params else None,
            slippage_bps=args.slippage,
            db_session=None,
        )

    # Print summary
    print(format_result_summary(result))

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_data = {
            "strategy_name": result.strategy_name,
            "start_date": str(result.start_date),
            "end_date": str(result.end_date),
            "initial_capital_idr": str(result.initial_capital_idr),
            "total_return_pct": result.total_return_pct,
            "cagr_pct": result.cagr_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "calmar_ratio": result.calmar_ratio,
            "omega_ratio": result.omega_ratio,
            "max_drawdown_pct": result.max_drawdown_pct,
            "max_drawdown_duration_days": result.max_drawdown_duration_days,
            "total_trades": result.total_trades,
            "win_rate_pct": result.win_rate_pct,
            "profit_factor": result.profit_factor,
            "avg_trades_per_month": result.avg_trades_per_month,
            "total_commission_paid_idr": str(result.total_commission_paid_idr),
            "total_levy_paid_idr": str(result.total_levy_paid_idr),
            "cost_drag_annualized_pct": result.cost_drag_annualized_pct,
            "benchmark_total_return_pct": result.benchmark_total_return_pct,
            "alpha_annualized_pct": result.alpha_annualized_pct,
            "beta": result.beta,
            "information_ratio": result.information_ratio,
        }
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        logger.info("Results saved to %s", output_path)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Run an IDX strategy backtest using the Pyhron engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_backtest.py
  python scripts/run_backtest.py --symbols BBCA BBRI TLKM --start 2023-01-01
  python scripts/run_backtest.py --capital 5000000000 --output results.json
  python scripts/run_backtest.py --use-db  # load from TimescaleDB
        """,
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="Symbols to backtest (default: LQ45 top 20)",
    )
    parser.add_argument(
        "--strategy",
        default="momentum",
        choices=["momentum"],
        help="Strategy to use (default: momentum)",
    )
    parser.add_argument(
        "--strategy-params",
        type=str,
        default=None,
        help="Strategy parameters as JSON (e.g. '{\"formation_months\": 6}')",
    )
    parser.add_argument(
        "--start",
        default="2023-01-01",
        help="Backtest start date YYYY-MM-DD (default: 2023-01-01)",
    )
    parser.add_argument(
        "--end",
        default="2024-12-31",
        help="Backtest end date YYYY-MM-DD (default: 2024-12-31)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1_000_000_000,
        help="Initial capital in IDR (default: 1,000,000,000)",
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=5.0,
        help="Slippage in basis points (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for JSON results",
    )
    parser.add_argument(
        "--use-db",
        action="store_true",
        help="Load historical data from TimescaleDB instead of synthetic data",
    )

    args = parser.parse_args()
    asyncio.run(run_backtest(args))


if __name__ == "__main__":
    main()
