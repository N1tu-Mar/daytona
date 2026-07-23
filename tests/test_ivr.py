"""Mock IVR state machine + agent navigation tests."""

from __future__ import annotations

import os

os.environ.pop("ELEVENLABS_API_KEY", None)

from services.ivr.agent import DAYS_SAVED_BY_STATUS, call_payer_ivr  # noqa: E402
from services.ivr.mock_ivr import IVRSession, IVR_TREE  # noqa: E402


def test_ivr_session_navigates_full_tree():
    session = IVRSession(packet_id="pkt-1")
    session.prompt()
    session.send("*")  # -> MAIN_MENU
    assert session.state == "MAIN_MENU"
    session.send("3")  # -> PA_SUBMENU
    assert session.state == "PA_SUBMENU"
    session.send("1234567890")  # -> HOLD_1
    assert session.state == "HOLD_1"
    session.send("*")  # -> HOLD_2
    assert session.state == "HOLD_2"
    session.send("*")  # -> STATUS_RESULT
    assert session.state == "STATUS_RESULT"
    assert session.is_terminal()
    assert session.status() in ("approved", "pending", "denied", "additional_info_needed")


def test_ivr_session_wrong_menu_choice_can_recover():
    session = IVRSession(packet_id="pkt-2")
    session.prompt()
    session.send("*")
    session.send("1")  # eligibility, wrong track
    assert session.state == "WRONG_TRACK_ELIGIBILITY"
    session.send("*")  # back to MAIN_MENU
    assert session.state == "MAIN_MENU"


def test_ivr_session_invalid_input_raises():
    session = IVRSession(packet_id="pkt-3")
    session.prompt()
    session.send("*")  # -> MAIN_MENU, which has no wildcard fallback
    import pytest

    with pytest.raises(ValueError):
        session.send("7")


def test_status_is_deterministic_per_packet_id():
    r1 = call_payer_ivr("pkt-deterministic")
    r2 = call_payer_ivr("pkt-deterministic")
    assert r1.status == r2.status
    assert r1.days_saved == r2.days_saved


def test_status_varies_across_packet_ids():
    statuses = {call_payer_ivr(f"pkt-{i}").status for i in range(20)}
    assert len(statuses) > 1


def test_call_produces_a_transcript():
    result = call_payer_ivr("pkt-transcript")
    assert result.transcript
    assert any("IVR:" in line for line in result.transcript)
    assert any("CALLER:" in line for line in result.transcript)


def test_days_saved_matches_status_mapping():
    result = call_payer_ivr("pkt-days-saved")
    assert result.days_saved == DAYS_SAVED_BY_STATUS[result.status]
