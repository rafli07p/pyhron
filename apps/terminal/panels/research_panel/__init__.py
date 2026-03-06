"""Research Panel for the Enthropy Terminal.

Provides access to backtesting, factor analysis, and dataset browsing
directly from the terminal interface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Summary of a backtest execution for display."""

    backtest_id: str = ""
    strategy_name: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    status: str = "PENDING"


@dataclass
class FactorResult:
    """Summary of a factor analysis run."""

    factor_name: str = ""
    ic_mean: float = 0.0
    ic_std: float = 0.0
    turnover: float = 0.0
    returns_1d: float = 0.0
    returns_5d: float = 0.0
    timestamp: Optional[datetime] = None


class ResearchPanel:
    """Access backtests, factor research, and datasets from the terminal.

    Provides a UI-oriented interface to the research services including
    backtest execution, factor analysis review, and dataset exploration.

    Parameters
    ----------
    data_client:
        Instance of ``apps.terminal.data_client.DataClient`` for calling
        research service endpoints. If ``None``, operates in offline mode.
    """

    def __init__(self, data_client: Any = None) -> None:
        self._data_client = data_client
        self._recent_backtests: list[BacktestResult] = []
        self._recent_factors: list[FactorResult] = []
        logger.info("ResearchPanel initialized")

    async def run_backtest_ui(
        self,
        strategy_name: str,
        start_date: str,
        end_date: str,
        symbols: list[str],
        initial_capital: float = 1_000_000.0,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Launch a backtest from the terminal UI.

        Parameters
        ----------
        strategy_name:
            Name of the strategy to backtest.
        start_date:
            Backtest start date (ISO format).
        end_date:
            Backtest end date (ISO format).
        symbols:
            Universe of symbols to include.
        initial_capital:
            Starting portfolio value.
        params:
            Additional strategy parameters.

        Returns
        -------
        dict[str, Any]
            Backtest submission result with ID and initial status.
        """
        config = {
            "strategy_name": strategy_name,
            "start_date": start_date,
            "end_date": end_date,
            "symbols": symbols,
            "initial_capital": initial_capital,
            "params": params or {},
        }

        result: dict[str, Any] = {"status": "SUBMITTED", "config": config}

        if self._data_client is not None:
            try:
                response = await self._data_client.run_backtest(config)
                if isinstance(response, dict):
                    result.update(response)
                    bt = BacktestResult(
                        backtest_id=response.get("backtest_id", ""),
                        strategy_name=strategy_name,
                        start_date=datetime.fromisoformat(start_date),
                        end_date=datetime.fromisoformat(end_date),
                        status=response.get("status", "RUNNING"),
                    )
                    self._recent_backtests.append(bt)
            except Exception as exc:
                logger.error("Backtest submission failed: %s", exc)
                result["status"] = "FAILED"
                result["error"] = str(exc)

        logger.info("Submitted backtest for '%s' (%s to %s)", strategy_name, start_date, end_date)
        return result

    async def show_factor_analysis(
        self,
        factor_name: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Display factor analysis results.

        Parameters
        ----------
        factor_name:
            Specific factor to show. If ``None``, shows all recent results.
        limit:
            Maximum number of results to return.

        Returns
        -------
        list[dict[str, Any]]
            Factor analysis summaries.
        """
        if self._data_client is not None:
            try:
                response = await self._data_client.get_market_data(
                    symbol="",
                    data_type="factor_analysis",
                    factor_name=factor_name,
                    limit=limit,
                )
                if isinstance(response, list):
                    self._recent_factors = [
                        FactorResult(
                            factor_name=f.get("factor_name", ""),
                            ic_mean=f.get("ic_mean", 0.0),
                            ic_std=f.get("ic_std", 0.0),
                            turnover=f.get("turnover", 0.0),
                            returns_1d=f.get("returns_1d", 0.0),
                            returns_5d=f.get("returns_5d", 0.0),
                        )
                        for f in response
                    ]
            except Exception as exc:
                logger.error("Factor analysis fetch failed: %s", exc)

        factors = self._recent_factors
        if factor_name:
            factors = [f for f in factors if f.factor_name == factor_name]

        return [
            {
                "factor_name": f.factor_name,
                "ic_mean": f.ic_mean,
                "ic_std": f.ic_std,
                "turnover": f.turnover,
                "returns_1d": f.returns_1d,
                "returns_5d": f.returns_5d,
            }
            for f in factors[:limit]
        ]

    async def list_datasets(self, category: Optional[str] = None) -> list[dict[str, Any]]:
        """List available datasets for research.

        Parameters
        ----------
        category:
            Optional category filter (e.g., ``equity``, ``macro``, ``alternative``).

        Returns
        -------
        list[dict[str, Any]]
            Available datasets with name, description, and metadata.
        """
        datasets: list[dict[str, Any]] = []

        if self._data_client is not None:
            try:
                response = await self._data_client.get_market_data(
                    symbol="",
                    data_type="datasets",
                    category=category,
                )
                if isinstance(response, list):
                    datasets = response
            except Exception as exc:
                logger.error("Dataset listing failed: %s", exc)

        if category:
            datasets = [d for d in datasets if d.get("category") == category]

        logger.info("Listed %d datasets (category=%s)", len(datasets), category)
        return datasets


__all__ = [
    "ResearchPanel",
    "BacktestResult",
    "FactorResult",
]
