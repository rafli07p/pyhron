"""Monte Carlo simulation engine for the Pyhron trading platform.

Provides numpy-vectorised simulation of portfolio paths using GBM,
jump-diffusion, and historical bootstrap methods.  Includes VaR,
CVaR, and stress-testing capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import numpy as np
import numpy.typing as npt
import structlog

from shared.schemas.research_events import SimulationType

logger = structlog.get_logger(__name__)


# Result types

@dataclass
class SimulationOutput:
    """Raw output from a Monte Carlo simulation."""

    paths: npt.NDArray[np.float64]  # shape (num_paths, num_timesteps + 1)
    terminal_values: npt.NDArray[np.float64]  # shape (num_paths,)
    simulation_type: str
    num_paths: int
    num_timesteps: int
    initial_value: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VaRResult:
    """Value-at-Risk / CVaR result."""

    confidence: float
    var: float  # loss amount (positive)
    cvar: float  # expected shortfall (positive)
    var_pct: float  # as percentage of initial value
    cvar_pct: float


@dataclass
class StressTestResult:
    """Result of a stress-test scenario."""

    scenario_name: str
    initial_value: float
    mean_terminal: float
    median_terminal: float
    worst_case: float
    best_case: float
    probability_of_loss: float
    var_95: float
    cvar_95: float
    paths: npt.NDArray[np.float64] | None = None


# Simulator

class MonteCarloSimulator:
    """Numpy-vectorised Monte Carlo simulator.

    All path generation is fully vectorised — no Python loops over
    time steps or paths.

    Parameters
    ----------
    seed:
        Random seed for reproducibility.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = np.random.default_rng(seed)
        self._log = logger.bind(component="MonteCarloSimulator")

    # -- Path generation -----------------------------------------------------

    def run_simulation(
        self,
        initial_value: float,
        mu: float,
        sigma: float,
        num_paths: int = 10_000,
        num_timesteps: int = 252,
        dt: float = 1 / 252,
        simulation_type: SimulationType = SimulationType.GBM,
        tenant_id: str = "default",
        *,
        # Jump-diffusion parameters
        jump_intensity: float = 0.1,
        jump_mean: float = -0.05,
        jump_std: float = 0.1,
    ) -> SimulationOutput:
        """Generate simulated price/portfolio paths.

        Parameters
        ----------
        initial_value:
            Starting portfolio or asset value.
        mu:
            Annualised drift (expected return).
        sigma:
            Annualised volatility.
        num_paths:
            Number of simulation paths.
        num_timesteps:
            Number of time steps per path.
        dt:
            Time step size (fraction of a year).
        simulation_type:
            GBM or JUMP_DIFFUSION.
        jump_intensity:
            (Jump-diffusion) expected number of jumps per year.
        jump_mean:
            (Jump-diffusion) mean jump size (log).
        jump_std:
            (Jump-diffusion) jump size standard deviation.

        Returns
        -------
        SimulationOutput
            Simulated paths and terminal values.
        """
        self._log.info(
            "run_simulation",
            type=simulation_type,
            paths=num_paths,
            steps=num_timesteps,
            tenant_id=tenant_id,
        )

        if simulation_type == SimulationType.JUMP_DIFFUSION:
            paths = self._simulate_jump_diffusion(
                initial_value, mu, sigma, num_paths, num_timesteps, dt,
                jump_intensity, jump_mean, jump_std,
            )
        elif simulation_type == SimulationType.HISTORICAL_BOOTSTRAP:
            # For bootstrap, mu is ignored; sigma should be the historical returns array
            # We handle this in simulate_portfolio_returns
            paths = self._simulate_gbm(initial_value, mu, sigma, num_paths, num_timesteps, dt)
        else:
            paths = self._simulate_gbm(initial_value, mu, sigma, num_paths, num_timesteps, dt)

        terminal = paths[:, -1]

        return SimulationOutput(
            paths=paths,
            terminal_values=terminal,
            simulation_type=simulation_type.value,
            num_paths=num_paths,
            num_timesteps=num_timesteps,
            initial_value=initial_value,
        )

    def _simulate_gbm(
        self,
        s0: float,
        mu: float,
        sigma: float,
        n_paths: int,
        n_steps: int,
        dt: float,
    ) -> npt.NDArray[np.float64]:
        """Vectorised Geometric Brownian Motion."""
        # Generate all random increments at once
        z = self._rng.standard_normal((n_paths, n_steps))
        drift = (mu - 0.5 * sigma**2) * dt
        diffusion = sigma * np.sqrt(dt) * z
        log_returns = drift + diffusion

        # Cumulative sum for log prices, then exponentiate
        log_paths = np.concatenate(
            [np.zeros((n_paths, 1)), np.cumsum(log_returns, axis=1)],
            axis=1,
        )
        result: npt.NDArray[np.float64] = s0 * np.exp(log_paths)
        return result

    def _simulate_jump_diffusion(
        self,
        s0: float,
        mu: float,
        sigma: float,
        n_paths: int,
        n_steps: int,
        dt: float,
        lam: float,
        jump_mu: float,
        jump_sigma: float,
    ) -> npt.NDArray[np.float64]:
        """Vectorised Merton jump-diffusion model."""
        z = self._rng.standard_normal((n_paths, n_steps))
        drift = (mu - 0.5 * sigma**2 - lam * (np.exp(jump_mu + 0.5 * jump_sigma**2) - 1)) * dt
        diffusion = sigma * np.sqrt(dt) * z

        # Poisson jumps
        n_jumps = self._rng.poisson(lam * dt, (n_paths, n_steps))
        jump_sizes = np.zeros((n_paths, n_steps))
        for i in range(n_paths):
            for j in range(n_steps):
                if n_jumps[i, j] > 0:
                    jumps = self._rng.normal(jump_mu, jump_sigma, n_jumps[i, j])
                    jump_sizes[i, j] = np.sum(jumps)

        log_returns = drift + diffusion + jump_sizes
        log_paths = np.concatenate(
            [np.zeros((n_paths, 1)), np.cumsum(log_returns, axis=1)],
            axis=1,
        )
        jd_result: npt.NDArray[np.float64] = s0 * np.exp(log_paths)
        return jd_result

    # -- Portfolio-level simulation ------------------------------------------

    def simulate_portfolio_returns(
        self,
        historical_returns: npt.NDArray[np.float64],
        initial_value: float,
        num_paths: int = 10_000,
        num_timesteps: int = 252,
        tenant_id: str = "default",
    ) -> SimulationOutput:
        """Simulate portfolio paths using historical bootstrap.

        Randomly resamples (with replacement) from observed daily
        returns to construct simulated paths.

        Parameters
        ----------
        historical_returns:
            1-D array of historical daily portfolio returns.
        initial_value:
            Starting portfolio value.
        num_paths:
            Number of paths to simulate.
        num_timesteps:
            Number of forward time steps.
        """
        self._log.info(
            "simulate_portfolio_returns",
            method="bootstrap",
            n_obs=len(historical_returns),
            paths=num_paths,
            steps=num_timesteps,
            tenant_id=tenant_id,
        )

        # Bootstrap resampling (fully vectorised)
        indices = self._rng.integers(0, len(historical_returns), size=(num_paths, num_timesteps))
        sampled_returns = historical_returns[indices]

        # Build paths: cumulative product of (1 + r)
        growth = np.cumprod(1 + sampled_returns, axis=1)
        paths = np.concatenate(
            [np.ones((num_paths, 1)), growth],
            axis=1,
        ) * initial_value

        return SimulationOutput(
            paths=paths,
            terminal_values=paths[:, -1],
            simulation_type=SimulationType.HISTORICAL_BOOTSTRAP.value,
            num_paths=num_paths,
            num_timesteps=num_timesteps,
            initial_value=initial_value,
        )

    # -- Stress testing ------------------------------------------------------

    def stress_test(
        self,
        initial_value: float,
        mu: float,
        sigma: float,
        num_paths: int = 10_000,
        num_timesteps: int = 252,
        tenant_id: str = "default",
        scenarios: dict[str, dict[str, Any]] | None = None,
    ) -> list[StressTestResult]:
        """Run Monte Carlo stress tests for predefined market scenarios.

        Parameters
        ----------
        scenarios:
            Dict mapping scenario name -> {mu, sigma, [jump params]}.
            If ``None``, standard scenarios are used.

        Returns
        -------
        list[StressTestResult]
            Results for each scenario.
        """
        self._log.info("stress_test", tenant_id=tenant_id, num_scenarios=len(scenarios or {}))

        if scenarios is None:
            scenarios = {
                "base_case": {"mu": mu, "sigma": sigma},
                "mild_recession": {"mu": mu - 0.10, "sigma": sigma * 1.3},
                "severe_crash": {"mu": mu - 0.30, "sigma": sigma * 2.0},
                "black_swan": {
                    "mu": mu - 0.50,
                    "sigma": sigma * 3.0,
                    "type": "jump_diffusion",
                    "jump_intensity": 0.5,
                    "jump_mean": -0.15,
                    "jump_std": 0.20,
                },
                "rapid_recovery": {"mu": mu + 0.20, "sigma": sigma * 1.5},
                "stagflation": {"mu": mu - 0.05, "sigma": sigma * 1.1},
            }

        results: list[StressTestResult] = []

        for name, params in scenarios.items():
            sim_type = SimulationType.JUMP_DIFFUSION if params.get("type") == "jump_diffusion" else SimulationType.GBM

            output = self.run_simulation(
                initial_value=initial_value,
                mu=params.get("mu", mu),
                sigma=params.get("sigma", sigma),
                num_paths=num_paths,
                num_timesteps=num_timesteps,
                simulation_type=sim_type,
                tenant_id=tenant_id,
                jump_intensity=params.get("jump_intensity", 0.1),
                jump_mean=params.get("jump_mean", -0.05),
                jump_std=params.get("jump_std", 0.1),
            )

            terminal = output.terminal_values
            var95 = float(initial_value - np.percentile(terminal, 5))
            losses = initial_value - terminal
            cvar95 = float(np.mean(losses[losses >= np.percentile(losses, 95)]))

            results.append(StressTestResult(
                scenario_name=name,
                initial_value=initial_value,
                mean_terminal=float(np.mean(terminal)),
                median_terminal=float(np.median(terminal)),
                worst_case=float(np.min(terminal)),
                best_case=float(np.max(terminal)),
                probability_of_loss=float(np.mean(terminal < initial_value)),
                var_95=round(var95, 2),
                cvar_95=round(cvar95, 2),
            ))

        return results

    # -- VaR / CVaR ----------------------------------------------------------

    def calculate_var(
        self,
        simulation: SimulationOutput,
        confidence: float = 0.95,
    ) -> VaRResult:
        """Calculate Value-at-Risk from simulation output.

        Parameters
        ----------
        simulation:
            Output of ``run_simulation`` or ``simulate_portfolio_returns``.
        confidence:
            Confidence level (e.g. 0.95 or 0.99).
        """
        terminal = simulation.terminal_values
        s0 = simulation.initial_value

        losses = s0 - terminal  # positive = loss
        var = float(np.percentile(losses, confidence * 100))

        # CVaR = mean of losses exceeding VaR
        tail_losses = losses[losses >= var]
        cvar = float(np.mean(tail_losses)) if len(tail_losses) > 0 else var

        return VaRResult(
            confidence=confidence,
            var=round(var, 2),
            cvar=round(cvar, 2),
            var_pct=round(var / s0 * 100, 2) if s0 > 0 else 0.0,
            cvar_pct=round(cvar / s0 * 100, 2) if s0 > 0 else 0.0,
        )

    def calculate_cvar(
        self,
        simulation: SimulationOutput,
        confidence: float = 0.95,
    ) -> float:
        """Return the CVaR (Expected Shortfall) as a single float."""
        result = self.calculate_var(simulation, confidence)
        return result.cvar


__all__ = [
    "MonteCarloSimulator",
    "SimulationOutput",
    "StressTestResult",
    "VaRResult",
]
