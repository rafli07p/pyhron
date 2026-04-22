from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

import yaml

from shared.platform_exception_hierarchy import DataQualityError, IngestionError
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from arelle.ModelInstanceObject import ModelFact
    from arelle.ModelXbrl import ModelXbrl

logger = get_logger(__name__)

_VALID_PERIOD_RE = re.compile(r"^\d{4}-(Q[1-4]|FY)$")

# Allowed monetary unit strings. Anything containing 'iso4217' but not
# 'IDR' is treated as a foreign-currency DataQualityError.
_IDR_UNIT_MARKERS = ("IDR", "Rupiah", "iso4217:IDR")
_NON_MONETARY_MARKERS = ("pure", "shares", "PureItemType", "XBRLI:PURE")

_BANKING_INDICATOR_LOCALNAMES = frozenset({
    "InterestIncome",
    "TotalLoansGross",
    "TotalLoansNet",
    "CurrentAccounts",
    "SavingsDeposits",
    "NetInterestIncome",
    "SubtotalInterestIncome",
    "TemporarySyirkahFunds",
})


@dataclass(frozen=True)
class ParsedFact:
    """One XBRL fact, normalized for downstream persistence.

    12 fields. Phase 1 persistence drops `raw_concept`, `unit`, `decimals`,
    `period_start`, `period_end`, `is_mapped` — they survive on the object
    for Phase 2 schema migration and for test assertions.
    """

    symbol: str
    period: str
    context_type: str
    metric: str
    value: Decimal
    raw_concept: str
    unit: str
    decimals: int | None
    period_start: date | None
    period_end: date | None
    is_mapped: bool
    filing_date: date


@dataclass
class ParseResult:
    """Aggregated output of one filing parse."""

    symbol: str
    period: str
    filing_date: date
    facts: list[ParsedFact] = field(default_factory=list)
    fact_count: int = 0
    mapped_count: int = 0
    unmapped_concepts: set[str] = field(default_factory=set)
    taxonomy_detected: str = "unknown"
    errors: list[str] = field(default_factory=list)

    @property
    def is_mapped_rate(self) -> float:
        if self.fact_count == 0:
            return 0.0
        return self.mapped_count / self.fact_count


@dataclass(frozen=True)
class _TaxonomyEntry:
    metric: str
    localnames: tuple[str, ...]
    contexts: tuple[str, ...]


class TaxonomyMap:
    """YAML-loaded mapping from XBRL concept localnames to normalized metrics.

    First match wins when a localname has multiple entries. Context filters
    (`contexts` list in YAML) let the same localname map to different
    metrics depending on whether the fact appears in a P&L or BS context.
    """

    def __init__(self, entries: list[_TaxonomyEntry]) -> None:
        self._entries = entries
        self._by_localname: dict[str, list[_TaxonomyEntry]] = {}
        for entry in entries:
            for localname in entry.localnames:
                self._by_localname.setdefault(localname, []).append(entry)

    @classmethod
    def from_yaml(cls, path: Path) -> TaxonomyMap:
        """Load map from YAML file.

        Raises:
            IngestionError: if file missing or malformed.
        """
        if not path.exists():
            raise IngestionError(f"taxonomy_map_file_missing: {path}")
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise IngestionError(f"taxonomy_map_yaml_error: {exc}") from exc

        if not isinstance(data, dict) or "metrics" not in data:
            raise IngestionError(
                f"taxonomy_map_missing_metrics_key: {path}",
            )

        raw_entries = data["metrics"]
        if not isinstance(raw_entries, list):
            raise IngestionError("taxonomy_map_metrics_not_list")

        entries: list[_TaxonomyEntry] = []
        for spec in raw_entries:
            if not isinstance(spec, dict):
                continue
            metric = spec.get("metric")
            localnames = spec.get("localnames", [])
            contexts = spec.get("contexts", ["*"])
            if not metric or not isinstance(localnames, list):
                continue
            entries.append(_TaxonomyEntry(
                metric=str(metric),
                localnames=tuple(str(ln) for ln in localnames),
                contexts=tuple(str(c) for c in contexts),
            ))
        return cls(entries)

    @property
    def metric_count(self) -> int:
        return len(self._entries)

    def resolve(self, localname: str, context_type: str) -> str | None:
        """Return the normalized metric name for a (localname, context)
        pair, or None if no entry matches."""
        for entry in self._by_localname.get(localname, ()):
            if "*" in entry.contexts or context_type in entry.contexts:
                return entry.metric
        return None


