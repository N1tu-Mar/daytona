"""Voice intake call orchestrator (build order step 5).

ElevenLabs owns the audio: turning QUESTION_SCRIPT prompts into speech and
turning the caller's speech into the text this module receives. Everything
downstream of that ASR boundary is deterministic and identical whether the
"transcript" came from a live ElevenLabs call or (as in this demo) a
hardcoded list of answers — CLAUDE.md explicitly allows hardcoded text for
the first working version of this call path.

Every line spoken back to the patient goes through
app.output_filter.send_patient_message. If that ever returns None, the call
fails closed to the escalation script rather than sending nothing and
leaving the patient on a silent line.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.db import ReferralRecord, TriageVerdictRecord, get_session
from app.output_filter import send_patient_message
from app.rule_engine import evaluate
from app.tracing import log_span, traced
from app.schemas import ReferralFeatures
from services.intake.booking import book_slot
from services.intake.parser import parse_choice, parse_number, parse_yes_no
from services.intake.questions import QUESTION_SCRIPT, ordered_top_level_questions

log = logging.getLogger("meridian.intake.call")

FALLBACK_LINE = "I'm not able to get a clear answer on that. A nurse will call you back to finish getting you scheduled."
LOW_CONFIDENCE_THRESHOLD = 0.5


@dataclass
class CallTranscriptTurn:
    speaker: str  # "agent" | "patient"
    text: str


@dataclass
class CallResult:
    referral_id: str
    transcript: list[CallTranscriptTurn]
    features: ReferralFeatures
    urgency: str
    disposition: str
    booked_slot: str | None
    final_message: str


def _by_field(field_name: str):
    return next(q for q in QUESTION_SCRIPT if q.field == field_name)


@traced
def run_call(referral_id: str, patient_answers: dict[str, str], patient_name: str = "") -> CallResult:
    """Runs the fixed-order script against a map of field -> patient answer
    text (this is the seam a live ElevenLabs webhook would fill in turn by
    turn; here it's supplied up front for a scripted/simulated call).

    Any field not present in `patient_answers`, or whose answer can't be
    parsed, is left None — the rule engine's own missing-data handling then
    decides whether that's safe to book through or must escalate. This
    function never guesses a value.
    """
    transcript: list[CallTranscriptTurn] = []
    values: dict[str, object] = {}
    source_refs: dict[str, str] = {}
    confidence: dict[str, float] = {}

    def ask(field_name: str) -> None:
        q = _by_field(field_name)
        say(q.prompt)
        answer_text = patient_answers.get(field_name)
        if answer_text is None:
            return
        transcript.append(CallTranscriptTurn(speaker="patient", text=answer_text))

        if q.kind == "yes_no":
            parsed = parse_yes_no(answer_text)
        elif q.kind == "number":
            parsed = parse_number(answer_text)
        elif q.kind == "choice":
            parsed = parse_choice(answer_text, q.choices)
        else:
            parsed = None

        if parsed is None:
            confidence[field_name] = 0.2
            log.warning("intake_answer_unparseable", extra={"field": field_name, "referral_id": referral_id})
            return

        values[field_name] = parsed
        source_refs[field_name] = f"voice_transcript:{field_name}"
        confidence[field_name] = 0.9

    def say(text: str) -> None:
        safe = send_patient_message(text)
        transcript.append(CallTranscriptTurn(speaker="agent", text=safe or FALLBACK_LINE))

    for q in ordered_top_level_questions():
        ask(q.field)
        if q.duration_follow_up and values.get(q.field) is True:
            ask(q.duration_follow_up)

    features = ReferralFeatures(**values, source_refs=source_refs, extraction_confidence=confidence)

    low_confidence = any(c < LOW_CONFIDENCE_THRESHOLD for c in confidence.values())

    if low_confidence:
        verdict = evaluate(features, referral_id=referral_id)
        # A low-confidence answer never gets waved through as routine —
        # force review regardless of what the rules alone would say.
        if verdict.disposition == "BOOK":
            verdict = verdict.model_copy(update={"disposition": "ESCALATE"})
    else:
        verdict = evaluate(features, referral_id=referral_id)

    def say_and_return(text: str) -> str:
        safe = send_patient_message(text)
        transcript.append(CallTranscriptTurn(speaker="agent", text=safe or FALLBACK_LINE))
        return safe or FALLBACK_LINE

    booked_slot = None
    if verdict.disposition == "BOOK":
        booked_slot = book_slot(verdict.urgency, referral_id)
        final_message = say_and_return(
            f"Based on what you've told me, I've booked you an appointment: {booked_slot}. "
            f"You'll get a confirmation text shortly. Is there anything else I can help with?"
        )
    else:
        final_message = say_and_return(
            "Thank you for answering those questions. I want to make sure a member of our "
            "clinical team looks at this personally before we schedule you, so a nurse will "
            "call you back shortly to finish getting you scheduled."
        )

    _persist(referral_id, features, verdict, booked_slot, patient_name)

    log_span(
        input={"referral_id": referral_id, "answers": patient_answers},
        output={"urgency": verdict.urgency, "disposition": verdict.disposition, "booked_slot": booked_slot},
        metadata={"rules_fired": verdict.rules_fired, "low_confidence": low_confidence},
    )
    return CallResult(
        referral_id=referral_id,
        transcript=transcript,
        features=features,
        urgency=verdict.urgency,
        disposition=verdict.disposition,
        booked_slot=booked_slot,
        final_message=final_message,
    )


def _persist(
    referral_id: str,
    features: ReferralFeatures,
    verdict,
    booked_slot: str | None,
    patient_name: str = "",
) -> None:
    session = get_session()
    try:
        session.add(
            ReferralRecord(
                id=referral_id,
                source="voice_call",
                raw_text="",
                patient_name=patient_name,
                features_json=features.model_dump_json(),
            )
        )
        session.add(
            TriageVerdictRecord(
                id=verdict.id,
                referral_id=verdict.referral_id,
                urgency=verdict.urgency,
                disposition=verdict.disposition,
                rules_fired=verdict.rules_fired,
                rule_version=verdict.rule_version,
                missing_features=verdict.missing_features,
                created_at=verdict.created_at,
                booked_slot=booked_slot,
            )
        )
        session.commit()
    finally:
        session.close()
