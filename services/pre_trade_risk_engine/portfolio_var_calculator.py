"""Portfolio Value-at-Risk (VaR) calculator.

Provides parametric VaR estimation using the variance-covariance method
(Gaussian assumption). Supports both portfolio-level and incremental VaR
computation for pre-trade risk assessment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from shared.proto_generated.equity_positions_pb2 import PortfolioSnapshot

logger = get_logger(__name__)

# Standard normal Z-scores for common confidence levels
Z_SCORES: dict[float, float] = {
    0.90: 1.2816,
    0.95: 1.6449,
    0.99: 2.3263,
}

# Default daily volatility assumption for instruments without historical data
DEFAULT_DAILY_VOLATILITY: float = 0.02  # 2%

# Default correlation assumption between instruments
DEFAULT_CORRELATION: float = 0.30


@dataclass(frozen=True)
class VaRResult:
    """Result of a VaR calculation.

    Attributes:
        var_absolute: VaR in absolute currency terms (potential loss).
        var_percentage: VaR as a percentage of total portfolio value.
        confidence_level: The confidence level used (e.g. 0.95 for 95%).
        holding_period_days: Number of trading days for the VaR horizon.
        method: Calculation method ("parametric", "historical", "monte_carlo").
        component_vars: Per-position VaR contributions if computed.
    """

    var_absolute: float
    var_percentage: float
    confidence_level: float
    holding_period_days: int
    method: str
    component_vars: dict[str, float] = field(default_factory=dict)


class PortfolioVaRCalculator:
    """Parametric VaR calculator for portfolio risk measurement.

    Uses the variance-covariance (delta-normal) method to estimate
    portfolio VaR. Supports per-position volatility overrides and a
    configurable correlation matrix.

    The parametric approach assumes normally distributed returns, which
    is computationally efficient for pre-trade risk checks but may
    underestimate tail risk.

    Usage::

        calculator = PortfolioVaRCalculator()
        calculator.set_volatility("BBCA", 0.018)
        calculator.set_volatility("BBRI", 0.022)
        result = calculator.compute_portfolio_var(portfolio_snapshot)
        print(f"95% 1-day VaR: {result.var_percentage:.2%}")
    """

    def __init__(
        self,
        confidence_level: float = 0.95,
        holding_period_days: int = 1,
    ) -> None:
        """Initialize the VaR calculator.

        Args:
            confidence_level: Confidence level for VaR (default 0.95).
            holding_period_days: Holding period in trading days (default 1).
        """
        self._confidence_level: float = confidence_level
        self._holding_period_days: int = holding_period_days
        self._volatilities: dict[str, float] = {}
        self._correlations: dict[tuple[str, str], float] = {}
        self._z_score: float = Z_SCORES.get(confidence_level, 1.6449)

    def set_volatility(self, symbol: str, daily_volatility: float) -> None:
        """Set the daily volatility for a specific instrument.

        Args:
            symbol: The instrument ticker symbol.
            daily_volatility: Annualized or daily volatility as a decimal
                (e.g. 0.02 for 2% daily vol).
        """
        self._volatilities[symbol] = daily_volatility

    def set_correlation(self, symbol_a: str, symbol_b: str, correlation: float) -> None:
        """Set the correlation between two instruments.

        Args:
            symbol_a: First instrument ticker symbol.
            symbol_b: Second instrument ticker symbol.
            correlation: Correlation coefficient in [-1, 1].
        """
        self._correlations[(symbol_a, symbol_b)] = correlation
        self._correlations[(symbol_b, symbol_a)] = correlation

    def get_volatility(self, symbol: str) -> float:
        """Get the daily volatility for a symbol, falling back to default.

        Args:
            symbol: The instrument ticker symbol.

        Returns:
            The daily volatility as a decimal.
        """
        return self._volatilities.get(symbol, DEFAULT_DAILY_VOLATILITY)

    def get_correlation(self, symbol_a: str, symbol_b: str) -> float:
        """Get the correlation between two symbols, falling back to default.

        Args:
            symbol_a: First instrument ticker symbol.
            symbol_b: Second instrument ticker symbol.

        Returns:
            The correlation coefficient.
        """
        if symbol_a == symbol_b:
            return 1.0
        return self._correlations.get((symbol_a, symbol_b), DEFAULT_CORRELATION)

    def compute_portfolio_var(self, portfolio: PortfolioSnapshot) -> VaRResult:
        """Compute parametric VaR for the entire portfolio.

        Uses the variance-covariance method:
          1. Compute individual position VaR for each holding.
          2. Build the portfolio variance using pairwise correlations.
          3. Scale by the Z-score and holding period.

        Args:
            portfolio: The portfolio snapshot containing current positions.

        Returns:
            A VaRResult with absolute and percentage VaR.
        """
        total_value = portfolio.total_market_value + portfolio.cash_balance
        if total_value <= 0:
            return VaRResult(
                var_absolute=0.0,
                var_percentage=0.0,
                confidence_level=self._confidence_level,
                holding_period_days=self._holding_period_days,
                method="parametric",
            )

        positions: list[tuple[str, float]] = []
        component_vars: dict[str, float] = {}

        for pos in portfolio.positions:
            if pos.market_value > 0:
                positions.append((pos.symbol, pos.market_value))

        if not positions:
            return VaRResult(
                var_absolute=0.0,
                var_percentage=0.0,
                confidence_level=self._confidence_level,
                holding_period_days=self._holding_period_days,
                method="parametric",
            )

        # Compute portfolio variance using correlation matrix
        portfolio_variance = 0.0
        for _i, (sym_i, val_i) in enumerate(positions):
            vol_i = self.get_volatility(sym_i)
            var_i = val_i * vol_i
            component_vars[sym_i] = var_i * self._z_score

            for _j, (sym_j, val_j) in enumerate(positions):
                vol_j = self.get_volatility(sym_j)
                corr = self.get_correlation(sym_i, sym_j)
                portfolio_variance += val_i * vol_i * val_j * vol_j * corr

        # Portfolio VaR = Z * sqrt(portfolio_variance) * sqrt(holding_period)
        portfolio_std = math.sqrt(max(0.0, portfolio_variance))
        var_absolute = self._z_score * portfolio_std * math.sqrt(self._holding_period_days)
        var_percentage = var_absolute / total_value if total_value > 0 else 0.0

        logger.debug(
            "portfolio_var_computed",
            var_absolute=round(var_absolute, 2),
            var_percentage=round(var_percentage, 4),
            confidence_level=self._confidence_level,
            num_positions=len(positions),
        )

        return VaRResult(
            var_absolute=round(var_absolute, 2),
            var_percentage=round(var_percentage, 6),
            confidence_level=self._confidence_level,
            holding_period_days=self._holding_period_days,
            method="parametric",
            component_vars=component_vars,
        )

    def compute_incremental_var(
        self,
        portfolio: PortfolioSnapshot,
        symbol: str,
        additional_value: float,
    ) -> float:
        """Estimate the incremental VaR from adding a new position.

        Computes the difference between portfolio VaR with and without
        the additional position. Used for pre-trade risk assessment.

        Args:
            portfolio: Current portfolio snapshot.
            symbol: The symbol being added.
            additional_value: Market value of the proposed additional position.

        Returns:
            The estimated incremental VaR as a percentage of portfolio value.
        """
        # Current VaR
        current_result = self.compute_portfolio_var(portfolio)
        current_var = current_result.var_absolute

        # Estimate new VaR with additional position
        total_value = portfolio.total_market_value + portfolio.cash_balance
        if total_value <= 0:
            return 0.0

        new_total = total_value + additional_value
        vol = self.get_volatility(symbol)

        # Marginal VaR contribution (linear approximation)
        additional_var_standalone = additional_value * vol * self._z_score

        # Account for diversification benefit via average correlation
        avg_corr = DEFAULT_CORRELATION
        diversified_contribution = additional_var_standalone * math.sqrt(
            1.0 + 2.0 * avg_corr * (current_var / additional_var_standalone) if additional_var_standalone > 0 else 1.0
        )

        incremental_var = diversified_contribution - current_var
        incremental_var_pct = incremental_var / new_total if new_total > 0 else 0.0

        return round(incremental_var_pct, 6)
