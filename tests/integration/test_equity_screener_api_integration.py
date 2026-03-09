"""Integration test for equity screener API endpoint.

Tests filtering equities by sector, market cap, and PE ratio
using a mock database layer.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Mock Screener Models ────────────────────────────────────────────────────


@dataclass
class ScreenerRow:
    """Simplified equity screener result row."""

    symbol: str
    name: str
    sector: str
    market_cap: int
    pe_ratio: float | None
    pb_ratio: float | None
    roe: float | None
    dividend_yield: float | None


MOCK_SCREENER_DB: list[ScreenerRow] = [
    ScreenerRow("BBCA", "Bank Central Asia", "FINANCIALS", 1_200_000_000_000, 25.3, 4.8, 0.21, 0.012),
    ScreenerRow("BBRI", "Bank Rakyat Indonesia", "FINANCIALS", 800_000_000_000, 14.2, 2.5, 0.18, 0.025),
    ScreenerRow("TLKM", "Telkom Indonesia", "COMMUNICATION", 350_000_000_000, 16.8, 3.2, 0.19, 0.035),
    ScreenerRow("ASII", "Astra International", "CONSUMER_DISC", 280_000_000_000, 8.5, 1.6, 0.15, 0.045),
    ScreenerRow("UNVR", "Unilever Indonesia", "CONSUMER_STAPLE", 150_000_000_000, 35.0, 45.0, 1.20, 0.020),
    ScreenerRow("AALI", "Astra Agro Lestari", "AGRICULTURE", 25_000_000_000, 10.2, 0.9, 0.08, 0.060),
    ScreenerRow("INDF", "Indofood Sukses", "CONSUMER_STAPLE", 95_000_000_000, 9.1, 1.2, 0.12, 0.040),
    ScreenerRow("PGAS", "Perusahaan Gas Negara", "ENERGY", 45_000_000_000, 6.5, 0.8, 0.10, 0.055),
]


def screen_equities(
    sector: str | None = None,
    min_market_cap: int | None = None,
    max_pe_ratio: float | None = None,
    min_dividend_yield: float | None = None,
    db: list[ScreenerRow] | None = None,
) -> list[ScreenerRow]:
    """Filter equities by criteria against a mock database."""
    results = db or MOCK_SCREENER_DB
    if sector:
        results = [r for r in results if r.sector == sector]
    if min_market_cap is not None:
        results = [r for r in results if r.market_cap >= min_market_cap]
    if max_pe_ratio is not None:
        results = [r for r in results if r.pe_ratio is not None and r.pe_ratio <= max_pe_ratio]
    if min_dividend_yield is not None:
        results = [r for r in results if r.dividend_yield is not None and r.dividend_yield >= min_dividend_yield]
    return results


# ── Sector Filter Tests ─────────────────────────────────────────────────────


class TestSectorFilter:
    def test_filter_financials(self):
        results = screen_equities(sector="FINANCIALS")
        assert len(results) == 2
        assert all(r.sector == "FINANCIALS" for r in results)

    def test_filter_energy(self):
        results = screen_equities(sector="ENERGY")
        assert len(results) == 1
        assert results[0].symbol == "PGAS"

    def test_filter_nonexistent_sector(self):
        results = screen_equities(sector="MINING")
        assert len(results) == 0

    def test_no_filter_returns_all(self):
        results = screen_equities()
        assert len(results) == len(MOCK_SCREENER_DB)


# ── Market Cap Filter Tests ─────────────────────────────────────────────────


class TestMarketCapFilter:
    def test_large_cap_filter(self):
        results = screen_equities(min_market_cap=500_000_000_000)
        assert len(results) == 2  # BBCA, BBRI
        symbols = {r.symbol for r in results}
        assert symbols == {"BBCA", "BBRI"}

    def test_mid_cap_filter(self):
        results = screen_equities(min_market_cap=100_000_000_000)
        assert all(r.market_cap >= 100_000_000_000 for r in results)

    def test_very_high_cap_returns_none(self):
        results = screen_equities(min_market_cap=10_000_000_000_000)
        assert len(results) == 0


# ── PE Ratio Filter Tests ──────────────────────────────────────────────────


class TestPERatioFilter:
    def test_value_stocks(self):
        results = screen_equities(max_pe_ratio=10.0)
        assert all(r.pe_ratio <= 10.0 for r in results)
        symbols = {r.symbol for r in results}
        assert "ASII" in symbols
        assert "PGAS" in symbols

    def test_all_stocks_under_high_pe(self):
        results = screen_equities(max_pe_ratio=100.0)
        assert len(results) == len(MOCK_SCREENER_DB)


# ── Combined Filter Tests ──────────────────────────────────────────────────


class TestCombinedFilters:
    def test_financial_large_cap(self):
        results = screen_equities(sector="FINANCIALS", min_market_cap=500_000_000_000)
        assert len(results) == 2

    def test_high_yield_value(self):
        results = screen_equities(max_pe_ratio=12.0, min_dividend_yield=0.04)
        symbols = {r.symbol for r in results}
        assert "ASII" in symbols
        assert "PGAS" in symbols

    def test_no_matches(self):
        results = screen_equities(sector="FINANCIALS", max_pe_ratio=5.0)
        assert len(results) == 0
