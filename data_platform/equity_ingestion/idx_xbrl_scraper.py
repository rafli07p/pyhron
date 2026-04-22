"""IDX XBRL Financial Statement Scraper.

Scrapes quarterly and annual financial statements directly from IDX
(idx.co.id) via their public financial report API, downloads XBRL
instance documents, and parses them into normalized financial facts
for storage in the financial_statements table.

Architecture:
    IDX Report API -> discover filings
    IDX File Server -> download instance.zip
    XBRL Parser     -> extract financial metrics
    TimescaleDB     -> upsert financial_statements

Taxonomy support:
    - Banking (idx-cor banking taxonomy)
    - General (idx-cor general taxonomy)
    - Both use same element naming with different subsets

Periods supported:
    TW1 = Q1 (March 31)
    TW2 = Q2 (June 30)
    TW3 = Q3 (September 30)
    Tahunan = Annual (December 31)
"""

from __future__ import annotations

import asyncio
import io
import re
import time
import zipfile
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from curl_cffi import CurlError
from curl_cffi.requests import AsyncSession as CurlSession
from sqlalchemy import text

from shared.async_database_session import get_session
from shared.platform_exception_hierarchy import (
    DataQualityError,
    IngestionError,
)
from shared.prometheus_metrics_registry import INGESTION_ROWS
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# -- Constants ----------------------------------------------------------------

IDX_BASE_URL = "https://www.idx.co.id"
IDX_REPORT_API = f"{IDX_BASE_URL}/primary/ListedCompany/GetFinancialReport"

# Periods: IDX code -> (quarter number, month-day of period end)
PERIOD_MAP: dict[str, tuple[int | None, str]] = {
    "TW1":     (1, "03-31"),
    "TW2":     (2, "06-30"),
    "TW3":     (3, "09-30"),
    "Tahunan": (None, "12-31"),
}

# HTTP headers that bypass Cloudflare for IDX
IDX_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
    "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan/",
    "X-Requested-With": "XMLHttpRequest",
}

# -- IDX Taxonomy -> Normalized metric mapping --------------------------------
# Banking taxonomy (BBCA, BBRI, BMRI, etc.)
BANKING_INCOME_MAP: dict[str, str] = {
    "InterestIncome":                   "revenue",
    "TotalInterestAndShariaIncome":     "revenue",
    "SubtotalInterestIncome":           "net_interest_income",
    "ProfitFromOperation":              "ebit",
    "ProfitLossBeforeIncomeTax":        "income_before_tax",
    "TaxBenefitExpenses":               "income_tax_expense",
    "ProfitLoss":                       "net_income",
    "ProfitLossFromContinuingOperations": "net_income",
    "GeneralAndAdministrativeExpenses": "operating_expenses",
    "OtherOperatingExpenses":           "other_operating_expenses",
    "RecoveryOfImpairmentLossesOfFinancialAssets": "impairment_losses",
}

BANKING_BALANCE_MAP: dict[str, str] = {
    "Assets":                           "total_assets",
    "LiabilitiesTemporarySyirkahFundsAndEquity": "total_assets",  # fallback
    "Liabilities":                      "total_liabilities",
    "TemporarySyirkahFunds":            "temporary_syirkah_funds",
    "Equity":                           "total_equity",
    "EquityAttributableToEquityOwnersOfParentEntity": "equity_parent",
    "TotalLoansGross":                  "total_loans_gross",
    "TotalLoansNet":                    "total_loans",
    "CashAndCashEquivalentsCashFlows":  "cash_and_equivalents",
    "Cash":                             "cash",
    "GovernmentBonds":                  "government_bonds",
    "PropertyPlantAndEquipment":        "ppe",
    "CommonStocks":                     "common_stock",
    "UnappropriatedRetainedEarnings":   "retained_earnings",
}

