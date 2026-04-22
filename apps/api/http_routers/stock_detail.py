"""IDX equity stock detail API endpoints.

Single stock deep dive: profile, financials, corporate actions,
and ownership structure.
"""

import asyncio
import contextlib
from datetime import date
from decimal import Decimal
from functools import partial
from typing import Any

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from data_platform.database_models.idx_equity_instrument import IdxEquityInstrument
from shared.async_database_session import get_session
from shared.security.auth import TokenPayload
from shared.security.rbac import Role, require_role
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/stocks", tags=["stock-detail"], redirect_slashes=False)


# Response Models
class StockProfile(BaseModel):
    symbol: str
    name: str
    exchange: str = "IDX"
    sector: str | None = None
    industry: str | None = None
    listing_date: date | None = None
    market_cap: Decimal | None = None
    last_price: Decimal | None = None
    shares_outstanding: int | None = None
    is_lq45: bool = False
    description: str | None = None


class FinancialSummary(BaseModel):
    symbol: str
    period: str
    statement_type: str
    revenue: Decimal | None = None
    net_income: Decimal | None = None
    total_assets: Decimal | None = None
    total_liabilities: Decimal | None = None
    total_equity: Decimal | None = None
    operating_income: Decimal | None = None
    gross_profit: Decimal | None = None
    operating_cash_flow: Decimal | None = None
    capex: Decimal | None = None
    free_cash_flow: Decimal | None = None


class FinancialFactsResponse(BaseModel):
    symbol: str
    periods: list[str]
    sections: list[dict[str, object]]


class CorporateAction(BaseModel):
    symbol: str
    action_type: str = Field(description="dividend, stock_split, rights_issue, etc.")
    ex_date: date
    record_date: date | None = None
    description: str
    value: Decimal | None = None


class OwnershipEntry(BaseModel):
    holder_name: str
    holder_type: str = Field(description="institution, insider, public")
    shares_held: int
    ownership_pct: float
    change_from_prior: float | None = None


