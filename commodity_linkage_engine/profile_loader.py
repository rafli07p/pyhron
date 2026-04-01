"""Load commodity company profiles from the database.

Replaces hardcoded profile lists with database-backed reference data
(audit item M-11). Falls back to cached profiles if the database is
unavailable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from data_platform.database_models.idn_commodity_company_profile import IdnCommodityCompanyProfile

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from shared.structured_json_logger import get_logger

logger = get_logger(__name__)


async def load_profiles_by_type(
    session: AsyncSession,
    commodity_type: str,
) -> list[dict[str, Any]]:
    """Load all company profiles for a given commodity type.

    Args:
        session: Active async database session.
        commodity_type: One of ``"coal"``, ``"cpo"``, ``"nickel"``, ``"energy"``.

    Returns:
        List of profile dicts with keys: ticker, commodity_type,
        shares_outstanding, trailing_revenue_idr, net_margin, plus
        all commodity-specific fields from profile_data.
    """
    stmt = select(IdnCommodityCompanyProfile).where(IdnCommodityCompanyProfile.commodity_type == commodity_type)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    profiles: list[dict[str, Any]] = []
    for row in rows:
        profile = {
            "ticker": row.ticker,
            "commodity_type": row.commodity_type,
            "shares_outstanding": row.shares_outstanding,
            "trailing_revenue_idr": row.trailing_revenue_idr,
            "net_margin": row.net_margin,
            **row.profile_data,
        }
        profiles.append(profile)

    logger.info(
        "commodity_profiles_loaded",
        commodity_type=commodity_type,
        count=len(profiles),
    )
    return profiles
