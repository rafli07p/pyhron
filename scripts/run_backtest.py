#!/usr/bin/env python3
"""
CLI script to run a sample backtest.

Executes a configurable backtest using the Enthropy backtesting engine
with support for multiple strategies, custom date ranges, and detailed
output including performance metrics and trade logs.

Usage:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --symbols BBCA.JK TLKM.JK --strategy momentum
    python scripts/run_backtest.py --start 2023-01-01 --end 2023-12-31 --capital 1000000000
    python scripts/run_backtest.py --output results/my_backtest.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("enthropy.run_backtest")

from enthropy.backtest.engine import BacktestEngine
from enthropy.backtest.config import BacktestConfig
from enthropy.market_data.historical import HistoricalDataLoader
from enthropy.pnl.engine import PnLEngine
from enthropy.risk.engine import RiskEngine
from enthropy.shared.schemas.risk import RiskLimits

# =============================================================================
# Strategy Registry
# =============================================================================
AVAILABLE_STRATEGIES = {
    "momentum": {
        "module": "enthropy.strategy.momentum",
        "class": "MomentumStrategy",
        "default_params": {
            "lookback_period": 20,
            "entry_threshold": "0.02",
            "exit_threshold": "-0.01",
            "position_size_pct": "0.10",
        },
    },
    "mean_reversion": {
        "module": "enthropy.strategy.mean_reversion",
        "class": "MeanReversionStrategy",
        "default_params": {
            "lookback_period": 20,
            "entry_z_score": "2.0",
            "exit_z_score": "0.5",
            "position_size_pct": "0.08",
        },
    },
    "pairs_trading": {
        "module": "enthropy.strategy.pairs",
        "class": "PairsTradingStrategy",
        "default_params": {
            "lookback_period": 60,
            "entry_z_score": "2.0",
            "exit_z_score": "0.5",
            "position_size_pct": "0.10",
        },
    },
}

DEFAULT_SYMBOLS = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]


# =============================================================================
# Strategy Loading
# =============================================================================
def load_strategy(strategy_name: str, params: dict | None = None):
    """Dynamically load a strategy class and instantiate it."""
    if strategy_name not in AVAILABLE_STRATEGIES:
        logger.error(
            f"Unknown strategy: {strategy_name}. "
            f"Available: {', '.join(AVAILABLE_STRATEGIES.keys())}"
        )
        sys.exit(1)

    strategy_info = AVAILABLE_STRATEGIES[strategy_name]
    module_name = strategy_info["module"]
    class_name = strategy_info["class"]

    import importlib
    module = importlib.import_module(module_name)
    strategy_class = getattr(module, class_name)

    # Merge default params with overrides
    strategy_params = strategy_info["default_params"].copy()
    if params:
        strategy_params.update(params)

    # Convert string numbers to Decimal where appropriate
    for key, value in strategy_params.items():
        if isinstance(value, str):
            try:
                strategy_params[key] = Decimal(value)
            except Exception:
                pass

    logger.info(f"Loading strategy: {class_name} with params: {strategy_params}")
    return strategy_class(**strategy_params)


# =============================================================================
# Output Formatting
# =============================================================================
def format_results(result, config: BacktestConfig) -> dict:
    """Format backtest results for display and export."""
    output = {
        "metadata": {
            "strategy": result.strategy_name if hasattr(result, "strategy_name") else "unknown",
            "symbols": config.symbols,
            "start_date": str(config.start_date),
            "end_date": str(config.end_date),
            "initial_capital": str(config.initial_capital),
            "commission_rate": str(config.commission_rate),
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "performance": {
            "total_return": str(result.total_return) if result.total_return else None,
            "total_return_pct": f"{float(result.total_return) * 100:.2f}%" if result.total_return else None,
            "annualized_return": str(result.annualized_return) if hasattr(result, "annualized_return") else None,
            "sharpe_ratio": f"{float(result.sharpe_ratio):.4f}" if result.sharpe_ratio else None,
            "sortino_ratio": f"{float(result.sortino_ratio):.4f}" if hasattr(result, "sortino_ratio") and result.sortino_ratio else None,
            "max_drawdown": f"{float(result.max_drawdown) * 100:.2f}%" if result.max_drawdown else None,
            "calmar_ratio": f"{float(result.calmar_ratio):.4f}" if hasattr(result, "calmar_ratio") and result.calmar_ratio else None,
        },
        "trading": {
            "total_trades": result.total_trades,
            "win_rate": f"{float(result.win_rate) * 100:.1f}%" if result.win_rate else None,
            "profit_factor": f"{float(result.profit_factor):.2f}" if hasattr(result, "profit_factor") and result.profit_factor else None,
            "avg_trade_pnl": str(result.avg_trade_pnl) if hasattr(result, "avg_trade_pnl") else None,
            "max_consecutive_wins": result.max_consecutive_wins if hasattr(result, "max_consecutive_wins") else None,
            "max_consecutive_losses": result.max_consecutive_losses if hasattr(result, "max_consecutive_losses") else None,
        },
        "risk": {
            "risk_violations": len(result.risk_violations) if hasattr(result, "risk_violations") else 0,
        },
    }

    # Add benchmark comparison if available
    if hasattr(result, "benchmark_return") and result.benchmark_return is not None:
        output["benchmark"] = {
            "benchmark_return": f"{float(result.benchmark_return) * 100:.2f}%",
            "alpha": f"{float(result.alpha):.4f}" if hasattr(result, "alpha") and result.alpha else None,
            "beta": f"{float(result.beta):.4f}" if hasattr(result, "beta") and result.beta else None,
            "information_ratio": f"{float(result.information_ratio):.4f}" if hasattr(result, "information_ratio") and result.information_ratio else None,
        }

    return output


def print_results(output: dict) -> None:
    """Pretty-print backtest results to console."""
    print("\n" + "=" * 70)
    print("  ENTHROPY BACKTEST RESULTS")
    print("=" * 70)

    meta = output["metadata"]
    print(f"\n  Strategy:   {meta['strategy']}")
    print(f"  Symbols:    {', '.join(meta['symbols'])}")
    print(f"  Period:     {meta['start_date']} to {meta['end_date']}")
    print(f"  Capital:    {meta['initial_capital']}")

    perf = output["performance"]
    print(f"\n  --- Performance ---")
    print(f"  Total Return:     {perf.get('total_return_pct', 'N/A')}")
    print(f"  Sharpe Ratio:     {perf.get('sharpe_ratio', 'N/A')}")
    print(f"  Sortino Ratio:    {perf.get('sortino_ratio', 'N/A')}")
    print(f"  Max Drawdown:     {perf.get('max_drawdown', 'N/A')}")
    print(f"  Calmar Ratio:     {perf.get('calmar_ratio', 'N/A')}")

    trading = output["trading"]
    print(f"\n  --- Trading ---")
    print(f"  Total Trades:     {trading.get('total_trades', 'N/A')}")
    print(f"  Win Rate:         {trading.get('win_rate', 'N/A')}")
    print(f"  Profit Factor:    {trading.get('profit_factor', 'N/A')}")

    risk = output["risk"]
    print(f"\n  --- Risk ---")
    print(f"  Risk Violations:  {risk.get('risk_violations', 0)}")

    if "benchmark" in output:
        bench = output["benchmark"]
        print(f"\n  --- Benchmark ---")
        print(f"  Benchmark Return: {bench.get('benchmark_return', 'N/A')}")
        print(f"  Alpha:            {bench.get('alpha', 'N/A')}")
        print(f"  Beta:             {bench.get('beta', 'N/A')}")

    print("\n" + "=" * 70)


# =============================================================================
# Main
# =============================================================================
async def run_backtest(args: argparse.Namespace) -> None:
    """Execute the backtest."""
    # Build configuration
    config = BacktestConfig(
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        symbols=args.symbols,
        initial_capital=Decimal(str(args.capital)),
        commission_rate=Decimal(str(args.commission)),
        slippage_bps=args.slippage,
        data_frequency=args.interval,
        benchmark_symbol=args.benchmark,
    )

    # Risk limits
    risk_limits = RiskLimits(
        max_position_size=Decimal(str(args.capital)) * Decimal("0.2"),
        max_order_size=Decimal(str(args.capital)) * Decimal("0.05"),
        max_daily_loss=Decimal(str(args.capital)) * Decimal("0.02"),
        max_drawdown_pct=Decimal("0.15"),
        max_var=Decimal(str(args.capital)) * Decimal("0.05"),
        max_concentration_pct=Decimal("0.30"),
        max_leverage=Decimal("1.0"),
    )

    # Load strategy
    strategy_params = None
    if args.strategy_params:
        strategy_params = json.loads(args.strategy_params)
    strategy = load_strategy(args.strategy, strategy_params)

    # Initialize engine
    data_loader = HistoricalDataLoader(
        cache_dir=os.environ.get("DATA_CACHE_DIR", str(PROJECT_ROOT / "data" / "historical")),
        source=os.environ.get("DATA_SOURCE", "yfinance"),
    )

    engine = BacktestEngine(
        config=config,
        risk_engine=RiskEngine(limits=risk_limits),
        pnl_engine=PnLEngine(),
        data_loader=data_loader,
    )

    # Run backtest
    logger.info("Starting backtest...")
    start_time = datetime.now(timezone.utc)
    result = engine.run(strategy=strategy)
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"Backtest completed in {elapsed:.2f}s")

    # Format and display results
    output = format_results(result, config)
    print_results(output)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        logger.info(f"Results saved to {output_path}")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Run a backtest using the Enthropy backtesting engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available strategies:
  {', '.join(AVAILABLE_STRATEGIES.keys())}

Examples:
  python scripts/run_backtest.py
  python scripts/run_backtest.py --strategy mean_reversion --symbols BBCA.JK TLKM.JK
  python scripts/run_backtest.py --start 2022-01-01 --end 2023-12-31 --capital 5000000000
  python scripts/run_backtest.py --output results/momentum_2023.json
        """,
    )
    parser.add_argument(
        "--symbols", nargs="+", default=DEFAULT_SYMBOLS,
        help=f"Symbols to backtest (default: {DEFAULT_SYMBOLS})",
    )
    parser.add_argument(
        "--strategy", default="momentum",
        choices=list(AVAILABLE_STRATEGIES.keys()),
        help="Strategy to use (default: momentum)",
    )
    parser.add_argument(
        "--strategy-params", type=str, default=None,
        help='Strategy parameters as JSON string (e.g., \'{"lookback_period": 30}\')',
    )
    parser.add_argument(
        "--start", default="2023-01-01",
        help="Backtest start date (YYYY-MM-DD, default: 2023-01-01)",
    )
    parser.add_argument(
        "--end", default="2023-12-31",
        help="Backtest end date (YYYY-MM-DD, default: 2023-12-31)",
    )
    parser.add_argument(
        "--capital", type=float, default=1_000_000_000,
        help="Initial capital in IDR (default: 1,000,000,000)",
    )
    parser.add_argument(
        "--commission", type=float, default=0.0015,
        help="Commission rate (default: 0.0015 = 0.15%%)",
    )
    parser.add_argument(
        "--slippage", type=int, default=5,
        help="Slippage in basis points (default: 5)",
    )
    parser.add_argument(
        "--interval", default="1d",
        help="Data frequency (default: 1d)",
    )
    parser.add_argument(
        "--benchmark", default="^JKSE",
        help="Benchmark symbol (default: ^JKSE)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output file path for JSON results",
    )
    parser.add_argument(
        "--tenant", default="dev",
        help="Tenant ID (default: dev)",
    )

    args = parser.parse_args()
    asyncio.run(run_backtest(args))


if __name__ == "__main__":
    main()
