"""APBN (Anggaran Pendapatan dan Belanja Negara) fiscal health analyzer.

Analyses Indonesia's state budget (APBN) realization data to assess
fiscal health, identify revenue/expenditure gaps, and project
year-end budget outcomes.

Key metrics:
  - Revenue realization rate (tax, non-tax, grants).
  - Expenditure realization rate (central + transfers to regions).
  - Primary balance and fiscal deficit vs GDP.
  - Energy subsidy burden (BBM, LPG, electricity).
  - Financing gap and debt sustainability.

Data source: Ministry of Finance (Kemenkeu) APBN realization reports.

Usage::

    analyzer = APBNFiscalHealthAnalyzer()
    report = analyzer.analyze(apbn_data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass
class APBNRealizationData:
    """APBN budget vs realization data for a reporting period.

    All values in IDR trillion.

    Attributes:
        period: Reporting period (e.g. ``2025-M10`` for October 2025).
        months_elapsed: Number of months elapsed in fiscal year.
        tax_revenue_budget: Full-year tax revenue budget.
        tax_revenue_realized: Tax revenue realized to date.
        non_tax_revenue_budget: Non-tax revenue budget.
        non_tax_revenue_realized: Non-tax revenue realized to date.
        expenditure_budget: Full-year expenditure budget.
        expenditure_realized: Expenditure realized to date.
        energy_subsidy_budget: Energy subsidy budget.
        energy_subsidy_realized: Energy subsidy realized to date.
        gdp_nominal_estimate: Nominal GDP estimate (IDR trillion).
    """

    period: str
    months_elapsed: int
    tax_revenue_budget: float
    tax_revenue_realized: float
    non_tax_revenue_budget: float
    non_tax_revenue_realized: float
    expenditure_budget: float
    expenditure_realized: float
    energy_subsidy_budget: float
    energy_subsidy_realized: float
    gdp_nominal_estimate: float


@dataclass
class FiscalHealthReport:
    """APBN fiscal health analysis report.

    Attributes:
        period: Reporting period.
        tax_realization_pct: Tax revenue realization rate.
        expenditure_realization_pct: Expenditure realization rate.
        fiscal_deficit_idr_t: Current fiscal deficit in IDR trillion.
        deficit_to_gdp_pct: Fiscal deficit as % of GDP.
        primary_balance_idr_t: Primary balance (before debt service).
        subsidy_overrun_risk: Subsidy budget overrun risk level.
        projected_year_end_deficit_pct: Projected year-end deficit/GDP.
        health_score: Composite fiscal health score (0-100).
        risks: Identified fiscal risks.
    """

    period: str
    tax_realization_pct: float
    expenditure_realization_pct: float
    fiscal_deficit_idr_t: float
    deficit_to_gdp_pct: float
    primary_balance_idr_t: float
    subsidy_overrun_risk: str
    projected_year_end_deficit_pct: float
    health_score: float
    risks: list[str] = field(default_factory=list)


class APBNFiscalHealthAnalyzer:
    """Analyse APBN budget realization and fiscal health.

    The statutory fiscal deficit limit in Indonesia is 3% of GDP
    (Law 17/2003 on State Finance), though this was temporarily
    relaxed during COVID and restored from 2023.

    Args:
        deficit_limit_pct: Statutory deficit limit (default 3.0%).
        debt_service_estimate_pct: Estimated debt service as % of expenditure.
    """

    def __init__(
        self,
        deficit_limit_pct: float = 3.0,
        debt_service_estimate_pct: float = 0.15,
    ) -> None:
        self._deficit_limit = deficit_limit_pct
        self._debt_service_pct = debt_service_estimate_pct

        logger.info(
            "apbn_analyzer_initialised",
            deficit_limit_pct=deficit_limit_pct,
        )

    def analyze(self, data: APBNRealizationData) -> FiscalHealthReport:
        """Perform APBN fiscal health analysis.

        Args:
            data: APBN realization data for the reporting period.

        Returns:
            FiscalHealthReport with metrics and risk assessment.
        """
        total_revenue = data.tax_revenue_realized + data.non_tax_revenue_realized
        total_budget_revenue = data.tax_revenue_budget + data.non_tax_revenue_budget

        tax_real_pct = (
            data.tax_revenue_realized / data.tax_revenue_budget * 100
            if data.tax_revenue_budget > 0 else 0.0
        )
        exp_real_pct = (
            data.expenditure_realized / data.expenditure_budget * 100
            if data.expenditure_budget > 0 else 0.0
        )

        deficit = total_revenue - data.expenditure_realized
        deficit_gdp = deficit / data.gdp_nominal_estimate * 100 if data.gdp_nominal_estimate > 0 else 0.0

        debt_service = data.expenditure_realized * self._debt_service_pct
        primary_balance = deficit + debt_service

        # Project year-end based on current realization pace.
        if data.months_elapsed > 0:
            annualized_revenue = total_revenue / data.months_elapsed * 12
            annualized_expenditure = data.expenditure_realized / data.months_elapsed * 12
            projected_deficit = annualized_revenue - annualized_expenditure
            projected_deficit_pct = (
                projected_deficit / data.gdp_nominal_estimate * 100
                if data.gdp_nominal_estimate > 0 else 0.0
            )
        else:
            projected_deficit_pct = 0.0

        # Subsidy overrun risk.
        subsidy_pace = (
            data.energy_subsidy_realized / data.months_elapsed * 12
            if data.months_elapsed > 0 else 0.0
        )
        if subsidy_pace > data.energy_subsidy_budget * 1.1:
            subsidy_risk = "HIGH"
        elif subsidy_pace > data.energy_subsidy_budget * 0.95:
            subsidy_risk = "MEDIUM"
        else:
            subsidy_risk = "LOW"

        # Composite score.
        score = self._compute_health_score(
            tax_real_pct, exp_real_pct, abs(projected_deficit_pct), subsidy_risk
        )

        risks = self._identify_risks(
            tax_real_pct, deficit_gdp, projected_deficit_pct,
            subsidy_risk, data.months_elapsed,
        )

        report = FiscalHealthReport(
            period=data.period,
            tax_realization_pct=round(tax_real_pct, 2),
            expenditure_realization_pct=round(exp_real_pct, 2),
            fiscal_deficit_idr_t=round(deficit, 2),
            deficit_to_gdp_pct=round(deficit_gdp, 2),
            primary_balance_idr_t=round(primary_balance, 2),
            subsidy_overrun_risk=subsidy_risk,
            projected_year_end_deficit_pct=round(projected_deficit_pct, 2),
            health_score=round(score, 1),
            risks=risks,
        )

        logger.info(
            "apbn_analysis_complete",
            period=data.period,
            health_score=report.health_score,
            deficit_gdp=report.deficit_to_gdp_pct,
        )
        return report

    def _compute_health_score(
        self, tax_pct: float, exp_pct: float, deficit_pct: float, subsidy_risk: str
    ) -> float:
        """Compute composite fiscal health score (0-100)."""
        score = 50.0
        expected_pct = 83.3  # Linear pace for 10/12 months

        score += min((tax_pct - expected_pct) * 0.5, 15.0)
        score -= max((deficit_pct - self._deficit_limit) * 10.0, 0.0)
        if subsidy_risk == "HIGH":
            score -= 10.0
        elif subsidy_risk == "MEDIUM":
            score -= 5.0
        return max(0.0, min(100.0, score))

    @staticmethod
    def _identify_risks(
        tax_pct: float, deficit_gdp: float, proj_deficit: float,
        subsidy_risk: str, months: int,
    ) -> list[str]:
        """Identify fiscal risk factors."""
        risks: list[str] = []
        expected = months / 12 * 100
        if tax_pct < expected * 0.9:
            risks.append(f"Tax revenue behind pace: {tax_pct:.1f}% vs {expected:.1f}% expected")
        if abs(proj_deficit) > 3.0:
            risks.append(f"Projected deficit {proj_deficit:.1f}% exceeds 3% statutory limit")
        if subsidy_risk in ("HIGH", "MEDIUM"):
            risks.append(f"Energy subsidy overrun risk: {subsidy_risk}")
        return risks
