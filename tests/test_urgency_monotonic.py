"""Property test for the escalate-only invariant (CLAUDE.md invariant #1).

Throws random sequences of proposed urgencies at apply_urgency() and asserts
the result never decreases, no matter the order.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.schemas import URGENCY_ORDER, Urgency
from app.urgency import apply_urgency, highest_urgency

urgency_strategy = st.sampled_from(URGENCY_ORDER)


@given(st.lists(urgency_strategy, min_size=1, max_size=50))
def test_urgency_never_decreases(sequence: list[Urgency]) -> None:
    current: Urgency = "routine"
    prev_rank = URGENCY_ORDER.index(current)
    for proposed in sequence:
        current = apply_urgency(current, proposed)
        rank = URGENCY_ORDER.index(current)
        assert rank >= prev_rank, f"urgency decreased: {prev_rank} -> {rank}"
        prev_rank = rank


@given(st.lists(urgency_strategy, min_size=0, max_size=50))
def test_result_is_max_of_all_proposals(sequence: list[Urgency]) -> None:
    current: Urgency = "routine"
    for proposed in sequence:
        current = apply_urgency(current, proposed)
    expected_rank = max(
        [URGENCY_ORDER.index("routine")] + [URGENCY_ORDER.index(u) for u in sequence]
    )
    assert URGENCY_ORDER.index(current) == expected_rank


def test_apply_urgency_basic_escalation() -> None:
    assert apply_urgency("routine", "urgent") == "urgent"
    assert apply_urgency("urgent", "routine") == "urgent"
    assert apply_urgency("soon", "soon") == "soon"
    assert apply_urgency("emergency", "routine") == "emergency"


def test_highest_urgency_never_first_match_wins() -> None:
    # Order in the list must not matter; the highest wins regardless of position.
    assert highest_urgency(["routine", "urgent", "soon"]) == "urgent"
    assert highest_urgency(["urgent", "routine", "soon"]) == "urgent"
    assert highest_urgency([]) == "routine"
    assert highest_urgency(["soon"], floor="routine") == "soon"
