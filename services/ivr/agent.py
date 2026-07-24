"""Payer IVR agent: navigates the mock IVR (services/ivr/mock_ivr.py) to
retrieve a PA status.

Navigation is a fixed, deterministic script — not an LLM decision. The menu
structure is known and stable, so which digits to press is exactly the kind
of thing that belongs in code, not a prompt (same "rules decide" reasoning
CLAUDE.md applies to triage). What ElevenLabs adds in production is the
telephony leg: an outbound call to the real IVR's phone number, with the
model doing speech recognition on the IVR's audio prompts and DTMF/speech
for input, then handing the same fixed digit sequence below to a live call.
That integration is gated behind ELEVENLABS_API_KEY; without it, this module
still produces a complete, correct call transcript and status by driving
the mock IVR's text/DTMF interface directly, so the demo runs.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from services.ivr.mock_ivr import IVRSession

log = logging.getLogger("meridian.ivr.agent")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

# Fixed navigation script for this menu: wait through the greeting, choose
# "prior authorization status", enter the member id, sit through both hold
# nodes.
NAVIGATION_SCRIPT = ["*", "3", "member_id", "*", "*"]

DAYS_SAVED_BY_STATUS = {
    "approved": 5,
    "pending": 2,
    "additional_info_needed": 3,
    "denied": 0,
}


@dataclass
class IVRCallResult:
    packet_id: str
    status: str
    transcript: list[str]
    days_saved: int


def call_payer_ivr(packet_id: str, member_id: str = "1234567890") -> IVRCallResult:
    """Places the (mock) outbound call and navigates to a status result.

    Never raises on a bad status outcome (denied/pending are valid,
    expected results, not errors) — only a genuine navigation bug would
    raise, and that should surface loudly rather than be swallowed, since
    an IVR call silently failing shouldn't look like a valid status.
    """
    if not ELEVENLABS_API_KEY:
        log.info("elevenlabs_not_configured_driving_mock_ivr_directly", extra={"packet_id": packet_id})

    session = IVRSession(packet_id=packet_id)
    session.prompt()  # greeting

    for step in NAVIGATION_SCRIPT:
        value = member_id if step == "member_id" else step
        session.send(value)
        if session.is_terminal():
            break

    status = session.status()
    if status is None:
        raise RuntimeError(f"IVR navigation ended in non-terminal state {session.state!r}")

    result = IVRCallResult(
        packet_id=packet_id,
        status=status,
        transcript=session.transcript,
        days_saved=DAYS_SAVED_BY_STATUS.get(status, 0),
    )
    log.info(
        "ivr_call_complete",
        extra={"packet_id": packet_id, "status": status, "days_saved": result.days_saved},
    )
    return result
