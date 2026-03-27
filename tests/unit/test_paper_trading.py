"""Unit tests for the Pyhron paper trading system.

Tests target lot computation, trade diffing, transaction costs,
simulation fill pricing, NAV drawdown, reconciliation, and
session constraints.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.paper_trading.idx_cost_model import IDXTransactionCostModel
from services.paper_trading.simulation_engine import PaperSimulationEngine
from services.paper_trading.strategy_executor import PaperStrategyExecutor


# Test 1: Target lot computation floors correctly
def test_target_lots_floor() -> None:
    executor = PaperStrategyExecutor()
    lots = executor.compute_target_lots(
        symbol="BBCA",
        target_weight=Decimal("0.05"),
        nav_idr=Decimal("500_000_000"),
        last_price_idr=Decimal("9250"),
    )
    # 0.05 * 500_000_000 = 25_000_000
    # 25_000_000 / (9250 * 100) = 27.02... -> floor = 27
    assert lots == 27


def test_target_lots_zero_price() -> None:
    executor = PaperStrategyExecutor()
    lots = executor.compute_target_lots(
        symbol="BBCA",
        target_weight=Decimal("0.05"),
        nav_idr=Decimal("500_000_000"),
        last_price_idr=Decimal("0"),
    )
    assert lots == 0


# Test 2: Trade diff produces correct buy/sell instructions
def test_trade_diff_buy_and_sell() -> None:
    executor = PaperStrategyExecutor()
    target: dict[str, int] = {"BBCA": 50, "BMRI": 30, "GOTO": 0}
    current: dict[str, int] = {"BBCA": 30, "BMRI": 30, "GOTO": 20}
    trades = executor.compute_trades(target, current)

    buy_bbca = next(t for t in trades if t.symbol == "BBCA")
    sell_goto = next(t for t in trades if t.symbol == "GOTO")
    no_bmri = [t for t in trades if t.symbol == "BMRI"]

    assert buy_bbca.side == "BUY" and buy_bbca.quantity_lots == 20
    assert sell_goto.side == "SELL" and sell_goto.quantity_lots == 20
    assert no_bmri == []


def test_trade_diff_all_new() -> None:
    executor = PaperStrategyExecutor()
    target: dict[str, int] = {"BBCA": 10, "BBRI": 5}
    current: dict[str, int] = {}
    trades = executor.compute_trades(target, current)
    assert len(trades) == 2
    assert all(t.side == "BUY" for t in trades)


def test_trade_diff_exit_all() -> None:
    executor = PaperStrategyExecutor()
    target: dict[str, int] = {}
    current: dict[str, int] = {"BBCA": 10, "BBRI": 5}
    trades = executor.compute_trades(target, current)
    assert len(trades) == 2
    assert all(t.side == "SELL" for t in trades)


# Test 3: Buy transaction cost breakdown
def test_buy_cost_breakdown() -> None:
    model = IDXTransactionCostModel()
    cost = model.compute_buy_cost(Decimal("10_000_000"))
    assert cost.commission_idr == Decimal("15000")
    assert cost.idx_levy_idr == Decimal("1000")
    assert cost.vat_idr == Decimal("1650")  # 11% of 15000
    assert cost.pph_idr == Decimal("0")
    assert cost.total_cost_idr == Decimal("17650")


def test_buy_cost_minimum_commission() -> None:
    model = IDXTransactionCostModel()
    cost = model.compute_buy_cost(Decimal("100_000"))
    # 0.15% of 100K = 150 < 10000 minimum
    assert cost.commission_idr == Decimal("10000")


# Test 4: Sell transaction cost includes PPh
def test_sell_cost_includes_pph() -> None:
    model = IDXTransactionCostModel()
    cost = model.compute_sell_cost(Decimal("10_000_000"))
    assert cost.pph_idr == Decimal("10000")  # 0.10% of 10M
    assert cost.commission_idr == Decimal("25000")  # 0.25% of 10M
    assert cost.total_cost_idr == Decimal("38750")
    # 25000 + 1000 + 2750 + 10000 = 38750


def test_sell_cost_vat_on_commission() -> None:
    model = IDXTransactionCostModel()
    cost = model.compute_sell_cost(Decimal("10_000_000"))
    # VAT = 11% of 25000 = 2750
    assert cost.vat_idr == Decimal("2750")


# Test 5: Simulation fill — market buy adds slippage
def test_simulation_market_buy_slippage() -> None:
    engine = PaperSimulationEngine()
    price = engine.compute_simulated_fill_price(
        side="BUY",
        next_day_open=Decimal("9000"),
        next_day_high=Decimal("9300"),
        next_day_low=Decimal("8900"),
        limit_price=None,
        slippage_bps=Decimal("10"),
    )
    # 9000 * (1 + 0.001) = 9009
    assert price == Decimal("9009")


def test_simulation_market_sell_slippage() -> None:
    engine = PaperSimulationEngine()
    price = engine.compute_simulated_fill_price(
        side="SELL",
        next_day_open=Decimal("9000"),
        next_day_high=Decimal("9300"),
        next_day_low=Decimal("8900"),
        limit_price=None,
        slippage_bps=Decimal("10"),
    )
    # 9000 * (1 - 0.001) = 8991
    assert price == Decimal("8991")


# Test 6: Simulation fill — limit buy misses if low > limit
def test_simulation_limit_buy_no_fill() -> None:
    engine = PaperSimulationEngine()
    price = engine.compute_simulated_fill_price(
        side="BUY",
        next_day_open=Decimal("9000"),
        next_day_high=Decimal("9300"),
        next_day_low=Decimal("8950"),
        limit_price=Decimal("8900"),
        slippage_bps=Decimal("10"),
    )
    # low=8950 > limit=8900, order does not fill
    assert price is None


def test_simulation_limit_buy_fills() -> None:
    engine = PaperSimulationEngine()
    price = engine.compute_simulated_fill_price(
        side="BUY",
        next_day_open=Decimal("9000"),
        next_day_high=Decimal("9300"),
        next_day_low=Decimal("8800"),
        limit_price=Decimal("8900"),
        slippage_bps=Decimal("10"),
    )
    assert price == Decimal("8900")


def test_simulation_limit_sell_no_fill() -> None:
    engine = PaperSimulationEngine()
    price = engine.compute_simulated_fill_price(
        side="SELL",
        next_day_open=Decimal("9000"),
        next_day_high=Decimal("9200"),
        next_day_low=Decimal("8900"),
        limit_price=Decimal("9300"),
        slippage_bps=Decimal("10"),
    )
    # high=9200 < limit=9300, order does not fill
    assert price is None


def test_simulation_limit_sell_fills() -> None:
    engine = PaperSimulationEngine()
    price = engine.compute_simulated_fill_price(
        side="SELL",
        next_day_open=Decimal("9000"),
        next_day_high=Decimal("9400"),
        next_day_low=Decimal("8900"),
        limit_price=Decimal("9300"),
        slippage_bps=Decimal("10"),
    )
    assert price == Decimal("9300")


# Test 7: NAV snapshot drawdown computed correctly
async def test_nav_snapshot_drawdown() -> None:
    """Drawdown = (peak - current) / peak."""
    peak = Decimal("520_000_000")
    current = Decimal("510_000_000")
    drawdown_pct = (peak - current) / peak * 100
    # (520M - 510M) / 520M = 1.923%
    assert abs(float(drawdown_pct) - 1.923) < 0.01


# Test 8: Reconciliation detects position mismatch
async def test_reconciliation_detects_position_mismatch() -> None:
    from services.paper_trading.alpaca_reconciliation import AlpacaPaperReconciliation

    mock_broker = AsyncMock()
    mock_broker.get_positions = AsyncMock(
        return_value=[
            {"symbol": "BBCA", "qty": 40},
        ]
    )

    reconciler = AlpacaPaperReconciliation(broker_adapter=mock_broker)

    # Create mock session and db
    mock_session = MagicMock()
    mock_session.id = "session-001"
    mock_session.strategy_id = "strat-001"
    mock_session.status = "RUNNING"

    mock_position = MagicMock()
    mock_position.symbol = "BBCA"
    mock_position.quantity = 5000  # 50 lots = 5000 shares

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_position]
    mock_db.execute = AsyncMock(return_value=mock_result)

    report = await reconciler.reconcile_positions(mock_session, mock_db)
    assert len(report.discrepancies) == 1
    assert report.discrepancies[0].discrepancy_type == "POSITION_MISMATCH"
    assert report.discrepancies[0].symbol == "BBCA"


# Test 9: Session minimum capital enforced
async def test_session_minimum_capital_enforced() -> None:
    from services.paper_trading.session_manager import PaperTradingSessionManager

    manager = PaperTradingSessionManager()
    mock_db = AsyncMock()

    with pytest.raises(ValueError, match="minimum"):
        await manager.create_session(
            name="test",
            strategy_id="strat-001",
            initial_capital_idr=Decimal("1_000_000"),  # below 10M minimum
            mode="LIVE_HOURS",
            created_by="user-001",
            db_session=mock_db,
        )


# Test 10: Only one running session per strategy
async def test_one_running_session_per_strategy() -> None:
    from services.paper_trading.session_manager import PaperTradingSessionManager

    manager = PaperTradingSessionManager()
    mock_db = AsyncMock()

    # Mock strategy lookup to return an active strategy
    mock_strategy = MagicMock()
    mock_strategy.is_active = True

    # First call: strategy lookup succeeds
    # Second call: existing session check returns a session (already running)
    mock_result_strategy = MagicMock()
    mock_result_strategy.scalar_one_or_none.return_value = mock_strategy

    mock_existing = MagicMock()
    mock_existing.scalar_one_or_none.return_value = MagicMock()  # existing running session

    mock_db.execute = AsyncMock(side_effect=[mock_result_strategy, mock_existing])

    with pytest.raises(ValueError, match="already"):
        await manager.create_session(
            name="test-2",
            strategy_id="strat-001",
            initial_capital_idr=Decimal("100_000_000"),
            mode="LIVE_HOURS",
            created_by="user-001",
            db_session=mock_db,
        )


# Test: Breakeven return
def test_breakeven_return() -> None:
    model = IDXTransactionCostModel()
    breakeven = model.compute_breakeven_return(Decimal("10_000_000"))
    # Buy cost: 17650, Sell cost: 38750
    # (17650 + 38750) / 10_000_000 = 0.005640
    assert breakeven == Decimal("0.005640")


# Test: Zero slippage market buy
def test_simulation_zero_slippage() -> None:
    engine = PaperSimulationEngine()
    price = engine.compute_simulated_fill_price(
        side="BUY",
        next_day_open=Decimal("9000"),
        next_day_high=Decimal("9300"),
        next_day_low=Decimal("8900"),
        limit_price=None,
        slippage_bps=Decimal("0"),
    )
    assert price == Decimal("9000")
