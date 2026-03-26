"""Unit tests for OMS state machine transition table.

Validates that the transition table correctly defines valid and
invalid state changes, terminal states, and the transition graph.
"""

from __future__ import annotations

import pytest

try:
    from data_platform.models.trading import OrderStatusEnum
    from services.order_management_system.order_state_machine import (
        TERMINAL_STATES,
        VALID_TRANSITIONS,
    )
except ImportError:
    pytest.skip("Requires OMS and data_platform modules", allow_module_level=True)


class TestTransitionTable:
    """Tests for the order state transition table."""

    def test_all_statuses_present(self) -> None:
        """Every OrderStatusEnum value should be in VALID_TRANSITIONS."""
        for status in OrderStatusEnum:
            assert status in VALID_TRANSITIONS, f"Missing transition entry for {status}"

    def test_pending_risk_transitions(self) -> None:
        """PENDING_RISK can transition to RISK_APPROVED or RISK_REJECTED."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.PENDING_RISK]
        assert OrderStatusEnum.RISK_APPROVED in allowed
        assert OrderStatusEnum.RISK_REJECTED in allowed
        assert len(allowed) == 2

    def test_risk_approved_transitions(self) -> None:
        """RISK_APPROVED can transition to SUBMITTED, REJECTED, or CANCELLED."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.RISK_APPROVED]
        assert OrderStatusEnum.SUBMITTED in allowed
        assert OrderStatusEnum.REJECTED in allowed
        assert OrderStatusEnum.CANCELLED in allowed

    def test_submitted_transitions(self) -> None:
        """SUBMITTED can transition to ACKNOWLEDGED or REJECTED."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.SUBMITTED]
        assert OrderStatusEnum.ACKNOWLEDGED in allowed
        assert OrderStatusEnum.REJECTED in allowed

    def test_acknowledged_transitions(self) -> None:
        """ACKNOWLEDGED can transition to PARTIAL_FILL, FILLED, CANCELLED, or EXPIRED."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.ACKNOWLEDGED]
        assert OrderStatusEnum.PARTIAL_FILL in allowed
        assert OrderStatusEnum.FILLED in allowed
        assert OrderStatusEnum.CANCELLED in allowed
        assert OrderStatusEnum.EXPIRED in allowed

    def test_partial_fill_can_continue_filling(self) -> None:
        """PARTIAL_FILL should allow transitioning to itself (more fills)."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.PARTIAL_FILL]
        assert OrderStatusEnum.PARTIAL_FILL in allowed
        assert OrderStatusEnum.FILLED in allowed
        assert OrderStatusEnum.CANCELLED in allowed


class TestTerminalStates:
    """Tests for terminal state identification."""

    @pytest.mark.parametrize(
        "status",
        [
            OrderStatusEnum.RISK_REJECTED,
            OrderStatusEnum.REJECTED,
            OrderStatusEnum.FILLED,
            OrderStatusEnum.CANCELLED,
            OrderStatusEnum.EXPIRED,
        ],
    )
    def test_terminal_states_have_no_transitions(self, status: OrderStatusEnum) -> None:
        """Terminal states should have empty transition sets."""
        assert len(VALID_TRANSITIONS[status]) == 0
        assert status in TERMINAL_STATES

    @pytest.mark.parametrize(
        "status",
        [
            OrderStatusEnum.PENDING_RISK,
            OrderStatusEnum.RISK_APPROVED,
            OrderStatusEnum.SUBMITTED,
            OrderStatusEnum.ACKNOWLEDGED,
            OrderStatusEnum.PARTIAL_FILL,
        ],
    )
    def test_non_terminal_states_have_transitions(self, status: OrderStatusEnum) -> None:
        """Non-terminal states should have at least one valid transition."""
        assert len(VALID_TRANSITIONS[status]) > 0
        assert status not in TERMINAL_STATES

    def test_terminal_states_complete(self) -> None:
        """All and only empty-transition statuses should be terminal."""
        expected_terminal = {s for s, allowed in VALID_TRANSITIONS.items() if len(allowed) == 0}
        assert expected_terminal == TERMINAL_STATES


class TestTransitionGraphProperties:
    """Tests for properties of the transition graph."""

    def test_no_self_transition_except_partial_fill(self) -> None:
        """Only PARTIAL_FILL should allow self-transitions."""
        for status, allowed in VALID_TRANSITIONS.items():
            if status == OrderStatusEnum.PARTIAL_FILL:
                assert status in allowed
            else:
                assert status not in allowed, f"{status} should not self-transition"

    def test_no_backward_transitions_from_terminal(self) -> None:
        """Terminal states should not appear as targets of terminal states."""
        for status in TERMINAL_STATES:
            assert len(VALID_TRANSITIONS[status]) == 0

    def test_filled_is_terminal(self) -> None:
        """FILLED is a terminal state; nothing follows a complete fill."""
        assert OrderStatusEnum.FILLED in TERMINAL_STATES
        assert len(VALID_TRANSITIONS[OrderStatusEnum.FILLED]) == 0

    def test_every_non_terminal_can_reach_a_terminal(self) -> None:
        """Every non-terminal state should have a path to a terminal state."""
        def can_reach_terminal(status: OrderStatusEnum, visited: set) -> bool:
            if status in TERMINAL_STATES:
                return True
            if status in visited:
                return False
            visited.add(status)
            return any(
                can_reach_terminal(next_s, visited)
                for next_s in VALID_TRANSITIONS.get(status, set())
            )

        for status in OrderStatusEnum:
            if status not in TERMINAL_STATES:
                assert can_reach_terminal(status, set()), f"{status} cannot reach a terminal state"
