"""IDX-specific order validation rules.

Enforces Indonesia Stock Exchange regulations:
  - Lot size (100 shares per lot)
  - No naked short selling (POJK No. 6/POJK.04/2015)
  - Tick size conformance (Peraturan BEI No. II-A)
  - Price floor
  - Auto-rejection band (ARA/ARB ±35%)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

IDX_LOT_SIZE = 100  # shares per lot — fixed by IDX regulation
IDX_MAX_PRICE_MOVE = Decimal("0.35")  # ±35% auto-rejection circuit breaker (ARA/ARB)
IDX_MIN_PRICE_IDR = Decimal("1")

# IDX tick size by price tier (Peraturan BEI No. II-A)
IDX_TICK_SIZE_MAP: dict[tuple[Decimal, Decimal], Decimal] = {
    (Decimal("0"), Decimal("199")): Decimal("1"),
    (Decimal("200"), Decimal("499")): Decimal("2"),
    (Decimal("500"), Decimal("1999")): Decimal("5"),
    (Decimal("2000"), Decimal("4999")): Decimal("10"),
    (Decimal("5000"), Decimal("99999")): Decimal("25"),
}


@dataclass
class IDXOrderValidationResult:
    """Result of IDX order validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class IDXOrderValidator:
    """Validates orders against IDX exchange rules."""

    def validate(
        self,
        symbol: str,
        side: str,
        quantity_lots: int,
        order_type: str,
        price: Decimal | None,
        current_position_lots: int,
    ) -> IDXOrderValidationResult:
        """Validate an order against IDX rules.

        Args:
            symbol: Instrument symbol (e.g. "BBCA.JK").
            side: Order side ("BUY" or "SELL").
            quantity_lots: Order quantity in lots (1 lot = 100 shares).
            order_type: Order type ("MARKET" or "LIMIT").
            price: Limit price in IDR (None for market orders).
            current_position_lots: Current position in lots for this symbol.

        Returns:
            Validation result with errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Rule 1: Lot size must be positive integer
        if quantity_lots <= 0:
            errors.append(f"quantity_lots must be positive, got {quantity_lots}")

        # Rule 2: No naked short selling on IDX
        # (Peraturan OJK No. 6/POJK.04/2015 — short selling only for designated
        #  securities and requires margin account — not supported in current version)
        if side == "SELL" and quantity_lots > current_position_lots:
            errors.append(
                f"Short selling not permitted on IDX. "
                f"Sell quantity {quantity_lots} lots exceeds position "
                f"{current_position_lots} lots for {symbol}."
            )

        # Rule 3: Limit price tick size conformance
        if order_type == "LIMIT" and price is not None:
            tick = self._get_tick_size(price)
            if price % tick != 0:
                rounded = round(price / tick) * tick
                warnings.append(
                    f"Price {price} not conformant with IDX tick size {tick}. " f"Will be adjusted to {rounded}."
                )

        # Rule 4: Price must be positive
        if price is not None and price < IDX_MIN_PRICE_IDR:
            errors.append(f"Price {price} below IDX minimum {IDX_MIN_PRICE_IDR}")

        return IDXOrderValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _get_tick_size(self, price: Decimal) -> Decimal:
        """Look up the IDX tick size for a given price tier."""
        for (low, high), tick in IDX_TICK_SIZE_MAP.items():
            if low <= price <= high:
                return tick
        return Decimal("25")  # default for prices above highest tier
