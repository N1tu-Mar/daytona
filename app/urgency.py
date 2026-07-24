"""The single chokepoint for setting urgency. Escalate-only, monotonic.

Every code path that touches urgency — rule engine, human overrides,
corrections — must call apply_urgency(). No direct assignment anywhere else.
"""

from __future__ import annotations

import logging

from app.schemas import URGENCY_ORDER, Urgency

log = logging.getLogger("meridian.urgency")


def apply_urgency(current: Urgency, proposed: Urgency) -> Urgency:
    """Urgency is monotonic. Downgrades are silently ignored and logged."""
    if URGENCY_ORDER.index(proposed) > URGENCY_ORDER.index(current):
        return proposed
    if proposed != current:
        log.warning(
            "downgrade_attempt", extra={"current": current, "proposed": proposed}
        )
    return current


def highest_urgency(urgencies: list[Urgency], floor: Urgency = "routine") -> Urgency:
    """Fold a list of proposed urgencies down to the single highest one.

    Used by the rule engine: evaluate all rules, collect every match, take
    the highest urgency. Never first-match-wins.
    """
    result: Urgency = floor
    for u in urgencies:
        result = apply_urgency(result, u)
    return result
