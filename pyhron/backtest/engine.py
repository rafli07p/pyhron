from __future__ import annotations

from pyhron.backtest.config import BacktestConfig
from pyhron.backtest.result import BacktestResult


class BacktestEngine:
    def __init__(self, config: BacktestConfig, risk_engine, pnl_engine, data_loader) -> None:
        self.config = config
        self.risk_engine = risk_engine
        self.pnl_engine = pnl_engine
        self.data_loader = data_loader
        self._strategy_name: str | None = None
        self._strategy_params: dict | None = None

    def run(self, strategy) -> BacktestResult:
        self._strategy_name = strategy.name
        self._strategy_params = strategy.parameters
        raise NotImplementedError("BacktestEngine.run is not yet implemented")