# General (non-banking) taxonomy
GENERAL_INCOME_MAP: dict[str, str] = {
    "Revenue":                          "revenue",
    "GrossProfit":                      "gross_profit",
    "OperatingIncome":                  "ebit",
    "ProfitBeforeTax":                  "income_before_tax",
    "IncomeTaxExpense":                 "income_tax_expense",
    "ProfitLoss":                       "net_income",
    "NetIncome":                        "net_income",
    "OperatingExpenses":                "operating_expenses",
    "CostOfRevenue":                    "cost_of_revenue",
    "EBITDA":                           "ebitda",
}

GENERAL_BALANCE_MAP: dict[str, str] = {
    "Assets":                           "total_assets",
    "Liabilities":                      "total_liabilities",
    "Equity":                           "total_equity",
    "CashAndCashEquivalents":           "cash_and_equivalents",
    "TotalDebt":                        "total_debt",
    "PropertyPlantAndEquipment":        "ppe",
    "GoodWill":                         "goodwill",
    "IntangibleAssets":                 "intangible_assets",
    "RetainedEarnings":                 "retained_earnings",
}

GENERAL_CASHFLOW_MAP: dict[str, str] = {
    "NetCashFromOperatingActivities":   "operating_cash_flow",
    "CashFlowsFromOperatingActivities": "operating_cash_flow",
    "NetCashFromInvestingActivities":   "investing_cash_flow",
    "NetCashFromFinancingActivities":   "financing_cash_flow",
    "CapitalExpenditures":              "capex",
    "FreeCashFlow":                     "free_cash_flow",
}

# Context -> period type mapping
DURATION_CONTEXTS = {"CurrentYearDuration", "PriorYearDuration"}
INSTANT_CONTEXTS = {
    "CurrentYearInstant", "PriorEndYearInstant",
    "CurrentYearInstant_1", "PriorEndYearInstant_1",
}


# -- Data classes -------------------------------------------------------------

@dataclass
class FilingInfo:
    """Metadata about an IDX financial filing."""

    symbol: str
    name: str
    period: str          # TW1, TW2, TW3, Tahunan
    year: int
    file_path: str       # Path to instance.zip on IDX server
    file_id: str
    file_modified: str


@dataclass
class ParsedStatement:
    """Normalized financial statement extracted from XBRL."""

    symbol: str
    fiscal_year: int
    quarter: int | None  # None for annual
    period_end: date
    statement_type: str  # income, balance, cashflow
    metrics: dict[str, Decimal]
    source_url: str
    filing_period: str


@dataclass
class ScraperResult:
    """Outcome of a scraping run."""

    symbol: str
    period: str
    year: int
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


# -- XBRL Parser --------------------------------------------------------------

