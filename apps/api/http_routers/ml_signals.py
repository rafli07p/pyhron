"""ML signals API endpoints.

Provides endpoints for retrieving ML signal scores, current regime,
and model metadata.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/ml", tags=["ml-signals"], redirect_slashes=False)


class SignalResponse(BaseModel):
    symbol: str
    score: float
    regime: str
    vol_forecast: float
    features: dict[str, float]


class RegimeResponse(BaseModel):
    regime: str
    confidence: float
    as_of: str


class ModelSummary(BaseModel):
    name: str
    version: str
    is_sharpe: float = Field(description="In-sample Sharpe ratio")
    registered_at: str


@router.get("/signals", response_model=list[SignalResponse])
async def get_signals(
    symbols: str = Query(..., description="Comma-separated symbols (e.g. BBCA,TLKM,ASII)"),
    as_of: str | None = Query(default=None, description="Point-in-time timestamp (ISO 8601)"),
) -> list[SignalResponse]:
    """Get ML signal scores for the specified symbols."""
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No symbols provided",
        )

    now = datetime.now(tz=UTC)
    as_of_str = as_of or now.isoformat()

    # In production, this would call FeatureStore + XGBRanker + RegimeClassifier
    # For now, return stub responses
    results: list[SignalResponse] = []
    for sym in symbol_list:
        results.append(
            SignalResponse(
                symbol=sym,
                score=0.0,
                regime="sideways",
                vol_forecast=0.02,
                features={},
            )
        )

    logger.info("ml_signals_served", n_symbols=len(results), as_of=as_of_str)
    return results


@router.get("/regime", response_model=RegimeResponse)
async def get_regime() -> RegimeResponse:
    """Get the current market regime classification."""
    now = datetime.now(tz=UTC)

    # In production: call RegimeClassifier.current_regime()
    return RegimeResponse(
        regime="sideways",
        confidence=0.0,
        as_of=now.isoformat(),
    )


@router.get("/models", response_model=list[ModelSummary])
async def list_models() -> list[ModelSummary]:
    """List all registered ML models."""
    # In production: query ModelRegistry
    return [
        ModelSummary(
            name="xgb_ranker",
            version="0",
            is_sharpe=0.0,
            registered_at=datetime.now(tz=UTC).isoformat(),
        ),
        ModelSummary(
            name="lstm_volatility",
            version="0",
            is_sharpe=0.0,
            registered_at=datetime.now(tz=UTC).isoformat(),
        ),
        ModelSummary(
            name="regime_classifier",
            version="0",
            is_sharpe=0.0,
            registered_at=datetime.now(tz=UTC).isoformat(),
        ),
    ]
