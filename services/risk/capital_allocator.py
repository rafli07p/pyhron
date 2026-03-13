"""Multi-strategy capital allocator.

Allocates total capital across concurrent strategies using
equal weight, risk parity, or Sharpe-weighted methods.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AllocationAdjustment:
    """Required capital transfer between strategies."""

    strategy_id: str
    current_capital_idr: Decimal
    target_capital_idr: Decimal
    delta_idr: Decimal
    direction: str  # INCREASE | DECREASE


class MultiStrategyCapitalAllocator:
    """Allocates total capital across concurrent strategies.

    Constraints applied after weights computed:
    - Minimum allocation per strategy: 5% of total capital
    - Maximum allocation per strategy: 60% of total capital
    - Sum of allocations = 100% (fully invested)
    """

    METHODS = ("EQUAL_WEIGHT", "RISK_PARITY", "SHARPE_WEIGHTED")
    MIN_ALLOCATION_PCT = Decimal("0.05")
    MAX_ALLOCATION_PCT = Decimal("0.60")
    REBALANCE_THRESHOLD_IDR = Decimal("5_000_000")

    async def compute_allocations(
        self,
        total_capital_idr: Decimal,
        active_strategies: list[str],
        method: str,
        db_session: AsyncSession | None = None,
        strategy_volatilities: dict[str, float] | None = None,
        strategy_sharpes: dict[str, float] | None = None,
    ) -> dict[str, Decimal]:
        """Compute capital allocations.

        Returns {strategy_id: allocated_capital_idr}.
        Sum of values equals total_capital_idr.
        """
        if not active_strategies:
            return {}

        if method not in self.METHODS:
            msg = f"Unknown allocation method: {method}. Must be one of {self.METHODS}"
            raise ValueError(msg)

        n = len(active_strategies)

        if method == "EQUAL_WEIGHT":
            weights = {s: Decimal("1") / Decimal(str(n)) for s in active_strategies}

        elif method == "RISK_PARITY":
            vols = strategy_volatilities or {}
            inv_vols = {}
            for s in active_strategies:
                vol = vols.get(s, 0.02)  # Default 2% daily vol
                inv_vols[s] = Decimal(str(1.0 / max(vol, 1e-8)))

            total_inv = sum(inv_vols.values())
            weights = {s: v / total_inv for s, v in inv_vols.items()}

        elif method == "SHARPE_WEIGHTED":
            sharpes = strategy_sharpes or {}
            positive_sharpes = {}
            for s in active_strategies:
                sh = sharpes.get(s, 0.0)
                positive_sharpes[s] = Decimal(str(max(sh, 0.0)))

            total_sharpe = sum(positive_sharpes.values())
            if total_sharpe > 0:
                weights = {s: v / total_sharpe for s, v in positive_sharpes.items()}
            else:
                # Fall back to equal weight if all Sharpe <= 0
                weights = {s: Decimal("1") / Decimal(str(n)) for s in active_strategies}
        else:
            weights = {s: Decimal("1") / Decimal(str(n)) for s in active_strategies}

        # Apply constraints
        weights = self._apply_constraints(weights)

        # Convert to IDR allocations
        allocations = {}
        for s, w in weights.items():
            allocations[s] = (total_capital_idr * w).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Fix rounding: adjust largest allocation to ensure sum == total
        alloc_sum = sum(allocations.values())
        diff = total_capital_idr - alloc_sum
        if diff != 0 and allocations:
            largest = max(allocations, key=lambda k: allocations[k])
            allocations[largest] += diff

        return allocations

    def _apply_constraints(self, weights: dict[str, Decimal]) -> dict[str, Decimal]:
        """Apply min/max allocation constraints.

        Clips weights to [MIN_ALLOCATION_PCT, MAX_ALLOCATION_PCT] and
        redistributes excess to unclamped strategies iteratively.
        """
        n = len(weights)
        if n == 0:
            return weights

        constrained = dict(weights)
        locked: set[str] = set()

        for _ in range(20):
            excess = Decimal("0")
            newly_locked = False

            for s in list(constrained.keys()):
                if s in locked:
                    continue
                if constrained[s] > self.MAX_ALLOCATION_PCT:
                    excess += constrained[s] - self.MAX_ALLOCATION_PCT
                    constrained[s] = self.MAX_ALLOCATION_PCT
                    locked.add(s)
                    newly_locked = True
                elif constrained[s] < self.MIN_ALLOCATION_PCT:
                    excess -= self.MIN_ALLOCATION_PCT - constrained[s]
                    constrained[s] = self.MIN_ALLOCATION_PCT
                    locked.add(s)
                    newly_locked = True

            if not newly_locked or excess == 0:
                break

            free = [s for s in constrained if s not in locked]
            if free:
                per_free = excess / Decimal(str(len(free)))
                for s in free:
                    constrained[s] += per_free
            elif excess > 0:
                # All strategies locked but excess remains — distribute proportionally
                # to strategies not at max, allowing them to rise toward max
                eligible = [s for s in constrained if constrained[s] < self.MAX_ALLOCATION_PCT]
                if eligible:
                    per_eligible = excess / Decimal(str(len(eligible)))
                    for s in eligible:
                        room = self.MAX_ALLOCATION_PCT - constrained[s]
                        constrained[s] += min(per_eligible, room)
                    locked.clear()  # Re-evaluate

        # Ensure weights sum to exactly 1.0
        total = sum(constrained.values())
        if total != Decimal("1") and total > 0:
            largest = max(constrained, key=lambda k: constrained[k])
            constrained[largest] += Decimal("1") - total

        return constrained

    async def rebalance_allocations(
        self,
        current_allocations: dict[str, Decimal],
        target_allocations: dict[str, Decimal],
        db_session: AsyncSession | None = None,
    ) -> list[AllocationAdjustment]:
        """Compute required capital transfers between strategies.

        Only returns adjustments above IDR 5,000,000 threshold.
        """
        adjustments = []
        all_strategies = set(current_allocations) | set(target_allocations)

        for strategy_id in all_strategies:
            current = current_allocations.get(strategy_id, Decimal("0"))
            target = target_allocations.get(strategy_id, Decimal("0"))
            delta = target - current

            if abs(delta) < self.REBALANCE_THRESHOLD_IDR:
                continue

            adjustments.append(
                AllocationAdjustment(
                    strategy_id=strategy_id,
                    current_capital_idr=current,
                    target_capital_idr=target,
                    delta_idr=delta,
                    direction="INCREASE" if delta > 0 else "DECREASE",
                )
            )

        return adjustments
