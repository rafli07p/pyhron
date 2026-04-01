"""Implementation Shortfall (Almgren-Chriss) execution algorithm.

Minimises E[Cost] + lambda * Var[Cost] over the trading trajectory
using the closed-form solution from the Almgren-Chriss (2000) framework.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from pyhron.execution.algorithms.base import (
    ChildOrder,
    ExecutionAlgorithm,
    IDXLotSizeValidator,
    MarketContext,
    Order,
)

_WIB = timezone(timedelta(hours=7))


class ImplementationShortfallAlgorithm(ExecutionAlgorithm):
    """Implementation Shortfall execution using Almgren-Chriss framework.

    Parameters
    ----------
    risk_aversion:
        Lambda parameter controlling risk-cost trade-off (default 1e-6).
    gamma:
        Permanent impact coefficient (default 0.1).
    eta:
        Temporary impact coefficient (default 0.05).
    daily_volatility:
        Annualised daily volatility of the asset (default 0.02 = 2% daily).
    num_slices:
        Number of time slices for discretisation.
    execution_horizon_days:
        Trading horizon in days (default 1).
    """

    def __init__(
        self,
        risk_aversion: float = 1e-6,
        gamma: float = 0.1,
        eta: float = 0.05,
        daily_volatility: float = 0.02,
        num_slices: int = 10,
        execution_horizon_days: float = 1.0,
    ) -> None:
        self._lambda = risk_aversion
        self._gamma = gamma
        self._eta = eta
        self._sigma = daily_volatility
        self._num_slices = num_slices
        self._horizon = execution_horizon_days

    def schedule(
        self,
        order: Order,
        market_context: MarketContext,
    ) -> list[ChildOrder]:
        lot_size = market_context.lot_size
        total_qty = order.quantity
        n = self._num_slices

        # Compute kappa: kappa^2 = lambda * sigma^2 / eta
        sigma = self._sigma
        eta = self._eta
        lam = self._lambda

        if eta <= 0 or sigma <= 0:
            # Fallback to uniform slicing
            return self._uniform_schedule(order, market_context)

        kappa_sq = lam * sigma * sigma / eta
        kappa = math.sqrt(kappa_sq) if kappa_sq > 0 else 1e-10

        T = self._horizon

        # Compute optimal trajectory x*(t) = X * sinh(kappa*(T-t)) / sinh(kappa*T)
        sinh_kT = math.sinh(kappa * T)
        if abs(sinh_kT) < 1e-15:
            return self._uniform_schedule(order, market_context)

        # Discretise: compute shares remaining at each time step
        dt = T / n
        trajectory: list[float] = []
        for i in range(n + 1):
            t = i * dt
            x_t = total_qty * math.sinh(kappa * (T - t)) / sinh_kT
            trajectory.append(x_t)

        # Shares to trade in each interval = x*(t_i) - x*(t_{i+1})
        now = datetime.now(tz=_WIB)
        interval_minutes = max(1, market_context.session_remaining_minutes // n)

        children: list[ChildOrder] = []
        allocated = 0

        for i in range(n):
            raw_qty = trajectory[i] - trajectory[i + 1]
            qty = IDXLotSizeValidator.snap_to_lot_floor(int(round(raw_qty)), lot_size)

            if i == n - 1:
                # Final slice gets the remainder
                qty = total_qty - allocated
                qty = IDXLotSizeValidator.snap_to_lot_floor(qty, lot_size)

            if qty <= 0:
                continue

            sched_time = now + timedelta(minutes=i * interval_minutes)
            allocated += qty

            children.append(
                ChildOrder(
                    symbol=order.symbol,
                    quantity=qty,
                    limit_price=None,
                    scheduled_time=sched_time,
                    algo_tag="IS",
                )
            )

        return sorted(children, key=lambda c: c.scheduled_time)

    def _uniform_schedule(
        self,
        order: Order,
        market_context: MarketContext,
    ) -> list[ChildOrder]:
        """Fallback: uniform slicing when trajectory is degenerate."""
        lot_size = market_context.lot_size
        n = self._num_slices
        total_qty = order.quantity
        now = datetime.now(tz=_WIB)
        interval_minutes = max(1, market_context.session_remaining_minutes // n)

        children: list[ChildOrder] = []
        allocated = 0

        for i in range(n):
            if i == n - 1:
                qty = total_qty - allocated
            else:
                qty = total_qty // n
            qty = IDXLotSizeValidator.snap_to_lot_floor(qty, lot_size)
            if qty <= 0:
                continue

            allocated += qty
            children.append(
                ChildOrder(
                    symbol=order.symbol,
                    quantity=qty,
                    limit_price=None,
                    scheduled_time=now + timedelta(minutes=i * interval_minutes),
                    algo_tag="IS",
                )
            )

        return sorted(children, key=lambda c: c.scheduled_time)