class IDXXBRLParser:
    """Parse IDX XBRL instance documents into normalized financial metrics.

    Uses regex-based parsing on the raw XML content for performance,
    avoiding full DOM parsing of potentially very large files (3-5MB).

    Context conventions used by IDX XBRL taxonomy:
        CurrentYearDuration  -> current period income statement
        PriorYearDuration    -> prior period income statement
        CurrentYearInstant   -> current period balance sheet
        PriorEndYearInstant  -> prior period balance sheet
    """

    # Regex to extract: tag, contextRef, numeric value
    # Handles both self-closing nil elements and elements with values
    NUMERIC_PATTERN = re.compile(
        r'<([\w:-]+)\s[^>]*contextRef="([^"]+)"[^>]*>(-?\d+(?:\.\d+)?)</\1>',
        re.MULTILINE,
    )

    def parse(
        self,
        xbrl_content: str,
        symbol: str,
        fiscal_year: int,
        period: str,
        source_url: str,
    ) -> list[ParsedStatement]:
        """Parse XBRL content into normalized statements.

        Args:
            xbrl_content: Raw XBRL XML string.
            symbol: IDX ticker symbol.
            fiscal_year: Fiscal year of the filing.
            period: IDX period code (TW1, TW2, TW3, Tahunan).
            source_url: Original file URL for audit trail.

        Returns:
            List of ParsedStatement (one per statement type per period).
        """
        quarter, period_month_day = PERIOD_MAP[period]

        # Extract all numeric values
        raw_facts: dict[str, dict[str, Decimal]] = {}
        for match in self.NUMERIC_PATTERN.finditer(xbrl_content):
            full_tag, context, value_str = match.groups()
            tag = full_tag.split(":")[-1]  # strip namespace prefix
            try:
                value = Decimal(value_str)
            except InvalidOperation:
                continue

            if context not in raw_facts:
                raw_facts[context] = {}
            # Keep first occurrence (most specific without dimension suffix)
            if tag not in raw_facts[context]:
                raw_facts[context][tag] = value

        # Determine taxonomy type (banking vs general)
        is_banking = self._is_banking_taxonomy(raw_facts)
        income_map = BANKING_INCOME_MAP if is_banking else GENERAL_INCOME_MAP
        balance_map = BANKING_BALANCE_MAP if is_banking else GENERAL_BALANCE_MAP

        statements: list[ParsedStatement] = []

        # Income statement -- CurrentYear and PriorYear
        for ctx_key, year_offset in [
            ("CurrentYearDuration", 0),
            ("PriorYearDuration", -1),
        ]:
            if ctx_key not in raw_facts:
                continue
            ctx_facts = raw_facts[ctx_key]
            income_metrics = self._map_metrics(ctx_facts, income_map)
            if income_metrics:
                stmt_year = fiscal_year + year_offset
                stmt_period_end = date.fromisoformat(
                    f"{stmt_year}-{period_month_day}",
                )
                statements.append(ParsedStatement(
                    symbol=symbol,
                    fiscal_year=stmt_year,
                    quarter=quarter if year_offset == 0 else None,
                    period_end=stmt_period_end,
                    statement_type="income",
                    metrics=income_metrics,
                    source_url=source_url,
                    filing_period=period,
                ))

        # Balance sheet -- Current and Prior
        for ctx_key, year_offset in [
            ("CurrentYearInstant", 0),
            ("PriorEndYearInstant", -1),
        ]:
            if ctx_key not in raw_facts:
                continue
            ctx_facts = raw_facts[ctx_key]
            balance_metrics = self._map_metrics(ctx_facts, balance_map)
            if balance_metrics:
                stmt_year = fiscal_year + year_offset
                if period == "Tahunan":
                    stmt_period_end = date.fromisoformat(f"{stmt_year}-12-31")
                else:
                    bs_year = fiscal_year if year_offset == 0 else fiscal_year - 1
                    stmt_period_end = date.fromisoformat(
                        f"{bs_year}-{period_month_day}",
                    )
                statements.append(ParsedStatement(
                    symbol=symbol,
                    fiscal_year=stmt_year,
                    quarter=quarter if year_offset == 0 else None,
                    period_end=stmt_period_end,
                    statement_type="balance",
                    metrics=balance_metrics,
                    source_url=source_url,
                    filing_period=period,
                ))

        return statements

    def _is_banking_taxonomy(
        self,
        raw_facts: dict[str, dict[str, Decimal]],
    ) -> bool:
        """Detect banking taxonomy by presence of bank-specific elements."""
        all_tags: set[str] = set()
        for ctx_facts in raw_facts.values():
            all_tags.update(ctx_facts.keys())
        banking_indicators = {
            "InterestIncome", "TotalLoansGross", "CurrentAccounts",
            "SavingsDeposits", "NetInterestIncome",
        }
        return bool(banking_indicators & all_tags)

    def _map_metrics(
        self,
        ctx_facts: dict[str, Decimal],
        metric_map: dict[str, str],
    ) -> dict[str, Decimal]:
        """Map XBRL tags to normalized metric names.

        Args:
            ctx_facts: Raw facts for one context.
            metric_map: Tag -> normalized name mapping.

        Returns:
            Dict of normalized_metric -> value (first match wins).
        """
        result: dict[str, Decimal] = {}
        for xbrl_tag, normalized in metric_map.items():
            if xbrl_tag in ctx_facts:
                value = ctx_facts[xbrl_tag]
                if normalized not in result:  # first match wins
                    result[normalized] = value
        return result


