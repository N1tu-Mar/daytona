"""Synthetic slot booking. No real scheduling system in scope for the demo
— this produces a deterministic, human-readable slot label per urgency so
the call has a real payoff ("the call ends with a real appointment").
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

CLINIC_LABELS = {
    "emergency": "Emergency GI clinic",
    "urgent": "Urgent GI clinic",
    "soon": "Priority GI clinic",
    "routine": "GI screening clinic",
}

# Business-day offset from "now" for the earliest available slot at each
# urgency — this is scheduling policy, not a clinical judgment, so it lives
# here rather than in the rule engine.
OFFSET_DAYS = {"emergency": 0, "urgent": 1, "soon": 7, "routine": 21}


def book_slot(urgency: str, referral_id: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    offset = OFFSET_DAYS.get(urgency, 21)
    slot_date = now + timedelta(days=offset)
    # deterministic time-of-day so retries in a demo produce the same slot
    hour = 9 + (int(hashlib.sha256(referral_id.encode()).hexdigest(), 16) % 8)
    slot_date = slot_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    clinic = CLINIC_LABELS.get(urgency, "GI clinic")
    return f"{clinic} — {slot_date.strftime('%A, %B %-d')} at {slot_date.strftime('%-I:%M %p')}"
