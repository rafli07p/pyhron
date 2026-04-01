"""Execution algorithm registry.

All four execution algorithms are exported here and registered in
``EXECUTION_ALGORITHMS`` for lookup by name.
"""

from __future__ import annotations

from pyhron.execution.algorithms.base import ExecutionAlgorithm
from pyhron.execution.algorithms.implementation_shortfall import (
    ImplementationShortfallAlgorithm,
)
from pyhron.execution.algorithms.pov import POVAlgorithm
from pyhron.execution.algorithms.twap import TWAPAlgorithm
from pyhron.execution.algorithms.vwap import VWAPAlgorithm

EXECUTION_ALGORITHMS: dict[str, type[ExecutionAlgorithm]] = {
    "TWAP": TWAPAlgorithm,
    "VWAP": VWAPAlgorithm,
    "POV": POVAlgorithm,
    "IS": ImplementationShortfallAlgorithm,
}

__all__ = [
    "EXECUTION_ALGORITHMS",
    "ExecutionAlgorithm",
    "ImplementationShortfallAlgorithm",
    "POVAlgorithm",
    "TWAPAlgorithm",
    "VWAPAlgorithm",
]
