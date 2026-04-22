"""Unit and integration tests for the Arelle-backed IDX XBRL parser.

Unit tests exercise the pure-Python paths (taxonomy map loading, context
classification, unit validation, value extraction) without requiring
`arelle` to be importable. Integration tests are guarded by
`pytest.importorskip("arelle")` and skip cleanly when Arelle or its
taxonomy cache is unavailable.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from data_platform.equity_ingestion.arelle_xbrl_parser import (
    IDXXBRLParser,
    ParsedFact,
    ParseResult,
    TaxonomyMap,
)
from shared.platform_exception_hierarchy import DataQualityError, IngestionError

_REPO_TAXONOMY_MAP = (
    Path(__file__).resolve().parents[2]
    / "data_platform"
    / "equity_ingestion"
    / "idx_taxonomy_map.yaml"
)


# ---------------------------------------------------------------------------
# Test doubles for Arelle model objects (so we can test _parse_fact without
# pulling arelle into the test environment).
# ---------------------------------------------------------------------------

@dataclass
class _FakeQName:
    localName: str  # noqa: N815 - mirrors arelle API
    namespaceURI: str = "http://xbrl.idx.co.id/taxonomy/psak"  # noqa: N815
    prefix: str = "idx-cor"


@dataclass
class _FakeUnit:
    measures: list[list[_FakeQName]]


@dataclass
class _FakeContext:
    startDatetime: datetime | None = None  # noqa: N815
    endDatetime: datetime | None = None  # noqa: N815
    instantDatetime: datetime | None = None  # noqa: N815


@dataclass
class _FakeFact:
    qname: _FakeQName | None
    contextID: str = "CurrentYearDuration"  # noqa: N815
    context: _FakeContext = field(default_factory=_FakeContext)
    unit: _FakeUnit | None = None
    value: str = "0"
    isNil: bool = False  # noqa: N815
    decimals: str | None = None


def _idr_unit() -> _FakeUnit:
    return _FakeUnit(measures=[[_FakeQName(
        localName="IDR", namespaceURI="http://www.xbrl.org/2003/iso4217",
        prefix="iso4217",
    )]])


def _pure_unit() -> _FakeUnit:
    return _FakeUnit(measures=[[_FakeQName(
        localName="pure", namespaceURI="http://www.xbrl.org/2003/instance",
        prefix="xbrli",
    )]])


def _usd_unit() -> _FakeUnit:
    return _FakeUnit(measures=[[_FakeQName(
        localName="USD", namespaceURI="http://www.xbrl.org/2003/iso4217",
        prefix="iso4217",
    )]])


@pytest.fixture
def parser() -> IDXXBRLParser:
    return IDXXBRLParser(taxonomy_map_path=_REPO_TAXONOMY_MAP)


@pytest.fixture
def minimal_map(tmp_path: Path) -> Path:
    """A tiny taxonomy map for focused resolver tests."""
    path = tmp_path / "mini.yaml"
    path.write_text(yaml.safe_dump({
        "metrics": [
            {"metric": "revenue", "localnames": ["Revenue"],
             "contexts": ["income_current", "income_prior"]},
            {"metric": "total_assets", "localnames": ["Assets"],
             "contexts": ["balance_current", "balance_prior"]},
            {"metric": "net_income", "localnames": ["ProfitLoss", "NetIncome"],
             "contexts": ["*"]},
        ],
    }))
    return path


# ---------------------------------------------------------------------------
# TaxonomyMap
# ---------------------------------------------------------------------------

class TestTaxonomyMap:
    def test_load_repo_map(self) -> None:
        tm = TaxonomyMap.from_yaml(_REPO_TAXONOMY_MAP)
        assert tm.metric_count >= 40, (
            f"expected >=40 metrics in shipped map, got {tm.metric_count}"
        )

    def test_load_missing_file_raises_ingestion_error(
        self, tmp_path: Path,
    ) -> None:
        with pytest.raises(IngestionError, match="taxonomy_map_file_missing"):
            TaxonomyMap.from_yaml(tmp_path / "nope.yaml")

    def test_load_missing_metrics_key_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("other_key: []")
        with pytest.raises(IngestionError, match="missing_metrics_key"):
            TaxonomyMap.from_yaml(bad)

    def test_load_malformed_yaml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "broken.yaml"
        bad.write_text("metrics: [unclosed")
        with pytest.raises(IngestionError, match="taxonomy_map_yaml_error"):
            TaxonomyMap.from_yaml(bad)

    def test_metrics_not_list_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad2.yaml"
        bad.write_text("metrics: not_a_list")
        with pytest.raises(IngestionError, match="metrics_not_list"):
            TaxonomyMap.from_yaml(bad)

    def test_resolve_known_localname_in_context(
        self, minimal_map: Path,
    ) -> None:
        tm = TaxonomyMap.from_yaml(minimal_map)
        assert tm.resolve("Revenue", "income_current") == "revenue"
        assert tm.resolve("Assets", "balance_current") == "total_assets"

    def test_resolve_unknown_localname_returns_none(
        self, minimal_map: Path,
    ) -> None:
        tm = TaxonomyMap.from_yaml(minimal_map)
        assert tm.resolve("NeverHeardOfIt", "income_current") is None

    def test_resolve_context_filter_rejects_wrong_context(
        self, minimal_map: Path,
    ) -> None:
        tm = TaxonomyMap.from_yaml(minimal_map)
        # Revenue is restricted to income_* contexts; balance_current misses.
        assert tm.resolve("Revenue", "balance_current") is None

    def test_resolve_wildcard_context_matches_anything(
        self, minimal_map: Path,
    ) -> None:
        tm = TaxonomyMap.from_yaml(minimal_map)
        # ProfitLoss is declared with contexts: ["*"]
        assert tm.resolve("ProfitLoss", "income_current") == "net_income"
        assert tm.resolve("ProfitLoss", "balance_current") == "net_income"
        assert tm.resolve("ProfitLoss", "other") == "net_income"

    def test_resolve_first_match_wins(self, minimal_map: Path) -> None:
        tm = TaxonomyMap.from_yaml(minimal_map)
        # Both "ProfitLoss" and "NetIncome" map to net_income.
        assert tm.resolve("NetIncome", "income_current") == "net_income"


# ---------------------------------------------------------------------------
# Period label validation
# ---------------------------------------------------------------------------

class TestPeriodLabel:
    @pytest.mark.parametrize("period", [
        "2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4", "2023-FY", "2024-Q1",
    ])
    def test_valid_periods_accepted(
        self, parser: IDXXBRLParser, period: str, tmp_path: Path,
    ) -> None:
        # parse() will bail on missing file before Arelle is touched —
        # but period validation runs first, so we verify no IngestionError
        # about period label.
        with pytest.raises(IngestionError, match="xbrl_file_missing"):
            parser.parse(
                xbrl_path=tmp_path / "nope.xbrl",
                symbol="BBCA", period=period, filing_date=date(2023, 5, 1),
            )

    @pytest.mark.parametrize("period", [
        "2023-Annual", "TW1", "2023-Q5", "2023-q1",
        "23-Q1", "2023-FY-Q1", "", "2023",
    ])
    def test_invalid_periods_rejected(
        self, parser: IDXXBRLParser, period: str, tmp_path: Path,
    ) -> None:
        with pytest.raises(IngestionError, match="invalid_period_label"):
            parser.parse(
                xbrl_path=tmp_path / "x.xbrl",
                symbol="BBCA", period=period, filing_date=date(2023, 5, 1),
            )


# ---------------------------------------------------------------------------
# Context classification
# ---------------------------------------------------------------------------

class TestContextClassification:
    @pytest.mark.parametrize("cid,expected", [
        ("CurrentYearDuration", "income_current"),
        ("CurrentYearDuration_1", "income_current"),
        ("PriorYearDuration", "income_prior"),
        ("PriorYearDuration_1", "income_prior"),
        ("CurrentYearInstant", "balance_current"),
        ("CurrentYearInstant_1", "balance_current"),
        ("PriorEndYearInstant", "balance_prior"),
        ("PriorEndYearInstant_1", "balance_prior"),
        ("PriorYearInstant", "balance_prior"),
        ("SegmentGeographyDuration", "other"),
        ("", "other"),
    ])
    def test_classify(
        self, parser: IDXXBRLParser, cid: str, expected: str,
    ) -> None:
        assert parser._classify_context(cid, object()) == expected


# ---------------------------------------------------------------------------
# Unit validation
# ---------------------------------------------------------------------------

class TestUnitValidation:
    def test_idr_unit_accepted(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="Revenue"),
            unit=_idr_unit(), value="1000000",
        )
        parser._validate_unit(fact, parser._unit_to_str(fact))  # no raise

    def test_pure_unit_accepted(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="EarningsPerShare"),
            unit=_pure_unit(), value="0.15",
        )
        parser._validate_unit(fact, parser._unit_to_str(fact))  # no raise

    def test_usd_unit_rejected(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="Revenue"),
            unit=_usd_unit(), value="1000000",
        )
        unit_str = parser._unit_to_str(fact)
        with pytest.raises(DataQualityError, match="non_idr_monetary_fact"):
            parser._validate_unit(fact, unit_str)

    def test_eur_unit_rejected(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="Revenue"),
            unit=_FakeUnit(measures=[[_FakeQName(
                localName="EUR",
                namespaceURI="http://www.xbrl.org/2003/iso4217",
                prefix="iso4217",
            )]]),
            value="1000",
        )
        unit_str = parser._unit_to_str(fact)
        with pytest.raises(DataQualityError, match="non_idr_monetary_fact"):
            parser._validate_unit(fact, unit_str)


# ---------------------------------------------------------------------------
# Value and decimals extraction
# ---------------------------------------------------------------------------

class TestValueExtraction:
    def test_extract_numeric_value(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(qname=_FakeQName(localName="X"), value="123456789")
        assert parser._extract_value(fact) == Decimal("123456789")

    def test_extract_decimal_with_fraction(
        self, parser: IDXXBRLParser,
    ) -> None:
        fact = _FakeFact(qname=_FakeQName(localName="X"), value="3.14")
        assert parser._extract_value(fact) == Decimal("3.14")

    def test_extract_negative(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(qname=_FakeQName(localName="X"), value="-100")
        assert parser._extract_value(fact) == Decimal("-100")

    def test_extract_empty_returns_none(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(qname=_FakeQName(localName="X"), value="")
        assert parser._extract_value(fact) is None

    def test_extract_nonnumeric_returns_none(
        self, parser: IDXXBRLParser,
    ) -> None:
        fact = _FakeFact(qname=_FakeQName(localName="X"), value="not a number")
        assert parser._extract_value(fact) is None

    def test_decimals_int(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="X"), value="0", decimals="-3",
        )
        assert parser._extract_decimals(fact) == -3

    def test_decimals_inf_returns_none(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="X"), value="0", decimals="INF",
        )
        assert parser._extract_decimals(fact) is None

    def test_decimals_missing_returns_none(
        self, parser: IDXXBRLParser,
    ) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="X"), value="0", decimals=None,
        )
        assert parser._extract_decimals(fact) is None


# ---------------------------------------------------------------------------
# _parse_fact end-to-end (pure-Python path, no Arelle load)
# ---------------------------------------------------------------------------

class TestParseFact:
    def test_nil_fact_returns_none(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="Revenue"),
            unit=_idr_unit(), value="", isNil=True,
        )
        out = parser._parse_fact(
            fact, "BBCA", "2023-Q1", date(2023, 5, 1),
        )
        assert out is None

    def test_unitless_fact_returns_none(self, parser: IDXXBRLParser) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="Narrative"), unit=None, value="text",
        )
        out = parser._parse_fact(
            fact, "BBCA", "2023-Q1", date(2023, 5, 1),
        )
        assert out is None

    def test_mapped_fact_is_mapped_true(
        self, parser: IDXXBRLParser,
    ) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="Assets"),
            contextID="CurrentYearInstant",
            unit=_idr_unit(), value="1000000000000",
        )
        out = parser._parse_fact(
            fact, "BBCA", "2023-Q1", date(2023, 5, 1),
        )
        assert out is not None
        assert out.is_mapped is True
        assert out.metric == "total_assets"
        assert out.context_type == "balance_current"
        assert out.value == Decimal("1000000000000")

    def test_unmapped_fact_uses_localname_as_metric(
        self, parser: IDXXBRLParser,
    ) -> None:
        fact = _FakeFact(
            qname=_FakeQName(localName="SomeExoticDisclosure"),
            contextID="CurrentYearDuration",
            unit=_idr_unit(), value="42",
        )
        out = parser._parse_fact(
            fact, "BBCA", "2023-Q1", date(2023, 5, 1),
        )
        assert out is not None
        assert out.is_mapped is False
        assert out.metric == "SomeExoticDisclosure"

    def test_raw_concept_preserves_namespace(
        self, parser: IDXXBRLParser,
    ) -> None:
        fact = _FakeFact(
            qname=_FakeQName(
                localName="Revenue",
                namespaceURI="http://xbrl.idx.co.id/taxonomy/psak/bank",
            ),
            contextID="CurrentYearDuration",
            unit=_idr_unit(), value="1",
        )
        out = parser._parse_fact(
            fact, "X", "2023-Q1", date(2023, 5, 1),
        )
        assert out is not None
        assert out.raw_concept == (
            "http://xbrl.idx.co.id/taxonomy/psak/bank:Revenue"
        )

    def test_filing_date_carried_through(
        self, parser: IDXXBRLParser,
    ) -> None:
        filing = date(2023, 4, 30)
        fact = _FakeFact(
            qname=_FakeQName(localName="Assets"),
            contextID="CurrentYearInstant",
            unit=_idr_unit(), value="1",
        )
        out = parser._parse_fact(fact, "BBCA", "2023-Q1", filing)
        assert out is not None
        assert out.filing_date == filing

    def test_period_dates_from_instant_context(
        self, parser: IDXXBRLParser,
    ) -> None:
        ctx = _FakeContext(instantDatetime=datetime(2023, 3, 31, tzinfo=UTC))
        fact = _FakeFact(
            qname=_FakeQName(localName="Assets"),
            contextID="CurrentYearInstant",
            context=ctx, unit=_idr_unit(), value="1",
        )
        out = parser._parse_fact(fact, "BBCA", "2023-Q1", date(2023, 5, 1))
        assert out is not None
        assert out.period_start is None
        assert out.period_end == date(2023, 3, 31)

    def test_period_dates_from_duration_context(
        self, parser: IDXXBRLParser,
    ) -> None:
        ctx = _FakeContext(
            startDatetime=datetime(2023, 1, 1, tzinfo=UTC),
            endDatetime=datetime(2023, 3, 31, tzinfo=UTC),
        )
        fact = _FakeFact(
            qname=_FakeQName(localName="Revenue"),
            contextID="CurrentYearDuration",
            context=ctx, unit=_idr_unit(), value="1",
        )
        out = parser._parse_fact(fact, "BBCA", "2023-Q1", date(2023, 5, 1))
        assert out is not None
        assert out.period_start == date(2023, 1, 1)
        assert out.period_end == date(2023, 3, 31)


# ---------------------------------------------------------------------------
# parse() entry-point guard paths (no Arelle needed)
# ---------------------------------------------------------------------------

class TestParseGuards:
    def test_missing_file_raises(
        self, parser: IDXXBRLParser, tmp_path: Path,
    ) -> None:
        with pytest.raises(IngestionError, match="xbrl_file_missing"):
            parser.parse(
                xbrl_path=tmp_path / "missing.xbrl",
                symbol="BBCA", period="2023-Q1",
                filing_date=date(2023, 5, 1),
            )

    def test_bad_period_raises_before_file_check(
        self, parser: IDXXBRLParser, tmp_path: Path,
    ) -> None:
        # Even with an existing file, bad period fails first.
        f = tmp_path / "x.xbrl"
        f.write_text("<xbrl/>")
        with pytest.raises(IngestionError, match="invalid_period_label"):
            parser.parse(
                xbrl_path=f, symbol="BBCA", period="bogus",
                filing_date=date(2023, 5, 1),
            )


# ---------------------------------------------------------------------------
# ParseResult accounting
# ---------------------------------------------------------------------------

class TestParseResult:
    def test_empty_result_rate_is_zero(self) -> None:
        r = ParseResult(
            symbol="BBCA", period="2023-Q1", filing_date=date(2023, 5, 1),
        )
        assert r.is_mapped_rate == 0.0

    def test_rate_computed_correctly(self) -> None:
        r = ParseResult(
            symbol="BBCA", period="2023-Q1", filing_date=date(2023, 5, 1),
            fact_count=10, mapped_count=7,
        )
        assert r.is_mapped_rate == 0.7

    def test_parsedfact_is_frozen(self) -> None:
        pf = ParsedFact(
            symbol="BBCA", period="2023-Q1", context_type="balance_current",
            metric="total_assets", value=Decimal("1"),
            raw_concept="ns:Assets", unit="iso4217:IDR",
            decimals=-3, period_start=None,
            period_end=date(2023, 3, 31), is_mapped=True,
            filing_date=date(2023, 5, 1),
        )
        with pytest.raises(FrozenInstanceError):
            pf.symbol = "BMRI"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration tests — real Arelle required. Skip gracefully when absent.
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestBBCAGoldenFile:
    """Golden-file integration test for BBCA 2023 Q1.

    Fixture path: tests/equity_ingestion/fixtures/bbca_2023_q1_instance.xbrl
    (plus its zip siblings for taxonomy link resolution)
    """

    FIXTURE = (
        Path(__file__).parent / "fixtures" / "bbca_2023_q1_instance.xbrl"
    )

    @pytest.fixture
    def _arelle_ready(self) -> None:
        pytest.importorskip("arelle")
        if not self.FIXTURE.exists():
            pytest.skip(f"golden fixture missing: {self.FIXTURE}")

    def test_parse_produces_facts(
        self, parser: IDXXBRLParser, _arelle_ready: None,
    ) -> None:
        result = parser.parse(
            xbrl_path=self.FIXTURE, symbol="BBCA", period="2023-Q1",
            filing_date=date(2023, 4, 28),
        )
        assert 400 <= result.fact_count <= 1200, (
            f"fact_count out of range: {result.fact_count}"
        )

    def test_net_income_within_tolerance(
        self, parser: IDXXBRLParser, _arelle_ready: None,
    ) -> None:
        result = parser.parse(
            xbrl_path=self.FIXTURE, symbol="BBCA", period="2023-Q1",
            filing_date=date(2023, 4, 28),
        )
        ni = [
            f for f in result.facts
            if f.metric == "net_income" and f.context_type == "income_current"
        ]
        assert ni, "no net_income fact in income_current context"
        expected = Decimal("11_530_000_000_000")
        tolerance = expected * Decimal("0.005")
        assert abs(ni[0].value - expected) < tolerance

    def test_total_assets_within_tolerance(
        self, parser: IDXXBRLParser, _arelle_ready: None,
    ) -> None:
        result = parser.parse(
            xbrl_path=self.FIXTURE, symbol="BBCA", period="2023-Q1",
            filing_date=date(2023, 4, 28),
        )
        ta = [
            f for f in result.facts
            if f.metric == "total_assets" and f.context_type == "balance_current"
        ]
        assert ta, "no total_assets fact in balance_current"
        expected = Decimal("1_321_000_000_000_000")
        tolerance = expected * Decimal("0.005")
        assert abs(ta[0].value - expected) < tolerance

    def test_idr_unit_present(
        self, parser: IDXXBRLParser, _arelle_ready: None,
    ) -> None:
        result = parser.parse(
            xbrl_path=self.FIXTURE, symbol="BBCA", period="2023-Q1",
            filing_date=date(2023, 4, 28),
        )
        assert any("IDR" in f.unit for f in result.facts)

    def test_no_duplicate_fact_keys(
        self, parser: IDXXBRLParser, _arelle_ready: None,
    ) -> None:
        result = parser.parse(
            xbrl_path=self.FIXTURE, symbol="BBCA", period="2023-Q1",
            filing_date=date(2023, 4, 28),
        )
        seen: set[tuple[str, str, str, str]] = set()
        for f in result.facts:
            key = (f.symbol, f.period, f.context_type, f.metric)
            # Unmapped metrics collide legitimately (localname = metric);
            # only dedupe mapped records for the uniqueness guarantee.
            if f.is_mapped:
                assert key not in seen, f"duplicate mapped fact key: {key}"
                seen.add(key)
