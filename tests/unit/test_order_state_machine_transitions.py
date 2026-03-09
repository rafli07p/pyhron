"""Unit tests for order state machine transitions.

Tests valid transition paths (e.g. PENDING_RISK -> RISK_APPROVED -> SUBMITTED -> FILLED)
and verifies that invalid transitions are blocked.
"""

from __future__ import annotations

import pytest

from data_platform.models.trading import OrderStatusEnum
from services.order_management_system.order_state_machine import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
)

# ── Valid Transition Path Tests ──────────────────────────────────────────────


class TestValidTransitionPaths:
    """Test complete valid order lifecycle paths."""

    def test_happy_path_buy_order(self):
        """NEW -> RISK_APPROVED -> SUBMITTED -> ACKNOWLEDGED -> FILLED."""
        path = [
            OrderStatusEnum.PENDING_RISK,
            OrderStatusEnum.RISK_APPROVED,
            OrderStatusEnum.SUBMITTED,
            OrderStatusEnum.ACKNOWLEDGED,
            OrderStatusEnum.FILLED,
        ]
        for i in range(len(path) - 1):
            from_s, to_s = path[i], path[i + 1]
            assert to_s in VALID_TRANSITIONS[from_s], f"Expected {from_s.value} -> {to_s.value} to be valid"

    def test_partial_fill_path(self):
        """ACKNOWLEDGED -> PARTIAL_FILL -> PARTIAL_FILL -> FILLED."""
        path = [
            OrderStatusEnum.ACKNOWLEDGED,
            OrderStatusEnum.PARTIAL_FILL,
            OrderStatusEnum.PARTIAL_FILL,
            OrderStatusEnum.FILLED,
        ]
        for i in range(len(path) - 1):
            from_s, to_s = path[i], path[i + 1]
            assert to_s in VALID_TRANSITIONS[from_s]

    def test_risk_rejection_path(self):
        """PENDING_RISK -> RISK_REJECTED (terminal)."""
        assert OrderStatusEnum.RISK_REJECTED in VALID_TRANSITIONS[OrderStatusEnum.PENDING_RISK]
        assert VALID_TRANSITIONS[OrderStatusEnum.RISK_REJECTED] == set()

    def test_cancellation_from_acknowledged(self):
        """ACKNOWLEDGED -> CANCELLED."""
        assert OrderStatusEnum.CANCELLED in VALID_TRANSITIONS[OrderStatusEnum.ACKNOWLEDGED]

    def test_cancellation_from_partial_fill(self):
        """PARTIAL_FILL -> CANCELLED."""
        assert OrderStatusEnum.CANCELLED in VALID_TRANSITIONS[OrderStatusEnum.PARTIAL_FILL]

    def test_expiry_from_acknowledged(self):
        """ACKNOWLEDGED -> EXPIRED."""
        assert OrderStatusEnum.EXPIRED in VALID_TRANSITIONS[OrderStatusEnum.ACKNOWLEDGED]

    def test_broker_rejection_path(self):
        """SUBMITTED -> REJECTED (terminal)."""
        assert OrderStatusEnum.REJECTED in VALID_TRANSITIONS[OrderStatusEnum.SUBMITTED]
        assert VALID_TRANSITIONS[OrderStatusEnum.REJECTED] == set()


# ── Invalid Transition Tests ────────────────────────────────────────────────


class TestInvalidTransitions:
    """Test that invalid transitions are properly blocked in the table."""

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            (OrderStatusEnum.FILLED, OrderStatusEnum.CANCELLED),
            (OrderStatusEnum.CANCELLED, OrderStatusEnum.FILLED),
            (OrderStatusEnum.RISK_REJECTED, OrderStatusEnum.SUBMITTED),
            (OrderStatusEnum.EXPIRED, OrderStatusEnum.ACKNOWLEDGED),
            (OrderStatusEnum.PENDING_RISK, OrderStatusEnum.FILLED),
            (OrderStatusEnum.PENDING_RISK, OrderStatusEnum.SUBMITTED),
            (OrderStatusEnum.SUBMITTED, OrderStatusEnum.FILLED),
            (OrderStatusEnum.REJECTED, OrderStatusEnum.ACKNOWLEDGED),
        ],
    )
    def test_invalid_transition_not_in_table(self, from_status, to_status):
        allowed = VALID_TRANSITIONS.get(from_status, set())
        assert to_status not in allowed, f"Transition {from_status.value} -> {to_status.value} should be invalid"

    def test_terminal_states_have_no_outgoing(self):
        for status in TERMINAL_STATES:
            assert VALID_TRANSITIONS[status] == set(), f"Terminal state {status.value} should have no transitions"

    def test_no_self_loops_except_partial_fill(self):
        for status, allowed in VALID_TRANSITIONS.items():
            if status == OrderStatusEnum.PARTIAL_FILL:
                assert OrderStatusEnum.PARTIAL_FILL in allowed
            else:
                assert status not in allowed, f"{status.value} has unexpected self-loop"

    def test_cannot_skip_risk_check(self):
        """Orders must go through risk check before submission."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.PENDING_RISK]
        assert OrderStatusEnum.SUBMITTED not in allowed
        assert OrderStatusEnum.ACKNOWLEDGED not in allowed

    def test_filled_is_truly_terminal(self):
        assert len(VALID_TRANSITIONS[OrderStatusEnum.FILLED]) == 0
