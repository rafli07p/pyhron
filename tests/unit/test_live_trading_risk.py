"""Unit tests for live trading risk management.

Tests kill switch, promotion gate, parametric VaR,
sector HHI, capital allocator, and promotion blocking.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from services.risk.capital_allocator import MultiStrategyCapitalAllocator
from services.risk.kill_switch import KillSwitch
from services.risk.paper_to_live_gate import PaperToLivePromotionGate, PromotionBlockedError
from services.risk.portfolio_risk_engine import PortfolioRiskEngine, PositionData


# Helpers
def _make_mock_redis(triggered: bool = False) -> AsyncMock:
    """Create a mock Redis that returns True/None for GET based on triggered."""
    mock = AsyncMock()
    if triggered:
        mock.get = AsyncMock(return_value='{"reason":"test","triggered_by":"admin"}')
    else:
        mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    return mock


def _make_positions_across_sectors(
    sectors: list[str],
    equal_weight: bool = True,
    nav: Decimal = Decimal("500_000_000"),
) -> dict[str, PositionData]:
    """Create positions distributed across sectors."""
    n = len(sectors)
    weight = nav / n if equal_weight else nav
    positions = {}
    for i, sector in enumerate(sectors):
        symbol = f"SYM{i}"
        positions[symbol] = PositionData(
            symbol=symbol,
            quantity_shares=1000,
            avg_cost_idr=Decimal("10000"),
            last_price_idr=Decimal(str(weight / 1000)),
            sector=sector,
            market_value_idr=weight,
        )
    return positions


# Test 1: Kill switch halts order submission
@pytest.mark.asyncio
async def test_kill_switch_blocks_order() -> None:
    """Kill switch must block orders when triggered."""
    mock_redis = _make_mock_redis(triggered=True)
    kill_switch = KillSwitch(mock_redis)
    is_halted = await kill_switch.is_halted(strategy_id="strat-001")
    assert is_halted is True


# Test 2: Kill switch allows order when not triggered
@pytest.mark.asyncio
async def test_kill_switch_allows_order_when_clear() -> None:
    """Kill switch must allow orders when not triggered."""
    mock_redis = _make_mock_redis(triggered=False)
    kill_switch = KillSwitch(mock_redis)
    is_halted = await kill_switch.is_halted(strategy_id="strat-001")
    assert is_halted is False


# Test 3: Promotion gate rejects session under minimum days
@pytest.mark.asyncio
async def test_promotion_gate_rejects_short_session() -> None:
    """Promotion gate must reject sessions with fewer than 30 trading days."""
    gate = PaperToLivePromotionGate()

    # Mock DB session that returns a session with only 20 trading days
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = {
        "id": "session-001",
        "total_trades": 150,
        "winning_trades": 85,
        "max_drawdown_pct": Decimal("8.0"),
        "status": "STOPPED",
        "strategy_id": "strat-001",
        "trading_days": 20,  # Below 30 minimum
        "snapshot_count": 20,
    }
    mock_result.mappings.return_value = mock_mappings
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()

    audit = await gate.evaluate(
        session_id="session-001",
        checked_by="admin-001",
        db_session=mock_db,
    )
    assert audit.overall_pass is False
    assert audit.min_trading_days_met is False


# Test 4: Promotion gate passes qualifying session
@pytest.mark.asyncio
async def test_promotion_gate_passes_qualifying_session() -> None:
    """Promotion gate must pass sessions meeting all criteria."""
    gate = PaperToLivePromotionGate()

    # Mock returns for session data
    session_mock = MagicMock()
    session_mappings = MagicMock()
    session_mappings.first.return_value = {
        "id": "session-001",
        "total_trades": 250,
        "winning_trades": 145,
        "max_drawdown_pct": Decimal("8.0"),
        "status": "STOPPED",
        "strategy_id": "strat-001",
        "trading_days": 60,
        "snapshot_count": 60,
    }
    session_mock.mappings.return_value = session_mappings

    # Mock returns for Sharpe computation (daily returns)
    sharpe_mock = MagicMock()
    # Generate 60 daily returns with mean=0.001, std=0.01 -> Sharpe ~ 1.58
    import random

    random.seed(42)
    returns = [(0.001 + random.gauss(0, 0.01),) for _ in range(60)]
    sharpe_mock.all.return_value = returns

    # Mock for INSERT RETURNING
    insert_mock = MagicMock()
    insert_mock.mappings.return_value = MagicMock(first=MagicMock(return_value=None))

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return session_mock
        if call_count == 2:
            return sharpe_mock
        return insert_mock

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_db.flush = AsyncMock()

    audit = await gate.evaluate("session-001", "admin-001", mock_db)
    assert audit.overall_pass is True
    assert audit.min_trading_days_met is True
    assert audit.min_trades_met is True
    assert audit.max_drawdown_met is True
    assert audit.win_rate_met is True


# Test 5: Parametric VaR computed correctly
def test_parametric_var_single_position() -> None:
    """VaR for single position: 100M * 1.645 * 0.02 = 3,290,000."""
    engine = PortfolioRiskEngine()
    weights = np.array([1.0])
    cov = np.array([[0.0004]])  # daily vol = 2%
    var = engine.compute_parametric_var(
        weights=weights,
        covariance_matrix=cov,
        portfolio_value=Decimal("100_000_000"),
        horizon_days=1,
    )
    assert abs(float(var) - 3_290_000) < 100


# Test 6: Sector HHI correct for uniform distribution
def test_sector_hhi_uniform() -> None:
    """5 sectors equal weight: HHI = 5 * (0.2)^2 = 0.20."""
    engine = PortfolioRiskEngine()
    nav = Decimal("500_000_000")
    positions = _make_positions_across_sectors(
        sectors=["Finance", "Consumer", "Energy", "Infra", "Tech"],
        equal_weight=True,
        nav=nav,
    )
    sector_map = {sym: pos.sector for sym, pos in positions.items()}
    hhi = engine.compute_sector_hhi(
        positions=positions,
        sector_map=sector_map,
        nav_idr=nav,
    )
    assert abs(hhi - 0.20) < 0.01


# Test 7: Capital allocator equal weight
@pytest.mark.asyncio
async def test_equal_weight_allocation() -> None:
    """Equal weight allocator must distribute evenly."""
    allocator = MultiStrategyCapitalAllocator()
    result = await allocator.compute_allocations(
        total_capital_idr=Decimal("1_000_000_000"),
        active_strategies=["strat-1", "strat-2", "strat-3", "strat-4"],
        method="EQUAL_WEIGHT",
    )
    for v in result.values():
        assert v == Decimal("250_000_000.00")
    assert sum(result.values()) == Decimal("1_000_000_000")


# Test 8: Capital allocator respects max allocation constraint
@pytest.mark.asyncio
async def test_risk_parity_max_allocation_capped() -> None:
    """Risk parity must cap allocations at 60% maximum."""
    allocator = MultiStrategyCapitalAllocator()
    result = await allocator.compute_allocations(
        total_capital_idr=Decimal("1_000_000_000"),
        active_strategies=["low-vol-strat", "high-vol-strat"],
        method="RISK_PARITY",
        strategy_volatilities={"low-vol-strat": 0.001, "high-vol-strat": 0.05},
    )
    for v in result.values():
        assert v <= Decimal("600_000_000.01")  # Small rounding tolerance
    assert sum(result.values()) == Decimal("1_000_000_000")


# Test 9: Kill switch trigger cancels open orders
@pytest.mark.asyncio
async def test_kill_switch_cancels_open_orders() -> None:
    """Kill switch trigger must attempt to cancel all open orders."""
    mock_redis = _make_mock_redis(triggered=False)
    mock_broker = AsyncMock()
    mock_broker.cancel_all_orders = AsyncMock()
    kill_switch = KillSwitch(mock_redis, broker_adapter=mock_broker)

    event = await kill_switch.trigger(
        level="global",
        key=None,
        reason="manual test",
        triggered_by="admin-001",
        cancel_open_orders=True,
    )
    mock_broker.cancel_all_orders.assert_awaited_once()
    assert event.level == "global"
    assert event.reason == "manual test"


# Test 10: Promotion blocked if no passing audit
@pytest.mark.asyncio
async def test_promotion_blocked_without_audit() -> None:
    """Promotion must be blocked when no passing audit exists within 7 days."""
    gate = PaperToLivePromotionGate()

    # Mock: session exists and is STOPPED
    session_mock = MagicMock()
    session_mappings = MagicMock()
    session_mappings.first.return_value = {
        "id": "session-001",
        "strategy_id": "strat-001",
        "status": "STOPPED",
    }
    session_mock.mappings.return_value = session_mappings

    # Mock: no passing audit found
    audit_mock = MagicMock()
    audit_mappings = MagicMock()
    audit_mappings.first.return_value = None
    audit_mock.mappings.return_value = audit_mappings

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return session_mock
        return audit_mock

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)

    with pytest.raises(PromotionBlockedError, match="No passing audit"):
        await gate.promote(
            session_id="session-001",
            initial_capital_idr=Decimal("500_000_000"),
            max_position_size_pct=Decimal("10"),
            max_daily_loss_idr=Decimal("25_000_000"),
            max_drawdown_pct=Decimal("15"),
            promoted_by="admin-001",
            db_session=mock_db,
        )
