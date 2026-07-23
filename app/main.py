"""FastAPI app. Every route is a thin layer over rule_engine/services —
no business logic lives here beyond request/response shaping and the human
sign-off bookkeeping required by invariant #4.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.approval import sign
from app.db import (
    PAPacketRecord,
    ReferralRecord,
    TriageVerdictRecord,
    get_session,
    init_db,
)
from app.schemas import ReferralFeatures

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("scoped.api")

app = FastAPI(title="Scoped API", description="DEMO — synthetic data. Not for clinical use.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://scoped.vercel.app",
        "https://scoped-git-*.vercel.app",
    ],
    allow_origin_regex=r"https://scoped-git-.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": True}


@app.get("/evals/summary")
def evals_summary() -> dict:
    """Backs the dashboard's escalation-recall / false-reassurance tiles.

    Reads the file evals/run.py writes (data/evals_summary.json) rather than
    recomputing on every request — evals are run explicitly, not on the hot
    path of a page load.
    """
    import json

    path = os.path.join(os.path.dirname(__file__), "..", "data", "evals_summary.json")
    if not os.path.exists(path):
        raise HTTPException(404, "no evals run yet — run `python -m evals.run`")
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Nurse worklist: referrals + verdicts
# ---------------------------------------------------------------------------


def _latest_verdict(session, referral_id: str) -> TriageVerdictRecord | None:
    rows = (
        session.query(TriageVerdictRecord)
        .filter(TriageVerdictRecord.referral_id == referral_id)
        .order_by(TriageVerdictRecord.created_at.desc())
        .all()
    )
    return rows[0] if rows else None


def _worklist_item(session, ref: ReferralRecord) -> dict:
    verdict = _latest_verdict(session, ref.id)
    features = ReferralFeatures.model_validate_json(ref.features_json)
    return {
        "referral_id": ref.id,
        "patient_name": ref.patient_name,
        "source": ref.source,
        "raw_text": ref.raw_text,
        "created_at": ref.created_at.isoformat(),
        "features": features.model_dump(mode="json"),
        "verdict": None
        if verdict is None
        else {
            "id": verdict.id,
            "urgency": verdict.urgency,
            "disposition": verdict.disposition,
            "rules_fired": verdict.rules_fired,
            "rule_version": verdict.rule_version,
            "missing_features": verdict.missing_features,
            "created_at": verdict.created_at.isoformat(),
            "approved_by": verdict.approved_by,
            "approved_at": verdict.approved_at.isoformat() if verdict.approved_at else None,
            "approval_hash": verdict.approval_hash,
            "booked_slot": verdict.booked_slot,
        },
    }


@app.get("/referrals")
def list_referrals() -> list[dict]:
    session = get_session()
    try:
        refs = session.query(ReferralRecord).order_by(ReferralRecord.created_at.desc()).all()
        return [_worklist_item(session, r) for r in refs]
    finally:
        session.close()


@app.get("/referrals/{referral_id}")
def get_referral(referral_id: str) -> dict:
    session = get_session()
    try:
        ref = session.get(ReferralRecord, referral_id)
        if not ref:
            raise HTTPException(404, "referral not found")
        return _worklist_item(session, ref)
    finally:
        session.close()


class ApproveRequest(BaseModel):
    actor: str
    slot: str | None = None  # appointment slot label, e.g. "2026-07-24T09:00 urgent clinic"


@app.post("/referrals/{referral_id}/verdicts/{verdict_id}/approve")
def approve_verdict(referral_id: str, verdict_id: str, body: ApproveRequest) -> dict:
    """Nurse approves a triage verdict. This is what confirms the booking
    (invariant #4: nurse approves every triage verdict before a booking is
    confirmed)."""
    session = get_session()
    try:
        verdict = session.get(TriageVerdictRecord, verdict_id)
        if not verdict or verdict.referral_id != referral_id:
            raise HTTPException(404, "verdict not found")
        if verdict.approved_by:
            raise HTTPException(409, "verdict already approved; corrections must create a new verdict")

        payload = {
            "verdict_id": verdict.id,
            "referral_id": verdict.referral_id,
            "urgency": verdict.urgency,
            "disposition": verdict.disposition,
            "rules_fired": verdict.rules_fired,
            "rule_version": verdict.rule_version,
            "slot": body.slot,
        }
        actor, approved_at, approval_hash = sign(body.actor, payload)

        verdict.approved_by = actor
        verdict.approved_at = approved_at
        verdict.approval_hash = approval_hash
        verdict.booked_slot = body.slot
        session.commit()
        log.info(
            "verdict_approved",
            extra={"referral_id": referral_id, "verdict_id": verdict_id, "actor": actor},
        )
        return {"status": "approved", "approval_hash": approval_hash, "approved_at": approved_at.isoformat()}
    finally:
        session.close()


class EscalateRequest(BaseModel):
    actor: str
    reason: str


@app.post("/referrals/{referral_id}/verdicts/{verdict_id}/escalate")
def escalate_verdict(referral_id: str, verdict_id: str, body: EscalateRequest) -> dict:
    """Nurse sends a verdict back for human review / more info. Does not
    mutate the existing verdict — logs the escalation as an event."""
    session = get_session()
    try:
        verdict = session.get(TriageVerdictRecord, verdict_id)
        if not verdict or verdict.referral_id != referral_id:
            raise HTTPException(404, "verdict not found")
        log.warning(
            "verdict_escalated_by_nurse",
            extra={
                "referral_id": referral_id,
                "verdict_id": verdict_id,
                "actor": body.actor,
                "reason": body.reason,
            },
        )
        return {"status": "escalated"}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# PA packets
# ---------------------------------------------------------------------------


@app.get("/pa-packets/{packet_id}")
def get_pa_packet(packet_id: str) -> dict:
    session = get_session()
    try:
        pkt = session.get(PAPacketRecord, packet_id)
        if not pkt:
            raise HTTPException(404, "packet not found")
        import json as _json

        return {
            "id": pkt.id,
            "referral_id": pkt.referral_id,
            "verdict_id": pkt.verdict_id,
            "sentences": _json.loads(pkt.sentences_json),
            "status": pkt.status,
            "created_at": pkt.created_at.isoformat(),
            "approved_by": pkt.approved_by,
            "approved_at": pkt.approved_at.isoformat() if pkt.approved_at else None,
            "approval_hash": pkt.approval_hash,
            "payer_status": pkt.payer_status,
            "days_saved": pkt.days_saved,
        }
    finally:
        session.close()


@app.get("/pa-packets")
def list_pa_packets() -> list[dict]:
    session = get_session()
    try:
        pkts = session.query(PAPacketRecord).order_by(PAPacketRecord.created_at.desc()).all()
        return [get_pa_packet(p.id) for p in pkts]
    finally:
        session.close()


class ApprovePacketRequest(BaseModel):
    actor: str


@app.post("/pa-packets/{packet_id}/approve")
def approve_pa_packet(packet_id: str, body: ApprovePacketRequest) -> dict:
    """Physician one-click approval. Nothing is marked submitted before this."""
    session = get_session()
    try:
        pkt = session.get(PAPacketRecord, packet_id)
        if not pkt:
            raise HTTPException(404, "packet not found")
        if pkt.approved_by:
            raise HTTPException(409, "packet already approved")

        import json as _json

        payload = {"packet_id": pkt.id, "sentences": _json.loads(pkt.sentences_json)}
        actor, approved_at, approval_hash = sign(body.actor, payload)
        pkt.approved_by = actor
        pkt.approved_at = approved_at
        pkt.approval_hash = approval_hash
        pkt.status = "approved"
        session.commit()
        return {"status": "approved", "approval_hash": approval_hash}
    finally:
        session.close()


@app.post("/pa-packets/{packet_id}/submit")
def submit_pa_packet(packet_id: str) -> dict:
    session = get_session()
    try:
        pkt = session.get(PAPacketRecord, packet_id)
        if not pkt:
            raise HTTPException(404, "packet not found")
        if not pkt.approved_by:
            raise HTTPException(409, "packet must be physician-approved before submission")
        pkt.status = "submitted"
        session.commit()
        return {"status": "submitted"}
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
