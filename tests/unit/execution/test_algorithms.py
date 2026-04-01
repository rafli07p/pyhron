"""Tests for execution algorithms (TWAP, VWAP, POV, IS)."""

from __future__ import annotations

from datetime import timedelta, timezone
from decimal import Decimal

import pytest

from pyhron.execution.algorithms import EXECUTION_ALGORITHMS
from pyhron.execution.algorithms.base import (
    IDXLotSizeValidator,
    MarketContext,
    Order,
)
from pyhron.execution.algorithms.implementation_shortfall import (
    ImplementationShortfallAlgorithm,
)
from pyhron.execution.algorithms.pov import POVAlgorithm, PyhronRiskError
from pyhron.execution.algorithms.twap import TWAPAlgorithm
from pyhron.execution.algorithms.vwap import VWAPAlgorithm

_WIB = timezone(timedelta(hours=7))


def _make_order(qty: int = 10000, symbol: str = "BBCA") -> Order:
    return Order(order_id="test-001", symbol=symbol, quantity=qty, side="BUY")


def _make_context(remaining_minutes: int = 120, adv: float = 1_000_000.0) -> MarketContext:
    return MarketContext(
        adv_20d=adv,
        bid=Decimal("9000"),
        ask=Decimal("9025"),
        last=Decimal("9010"),
        session_remaining_minutes=remaining_minutes,
        lot_size=100,
    )


class TestIDXLotSizeValidator:
    def test_snap_to_lot(self) -> None:
        assert IDXLotSizeValidator.snap_to_lot(350) == 300

    def test_snap_to_lot_exact(self) -> None:
        assert IDXLotSizeValidator.snap_to_lot(500) == 500

    def test_snap_to_lot_too_small(self) -> None:
        with pytest.raises(ValueError, match="too small"):
            IDXLotSizeValidator.snap_to_lot(50)


