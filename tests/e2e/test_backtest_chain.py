"""
End-to-end test for the full backtest chain.

Tests the complete backtest pipeline: data fetching, signal generation,
order simulation, fill modeling, PnL calculation, and report generation.
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest

pytestmark = pytest.mark.e2e

# TODO: update imports when pyhron backtest/strategy interfaces are implemented
# Future paths:
#   from strategy_engine.backtesting.idx_vectorbt_backtest_engine import IDXVectorbtBacktestEngine (as BacktestEngine), BacktestResult
#   from strategy_engine.idx_momentum_cross_section_strategy import IDXMomentumCrossSectionStrategy (as MomentumStrategy)
#   from strategy_engine.idx_bollinger_mean_reversion_strategy import IDXBollingerMeanReversionStrategy (as MeanReversionStrategy)
#   from services.portfolio.pnl_engine import PnLEngine
#   from services.risk.risk_limits import RiskLimitEngine (as RiskEngine), TenantRiskLimits (as RiskLimits)
#   BacktestConfig, HistoricalDataLoader — not yet implemented
pytest.importorskip("pyhron.backtest.config", reason="module not yet implemented")
from pyhron.backtest.config import BacktestConfig
from pyhron.backtest.engine import BacktestEngine
from pyhron.backtest.result import BacktestResult
from pyhron.market_data.historical import HistoricalDataLoader
from pyhron.pnl.engine import PnLEngine
from pyhron.risk.engine import RiskEngine
from pyhron.shared.schemas.risk import RiskLimits
from pyhron.strategy.mean_reversion import MeanReversionStrategy
from pyhron.strategy.momentum import MomentumStrategy

# Skip Conditions
SKIP_E2E = pytest.mark.skipif(
    os.environ.get("SKIP_E2E", "false").lower() == "true",
    reason="SKIP_E2E is set. Skipping end-to-end tests.",
)


# Fixtures
@pytest.fixture
def backtest_config() -> BacktestConfig:
    """Standard backtest configuration."""
    return BacktestConfig(
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        symbols=["BBCA.JK", "TLKM.JK", "BMRI.JK", "BBRI.JK"],
        initial_capital=Decimal("1000000000.00"),  # 1B IDR
        commission_rate=Decimal("0.0015"),  # 0.15%
        slippage_bps=5,
        data_frequency="1d",
        benchmark_symbol="^JKSE",
    )


@pytest.fixture
def risk_limits() -> RiskLimits:
    """Risk limits for backtesting."""
    return RiskLimits(
        max_position_size=Decimal("200000000.00"),
        max_order_size=Decimal("50000000.00"),
        max_daily_loss=Decimal("20000000.00"),
        max_drawdown_pct=Decimal("0.15"),
        max_var=Decimal("50000000.00"),
        max_concentration_pct=Decimal("0.30"),
        max_leverage=Decimal("1.0"),
    )


@pytest.fixture
def historical_loader() -> HistoricalDataLoader:
    """Historical data loader (uses local cache or yfinance)."""
    return HistoricalDataLoader(
        cache_dir=os.environ.get("DATA_CACHE_DIR", "/tmp/pyhron_test_data"),
        source=os.environ.get("DATA_SOURCE", "yfinance"),
    )


@pytest.fixture
def momentum_strategy() -> MomentumStrategy:
    """Momentum strategy with default parameters."""
    return MomentumStrategy(
        lookback_period=20,
        entry_threshold=Decimal("0.02"),
        exit_threshold=Decimal("-0.01"),
        position_size_pct=Decimal("0.10"),
    )


@pytest.fixture
def mean_reversion_strategy() -> MeanReversionStrategy:
    """Mean reversion strategy with default parameters."""
    return MeanReversionStrategy(
        lookback_period=20,
        entry_z_score=Decimal("2.0"),
        exit_z_score=Decimal("0.5"),
        position_size_pct=Decimal("0.08"),
    )


@pytest.fixture
def backtest_engine(
    backtest_config: BacktestConfig,
    risk_limits: RiskLimits,
    historical_loader: HistoricalDataLoader,
) -> BacktestEngine:
    """Fully configured backtest engine."""
    return BacktestEngine(
        config=backtest_config,
        risk_engine=RiskEngine(limits=risk_limits),
        pnl_engine=PnLEngine(),
        data_loader=historical_loader,
    )


# Full Backtest Chain Tests
class TestFullBacktestChain:
    """End-to-end tests for the complete backtest pipeline."""

    @SKIP_E2E
    def test_momentum_strategy_backtest(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
        backtest_config: BacktestConfig,
    ):
        """Full backtest with momentum strategy should produce valid results."""
        result = backtest_engine.run(strategy=momentum_strategy)

        assert isinstance(result, BacktestResult)

        # Result should contain performance metrics
        assert result.total_return is not None
        assert result.sharpe_ratio is not None
        assert result.max_drawdown is not None
        assert result.total_trades >= 0
        assert result.win_rate is not None

        # Date range should match config
        assert result.start_date == backtest_config.start_date
        assert result.end_date == backtest_config.end_date

        # Initial capital should be preserved in metadata
        assert result.initial_capital == backtest_config.initial_capital

    @SKIP_E2E
    def test_mean_reversion_strategy_backtest(
        self,
        backtest_engine: BacktestEngine,
        mean_reversion_strategy: MeanReversionStrategy,
    ):
        """Full backtest with mean reversion should produce valid results."""
        result = backtest_engine.run(strategy=mean_reversion_strategy)

        assert isinstance(result, BacktestResult)
        assert result.total_return is not None
        assert result.total_trades >= 0

    @SKIP_E2E
    def test_backtest_equity_curve(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
        backtest_config: BacktestConfig,
    ):
        """Equity curve should be continuous and start at initial capital."""
        result = backtest_engine.run(strategy=momentum_strategy)

        equity_curve = result.equity_curve
        assert len(equity_curve) > 0

        # First value should be initial capital
        assert equity_curve[0].value == backtest_config.initial_capital

        # All values should be positive (no negative equity)
        assert all(point.value > 0 for point in equity_curve)

        # Dates should be monotonically increasing
        dates = [point.date for point in equity_curve]
        assert dates == sorted(dates)

    @SKIP_E2E
    def test_backtest_trade_log(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
    ):
        """Trade log should contain valid trade records."""
        result = backtest_engine.run(strategy=momentum_strategy)

        if result.total_trades > 0:
            for trade in result.trades:
                assert trade.symbol in ["BBCA.JK", "TLKM.JK", "BMRI.JK", "BBRI.JK"]
                assert trade.quantity > 0
                assert trade.price > 0
                assert trade.commission >= 0
                assert trade.timestamp is not None
                assert trade.direction in ("buy", "sell")

    @SKIP_E2E
    def test_backtest_risk_compliance(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
        risk_limits: RiskLimits,
    ):
        """Backtest should respect risk limits throughout."""
        result = backtest_engine.run(strategy=momentum_strategy)

        # Max drawdown should not exceed limit
        assert abs(result.max_drawdown) <= float(risk_limits.max_drawdown_pct) + 0.001

        # No risk violations should be recorded
        assert len(result.risk_violations) == 0, f"Risk violations detected: {result.risk_violations}"

    @SKIP_E2E
    def test_backtest_pnl_consistency(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
        backtest_config: BacktestConfig,
    ):
        """PnL should be consistent with equity curve."""
        result = backtest_engine.run(strategy=momentum_strategy)

        # Total return should match equity curve change
        if len(result.equity_curve) >= 2:
            initial = result.equity_curve[0].value
            final = result.equity_curve[-1].value
            expected_return = (final - initial) / initial
            assert abs(float(result.total_return) - float(expected_return)) < 0.001

    @SKIP_E2E
    def test_backtest_with_benchmark(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
    ):
        """Backtest should include benchmark comparison metrics."""
        result = backtest_engine.run(strategy=momentum_strategy)

        assert result.benchmark_return is not None
        assert result.alpha is not None
        assert result.beta is not None
        assert result.information_ratio is not None


# Data Loading Tests
class TestBacktestDataLoading:
    """Tests for historical data loading within backtest."""

    @SKIP_E2E
    def test_data_loaded_for_all_symbols(
        self,
        historical_loader: HistoricalDataLoader,
        backtest_config: BacktestConfig,
    ):
        """Data should be loaded for all configured symbols."""
        data = historical_loader.load(
            symbols=backtest_config.symbols,
            start_date=backtest_config.start_date,
            end_date=backtest_config.end_date,
        )

        for symbol in backtest_config.symbols:
            assert symbol in data, f"Missing data for {symbol}"
            assert len(data[symbol]) > 0, f"Empty data for {symbol}"

    @SKIP_E2E
    def test_data_has_no_gaps(
        self,
        historical_loader: HistoricalDataLoader,
        backtest_config: BacktestConfig,
    ):
        """Loaded data should not have unexpected gaps."""
        data = historical_loader.load(
            symbols=["BBCA.JK"],
            start_date=backtest_config.start_date,
            end_date=backtest_config.end_date,
        )

        bars = data["BBCA.JK"]
        dates = [bar.date for bar in bars]

        # Check for gaps longer than 5 days (weekends + holidays tolerance)
        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i - 1]).days
            assert gap <= 5, f"Data gap of {gap} days found at {dates[i]}"

    @SKIP_E2E
    def test_data_ohlcv_integrity(
        self,
        historical_loader: HistoricalDataLoader,
        backtest_config: BacktestConfig,
    ):
        """OHLCV data should have correct relationships."""
        data = historical_loader.load(
            symbols=["BBCA.JK"],
            start_date=backtest_config.start_date,
            end_date=backtest_config.end_date,
        )

        for bar in data["BBCA.JK"]:
            assert bar.high >= bar.low, f"High < Low on {bar.date}"
            assert bar.high >= bar.open, f"High < Open on {bar.date}"
            assert bar.high >= bar.close, f"High < Close on {bar.date}"
            assert bar.low <= bar.open, f"Low > Open on {bar.date}"
            assert bar.low <= bar.close, f"Low > Close on {bar.date}"
            assert bar.volume >= 0, f"Negative volume on {bar.date}"


# Report Generation Tests
class TestBacktestReportGeneration:
    """Tests for backtest report generation."""

    @SKIP_E2E
    def test_generate_html_report(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
    ):
        """HTML report should be generatable from results."""
        result = backtest_engine.run(strategy=momentum_strategy)
        html = result.to_html()

        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "sharpe" in html.lower()
        assert "drawdown" in html.lower()

    @SKIP_E2E
    def test_generate_json_report(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
    ):
        """JSON report should be serializable."""
        result = backtest_engine.run(strategy=momentum_strategy)
        json_data = result.to_dict()

        assert isinstance(json_data, dict)
        assert "total_return" in json_data
        assert "sharpe_ratio" in json_data
        assert "max_drawdown" in json_data
        assert "trades" in json_data
        assert "equity_curve" in json_data

    @SKIP_E2E
    def test_report_includes_strategy_params(
        self,
        backtest_engine: BacktestEngine,
        momentum_strategy: MomentumStrategy,
    ):
        """Report should include strategy parameters for reproducibility."""
        result = backtest_engine.run(strategy=momentum_strategy)
        report = result.to_dict()

        assert "strategy" in report
        assert report["strategy"]["name"] == "MomentumStrategy"
        assert "parameters" in report["strategy"]
        assert "lookback_period" in report["strategy"]["parameters"]
