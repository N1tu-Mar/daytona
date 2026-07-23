"""Mock payer IVR: a deliberately annoying phone tree state machine.

CLAUDE.md is explicit that we build this ourselves — never call a real
payer. It's a joke (menus, hold music) and also realistic (real payer IVRs
are exactly this annoying), which is why the ElevenLabs agent has to
actually navigate it rather than skip straight to an answer.

Payer status is looked up by PA packet id so the demo produces a
deterministic, reproducible result per packet rather than random noise —
useful for a live demo you might have to retry.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

# The tree. Each node: prompt text (what a caller would hear) and a mapping
# of DTMF digit -> next node id. "HOLD" nodes require the caller to just
# wait (agent sends nothing, tree auto-advances after the hold).
IVR_TREE: dict[str, dict] = {
    "START": {
        "prompt": (
            "Thank you for calling Payer Health Services. Para español, oprima nueve. "
            "This call may be monitored for quality assurance. "
            "Please listen carefully as our menu options have changed."
        ),
        "options": {"*": "MAIN_MENU"},
    },
    "MAIN_MENU": {
        "prompt": (
            "For eligibility and benefits, press 1. "
            "For claims status, press 2. "
            "For prior authorization status, press 3. "
            "To repeat this menu, press 9."
        ),
        "options": {"1": "WRONG_TRACK_ELIGIBILITY", "2": "WRONG_TRACK_CLAIMS", "3": "PA_SUBMENU", "9": "MAIN_MENU"},
    },
    "WRONG_TRACK_ELIGIBILITY": {
        "prompt": "You've reached eligibility and benefits. For prior authorization, press 3 to return to the main menu, then press 3 again.",
        "options": {"*": "MAIN_MENU"},
    },
    "WRONG_TRACK_CLAIMS": {
        "prompt": "You've reached claims status. For prior authorization, press 3 to return to the main menu, then press 3 again.",
        "options": {"*": "MAIN_MENU"},
    },
    "PA_SUBMENU": {
        "prompt": (
            "You've reached prior authorization status. "
            "Please enter the ten digit member ID followed by the pound sign."
        ),
        "options": {"member_id": "HOLD_1"},
    },
    "HOLD_1": {
        "prompt": "Thank you. Please hold while we look up this authorization. [HOLD MUSIC]",
        "options": {"*": "HOLD_2"},
        "hold": True,
    },
    "HOLD_2": {
        "prompt": "Your call is important to us. Estimated wait time is between two and forty-five minutes. [HOLD MUSIC CONTINUES]",
        "options": {"*": "STATUS_RESULT"},
        "hold": True,
    },
    "STATUS_RESULT": {
        "prompt": None,  # filled in dynamically with the looked-up status
        "options": {},
        "terminal": True,
    },
}

STATUS_OUTCOMES = ["approved", "pending", "denied", "additional_info_needed"]

STATUS_SCRIPTS = {
    "approved": "This authorization has been approved. Reference number {ref}. Goodbye.",
    "pending": "This authorization is still under clinical review. Please call back in three to five business days. Reference number {ref}. Goodbye.",
    "denied": "This authorization has been denied. A letter with appeal instructions has been mailed. Reference number {ref}. Goodbye.",
    "additional_info_needed": "This authorization requires additional clinical documentation. Please have your provider fax records to extension 4-1-2. Reference number {ref}. Goodbye.",
}


def _deterministic_status(packet_id: str) -> str:
    """Deterministic per packet_id so a demo call is reproducible on retry,
    while still varying across packets so the dashboard isn't monotonous."""
    digest = hashlib.sha256(packet_id.encode()).hexdigest()
    idx = int(digest[:8], 16) % len(STATUS_OUTCOMES)
    return STATUS_OUTCOMES[idx]


def _reference_number(packet_id: str) -> str:
    return hashlib.sha256(packet_id.encode()).hexdigest()[:8].upper()


@dataclass
class IVRSession:
    packet_id: str
    state: str = "START"
    transcript: list[str] = field(default_factory=list)

    def prompt(self) -> str:
        node = IVR_TREE[self.state]
        if self.state == "STATUS_RESULT":
            status = _deterministic_status(self.packet_id)
            text = STATUS_SCRIPTS[status].format(ref=_reference_number(self.packet_id))
            self.transcript.append(f"IVR: {text}")
            return text
        text = node["prompt"]
        self.transcript.append(f"IVR: {text}")
        return text

    def is_terminal(self) -> bool:
        return IVR_TREE[self.state].get("terminal", False)

    def send(self, input_value: str) -> str:
        """Advance the tree given caller input (a DTMF digit, "member_id" for
        the ID-entry step, or "*" for hold/any-input nodes). Returns the next
        prompt."""
        node = IVR_TREE[self.state]
        self.transcript.append(f"CALLER: {input_value}")
        options = node["options"]
        # "member_id" nodes accept any digit string as the entered ID, not
        # a literal match against the key "member_id".
        if "member_id" in options and input_value not in options:
            next_state = options["member_id"]
        else:
            next_state = options.get(input_value) or options.get("*")
        if not next_state:
            raise ValueError(f"invalid input {input_value!r} for state {self.state}")
        self.state = next_state
        return self.prompt()

    def status(self) -> str | None:
        if self.state == "STATUS_RESULT":
            return _deterministic_status(self.packet_id)
        return None
