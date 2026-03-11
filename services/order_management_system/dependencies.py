"""FastAPI dependency providers for the Order Management System.

Constructs and caches the OMS components needed by API endpoints:
  - IDXOrderValidator
  - OrderStateMachine
  - OrderSubmissionHandler (direct API mode)
  - OrderFillEventProcessor

All components are singletons scoped to the application lifecycle.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from services.order_management_system.idx_order_validator import IDXOrderValidator
from services.order_management_system.order_fill_event_processor import (
    OrderFillEventProcessor,
)
from services.order_management_system.order_state_machine import OrderStateMachine
from services.order_management_system.order_submission_handler import (
    OrderSubmissionHandler,
)
from shared.async_database_session import get_session_factory
from shared.structured_json_logger import get_logger

if TYPE_CHECKING:
    from services.broker_connectivity.broker_adapter_interface import BrokerAdapterInterface
    from shared.kafka_producer_consumer import PyhronProducer

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_idx_validator() -> IDXOrderValidator:
    """Return the singleton IDXOrderValidator."""
    return IDXOrderValidator()


def build_order_submission_handler(
    broker_adapter: BrokerAdapterInterface,
    kafka_producer: PyhronProducer,
) -> OrderSubmissionHandler:
    """Build an OrderSubmissionHandler configured for direct API mode.

    Args:
        broker_adapter: The broker adapter for the IDX exchange.
        kafka_producer: Kafka producer for publishing order events.

    Returns:
        Fully wired OrderSubmissionHandler.
    """
    state_machine = OrderStateMachine(kafka_producer)

    return OrderSubmissionHandler(
        broker_registry={"IDX": broker_adapter},
        broker_adapter=broker_adapter,
        order_state_machine=state_machine,
        kafka_producer=kafka_producer,
        db_session_factory=get_session_factory(),
        idx_validator=get_idx_validator(),
    )


def build_fill_event_processor(
    kafka_producer: PyhronProducer,
) -> OrderFillEventProcessor:
    """Build an OrderFillEventProcessor.

    Args:
        kafka_producer: Kafka producer for publishing order events.

    Returns:
        Fully wired OrderFillEventProcessor.
    """
    return OrderFillEventProcessor(producer=kafka_producer)
