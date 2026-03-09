"""Indonesian government bond yield curve calculator.

Implements Nelson-Siegel-Svensson (NSS) interpolation to construct
a smooth yield curve from observed Indonesian government bond (SUN/SBN)
benchmark yields.

The NSS model:
    y(t) = b0 + b1 * [(1 - exp(-t/t1)) / (t/t1)]
         + b2 * [(1 - exp(-t/t1)) / (t/t1) - exp(-t/t1)]
         + b3 * [(1 - exp(-t/t2)) / (t/t2) - exp(-t/t2)]

Where b0=level, b1=slope, b2=curvature1, b3=curvature2.

Usage::

    calc = IndonesiaYieldCurveCalculator()
    curve = calc.fit_curve(observed_yields)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy.optimize import minimize

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ObservedYield:
    """Observed benchmark bond yield.

    Attributes:
        tenor_years: Time to maturity in years.
        yield_pct: Yield to maturity in percent.
        bond_code: Bond series code (e.g. ``FR0098``).
        observed_at: Observation timestamp.
    """

    tenor_years: float
    yield_pct: float
    bond_code: str
    observed_at: datetime


@dataclass
class YieldCurveSnapshot:
    """Fitted yield curve snapshot.

    Attributes:
        fitted_at: Curve fitting timestamp.
        nss_params: NSS model parameters (b0, b1, b2, b3, t1, t2).
        tenors: Array of tenor points (years).
        fitted_yields: Array of fitted yields at each tenor.
        residual_rmse: Root mean squared fitting error.
        spread_2y10y: 2Y-10Y yield spread in bps.
        curve_shape: Shape classification (normal, flat, inverted).
    """

    fitted_at: datetime
    nss_params: dict[str, float]
    tenors: list[float]
    fitted_yields: list[float]
    residual_rmse: float
    spread_2y10y: float
    curve_shape: str


class IndonesiaYieldCurveCalculator:
    """Nelson-Siegel-Svensson yield curve interpolation for SUN/SBN bonds.

    Fits the NSS model to observed benchmark yields and produces a
    smooth curve for pricing, spread analysis, and macro signalling.

    Args:
        output_tenors: Tenors at which to evaluate the fitted curve.
    """

    _DEFAULT_TENORS: list[float] = [
        0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0
    ]

    def __init__(
        self, output_tenors: list[float] | None = None
    ) -> None:
        self._output_tenors = output_tenors or list(self._DEFAULT_TENORS)
        logger.info(
            "yield_curve_calculator_initialised",
            num_output_tenors=len(self._output_tenors),
        )

    @staticmethod
    def _nss_yield(
        t: np.ndarray,
        b0: float, b1: float, b2: float, b3: float,
        t1: float, t2: float,
    ) -> np.ndarray:
        """Evaluate NSS model at given tenors.

        Args:
            t: Array of tenors (years).
            b0, b1, b2, b3: Level, slope, curvature1, curvature2.
            t1, t2: Decay parameters.

        Returns:
            Array of yield values.
        """
        t1 = max(t1, 0.01)
        t2 = max(t2, 0.01)
        x1 = t / t1
        x2 = t / t2

        factor1 = np.where(x1 > 0, (1 - np.exp(-x1)) / x1, 1.0)
        factor2 = factor1 - np.exp(-x1)
        factor3 = np.where(x2 > 0, (1 - np.exp(-x2)) / x2 - np.exp(-x2), 0.0)

        return b0 + b1 * factor1 + b2 * factor2 + b3 * factor3

    def fit_curve(
        self, observed: list[ObservedYield]
    ) -> YieldCurveSnapshot:
        """Fit NSS model to observed benchmark yields.

        Args:
            observed: List of observed benchmark bond yields.

        Returns:
            YieldCurveSnapshot with fitted parameters and evaluated curve.
        """
        tenors = np.array([o.tenor_years for o in observed])
        yields = np.array([o.yield_pct for o in observed])

        def objective(params: np.ndarray) -> float:
            b0, b1, b2, b3, t1, t2 = params
            fitted = self._nss_yield(tenors, b0, b1, b2, b3, t1, t2)
            return float(np.sum((yields - fitted) ** 2))

        x0 = np.array([7.0, -1.0, 0.5, 0.5, 1.5, 5.0])
        bounds = [(0, 20), (-10, 10), (-10, 10), (-10, 10), (0.01, 30), (0.01, 30)]

        result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
        b0, b1, b2, b3, t1, t2 = result.x

        output_t = np.array(self._output_tenors)
        fitted_yields = self._nss_yield(output_t, b0, b1, b2, b3, t1, t2)

        fitted_at_tenors = self._nss_yield(tenors, b0, b1, b2, b3, t1, t2)
        rmse = float(np.sqrt(np.mean((yields - fitted_at_tenors) ** 2)))

        y2 = float(self._nss_yield(np.array([2.0]), b0, b1, b2, b3, t1, t2)[0])
        y10 = float(self._nss_yield(np.array([10.0]), b0, b1, b2, b3, t1, t2)[0])
        spread = (y10 - y2) * 100  # bps

        if spread > 50:
            shape = "NORMAL"
        elif spread > -20:
            shape = "FLAT"
        else:
            shape = "INVERTED"

        snapshot = YieldCurveSnapshot(
            fitted_at=datetime.now(timezone.utc),
            nss_params={"b0": b0, "b1": b1, "b2": b2, "b3": b3, "t1": t1, "t2": t2},
            tenors=self._output_tenors,
            fitted_yields=[round(float(y), 4) for y in fitted_yields],
            residual_rmse=round(rmse, 6),
            spread_2y10y=round(spread, 2),
            curve_shape=shape,
        )

        logger.info(
            "yield_curve_fitted",
            rmse=snapshot.residual_rmse,
            spread_2y10y=snapshot.spread_2y10y,
            shape=shape,
        )
        return snapshot

    def interpolate_yield(
        self, tenor: float, params: dict[str, float]
    ) -> float:
        """Interpolate yield at arbitrary tenor using fitted NSS params.

        Args:
            tenor: Maturity in years.
            params: NSS parameters dictionary.

        Returns:
            Interpolated yield in percent.
        """
        t = np.array([tenor])
        y = self._nss_yield(
            t, params["b0"], params["b1"], params["b2"],
            params["b3"], params["t1"], params["t2"],
        )
        return float(y[0])