# -- IDX Filing Discoverer ----------------------------------------------------

class IDXFilingDiscoverer:
    """Discover available XBRL filings from IDX report API.

    Paginates through IDX API to find instance.zip attachments
    for specified symbols, years, and periods.
    """

    MAX_RETRIES = 3
    PAGE_SIZE = 20  # IDX default page size

    def __init__(self, client: CurlSession[Any]) -> None:
        self._client = client

    async def discover(
        self,
        symbol: str,
        year: int,
        period: str | None = None,
    ) -> list[FilingInfo]:
        """Discover XBRL instance.zip filings for a symbol.

        Args:
            symbol: IDX ticker (e.g. BBCA).
            year: Fiscal year.
            period: Optional period filter (TW1/TW2/TW3/Tahunan).
                   If None, returns all periods for the year.

        Returns:
            List of FilingInfo with downloadable instance.zip paths.
        """
        periods_to_check = (
            [period] if period
            else ["TW1", "TW2", "TW3", "Tahunan"]
        )

        filings: list[FilingInfo] = []
        for p in periods_to_check:
            found = await self._fetch_period(symbol, year, p)
            filings.extend(found)
            # Rate limit: be respectful to IDX servers
            await asyncio.sleep(0.5)

        # Deduplicate by file_id: the IDX API sometimes returns the same
        # filing for multiple period queries (e.g. an annual filing shows
        # up under both "Tahunan" and the last quarterly window), which
        # would otherwise cause 4x duplicate rows per statement.
        seen_file_ids: set[str] = set()
        unique_filings: list[FilingInfo] = []
        for f in filings:
            if f.file_id not in seen_file_ids:
                seen_file_ids.add(f.file_id)
                unique_filings.append(f)
        return unique_filings

    async def _fetch_period(
        self,
        symbol: str,
        year: int,
        period: str,
    ) -> list[FilingInfo]:
        """Fetch filings for one symbol/year/period combination."""
        params: dict[str, str] = {
            "indexFrom": "0",
            "pageSize": str(self.PAGE_SIZE),
            "reportType": "rdf",
            "KodeEmiten": symbol,
            "Year": str(year),
            "period": period,
        }

        data: dict[str, object] = {}
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = await self._client.get(
                    IDX_REPORT_API,
                    params=params,
                    headers=IDX_HEADERS,
                    timeout=30,
                )
                if resp.status_code >= 400:
                    if attempt == self.MAX_RETRIES:
                        raise IngestionError(
                            f"IDX API error for {symbol}/{year}/{period}: "
                            f"HTTP {resp.status_code}",
                        )
                    await asyncio.sleep(2 ** attempt)
                    continue
                data = resp.json()
                break
            except CurlError as exc:
                if attempt == self.MAX_RETRIES:
                    raise IngestionError(
                        f"IDX connection error for {symbol}/{year}/{period}: "
                        f"{exc}",
                    ) from exc
                await asyncio.sleep(2 ** attempt)

        results = data.get("Results", []) if isinstance(data, dict) else []
        if not isinstance(results, list):
            return []

        filings: list[FilingInfo] = []

        for entry in results:
            if not isinstance(entry, dict):
                continue
            emiten_code = str(entry.get("KodeEmiten", ""))
            if emiten_code.upper() != symbol.upper():
                continue

            # Find instance.zip attachment
            attachments = entry.get("Attachments", [])
            if not isinstance(attachments, list):
                continue
            for attachment in attachments:
                if not isinstance(attachment, dict):
                    continue
                fname = str(attachment.get("File_Name", "")).lower()
                if fname == "instance.zip":
                    filings.append(FilingInfo(
                        symbol=symbol,
                        name=str(entry.get("NamaEmiten", "")),
                        period=str(entry.get("Report_Period", period)),
                        year=int(entry.get("Report_Year", year)),
                        file_path=str(attachment["File_Path"]),
                        file_id=str(attachment["File_ID"]),
                        file_modified=str(attachment.get("File_Modified", "")),
                    ))
                    break  # Only need instance.zip per filing

        return filings


