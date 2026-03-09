"""Auto-generated Protobuf bindings for macro_economic_indicators.proto.

Regenerate with: bash scripts/generate_protobuf_python_bindings.sh
"""

from google.protobuf import message as _message

# Enum value constants for MacroIndicatorSource
MACRO_INDICATOR_SOURCE_UNSPECIFIED = 0
MACRO_INDICATOR_SOURCE_BANK_INDONESIA = 1
MACRO_INDICATOR_SOURCE_BPS_STATISTICS = 2
MACRO_INDICATOR_SOURCE_KEMENKEU = 3
MACRO_INDICATOR_SOURCE_ESDM = 4
MACRO_INDICATOR_SOURCE_BMKG = 5
MACRO_INDICATOR_SOURCE_NOAA = 6
MACRO_INDICATOR_SOURCE_OJK = 7

# Enum value constants for MacroIndicatorFrequency
MACRO_INDICATOR_FREQUENCY_UNSPECIFIED = 0
MACRO_INDICATOR_FREQUENCY_DAILY = 1
MACRO_INDICATOR_FREQUENCY_WEEKLY = 2
MACRO_INDICATOR_FREQUENCY_MONTHLY = 3
MACRO_INDICATOR_FREQUENCY_QUARTERLY = 4
MACRO_INDICATOR_FREQUENCY_POLICY_MEETING = 5


class MacroIndicatorEvent(_message.Message):
    """MacroIndicatorEvent protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        event_id: str = "",
        indicator_code: str = "",
        indicator_name: str = "",
        source: int = 0,
        frequency: int = 0,
        value: float = 0.0,
        previous_value: float = 0.0,
        change_absolute: float = 0.0,
        change_pct: float = 0.0,
        unit: str = "",
        period: str = "",
        reference_date=None,
        published_at=None,
        ingested_at=None,
        **kwargs,
    ):
        self.event_id = event_id
        self.indicator_code = indicator_code
        self.indicator_name = indicator_name
        self.source = source
        self.frequency = frequency
        self.value = value
        self.previous_value = previous_value
        self.change_absolute = change_absolute
        self.change_pct = change_pct
        self.unit = unit
        self.period = period
        self.reference_date = reference_date
        self.published_at = published_at
        self.ingested_at = ingested_at

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class CommodityPriceEvent(_message.Message):
    """CommodityPriceEvent protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        event_id: str = "",
        commodity_code: str = "",
        commodity_name: str = "",
        price: float = 0.0,
        previous_price: float = 0.0,
        change_pct: float = 0.0,
        currency: str = "",
        unit: str = "",
        source: int = 0,
        price_date=None,
        ingested_at=None,
        **kwargs,
    ):
        self.event_id = event_id
        self.commodity_code = commodity_code
        self.commodity_name = commodity_name
        self.price = price
        self.previous_price = previous_price
        self.change_pct = change_pct
        self.currency = currency
        self.unit = unit
        self.source = source
        self.price_date = price_date
        self.ingested_at = ingested_at

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class PolicyEventNotification(_message.Message):
    """PolicyEventNotification protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        event_id: str = "",
        event_type: str = "",
        title: str = "",
        description: str = "",
        source: int = 0,
        scheduled_at=None,
        expected_impact: str = "",
        affected_sectors=None,
        **kwargs,
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.title = title
        self.description = description
        self.source = source
        self.scheduled_at = scheduled_at
        self.expected_impact = expected_impact
        self.affected_sectors = affected_sectors or []

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class YieldCurvePoint(_message.Message):
    """YieldCurvePoint protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        tenor: str = "",
        yield_pct: float = 0.0,
        change_bps: float = 0.0,
        tenor_months: int = 0,
        **kwargs,
    ):
        self.tenor = tenor
        self.yield_pct = yield_pct
        self.change_bps = change_bps
        self.tenor_months = tenor_months

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")


class YieldCurveSnapshot(_message.Message):
    """YieldCurveSnapshot protobuf message stub."""

    DESCRIPTOR = None

    def __init__(
        self,
        snapshot_id: str = "",
        curve_date=None,
        points=None,
        two_year_ten_year_spread_bps: float = 0.0,
        real_yield_ten_year: float = 0.0,
        spread_vs_us_ten_year_bps: float = 0.0,
        **kwargs,
    ):
        self.snapshot_id = snapshot_id
        self.curve_date = curve_date
        self.points = points or []
        self.two_year_ten_year_spread_bps = two_year_ten_year_spread_bps
        self.real_yield_ten_year = real_yield_ten_year
        self.spread_vs_us_ten_year_bps = spread_vs_us_ten_year_bps

    def SerializeToString(self) -> bytes:
        raise NotImplementedError("Use protoc-generated code for serialization")

    def ParseFromString(self, data: bytes) -> None:
        raise NotImplementedError("Use protoc-generated code for deserialization")