# Endpoints
# NOTE: `/` must be registered before `/{symbol}` so FastAPI matches it first.
@router.get("", response_model=list[dict[str, str]])
async def list_symbols(
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[dict[str, str]]:
    """List all active IDX instruments for dropdown."""
    async with get_session() as session:
        result = await session.execute(
            select(IdxEquityInstrument.symbol, IdxEquityInstrument.company_name)
            .where(IdxEquityInstrument.is_active.is_(True))
            .order_by(IdxEquityInstrument.symbol)
        )
        rows = result.all()
    return [{"symbol": r.symbol, "name": r.company_name} for r in rows]


@router.get("/{symbol}", response_model=StockProfile)
async def get_stock_profile(
    symbol: str,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> StockProfile:
    """Get stock profile enriched with yfinance data."""
    logger.info("stock_profile_queried", symbol=symbol)

    async with get_session() as session:
        result = await session.execute(
            select(IdxEquityInstrument).where(
                IdxEquityInstrument.symbol == symbol.upper(),
                IdxEquityInstrument.is_active.is_(True),
            )
        )
        instrument = result.scalar_one_or_none()

    if instrument is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found",
        )

    def _fetch_yf(sym: str) -> dict[str, Any]:
        try:
            ticker = yf.Ticker(f"{sym}.JK")
            info = ticker.info or {}
            hist = ticker.history(period="2d")
            last_price = float(hist["Close"].iloc[-1]) if not hist.empty else None
            return {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "description": info.get("longBusinessSummary"),
                "market_cap": info.get("marketCap"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "last_price": last_price,
            }
        except Exception:
            return {}

    loop = asyncio.get_event_loop()
    yf_data = await loop.run_in_executor(None, partial(_fetch_yf, symbol.upper()))

    return StockProfile(
        symbol=instrument.symbol,
        name=instrument.company_name,
        exchange="IDX",
        sector=yf_data.get("sector") or instrument.sector,
        industry=yf_data.get("industry"),
        listing_date=instrument.listing_date,
        market_cap=(
            Decimal(str(yf_data["market_cap"]))
            if yf_data.get("market_cap")
            else (Decimal(instrument.market_cap_idr) if instrument.market_cap_idr else None)
        ),
        last_price=(
            Decimal(str(yf_data["last_price"])) if yf_data.get("last_price") else None
        ),
        shares_outstanding=yf_data.get("shares_outstanding") or instrument.shares_outstanding,
        is_lq45=False,
        description=yf_data.get("description"),
    )


@router.get("/{symbol}/financials", response_model=list[FinancialSummary])
async def get_financials(
    symbol: str,
    statement_type: str = Query("income", pattern="^(income|balance|cashflow)$"),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[FinancialSummary]:
    """Get financial statements from IDX XBRL data in TimescaleDB."""
    logger.info("financials_queried", symbol=symbol, statement_type=statement_type)
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    symbol, period, statement_type,
                    revenue_idr, net_income_idr,
                    total_assets_idr, total_liabilities_idr, total_equity_idr,
                    operating_income_idr,
                    gross_profit_idr,
                    operating_cash_flow_idr,
                    capital_expenditure_idr,
                    free_cash_flow_idr
                FROM financial_statements
                WHERE symbol = :symbol
                  AND statement_type = :statement_type
                ORDER BY period DESC
                LIMIT 12
            """),
            {"symbol": symbol.upper(), "statement_type": statement_type},
        )
        rows = result.mappings().all()
    return [
        FinancialSummary(
            symbol=r["symbol"],
            period=r["period"],
            statement_type=r["statement_type"],
            revenue=r["revenue_idr"],
            net_income=r["net_income_idr"],
            total_assets=r["total_assets_idr"],
            total_liabilities=r["total_liabilities_idr"],
            total_equity=r["total_equity_idr"],
            operating_income=r["operating_income_idr"],
            gross_profit=r["gross_profit_idr"],
            operating_cash_flow=r["operating_cash_flow_idr"],
            capex=r["capital_expenditure_idr"],
            free_cash_flow=r["free_cash_flow_idr"],
        )
        for r in rows
    ]


@router.get("/{symbol}/financial-facts", response_model=FinancialFactsResponse)
async def get_financial_facts(
    symbol: str,
    context_type: str = Query(
        "income_current",
        pattern="^(income_current|income_prior|balance_current|balance_prior)$",
    ),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> FinancialFactsResponse:
    """Get full XBRL financial facts from EAV table."""
    logger.info("financial_facts_queried", symbol=symbol, context_type=context_type)

    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT period, metric, value
                FROM financial_facts
                WHERE symbol = :symbol
                  AND context_type = :context_type
                ORDER BY period ASC, metric ASC
            """),
            {"symbol": symbol.upper(), "context_type": context_type},
        )
        rows = result.mappings().all()

    pivot: dict[str, dict[str, str]] = {}
    periods_set: set[str] = set()
    for row in rows:
        metric = str(row["metric"])
        period = str(row["period"])
        value = str(row["value"]) if row["value"] is not None else None
        periods_set.add(period)
        if metric not in pivot:
            pivot[metric] = {}
        if value is not None:
            pivot[metric][period] = value

    def period_order(p: str) -> int:
        parts = p.split("-")
        year = int(parts[0]) if parts[0].isdigit() else 0
        q_map = {"Q1": 1, "Q2": 2, "Q3": 3, "Annual": 4}
        q = q_map.get(parts[1] if len(parts) > 1 else "", 0)
        return year * 10 + q

    periods = sorted(periods_set, key=period_order)

    income_sections: list[dict[str, object]] = [
        {
            "title": "Interest Income",
            "rows": [
                {"label": "Total Interest & Sharia Income", "metric": "TotalInterestAndShariaIncome", "bold": True},
                {"label": "Interest Income", "metric": "SubtotalInterestIncome", "indent": True},
                {"label": "Loan Interest Income", "metric": "LoansInterestIncome", "indent": True},
                {"label": "Securities Income", "metric": "MarketableSecuritiesIncome", "indent": True},
                {"label": "Placement Income", "metric": "PlacementsWithBankIndonesiaAndOtherBanksIncome", "indent": True},
                {"label": "Sharia Income", "metric": "SubtotalShariaIncome", "indent": True},
                {"label": "Total Interest & Sharia Expense", "metric": "TotalInterestAndShariaExpense", "bold": True},
                {"label": "Time Deposit Expense", "metric": "TimeDepositsInterestExpense", "indent": True},
                {"label": "Savings Deposit Expense", "metric": "SavingDepositsInterestExpense", "indent": True},
                {"label": "Borrowing Expense", "metric": "BorrowingsInterestExpense", "indent": True},
                {"label": "Guarantee Premium", "metric": "PremiumOnThirdPartyFundGuarantees", "indent": True},
            ],
        },
        {
            "title": "Other Operating Income",
            "rows": [
                {"label": "Trading Revenue", "metric": "RevenueFromTradingTransactions"},
                {"label": "Realised Derivative Gains/Losses", "metric": "RealisedGainsLossesFromDerivativeInstruments"},
                {"label": "Other Operating Income", "metric": "OtherOperatingIncome", "bold": True},
            ],
        },
        {
            "title": "Operating Expenses",
            "rows": [
                {"label": "Impairment Allowances (CKPN)", "metric": "AllowancesForImpairmentLossesOnEarningsAssets"},
                {"label": "Impairment Recovery", "metric": "RecoveryOfImpairmentLossesOfFinancialAssets"},
                {"label": "General & Administrative Expenses", "metric": "GeneralAndAdministrativeExpenses", "bold": True},
                {"label": "Other Operating Expenses", "metric": "OtherOperatingExpenses", "bold": True},
                {"label": "Other Fees & Commissions", "metric": "OtherFeesAndCommissionsExpenses"},
            ],
        },
        {
            "title": "Profit & Loss",
            "rows": [
                {"label": "Operating Profit", "metric": "ProfitFromOperation", "bold": True},
                {"label": "Profit Before Tax", "metric": "ProfitLossBeforeIncomeTax", "bold": True},
                {"label": "Tax Expense", "metric": "TaxBenefitExpenses"},
                {"label": "Net Profit", "metric": "ProfitLoss", "bold": True},
                {"label": "Comprehensive Income", "metric": "ComprehensiveIncome", "bold": True},
                {"label": "Attributable to Parent", "metric": "ProfitLossAttributableToParentEntity", "indent": True},
                {"label": "EPS (Basic)", "metric": "BasicEarningsLossPerShareFromContinuingOperations"},
                {"label": "EPS (Diluted)", "metric": "DilutedEarningsLossPerShareFromContinuingOperations"},
            ],
        },
    ]

    balance_sections: list[dict[str, object]] = [
        {
            "title": "Assets",
            "rows": [
                {"label": "Total Assets", "metric": "Assets", "bold": True},
                {"label": "Cash", "metric": "Cash", "indent": True},
                {"label": "Current Accounts with BI", "metric": "CurrentAccountsWithBankIndonesia", "indent": True},
                {"label": "Placements with Other Banks", "metric": "PlacementsWithBankIndonesiaAndOtherBanksThirdParties", "indent": True},
                {"label": "Marketable Securities", "metric": "MarketableSecuritiesThirdParties", "indent": True},
                {"label": "Securities under Resale Agreement", "metric": "SecuritiesPurchasedUnderAgreementToResale", "indent": True},
                {"label": "Government Bonds", "metric": "GovernmentBonds", "indent": True},
                {"label": "Loans (Third Parties)", "metric": "LoansThirdParties", "indent": True},
                {"label": "Total Loans (Gross)", "metric": "TotalLoansGross", "bold": True},
                {"label": "Total Loans (Net)", "metric": "TotalLoansNet", "indent": True},
                {"label": "Allowance for Loan Losses", "metric": "AllowanceForImpairmentLossesForLoans", "indent": True},
                {"label": "Other Financial Assets", "metric": "OtherFinancialAssets", "indent": True},
                {"label": "Property, Plant & Equipment", "metric": "PropertyPlantAndEquipment", "indent": True},
                {"label": "Goodwill", "metric": "Goodwill", "indent": True},
                {"label": "Deferred Tax Assets", "metric": "DeferredTaxAssets", "indent": True},
                {"label": "Other Assets", "metric": "OtherAssets", "indent": True},
            ],
        },
        {
            "title": "Liabilities",
            "rows": [
                {"label": "Total Liabilities", "metric": "Liabilities", "bold": True},
                {"label": "Current Accounts (Deposits)", "metric": "CurrentAccounts", "indent": True},
                {"label": "Savings Deposits", "metric": "SavingsDeposits", "indent": True},
                {"label": "Time Deposits", "metric": "TimeDeposits", "indent": True},
                {"label": "Sharia Deposits", "metric": "ShariaDeposits", "indent": True},
                {"label": "Interbank Deposits", "metric": "OtherBanksDepositsThirdParties", "indent": True},
                {"label": "Derivative Payables", "metric": "DerivativePayablesThirdParties", "indent": True},
                {"label": "Borrowings", "metric": "Borrowings", "indent": True},
                {"label": "Post-Employment Obligations", "metric": "PostEmploymentBenefitObligations", "indent": True},
                {"label": "Taxes Payable", "metric": "TaxesPayable", "indent": True},
                {"label": "Other Liabilities", "metric": "OtherLiabilities", "indent": True},
                {"label": "Temporary Syirkah Funds", "metric": "TemporarySyirkahFunds", "bold": True},
            ],
        },
        {
            "title": "Equity",
            "rows": [
                {"label": "Total Equity", "metric": "Equity", "bold": True},
                {"label": "Common Stock", "metric": "CommonStocks", "indent": True},
                {"label": "Additional Paid-in Capital", "metric": "AdditionalPaidInCapital", "indent": True},
                {"label": "Revaluation Reserves", "metric": "RevaluationReserves", "indent": True},
                {"label": "Retained Earnings", "metric": "UnappropriatedRetainedEarnings", "indent": True},
                {"label": "General & Legal Reserves", "metric": "GeneralAndLegalReserves", "indent": True},
                {"label": "Non-Controlling Interests", "metric": "NonControllingInterests", "indent": True},
            ],
        },
    ]

    cashflow_sections: list[dict[str, object]] = [
        {
            "title": "Operating Activities",
            "rows": [
                {"label": "Net Cash from Operating Activities", "metric": "NetCashFlowsReceivedFromUsedInOperatingActivities", "bold": True},
                {"label": "Interest & Commission Received", "metric": "InterestInvestmentIncomeFeesAndCommissionsReceived", "indent": True},
                {"label": "Interest & Commission Paid", "metric": "PaymentsOfInterestAndBonusFeesAndCommissions", "indent": True},
                {"label": "Income Tax Paid", "metric": "RefundsPaymentsOfIncomeTax", "indent": True},
                {"label": "Other Operating Expenses Paid", "metric": "PaymentsForOtherOperatingExpenses", "indent": True},
                {"label": "Change in Loans", "metric": "DecreaseIncreaseInLoans", "indent": True},
                {"label": "Change in Deposits (Current + Savings)", "metric": "IncreaseDecreaseInCustomersCurrentAccountsAndSavings", "indent": True},
                {"label": "Change in Time Deposits", "metric": "IncreaseDecreaseInCustomersTimeDeposits", "indent": True},
            ],
        },
        {
            "title": "Investing Activities",
            "rows": [
                {"label": "Net Cash from Investing Activities", "metric": "NetCashFlowsReceivedFromUsedInInvestingActivities", "bold": True},
                {"label": "Purchase/Disposal of Fixed Assets", "metric": "ProceedsFromDisposalAcquisitionOfPropertyAndEquipment", "indent": True},
                {"label": "Other Investing Activities", "metric": "OtherCashInflowsOutflowsFromInvestingActivities", "indent": True},
            ],
        },
        {
            "title": "Financing Activities",
            "rows": [
                {"label": "Net Cash from Financing Activities", "metric": "NetCashFlowsReceivedFromUsedInFinancingActivities", "bold": True},
                {"label": "Proceeds from Borrowings", "metric": "ProceedsFromBorrowings", "indent": True},
                {"label": "Repayment of Borrowings", "metric": "PaymentsForBorrowings", "indent": True},
                {"label": "Cash Dividends Paid", "metric": "DistributionsOfCashDividends", "indent": True},
            ],
        },
        {
            "title": "Cash Position",
            "rows": [
                {"label": "Net Change in Cash", "metric": "NetIncreaseDecreaseInCashAndCashEquivalents", "bold": True},
                {"label": "FX Effect on Cash", "metric": "EffectOfExchangeRateChangesOnCashAndCashEquivalents", "indent": True},
                {"label": "Cash & Equivalents", "metric": "CashAndCashEquivalentsCashFlows", "bold": True},
            ],
        },
    ]

    # Cashflow facts are embedded in the *Duration* (income) contexts
    if context_type in ("income_current", "income_prior"):
        all_sections = income_sections + cashflow_sections
    else:
        all_sections = balance_sections

    # Enrich sections with actual values
    enriched: list[dict[str, object]] = []
    for section in all_sections:
        section_rows = section["rows"]
        if not isinstance(section_rows, list):
            continue
        enriched_rows: list[dict[str, object]] = []
        for row_def in section_rows:
            if not isinstance(row_def, dict):
                continue
            metric = str(row_def["metric"])
            values = {p: pivot.get(metric, {}).get(p) for p in periods}
            has_data = any(v is not None for v in values.values())
            if not has_data:
                continue
            enriched_rows.append({
                "label":  row_def.get("label"),
                "metric": metric,
                "bold":   row_def.get("bold", False),
                "indent": row_def.get("indent", False),
                "values": values,
            })
        if enriched_rows:
            enriched.append({"title": section["title"], "rows": enriched_rows})

    return FinancialFactsResponse(
        symbol=symbol.upper(),
        periods=periods,
        sections=enriched,
    )


@router.get("/{symbol}/corporate-actions", response_model=list[CorporateAction])
async def get_corporate_actions(
    symbol: str,
    action_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[CorporateAction]:
    """Get corporate actions history (dividends, splits) via yfinance."""
    def _fetch(sym: str) -> list[dict[str, Any]]:
        try:
            t = yf.Ticker(f"{sym}.JK")
            results: list[dict[str, Any]] = []
            divs = t.dividends
            if divs is not None and not divs.empty:
                for ts, val in divs.tail(limit).items():
                    with contextlib.suppress(Exception):
                        results.append(
                            {
                                "symbol": sym,
                                "action_type": "dividend",
                                "ex_date": ts.date(),
                                "record_date": None,
                                "description": f"Cash Dividend IDR {val:,.0f} per share",
                                "value": float(val),
                            }
                        )
            splits = t.splits
            if splits is not None and not splits.empty:
                for ts, ratio in splits.tail(5).items():
                    with contextlib.suppress(Exception):
                        results.append(
                            {
                                "symbol": sym,
                                "action_type": "stock_split",
                                "ex_date": ts.date(),
                                "record_date": None,
                                "description": f"Stock Split {ratio}:1",
                                "value": float(ratio),
                            }
                        )
            results.sort(key=lambda x: x["ex_date"], reverse=True)
            return results[:limit]
        except Exception:
            logger.warning("corp_actions_fetch_failed", symbol=sym)
            return []

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, partial(_fetch, symbol.upper()))
    if action_type:
        raw = [r for r in raw if r["action_type"] == action_type]
    return [CorporateAction(**r) for r in raw]


@router.get("/{symbol}/ownership", response_model=list[OwnershipEntry])
async def get_ownership(
    symbol: str,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[OwnershipEntry]:
    """Get ownership breakdown (insider/institutional/public) via yfinance."""
    def _fetch(sym: str) -> list[dict[str, Any]]:
        try:
            t = yf.Ticker(f"{sym}.JK")
            holders = t.major_holders
            if holders is None or holders.empty:
                return []

            def _safe_pct(key: str) -> float:
                try:
                    row = holders[holders.index == key]
                    if not row.empty:
                        return float(row.iloc[0, 0]) * 100
                except Exception:
                    return 0.0
                return 0.0

            insider_pct = _safe_pct("insidersPercentHeld")
            inst_pct = _safe_pct("institutionsPercentHeld")
            public_pct = max(0.0, 100.0 - insider_pct - inst_pct)

            results: list[dict[str, Any]] = []
            if insider_pct > 0:
                results.append({
                    "holder_name": "Insider / Management",
                    "holder_type": "insider",
                    "shares_held": 0,
                    "ownership_pct": round(insider_pct, 2),
                    "change_from_prior": None,
                })
            if inst_pct > 0:
                results.append({
                    "holder_name": "Institutional Investors",
                    "holder_type": "institution",
                    "shares_held": 0,
                    "ownership_pct": round(inst_pct, 2),
                    "change_from_prior": None,
                })
            if public_pct > 0:
                results.append({
                    "holder_name": "Public / Retail",
                    "holder_type": "public",
                    "shares_held": 0,
                    "ownership_pct": round(public_pct, 2),
                    "change_from_prior": None,
                })
            return results
        except Exception:
            logger.warning("ownership_fetch_failed", symbol=sym)
            return []

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, partial(_fetch, symbol.upper()))
    return [OwnershipEntry(**r) for r in raw]


# IDX sector peers (static curated list; tier 1 LQ45 constituents)
SECTOR_PEERS: dict[str, list[str]] = {
    "BBCA": ["BBRI", "BMRI", "BBNI", "BNGA", "BDMN"],
    "BBRI": ["BBCA", "BMRI", "BBNI", "BNGA"],
    "BMRI": ["BBCA", "BBRI", "BBNI", "BNGA"],
    "BBNI": ["BBCA", "BBRI", "BMRI", "BNGA"],
    "TLKM": ["EXCL", "ISAT", "FREN"],
    "ASII": ["SMSM", "AUTO", "IMAS"],
    "UNVR": ["ICBP", "MYOR", "KLBF"],
    "GOTO": ["BUKA", "EMTK"],
}


@router.get("/{symbol}/peers", response_model=list[dict[str, Any]])
async def get_peers(
    symbol: str,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[dict[str, Any]]:
    """Get peer comparison — same sector stocks with key metrics."""
    upper = symbol.upper()
    peers = SECTOR_PEERS.get(upper, [])
    if not peers:
        async with get_session() as db:
            instr_res = await db.execute(
                select(IdxEquityInstrument.symbol)
                .where(IdxEquityInstrument.is_active.is_(True))
                .limit(6)
            )
            peers = [r[0] for r in instr_res.all() if r[0] != upper][:5]

    all_symbols = [upper, *peers[:5]]

    def _fetch_peers(syms: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for sym in syms:
            try:
                t = yf.Ticker(f"{sym}.JK")
                info = t.info or {}
                hist_1y = t.history(period="1y")
                hist_2d = t.history(period="2d")
                last_price = round(float(hist_2d["Close"].iloc[-1]), 0) if not hist_2d.empty else None
                price_change_1y = None
                if not hist_1y.empty and len(hist_1y) >= 2:
                    p_start = float(hist_1y["Close"].iloc[0])
                    p_end = float(hist_1y["Close"].iloc[-1])
                    price_change_1y = round((p_end - p_start) / p_start * 100, 2) if p_start else None
                # yfinance returns these fields as decimal fractions (0.0523 = 5.23%).
                raw_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
                dividend_yield = round(float(raw_yield) * 100, 2) if raw_yield else None
                payout = info.get("payoutRatio")
                payout_pct = round(float(payout) * 100, 1) if payout else None
                profit_margin = info.get("profitMargins")
                profit_margin_pct = round(float(profit_margin) * 100, 2) if profit_margin else None
                rev_growth = info.get("revenueGrowth")
                rev_growth_pct = round(float(rev_growth) * 100, 2) if rev_growth else None
                eps_growth = info.get("earningsGrowth")
                eps_growth_pct = round(float(eps_growth) * 100, 2) if eps_growth else None
                roe_raw = info.get("returnOnEquity")
                roe_pct = round(float(roe_raw) * 100, 2) if roe_raw else None
                health = "—"
                if roe_pct is not None:
                    if roe_pct >= 18:
                        health = "Strong"
                    elif roe_pct >= 12:
                        health = "Satisfactory"
                    elif roe_pct >= 6:
                        health = "Marginal"
                    else:
                        health = "Weak"
                results.append({
                    "symbol": sym,
                    "name": info.get("shortName", sym),
                    "health": health,
                    "last_price": last_price,
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "pbv_ratio": info.get("priceToBook"),
                    "roe": roe_pct,
                    "net_profit_margin": profit_margin_pct,
                    "revenue_growth": rev_growth_pct,
                    "eps_growth": eps_growth_pct,
                    "dividend_yield": dividend_yield,
                    "payout_ratio": payout_pct,
                    "price_change_1y": price_change_1y,
                    "is_selected": sym == upper,
                })
            except Exception:
                results.append({
                    "symbol": sym, "name": sym, "health": "—",
                    "last_price": None, "market_cap": None,
                    "pe_ratio": None, "pbv_ratio": None,
                    "roe": None, "net_profit_margin": None,
                    "revenue_growth": None, "eps_growth": None,
                    "dividend_yield": None, "payout_ratio": None,
                    "price_change_1y": None, "is_selected": sym == upper,
                })
        return results

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_fetch_peers, all_symbols))


@router.get("/{symbol}/financial-highlights", response_model=dict[str, Any])
async def get_financial_highlights(
    symbol: str,
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> dict[str, Any]:
    """Get complete financial highlights — curated data for BBCA, yfinance fallback."""
    sym = symbol.upper()

    if sym == "BBCA":
        from apps.api.data.bbca_financials import (
            BBCA_FINANCIAL_POSITION,
            BBCA_INCOME,
            BBCA_RATIOS,
            BBCA_STOCK_HIGHLIGHTS,
        )
        return {
            "symbol": sym,
            "source": "Annual Report 2025 | PT Bank Central Asia Tbk",
            "currency": "IDR Billion",
            "financial_position": BBCA_FINANCIAL_POSITION,
            "income": BBCA_INCOME,
            "ratios": BBCA_RATIOS,
            "stock_highlights": BBCA_STOCK_HIGHLIGHTS,
        }

    def _fetch_basic(s: str) -> dict[str, Any]:
        try:
            t = yf.Ticker(f"{s}.JK")
            info = t.info or {}
            return {
                "symbol": s,
                "source": "Yahoo Finance",
                "currency": "IDR",
                "financial_position": [],
                "income": [],
                "ratios": [],
                "stock_highlights": [],
                "message": (
                    "Detailed financial data for this company is not yet available. "
                    "Data will be added in a future release."
                ),
                "pe": info.get("trailingPE"),
                "pbv": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
            }
        except Exception:
            return {"symbol": s, "message": "Data unavailable"}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_fetch_basic, sym))


@router.get("/{symbol}/price-history", response_model=list[dict[str, Any]])
async def get_price_history(
    symbol: str,
    period: str = Query("5y", pattern="^(1y|2y|5y|10y)$"),
    _user: TokenPayload = Depends(require_role(Role.VIEWER)),
) -> list[dict[str, Any]]:
    """Get historical price data for charting (weekly bars)."""
    def _fetch(sym: str, per: str) -> list[dict[str, Any]]:
        try:
            t = yf.Ticker(f"{sym}.JK")
            hist = t.history(period=per, interval="1wk")
            if hist.empty:
                return []
            result: list[dict[str, Any]] = []
            for dt, row in hist.iterrows():
                result.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 0),
                    "high": round(float(row["High"]), 0),
                    "low": round(float(row["Low"]), 0),
                    "close": round(float(row["Close"]), 0),
                    "volume": int(row["Volume"]),
                })
            return result
        except Exception:
            logger.warning("price_history_fetch_failed", symbol=sym, period=per)
            return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_fetch, symbol.upper(), period))