# -- Main Scraper -------------------------------------------------------------

class IDXXBRLScraper:
    """Orchestrates discovery, download, parsing, and persistence of IDX XBRL
    financial statements.

    Usage::

        scraper = IDXXBRLScraper()

        # Scrape all periods for a symbol in a year
        results = await scraper.scrape_symbol(
            symbol="BBCA",
            year=2023,
        )

        # Scrape multiple symbols
        results = await scraper.scrape_batch(
            symbols=["BBCA", "BBRI", "BMRI", "TLKM"],
            years=[2022, 2023, 2024],
        )
    """

    def __init__(self) -> None:
        self._parser = IDXXBRLParser()
        self._logger = get_logger(__name__)

    async def scrape_symbol(
        self,
        symbol: str,
        year: int,
        period: str | None = None,
    ) -> list[ScraperResult]:
        """Scrape financial statements for one symbol.

        Args:
            symbol: IDX ticker (e.g. BBCA).
            year: Fiscal year.
            period: Optional period (TW1/TW2/TW3/Tahunan).
                   If None, scrapes all available periods.

        Returns:
            List of ScraperResult per period scraped.
        """
        async with CurlSession(impersonate="chrome120", timeout=60) as client:
            discoverer = IDXFilingDiscoverer(client)
            filings = await discoverer.discover(symbol, year, period)

            if not filings:
                self._logger.warning(
                    "no_xbrl_filings_found",
                    symbol=symbol,
                    year=year,
                    period=period,
                )
                return []

            results: list[ScraperResult] = []
            for filing in filings:
                result = await self._process_filing(filing, client)
                results.append(result)
                # Respectful rate limiting
                await asyncio.sleep(1.0)

        return results

    async def scrape_batch(
        self,
        symbols: list[str],
        years: list[int],
        periods: list[str] | None = None,
        delay_between_symbols: float = 2.0,
    ) -> list[ScraperResult]:
        """Scrape multiple symbols sequentially.

        Sequential (not concurrent) to be respectful to IDX servers
        and avoid triggering Cloudflare rate limits.

        Args:
            symbols: List of IDX tickers.
            years: List of fiscal years to scrape.
            periods: Optional list of periods. If None, all periods.
            delay_between_symbols: Seconds to wait between symbols.

        Returns:
            All scraper results.
        """
        all_results: list[ScraperResult] = []

        for symbol in symbols:
            for year in years:
                if periods:
                    for period in periods:
                        results = await self.scrape_symbol(symbol, year, period)
                        all_results.extend(results)
                        await asyncio.sleep(delay_between_symbols)
                else:
                    results = await self.scrape_symbol(symbol, year)
                    all_results.extend(results)
                    await asyncio.sleep(delay_between_symbols)

            self._logger.info(
                "symbol_scrape_complete",
                symbol=symbol,
                total_results=len(all_results),
            )

        return all_results

    async def _process_filing(
        self,
        filing: FilingInfo,
        client: CurlSession[Any],
    ) -> ScraperResult:
        """Download, parse, and persist one XBRL filing.

        Args:
            filing: FilingInfo with download path.
            client: Shared HTTP client.

        Returns:
            ScraperResult with insertion counts.
        """
        t0 = time.monotonic()
        result = ScraperResult(
            symbol=filing.symbol,
            period=filing.period,
            year=filing.year,
        )

        try:
            # Download instance.zip
            xbrl_content = await self._download_xbrl(filing, client)

            # Parse XBRL
            statements = self._parser.parse(
                xbrl_content=xbrl_content,
                symbol=filing.symbol,
                fiscal_year=filing.year,
                period=filing.period,
                source_url=f"{IDX_BASE_URL}{filing.file_path}",
            )

            if not statements:
                result.errors.append("No statements parsed from XBRL")
                result.rows_skipped += 1
                return result

            # Validate statements
            valid_statements: list[ParsedStatement] = []
            for stmt in statements:
                try:
                    self._validate_statement(stmt)
                    valid_statements.append(stmt)
                except DataQualityError as exc:
                    result.errors.append(str(exc))
                    result.rows_skipped += 1

            # Persist to DB
            inserted, updated = await self._upsert_statements(valid_statements)
            result.rows_inserted = inserted
            result.rows_updated = updated

            INGESTION_ROWS.labels(
                source="idx_xbrl",
                symbol=filing.symbol,
                operation="inserted",
            ).inc(inserted)
            INGESTION_ROWS.labels(
                source="idx_xbrl",
                symbol=filing.symbol,
                operation="updated",
            ).inc(updated)

            self._logger.info(
                "xbrl_filing_processed",
                symbol=filing.symbol,
                period=filing.period,
                year=filing.year,
                statements_parsed=len(statements),
                rows_inserted=inserted,
                rows_updated=updated,
            )

        except IngestionError as exc:
            result.errors.append(str(exc))
            self._logger.error(
                "xbrl_filing_failed",
                symbol=filing.symbol,
                period=filing.period,
                year=filing.year,
                error=str(exc),
            )
        finally:
            result.duration_ms = (time.monotonic() - t0) * 1000

        return result

    async def _download_xbrl(
        self,
        filing: FilingInfo,
        client: CurlSession[Any],
    ) -> str:
        """Download and extract XBRL content from instance.zip.

        Args:
            filing: FilingInfo with file path.
            client: Shared HTTP client.

        Returns:
            Raw XBRL XML string.

        Raises:
            IngestionError: On download or extraction failure.
        """
        # URL-encode spaces in path
        encoded_path = filing.file_path.replace(" ", "%20")
        url = f"{IDX_BASE_URL}{encoded_path}"

        zip_bytes = b""
        for attempt in range(1, 4):
            try:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": IDX_HEADERS["User-Agent"],
                        "Referer": IDX_BASE_URL + "/",
                    },
                    allow_redirects=True,
                    timeout=60,
                )
                if resp.status_code >= 400:
                    if attempt == 3:
                        raise IngestionError(
                            f"Failed to download {url}: "
                            f"HTTP {resp.status_code}",
                        )
                    await asyncio.sleep(2 ** attempt)
                    continue
                zip_bytes = resp.content
                break
            except CurlError as exc:
                if attempt == 3:
                    raise IngestionError(
                        f"Connection error downloading {url}: {exc}",
                    ) from exc
                await asyncio.sleep(2 ** attempt)

        # Extract instance.xbrl from zip
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                xbrl_files = [n for n in zf.namelist() if n.endswith(".xbrl")]
                if not xbrl_files:
                    raise IngestionError(
                        f"No .xbrl file found in {filing.file_path}",
                    )
                xbrl_bytes = zf.read(xbrl_files[0])
                return xbrl_bytes.decode("utf-8", errors="ignore")
        except zipfile.BadZipFile as exc:
            raise IngestionError(
                f"Invalid zip file from {url}: {exc}",
            ) from exc

    def _validate_statement(self, stmt: ParsedStatement) -> None:
        """Validate financial statement accounting identities.

        Raises:
            DataQualityError: If critical validation fails.
        """
        metrics = stmt.metrics

        if stmt.statement_type == "balance":
            total_assets = metrics.get("total_assets")
            total_liab = metrics.get("total_liabilities")
            total_equity = metrics.get("total_equity")

            if total_assets and total_liab and total_equity:
                # Islamic banking taxonomy adds TemporarySyirkahFunds between
                # Liabilities and Equity. Non-syirkah banks have it as 0/None.
                syirkah = metrics.get("temporary_syirkah_funds") or Decimal(0)
                diff = abs(total_assets - (total_liab + syirkah + total_equity))
                tolerance = total_assets * Decimal("0.02")  # 2% tolerance
                if diff > tolerance:
                    raise DataQualityError(
                        f"Balance sheet identity mismatch for "
                        f"{stmt.symbol}/{stmt.fiscal_year}/"
                        f"{stmt.filing_period}: "
                        f"assets={total_assets:,}, "
                        f"liab+syirkah+equity="
                        f"{total_liab + syirkah + total_equity:,}, "
                        f"diff={diff:,}",
                    )

    async def _upsert_statements(
        self,
        statements: list[ParsedStatement],
    ) -> tuple[int, int]:
        """Upsert parsed statements into financial_statements table.

        Args:
            statements: Validated ParsedStatement objects.

        Returns:
            Tuple of (inserted, updated) counts.
        """
        if not statements:
            return 0, 0

        inserted = 0
        updated = 0

        # Actual deployed schema (after migration 013 consolidate_public_schema):
        # table: public.financial_statements
        # cols:  symbol, period (varchar), statement_type (varchar),
        #        revenue_idr, gross_profit_idr, operating_income_idr,
        #        net_income_idr, total_assets_idr, total_liabilities_idr,
        #        total_equity_idr, operating_cash_flow_idr,
        #        capital_expenditure_idr, free_cash_flow_idr,
        #        filing_date, ingested_at
        # index: ix_financial_stmt_symbol_period (symbol, period) -- NOT unique
        # => no ON CONFLICT target; use DELETE + INSERT for idempotence.

        delete_sql = text("""
            DELETE FROM financial_statements
            WHERE symbol = :symbol
              AND period = :period
              AND statement_type = :statement_type
        """)

        insert_sql = text("""
            INSERT INTO financial_statements (
                symbol, period, statement_type,
                revenue_idr, gross_profit_idr, operating_income_idr, net_income_idr,
                total_assets_idr, total_liabilities_idr, total_equity_idr,
                operating_cash_flow_idr, capital_expenditure_idr, free_cash_flow_idr,
                filing_date, ingested_at
            ) VALUES (
                :symbol, :period, :statement_type,
                :revenue_idr, :gross_profit_idr, :operating_income_idr, :net_income_idr,
                :total_assets_idr, :total_liabilities_idr, :total_equity_idr,
                :operating_cash_flow_idr, :capital_expenditure_idr, :free_cash_flow_idr,
                :filing_date, NOW()
            )
        """)

        def _to_int(v: Decimal | None) -> int | None:
            return int(v) if v is not None else None

        def _period_str(fiscal_year: int, quarter: int | None) -> str:
            return f"{fiscal_year}-Q{quarter}" if quarter else f"{fiscal_year}-Annual"

        async with get_session() as session:
            for stmt in statements:
                m = stmt.metrics
                period = _period_str(stmt.fiscal_year, stmt.quarter)

                key_params = {
                    "symbol": stmt.symbol,
                    "period": period,
                    "statement_type": stmt.statement_type,
                }

                # DELETE any prior row with the same key (idempotent re-run).
                del_result = await session.execute(delete_sql, key_params)
                # rowcount is on CursorResult at runtime; not in Result stub.
                prior_rows = getattr(del_result, "rowcount", 0) or 0

                # INSERT the fresh values.
                await session.execute(insert_sql, {
                    **key_params,
                    "revenue_idr":             _to_int(m.get("revenue")),
                    "gross_profit_idr":        _to_int(m.get("gross_profit")),
                    "operating_income_idr":    _to_int(m.get("ebit")),
                    "net_income_idr":          _to_int(m.get("net_income")),
                    "total_assets_idr":        _to_int(m.get("total_assets")),
                    "total_liabilities_idr":   _to_int(m.get("total_liabilities")),
                    "total_equity_idr":        _to_int(m.get("total_equity")),
                    "operating_cash_flow_idr": _to_int(m.get("operating_cash_flow")),
                    "capital_expenditure_idr": _to_int(m.get("capex")),
                    "free_cash_flow_idr":      _to_int(m.get("free_cash_flow")),
                    "filing_date":             stmt.period_end,
                })

                if prior_rows > 0:
                    updated += 1
                else:
                    inserted += 1

        return inserted, updated
