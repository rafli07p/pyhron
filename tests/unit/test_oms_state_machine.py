"""Unit tests for the OMS order state machine.

Tests validate the transition table logic and guard conditions.
DB/Kafka interactions are mocked since they are side effects.
"""

from __future__ import annotations

import pytest

# Transitive import to shared.kafka_producer_consumer uses Python 3.12+
# generic class syntax (PEP 695).  Skip on older runtimes.
try:
    from data_platform.models.trading import OrderStatusEnum
    from services.order_management_system.order_state_machine import TERMINAL_STATES, VALID_TRANSITIONS
except SyntaxError:
    pytest.skip(
        "Requires Python 3.12+ (PEP 695 generic syntax in kafka_producer_consumer)",
        allow_module_level=True,
    )

# ── Transition Table Tests ───────────────────────────────────────────────────


class TestTransitionTable:
    """Validate the transition graph is well-formed."""

    def test_all_statuses_have_entries(self):
        """Every OrderStatusEnum value must appear in VALID_TRANSITIONS."""
        for status in OrderStatusEnum:
            assert status in VALID_TRANSITIONS, f"{status.value} missing from VALID_TRANSITIONS"

    def test_terminal_states_have_no_transitions(self):
        """Terminal states must map to empty sets."""
        for status in TERMINAL_STATES:
            assert VALID_TRANSITIONS[status] == set(), f"Terminal state {status.value} has outgoing transitions"

    def test_expected_terminal_states(self):
        expected = {
            OrderStatusEnum.RISK_REJECTED,
            OrderStatusEnum.REJECTED,
            OrderStatusEnum.FILLED,
            OrderStatusEnum.CANCELLED,
            OrderStatusEnum.EXPIRED,
        }
        assert expected == TERMINAL_STATES

    def test_no_self_loops_except_partial_fill(self):
        """Only PARTIAL_FILL should allow self-transition."""
        for status, allowed in VALID_TRANSITIONS.items():
            if status == OrderStatusEnum.PARTIAL_FILL:
                assert OrderStatusEnum.PARTIAL_FILL in allowed
            else:
                assert status not in allowed, f"{status.value} has unexpected self-loop"


# ── Specific Transition Validation ───────────────────────────────────────────


class TestSpecificTransitions:
    """Validate key business rules in the transition graph."""

    def test_pending_risk_can_be_approved_or_rejected(self):
        allowed = VALID_TRANSITIONS[OrderStatusEnum.PENDING_RISK]
        assert OrderStatusEnum.RISK_APPROVED in allowed
        assert OrderStatusEnum.RISK_REJECTED in allowed
        assert len(allowed) == 2

    def test_risk_approved_to_submitted_or_cancelled(self):
        allowed = VALID_TRANSITIONS[OrderStatusEnum.RISK_APPROVED]
        assert OrderStatusEnum.SUBMITTED in allowed
        assert OrderStatusEnum.CANCELLED in allowed

    def test_submitted_to_acknowledged_or_rejected(self):
        allowed = VALID_TRANSITIONS[OrderStatusEnum.SUBMITTED]
        assert OrderStatusEnum.ACKNOWLEDGED in allowed
        assert OrderStatusEnum.REJECTED in allowed

    def test_acknowledged_can_fill_cancel_or_expire(self):
        allowed = VALID_TRANSITIONS[OrderStatusEnum.ACKNOWLEDGED]
        assert OrderStatusEnum.PARTIAL_FILL in allowed
        assert OrderStatusEnum.FILLED in allowed
        assert OrderStatusEnum.CANCELLED in allowed
        assert OrderStatusEnum.EXPIRED in allowed

    def test_partial_fill_can_complete_or_cancel(self):
        allowed = VALID_TRANSITIONS[OrderStatusEnum.PARTIAL_FILL]
        assert OrderStatusEnum.FILLED in allowed
        assert OrderStatusEnum.CANCELLED in allowed
        assert OrderStatusEnum.PARTIAL_FILL in allowed

    def test_cannot_skip_risk(self):
        """Orders cannot go directly from PENDING_RISK to SUBMITTED."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.PENDING_RISK]
        assert OrderStatusEnum.SUBMITTED not in allowed

    def test_filled_cannot_be_cancelled(self):
        """Filled orders are terminal — no further transitions."""
        allowed = VALID_TRANSITIONS[OrderStatusEnum.FILLED]
        assert len(allowed) == 0

    def test_rejected_is_terminal(self):
        assert VALID_TRANSITIONS[OrderStatusEnum.REJECTED] == set()

    def test_risk_rejected_is_terminal(self):
        assert VALID_TRANSITIONS[OrderStatusEnum.RISK_REJECTED] == set()


# ── Invalid Transition Detection ─────────────────────────────────────────────


class TestInvalidTransitions:
    """Ensure invalid transitions are properly blocked."""

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            (OrderStatusEnum.FILLED, OrderStatusEnum.CANCELLED),
            (OrderStatusEnum.CANCELLED, OrderStatusEnum.FILLED),
            (OrderStatusEnum.RISK_REJECTED, OrderStatusEnum.SUBMITTED),
            (OrderStatusEnum.EXPIRED, OrderStatusEnum.ACKNOWLEDGED),
            (OrderStatusEnum.PENDING_RISK, OrderStatusEnum.FILLED),
            (OrderStatusEnum.SUBMITTED, OrderStatusEnum.FILLED),
        ],
    )
    def test_invalid_transition_not_allowed(self, from_status, to_status):
        allowed = VALID_TRANSITIONS.get(from_status, set())
        assert (
            to_status not in allowed
        ), f"Transition {from_status.value} -> {to_status.value} should be invalid but is allowed"
