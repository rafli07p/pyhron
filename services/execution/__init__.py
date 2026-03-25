"""Execution service for the Pyhron trading platform.

Provides smart order routing, real exchange connectivity (Alpaca, CCXT),
low-latency execution engine, and an internal trade-matching engine for
paper trading and dark-pool simulation.
"""

from services.execution.exchange_connectors import AlpacaConnector, CCXTConnector
from services.execution.execution_engine import ExecutionEngine
from services.execution.order_router import OrderRouter
from services.execution.trade_matching import TradeMatchingEngine

__all__ = [
    "AlpacaConnector",
    "CCXTConnector",
    "ExecutionEngine",
    "OrderRouter",
    "TradeMatchingEngine",
]
