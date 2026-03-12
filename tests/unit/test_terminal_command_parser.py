"""Tests for the Bloomberg-style terminal command parser."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apps.terminal.command_palette.parser import CommandParser, get_market_status
from apps.terminal.demo import DemoDataProvider


class TestCommandParser:
    """Tests for CommandParser.parse()."""

    def test_parse_equity_go(self) -> None:
        cmd = CommandParser().parse("BBCA EQUITY GO")
        assert cmd is not None
        assert cmd.command_type == "LOAD_EQUITY"
        assert cmd.symbol == "BBCA"

    def test_parse_buy_limit(self) -> None:
        cmd = CommandParser().parse("BUY BBCA 10 L")
        assert cmd is not None
        assert cmd.command_type == "SUBMIT_ORDER"
        assert cmd.params["side"] == "BUY"
        assert cmd.params["quantity_lots"] == 10
        assert cmd.params["order_type"] == "LIMIT"

    def test_parse_sell_market(self) -> None:
        cmd = CommandParser().parse("SELL TLKM 5 M")
        assert cmd is not None
        assert cmd.params["side"] == "SELL"
        assert cmd.params["order_type"] == "MARKET"

    def test_parse_invalid_returns_none(self) -> None:
        assert CommandParser().parse("GIBBERISH XYZ 123") is None

    def test_fuzzy_symbol_suggestion(self) -> None:
        suggestions = CommandParser().suggest_symbols("BCA", universe=["BBCA", "BCAP", "BCIC", "BMRI"])
        assert "BBCA" in suggestions

    def test_parse_layout_switch(self) -> None:
        cmd = CommandParser().parse("RISK")
        assert cmd is not None
        assert cmd.command_type == "SWITCH_LAYOUT"
        assert cmd.params["layout"] == "risk"

    def test_case_insensitive_parsing(self) -> None:
        cmd = CommandParser().parse("bbca equity go")
        assert cmd is not None
        assert cmd.symbol == "BBCA"

    def test_zero_lots_rejected(self) -> None:
        cmd = CommandParser().parse("BUY BBCA 0 L")
        assert cmd is None


class TestMarketStatus:
    """Tests for get_market_status()."""

    def test_market_status_open(self) -> None:
        dt = datetime(2025, 3, 3, 10, 0, 0, tzinfo=ZoneInfo("Asia/Jakarta"))
        assert get_market_status(dt) == "OPEN"

    def test_market_status_closed(self) -> None:
        dt = datetime(2025, 3, 3, 17, 0, 0, tzinfo=ZoneInfo("Asia/Jakarta"))
        assert get_market_status(dt) == "CLOSED"


class TestDemoProvider:
    """Tests for DemoDataProvider."""

    def test_demo_prices_respect_ara_arb(self) -> None:
        provider = DemoDataProvider(seed=42)
        start_price = provider.get_quote("BBCA").last
        prices = [provider.get_quote("BBCA").last for _ in range(100)]
        assert all(abs(p / start_price - 1) < 0.35 for p in prices)