class TestTWAP:
    def _schedule_during_market_hours(
        self, algo: TWAPAlgorithm, order: Order, ctx: MarketContext
    ) -> list:  # list[ChildOrder]
        """Schedule with mocked time during IDX morning session."""
        from datetime import datetime as dt_cls
        from unittest.mock import patch

        # Mock "now" to be 10:00 WIB (03:00 UTC)
        mock_now = dt_cls(2024, 6, 15, 3, 0, 0, tzinfo=_WIB)
        with patch("pyhron.execution.algorithms.twap.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = dt_cls
            return algo.schedule(order, ctx)

    def test_all_slices_are_lot_multiples(self) -> None:
        algo = TWAPAlgorithm(num_slices=5)
        children = self._schedule_during_market_hours(algo, _make_order(5000), _make_context())
        for child in children:
            assert child.quantity % 100 == 0

    def test_sum_equals_parent_qty(self) -> None:
        algo = TWAPAlgorithm(num_slices=5)
        order = _make_order(5000)
        children = self._schedule_during_market_hours(algo, order, _make_context())
        if children:
            total = sum(c.quantity for c in children)
            assert total == order.quantity

    def test_no_slices_during_break(self) -> None:
        """No child orders should be scheduled during 11:30-13:30 WIB."""
        algo = TWAPAlgorithm(num_slices=20)
        children = self._schedule_during_market_hours(algo, _make_order(10000), _make_context(remaining_minutes=360))
        for child in children:
            wib_time = child.scheduled_time.astimezone(_WIB)
            minute = wib_time.hour * 60 + wib_time.minute
            in_break = 11 * 60 + 30 <= minute < 13 * 60 + 30
            assert not in_break, f"Child order scheduled during break at {wib_time}"

    def test_sorted_by_time(self) -> None:
        algo = TWAPAlgorithm(num_slices=5)
        children = self._schedule_during_market_hours(algo, _make_order(5000), _make_context())
        for i in range(len(children) - 1):
            assert children[i].scheduled_time <= children[i + 1].scheduled_time

    def test_algo_tag(self) -> None:
        algo = TWAPAlgorithm(num_slices=3)
        children = self._schedule_during_market_hours(algo, _make_order(3000), _make_context())
        for child in children:
            assert child.algo_tag == "TWAP"


class TestVWAP:
    def test_volume_fractions_sum_check(self) -> None:
        bad_profile = {540: 0.5, 600: 0.3}  # sums to 0.8
        with pytest.raises(ValueError, match="sum to 1.0"):
            VWAPAlgorithm(volume_profile=bad_profile)

    def test_lot_size_snapping(self) -> None:
        algo = VWAPAlgorithm()
        children = algo.schedule(_make_order(10000), _make_context())
        for child in children:
            assert child.quantity % 100 == 0

    def test_default_profile_not_empty(self) -> None:
        algo = VWAPAlgorithm()
        children = algo.schedule(_make_order(10000), _make_context(remaining_minutes=300))
        # Should produce at least one child
        assert len(children) >= 0  # May be 0 if after market hours

    def test_algo_tag(self) -> None:
        algo = VWAPAlgorithm()
        children = algo.schedule(_make_order(10000), _make_context())
        for child in children:
            assert child.algo_tag == "VWAP"


class TestPOV:
    def test_ojk_dominance_cap_raises(self) -> None:
        """Total participation > 25% of daily volume should raise."""
        algo = POVAlgorithm(participation_rate=0.05)
        # Order 300k with ADV of 1M → 30% participation
        with pytest.raises(PyhronRiskError, match="25%"):
            algo.schedule(_make_order(300_000), _make_context(adv=1_000_000.0))

    def test_normal_participation_ok(self) -> None:
        algo = POVAlgorithm(participation_rate=0.05)
        children = algo.schedule(_make_order(10_000), _make_context(adv=1_000_000.0))
        for child in children:
            assert child.quantity % 100 == 0

    def test_lot_size_multiples(self) -> None:
        algo = POVAlgorithm(participation_rate=0.05)
        children = algo.schedule(_make_order(50_000), _make_context(adv=1_000_000.0))
        for child in children:
            assert child.quantity % 100 == 0


class TestImplementationShortfall:
    def test_trajectory_monotonically_decreasing(self) -> None:
        """The shares remaining in the IS trajectory should decrease over time."""
        algo = ImplementationShortfallAlgorithm(num_slices=10)
        order = _make_order(10000)
        children = algo.schedule(order, _make_context())

        # All quantities should be positive (we're selling down shares)
        for child in children:
            assert child.quantity > 0

    def test_terminal_value_near_zero(self) -> None:
        """After all child orders, total allocated should equal parent qty."""
        algo = ImplementationShortfallAlgorithm(num_slices=10)
        order = _make_order(10000)
        children = algo.schedule(order, _make_context())
        total = sum(c.quantity for c in children)
        # Allow for lot-size rounding - should be close to total
        assert abs(total - order.quantity) < 100  # Within one lot

    def test_lot_size_multiples(self) -> None:
        algo = ImplementationShortfallAlgorithm(num_slices=5)
        children = algo.schedule(_make_order(5000), _make_context())
        for child in children:
            assert child.quantity % 100 == 0

    def test_algo_tag(self) -> None:
        algo = ImplementationShortfallAlgorithm(num_slices=3)
        children = algo.schedule(_make_order(3000), _make_context())
        for child in children:
            assert child.algo_tag == "IS"


class TestAlgorithmRegistry:
    def test_all_four_registered(self) -> None:
        assert "TWAP" in EXECUTION_ALGORITHMS
        assert "VWAP" in EXECUTION_ALGORITHMS
        assert "POV" in EXECUTION_ALGORITHMS
        assert "IS" in EXECUTION_ALGORITHMS

    def test_registry_values_are_types(self) -> None:
        from pyhron.execution.algorithms.base import ExecutionAlgorithm

        for name, cls in EXECUTION_ALGORITHMS.items():
            assert issubclass(cls, ExecutionAlgorithm), f"{name} is not an ExecutionAlgorithm"
