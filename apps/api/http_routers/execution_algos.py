"""Execution algorithms API endpoints.

Provides endpoints for listing available algorithms, scheduling
child orders, and querying execution status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/execution", tags=["execution-algorithms"], redirect_slashes=False)

# In-memory schedule store (production: use DB)
_schedules: dict[str, dict[str, Any]] = {}


class AlgorithmInfo(BaseModel):
    name: str
    description: str
    parameters: list[str]


class ScheduleRequest(BaseModel):
    order_id: str
    algorithm: str = Field(default="TWAP", description="TWAP, VWAP, POV, or IS")
    params: dict[str, Any] = Field(default_factory=dict)


class ChildOrderResponse(BaseModel):
    symbol: str
    quantity: int
    limit_price: str | None = None
    scheduled_time: str
    algo_tag: str


class ScheduleResponse(BaseModel):
    schedule_id: str
    order_id: str
    algorithm: str
    child_orders: list[ChildOrderResponse]
    estimated_completion: str
    status: str = "pending"


class ScheduleStatusResponse(BaseModel):
    schedule_id: str
    order_id: str
    algorithm: str
    status: str
    total_child_orders: int
    filled_child_orders: int
    created_at: str


@router.get("/algorithms", response_model=list[AlgorithmInfo])
async def list_algorithms() -> list[AlgorithmInfo]:
    """List all available execution algorithms and their parameters."""
    return [
        AlgorithmInfo(
            name="TWAP",
            description="Time-Weighted Average Price",
            parameters=["num_slices", "randomize_pct"],
        ),
        AlgorithmInfo(
            name="VWAP",
            description="Volume-Weighted Average Price",
            parameters=["num_buckets", "volume_profile"],
        ),
        AlgorithmInfo(
            name="POV",
            description="Percentage of Volume",
            parameters=["participation_rate", "max_pct_adv"],
        ),
        AlgorithmInfo(
            name="IS",
            description="Implementation Shortfall (Almgren-Chriss)",
            parameters=["risk_aversion", "gamma", "eta", "daily_volatility"],
        ),
    ]


@router.post("/schedule", response_model=ScheduleResponse)
async def schedule_execution(request: ScheduleRequest) -> ScheduleResponse:
    """Schedule an execution algorithm for an order."""
    from pyhron.execution.algorithms import EXECUTION_ALGORITHMS

    if request.algorithm not in EXECUTION_ALGORITHMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown algorithm: {request.algorithm}. Available: {list(EXECUTION_ALGORITHMS.keys())}",
        )

    schedule_id = str(uuid4())
    now = datetime.now(tz=UTC)

    # Store schedule
    _schedules[request.order_id] = {
        "schedule_id": schedule_id,
        "order_id": request.order_id,
        "algorithm": request.algorithm,
        "params": request.params,
        "status": "pending",
        "created_at": now.isoformat(),
        "child_orders": [],
        "filled": 0,
    }

    logger.info(
        "execution_scheduled",
        schedule_id=schedule_id,
        order_id=request.order_id,
        algorithm=request.algorithm,
    )

    return ScheduleResponse(
        schedule_id=schedule_id,
        order_id=request.order_id,
        algorithm=request.algorithm,
        child_orders=[],
        estimated_completion=now.isoformat(),
        status="pending",
    )


@router.get("/schedule/{order_id}", response_model=ScheduleStatusResponse)
async def get_schedule_status(order_id: str) -> ScheduleStatusResponse:
    """Get the current status of a scheduled execution."""
    schedule = _schedules.get(order_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No schedule found for order {order_id}",
        )

    return ScheduleStatusResponse(
        schedule_id=schedule["schedule_id"],
        order_id=schedule["order_id"],
        algorithm=schedule["algorithm"],
        status=schedule["status"],
        total_child_orders=len(schedule["child_orders"]),
        filled_child_orders=schedule["filled"],
        created_at=schedule["created_at"],
    )
