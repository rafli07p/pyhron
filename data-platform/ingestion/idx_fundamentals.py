"""IDX fundamentals ingestion from EODHD.

Fetches income statement, balance sheet, and cash flow data for quarterly
and annual periods. Computes and upserts ``ComputedRatio`` after storing
raw financials.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy import text

from shared.config import get_config
from shared.database import get_session
from shared.exceptions import IngestionError
from shared.logging import get_logger

logger = get_logger(__name__)


def _safe_decimal(value: object) -> Decimal | None:
    """Convert value to Decimal, returning None on failure."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    """Convert value to int, returning None on failure."""
    if value is None or value == "":
        return None
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None


class IDXFundamentalsIngester:
    """Ingests IDX company fundamentals from EODHD API."""

    def __init__(self) -> None:
        config = get_config()
        self._eodhd_key = config.eodhd_api_key

    async def ingest_symbol(self, symbol: str) -> dict:
        """Fetch and store fundamentals for a single IDX symbol."""
        if not self._eodhd_key:
            raise IngestionError("EODHD API key not configured")

        url = f"https://eodhd.com/api/fundamentals/{symbol}.IDX"
        params = {"api_token": self._eodhd_key, "fmt": "json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise IngestionError(f"EODHD fundamentals error for {symbol}: {exc}") from exc

        financials = data.get("Financials", {})
        income = financials.get("Income_Statement", {})
        balance = financials.get("Balance_Sheet", {})
        cashflow = financials.get("Cash_Flow", {})

        statements_stored = 0

        # Process each period (quarterly and annual)
        for period_type, statement_data in [
            ("quarterly", {**income.get("quarterly", {})}),
            ("yearly", {**income.get("yearly", {})}),
        ]:
            for period_key, stmt in statement_data.items():
                period_end = stmt.get("date")
                if not period_end:
                    continue

                fiscal_year = int(period_end[:4])
                quarter = None
                if period_type == "quarterly":
                    month = int(period_end[5:7])
                    quarter = (month - 1) // 3 + 1

                # Merge balance sheet and cash flow for same period
                bal = balance.get(period_type, {}).get(period_key, {})
                cf = cashflow.get(period_type, {}).get(period_key, {})

                await self._upsert_statement(
                    symbol=symbol,
                    period_end=period_end,
                    fiscal_year=fiscal_year,
                    quarter=quarter,
                    stmt=stmt,
                    bal=bal,
                    cf=cf,
                )
                statements_stored += 1

        # Compute ratios from latest data
        await self._compute_ratios(symbol)

        logger.info(
            "fundamentals_ingested",
            symbol=symbol,
            statements=statements_stored,
        )
        return {"symbol": symbol, "statements_stored": statements_stored}

    async def _upsert_statement(
        self,
        symbol: str,
        period_end: str,
        fiscal_year: int,
        quarter: int | None,
        stmt: dict,
        bal: dict,
        cf: dict,
    ) -> None:
        """Upsert a financial statement into the database."""
        for stmt_type, data in [("income", stmt), ("balance", bal), ("cashflow", cf)]:
            if not data:
                continue

            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO financial_statements (
                            id, symbol, period_end, fiscal_year, quarter, statement_type,
                            revenue, gross_profit, ebit, ebitda, net_income,
                            total_assets, total_liabilities, total_equity,
                            total_debt, cash_and_equivalents,
                            operating_cash_flow, capex, free_cash_flow,
                            shares_outstanding, eps
                        ) VALUES (
                            uuid_generate_v4(), :symbol, :period_end, :fiscal_year, :quarter,
                            :statement_type,
                            :revenue, :gross_profit, :ebit, :ebitda, :net_income,
                            :total_assets, :total_liabilities, :total_equity,
                            :total_debt, :cash_and_equivalents,
                            :operating_cash_flow, :capex, :free_cash_flow,
                            :shares_outstanding, :eps
                        )
                        ON CONFLICT (symbol, period_end, statement_type) DO UPDATE SET
                            revenue = EXCLUDED.revenue,
                            gross_profit = EXCLUDED.gross_profit,
                            net_income = EXCLUDED.net_income,
                            total_assets = EXCLUDED.total_assets,
                            total_equity = EXCLUDED.total_equity
                    """),
                    {
                        "symbol": symbol,
                        "period_end": period_end,
                        "fiscal_year": fiscal_year,
                        "quarter": quarter,
                        "statement_type": stmt_type,
                        "revenue": _safe_int(data.get("totalRevenue")),
                        "gross_profit": _safe_int(data.get("grossProfit")),
                        "ebit": _safe_int(data.get("ebit")),
                        "ebitda": _safe_int(data.get("ebitda")),
                        "net_income": _safe_int(data.get("netIncome")),
                        "total_assets": _safe_int(data.get("totalAssets")),
                        "total_liabilities": _safe_int(data.get("totalLiab")),
                        "total_equity": _safe_int(data.get("totalStockholderEquity")),
                        "total_debt": _safe_int(data.get("longTermDebt")),
                        "cash_and_equivalents": _safe_int(data.get("cash")),
                        "operating_cash_flow": _safe_int(data.get("totalCashFromOperatingActivities")),
                        "capex": _safe_int(data.get("capitalExpenditures")),
                        "free_cash_flow": _safe_int(data.get("freeCashFlow")),
                        "shares_outstanding": _safe_int(data.get("commonStockSharesOutstanding")),
                        "eps": float(_safe_decimal(data.get("eps")) or 0),
                    },
                )

    async def _compute_ratios(self, symbol: str) -> None:
        """Compute and upsert valuation ratios from latest fundamentals."""
        async with get_session() as session:
            # Get latest close price
            price_row = await session.execute(
                text("""
                    SELECT close FROM market_ticks
                    WHERE symbol = :symbol AND exchange = 'IDX'
                    ORDER BY time DESC LIMIT 1
                """),
                {"symbol": symbol},
            )
            price = price_row.scalar()
            if not price:
                return

            # Get latest income statement
            income_row = await session.execute(
                text("""
                    SELECT eps, revenue, gross_profit, net_income, shares_outstanding
                    FROM financial_statements
                    WHERE symbol = :symbol AND statement_type = 'income'
                    ORDER BY period_end DESC LIMIT 1
                """),
                {"symbol": symbol},
            )
            income = income_row.fetchone()
            if not income:
                return

            eps = float(income[0] or 0)
            pe_ratio = float(price) / eps if eps > 0 else None

            await session.execute(
                text("""
                    INSERT INTO computed_ratios (id, symbol, computed_at, price_used, pe_ratio)
                    VALUES (uuid_generate_v4(), :symbol, now(), :price, :pe_ratio)
                """),
                {"symbol": symbol, "price": float(price), "pe_ratio": pe_ratio},
            )
