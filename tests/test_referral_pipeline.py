"""Pipeline-level fail-safe tests: no network, no Daytona/Fireworks keys needed.

Confirms the pipeline never raises and always leaves a human-visible
ESCALATE verdict on the worklist when a downstream step can't run.
"""

from __future__ import annotations

import os

from app.db import ReferralRecord, TriageVerdictRecord, get_session, init_db

os.environ.pop("FIREWORKS_API_KEY", None)
os.environ.pop("DAYTONA_API_KEY", None)

from services.referral.pipeline import process_referral  # noqa: E402


def setup_module(module):
    init_db()


def test_missing_extraction_key_escalates_instead_of_crashing():
    record, verdict = process_referral(
        content=b"Patient: 42 y/o, rectal bleeding x 3 weeks.",
        filename="referral.txt",
        patient_name="Test Patient",
        source="fax_scan",
    )
    assert verdict.disposition == "ESCALATE"

    session = get_session()
    try:
        assert session.get(ReferralRecord, record.id) is not None
        assert session.get(TriageVerdictRecord, verdict.id) is not None
    finally:
        session.close()


def test_empty_document_escalates():
    record, verdict = process_referral(content=b"", filename="blank.txt")
    assert verdict.disposition == "ESCALATE"
