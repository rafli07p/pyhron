#!/usr/bin/env python3
"""CLI script to run a paper trading session with live market data.

Launches the intraday data ingestion service and paper trading engine
together, feeding real-time Alpaca market data into the paper account.

Usage:
    python scripts/run_paper_trading.py --strategy momentum
    python scripts/run_paper_trading.py --symbols AAPL MSFT --capital 100000
    python scripts/run_paper_trading.py --mode simulation --start 2024-01-01 --end 2024-03-31
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pyhron.paper_trading")

DEFAULT_SYMBOLS = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]
DEFAULT_CAPITAL_IDR = 500_000_000  # 500M IDR


async def run_live_paper_session(args: argparse.Namespace) -> None:
    """Run a live paper trading session with real-time market data."""
    from data_platform.consumers.intraday_ingestion import IntradayIngestionService
    from services.broker_connectivity.alpaca_broker_adapter import AlpacaBrokerAdapter
    from shared.configuration_settings import get_config

    config = get_config()

    logger.info(
        "Starting live paper trading session: symbols=%s, capital=%s IDR",
        args.symbols,
        f"{args.capital:,.0f}",
    )

    # Start the intraday data ingestion service
    ingestion = IntradayIngestionService(
        symbols=args.symbols,
        bootstrap_servers=config.kafka_bootstrap_servers,
        trades=True,
        quotes=False,
        bars=True,
    )

    # Start the Alpaca broker adapter for order execution
    adapter = AlpacaBrokerAdapter()

    try:
        # Verify Alpaca connectivity
        account = await adapter.get_account()
        logger.info(
            "Alpaca paper account connected: equity=$%s, buying_power=$%s",
            f"{account['equity']:,.2f}",
            f"{account['buying_power']:,.2f}",
        )

        # Start ingestion
        await ingestion.start()
        logger.info("Intraday data ingestion started for %d symbols", len(args.symbols))

        # Stream fills in background
        fill_task = asyncio.create_task(_stream_fills(adapter), name="fill_streamer")
        ingestion_task = asyncio.create_task(ingestion.run(), name="ingestion")

        logger.info(
            "Paper trading session RUNNING. Press Ctrl+C to stop.\n"
            "  Symbols: %s\n"
            "  Capital: %s IDR\n"
            "  Mode: LIVE_HOURS",
            ", ".join(args.symbols),
            f"{args.capital:,.0f}",
        )

        # Wait for cancellation
        await asyncio.gather(ingestion_task, fill_task)

    except KeyboardInterrupt:
        logger.info("Paper trading session stopped by user")
    except Exception:
        logger.exception("Paper trading session error")
    finally:
        await ingestion.stop()
        await adapter.close()
        logger.info("Paper trading session shut down cleanly")


async def _stream_fills(adapter: object) -> None:
    """Stream trade fills from Alpaca and log them."""
    try:
        async for fill in adapter.stream_fills():
            event_type = fill.get("event_type", "")
            symbol = fill.get("symbol", "")
            side = fill.get("side", "")
            qty = fill.get("filled_qty", 0)
            price = fill.get("filled_price", 0)

            if event_type in ("fill", "partial_fill"):
                logger.info(
                    "FILL: %s %s %d @ $%.2f (status: %s)",
                    side.upper(),
                    symbol,
                    qty,
                    price,
                    fill.get("order_status", ""),
                )
            else:
                logger.info(
                    "ORDER EVENT: %s %s — %s",
                    symbol,
                    event_type,
                    fill.get("order_status", ""),
                )
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Fill stream error")


async def run_simulation(args: argparse.Namespace) -> None:
    """Run a paper trading simulation over historical data."""
    logger.info(
        "Starting paper trading SIMULATION: %s to %s, capital=%s IDR, slippage=%d bps",
        args.start,
        args.end,
        f"{args.capital:,.0f}",
        args.slippage,
    )

    # Import simulation engine (requires DB access)
    try:
        from services.paper_trading.simulation_engine import PaperSimulationEngine
        from shared.async_database_session import get_async_session_factory
    except ImportError:
        logger.error(
            "Simulation requires database connectivity. " "Ensure DATABASE_URL is set and the DB is accessible."
        )
        sys.exit(1)

    engine = PaperSimulationEngine()
    session_factory = get_async_session_factory()

    async with session_factory() as db_session:
        # Create a temporary session for simulation
        from data_platform.database_models.pyhron_paper_trading_session import PyhronPaperTradingSession

        session = PyhronPaperTradingSession(
            name=f"sim-{args.strategy}-{args.start}-{args.end}",
            strategy_id=args.strategy_id,
            user_id=args.user_id,
            initial_capital_idr=Decimal(str(args.capital)),
            current_nav_idr=Decimal(str(args.capital)),
            peak_nav_idr=Decimal(str(args.capital)),
            settled_cash_idr=Decimal(str(args.capital)),
            unsettled_cash_idr=Decimal("0"),
            status="RUNNING",
            mode="SIMULATION",
        )
        db_session.add(session)
        await db_session.commit()

        summary = await engine.run(
            session=session,
            date_from=date.fromisoformat(args.start),
            date_to=date.fromisoformat(args.end),
            slippage_bps=Decimal(str(args.slippage)),
            db_session=db_session,
        )

    # Print results
    logger.info("=" * 60)
    logger.info("SIMULATION COMPLETE")
    logger.info("=" * 60)
    logger.info("Session:          %s", summary.name)
    logger.info("Initial Capital:  %s IDR", f"{summary.initial_capital_idr:,.0f}")
    logger.info("Final NAV:        %s IDR", f"{summary.final_nav_idr:,.0f}")
    logger.info("Total Return:     %.2f%%", summary.total_return_pct)
    logger.info("Max Drawdown:     %.2f%%", summary.max_drawdown_pct)
    if summary.sharpe_ratio is not None:
        logger.info("Sharpe Ratio:     %.4f", summary.sharpe_ratio)
    if summary.sortino_ratio is not None:
        logger.info("Sortino Ratio:    %.4f", summary.sortino_ratio)
    logger.info("Total Trades:     %d", summary.total_trades)
    logger.info("Win Rate:         %.1f%%", summary.win_rate_pct)
    logger.info("Commissions:      %s IDR", f"{summary.total_commission_idr:,.0f}")
    logger.info(
        "Net Return:       %.2f%% (after costs)",
        summary.net_return_after_costs_pct,
    )

    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results = {
            "session_id": summary.session_id,
            "name": summary.name,
            "initial_capital_idr": str(summary.initial_capital_idr),
            "final_nav_idr": str(summary.final_nav_idr),
            "total_return_pct": summary.total_return_pct,
            "max_drawdown_pct": summary.max_drawdown_pct,
            "sharpe_ratio": summary.sharpe_ratio,
            "sortino_ratio": summary.sortino_ratio,
            "calmar_ratio": summary.calmar_ratio,
            "total_trades": summary.total_trades,
            "win_rate_pct": summary.win_rate_pct,
            "total_commission_idr": str(summary.total_commission_idr),
            "net_return_after_costs_pct": summary.net_return_after_costs_pct,
            "duration_days": summary.duration_days,
            "run_timestamp": datetime.now(UTC).isoformat(),
        }
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Results saved to %s", output_path)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Run paper trading with live or simulated market data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  live        Connect to Alpaca paper account with real-time market data
  simulation  Replay historical signals against paper account

Examples:
  python scripts/run_paper_trading.py --mode live --symbols AAPL MSFT
  python scripts/run_paper_trading.py --mode simulation --start 2024-01-01 --end 2024-03-31
  python scripts/run_paper_trading.py --capital 1000000000 --strategy momentum
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["live", "simulation"],
        default="live",
        help="Paper trading mode (default: live)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help=f"Symbols to trade (default: {DEFAULT_SYMBOLS})",
    )
    parser.add_argument(
        "--strategy",
        default="momentum",
        help="Strategy name (default: momentum)",
    )
    parser.add_argument(
        "--strategy-id",
        dest="strategy_id",
        default=None,
        help="Strategy UUID for simulation mode (reads signals from DB)",
    )
    parser.add_argument(
        "--user-id",
        dest="user_id",
        default=None,
        help="User UUID for simulation mode",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=DEFAULT_CAPITAL_IDR,
        help=f"Initial capital in IDR (default: {DEFAULT_CAPITAL_IDR:,.0f})",
    )
    parser.add_argument(
        "--slippage",
        type=int,
        default=10,
        help="Slippage in basis points (default: 10)",
    )
    parser.add_argument(
        "--start",
        default="2024-01-01",
        help="Simulation start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default="2024-12-31",
        help="Simulation end date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for JSON results",
    )

    args = parser.parse_args()

    if args.mode == "live":
        asyncio.run(run_live_paper_session(args))
    else:
        asyncio.run(run_simulation(args))


if __name__ == "__main__":
    main()
