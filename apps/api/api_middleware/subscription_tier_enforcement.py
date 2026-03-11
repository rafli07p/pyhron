"""Subscription tier enforcement middleware.

Checks the authenticated user's subscription tier against endpoint
requirements. Premium endpoints return 403 for free-tier users.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.structured_json_logger import get_logger

logger = get_logger(__name__)

# ── Tier Configuration ───────────────────────────────────────────────────────

TIER_LEVELS: dict[str, int] = {
    "free": 0,
    "basic": 1,
    "pro": 2,
    "enterprise": 3,
}

# Path prefixes that require a minimum subscription tier
PREMIUM_PATHS: dict[str, str] = {
    "/v1/screener": "basic",
    "/v1/commodity-impact": "pro",
    "/v1/governance": "pro",
    "/v1/fixed-income": "basic",
    "/v1/backtest": "basic",
    "/v1/macro": "basic",
    "/v1/stocks": "basic",
}


def _get_required_tier(path: str) -> str | None:
    """Return the minimum tier required for a given path, or None if free."""
    for prefix, tier in PREMIUM_PATHS.items():
        if path.startswith(prefix):
            return tier
    return None


def _user_tier_level(tier: str) -> int:
    """Convert a tier name to its numeric level for comparison."""
    return TIER_LEVELS.get(tier, 0)


# ── Middleware ───────────────────────────────────────────────────────────────


class SubscriptionTierMiddleware(BaseHTTPMiddleware):
    """Enforce subscription tier requirements on premium endpoints."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        required_tier = _get_required_tier(request.url.path)
        if required_tier is None:
            return await call_next(request)

        # Extract user tier from request state (set by JWT middleware)
        user_claims: dict[str, Any] = getattr(request.state, "user_claims", {})
        user_tier = user_claims.get("subscription_tier", "free")
        required_level = _user_tier_level(required_tier)
        user_level = _user_tier_level(user_tier)

        if user_level < required_level:
            logger.warning(
                "subscription_tier_blocked",
                path=request.url.path,
                user_tier=user_tier,
                required_tier=required_tier,
            )
            return Response(
                content=(f'{{"detail":"Upgrade to {required_tier} tier or above to access this endpoint"}}'),
                status_code=403,
                media_type="application/json",
            )

        return await call_next(request)