class IDXXBRLParser:
    """Parse IDX XBRL instance documents into `ParsedFact` records.

    One instance per process. The underlying Arelle `Cntlr` is lazily
    acquired from `arelle_controller.get_cntlr()` on each `parse()` call,
    so this object itself is cheap to construct.
    """

    def __init__(self, taxonomy_map_path: Path) -> None:
        self._taxonomy_map = TaxonomyMap.from_yaml(taxonomy_map_path)

    @property
    def taxonomy_map(self) -> TaxonomyMap:
        return self._taxonomy_map

    def parse(
        self,
        xbrl_path: Path,
        symbol: str,
        period: str,
        filing_date: date,
    ) -> ParseResult:
        """Parse one XBRL instance file.

        Args:
            xbrl_path: Filesystem path to the `.xbrl` instance document.
                Arelle needs the linked schemaRef/label/presentation files
                to be co-located on disk — extract the full `instance.zip`
                to a temp directory first.
            symbol: IDX ticker (e.g. "BBCA").
            period: Normalized period label, `YYYY-Q[1-4]` or `YYYY-FY`.
            filing_date: IDX receipt date (NOT the XBRL context period_end).

        Returns:
            `ParseResult` with all facts from the four primary contexts.

        Raises:
            IngestionError: on file/load/validation errors.
            DataQualityError: on non-IDR monetary facts.
        """
        if not _VALID_PERIOD_RE.match(period):
            raise IngestionError(
                f"invalid_period_label: {period!r} "
                "(expected YYYY-Q[1-4] or YYYY-FY)",
            )
        if not xbrl_path.exists():
            raise IngestionError(f"xbrl_file_missing: {xbrl_path}")

        from .arelle_controller import get_cntlr

        cntlr = get_cntlr()
        try:
            model_xbrl = cntlr.modelManager.load(str(xbrl_path))
        except Exception as exc:
            raise IngestionError(
                f"arelle_load_error: {xbrl_path}: {exc}",
            ) from exc

        if model_xbrl is None:
            raise IngestionError(f"arelle_load_returned_none: {xbrl_path}")

        try:
            return self._parse_model(model_xbrl, symbol, period, filing_date)
        finally:
            try:
                cntlr.modelManager.close(model_xbrl)
            except (AttributeError, RuntimeError) as exc:
                logger.warning("arelle_model_close_failed", error=str(exc))

    def _parse_model(
        self,
        model_xbrl: ModelXbrl,
        symbol: str,
        period: str,
        filing_date: date,
    ) -> ParseResult:
        """Iterate facts in a loaded model and build the `ParseResult`."""
        result = ParseResult(
            symbol=symbol,
            period=period,
            filing_date=filing_date,
        )
        banking_hit = False

        for fact in model_xbrl.factsInInstance:
            try:
                parsed = self._parse_fact(fact, symbol, period, filing_date)
            except DataQualityError as exc:
                result.errors.append(str(exc))
                continue
            if parsed is None:
                continue

            result.facts.append(parsed)
            result.fact_count += 1
            if parsed.is_mapped:
                result.mapped_count += 1
            else:
                result.unmapped_concepts.add(parsed.raw_concept)

            localname = parsed.raw_concept.rsplit(":", 1)[-1]
            if localname in _BANKING_INDICATOR_LOCALNAMES:
                banking_hit = True

        result.taxonomy_detected = "banking" if banking_hit else "general"
        return result

    def _parse_fact(
        self,
        fact: ModelFact,
        symbol: str,
        period: str,
        filing_date: date,
    ) -> ParsedFact | None:
        """Translate one Arelle `ModelFact` into a `ParsedFact` or None."""
        # xsi:nil="true" — explicit non-disclosure. Distinct signal from
        # reported-as-zero. Drop for Phase 1; Phase 2 may emit with
        # value=NULL and a nil flag once schema supports it.
        if getattr(fact, "isNil", False):
            return None

        # Non-numeric facts (narrative disclosures, etc.) have no unit.
        if getattr(fact, "unit", None) is None:
            return None

        unit_str = self._unit_to_str(fact)
        self._validate_unit(fact, unit_str)

        value = self._extract_value(fact)
        if value is None:
            return None

        concept = fact.qname
        if concept is None:
            return None
        namespace = concept.namespaceURI or ""
        localname = concept.localName
        raw_concept = f"{namespace}:{localname}" if namespace else localname

        ctx = getattr(fact, "context", None)
        if ctx is None:
            return None
        context_id = getattr(fact, "contextID", "") or ""
        context_type = self._classify_context(context_id, ctx)

        metric = self._taxonomy_map.resolve(localname, context_type)
        is_mapped = metric is not None

        period_start, period_end = self._extract_period_dates(ctx)

        return ParsedFact(
            symbol=symbol,
            period=period,
            context_type=context_type,
            metric=metric if metric is not None else localname,
            value=value,
            raw_concept=raw_concept,
            unit=unit_str,
            decimals=self._extract_decimals(fact),
            period_start=period_start,
            period_end=period_end,
            is_mapped=is_mapped,
            filing_date=filing_date,
        )

    def _extract_value(self, fact: ModelFact) -> Decimal | None:
        """Convert the fact's string value to Decimal, or None if unusable."""
        raw = getattr(fact, "value", None)
        if raw is None or raw == "":
            return None
        try:
            return Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return None

    def _unit_to_str(self, fact: ModelFact) -> str:
        """Render the fact's unit as a short string like 'iso4217:IDR' or 'pure'."""
        unit = fact.unit
        measures = getattr(unit, "measures", None)
        if not measures or not measures[0]:
            return "unknown"
        parts: list[str] = []
        for qn in measures[0]:
            prefix = getattr(qn, "prefix", "") or ""
            localname = getattr(qn, "localName", "") or str(qn)
            parts.append(f"{prefix}:{localname}" if prefix else localname)
        return "*".join(parts)

    def _validate_unit(self, fact: ModelFact, unit_str: str) -> None:
        """Raise DataQualityError for non-IDR monetary units.

        Pure/shares/percentage units are accepted as non-monetary.
        """
        lowered = unit_str.lower()
        if any(m in unit_str for m in _IDR_UNIT_MARKERS):
            return
        if any(m.lower() in lowered for m in _NON_MONETARY_MARKERS):
            return
        if "iso4217" in lowered:
            concept_name = (
                fact.qname.localName if fact.qname is not None else "unknown"
            )
            raise DataQualityError(
                f"non_idr_monetary_fact: concept={concept_name} "
                f"unit={unit_str}",
            )
        # Unknown unit namespace — not a known monetary currency. Let through
        # but log once; common for custom IDX unit definitions like "shares".

    def _classify_context(self, context_id: str, ctx: Any) -> str:
        """Map an IDX contextID to one of the four primary context types.

        IDX XBRL conventions:
            CurrentYearDuration[_N]    -> income_current
            PriorYearDuration[_N]      -> income_prior
            CurrentYearInstant[_N]     -> balance_current
            PriorEndYearInstant[_N]    -> balance_prior
            PriorYearInstant[_N]       -> balance_prior (some filings)

        Anything else (dimensional, restated, segmented) is classified as
        `other` and currently dropped from the four-context downstream
        path. Facts are still captured in the result for completeness.
        """
        cid = context_id or ""
        has_current = "CurrentYear" in cid
        has_prior = "PriorYear" in cid or "PriorEndYear" in cid
        has_duration = "Duration" in cid
        has_instant = "Instant" in cid

        if has_current and has_duration:
            return "income_current"
        if has_prior and has_duration:
            return "income_prior"
        if has_current and has_instant:
            return "balance_current"
        if has_prior and has_instant:
            return "balance_prior"
        return "other"

    def _extract_decimals(self, fact: ModelFact) -> int | None:
        raw = getattr(fact, "decimals", None)
        if raw is None or raw == "" or raw == "INF":
            return None
        try:
            return int(str(raw))
        except (ValueError, TypeError):
            return None

    def _extract_period_dates(
        self, ctx: Any,
    ) -> tuple[date | None, date | None]:
        """Extract (period_start, period_end) from a ModelContext."""
        start_dt = getattr(ctx, "startDatetime", None)
        end_dt = getattr(ctx, "endDatetime", None)
        instant_dt = getattr(ctx, "instantDatetime", None)

        start = start_dt.date() if start_dt is not None else None
        if end_dt is not None:
            end: date | None = end_dt.date()
        elif instant_dt is not None:
            end = instant_dt.date()
        else:
            end = None
        return start, end
