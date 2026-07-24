"""PA packet drafting. Fireworks for prose, but source_refs are never
LLM-generated — they're carried over verbatim from the extraction step and
the rule engine's own audit trail, both of which are already trusted.

Invariant #5: a sentence with no source_ref does not render. We enforce
this by construction — draft_packet() only ever asks the model to phrase a
sentence for a claim that already has a known source_ref, and if the model
call fails or is unavailable, a deterministic template stands in. There is
no code path where an LLM sentence reaches the packet without a source_ref
we assigned ourselves.
"""

from __future__ import annotations

import logging
import os

import httpx

from app.output_filter import check_output
from app.schemas import PASentence, ReferralFeatures, TriageVerdict

log = logging.getLogger("meridian.priorauth.draft")

FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY")
FIREWORKS_MODEL = os.environ.get("FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-70b-instruct")
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
TIMEOUT_SECONDS = 15.0

FEATURE_LABELS = {
    "age": "Patient age",
    "rectal_bleeding": "Rectal bleeding",
    "bleeding_duration_weeks": "Duration of rectal bleeding",
    "change_in_bowel_habit": "Change in bowel habit",
    "bowel_habit_duration_weeks": "Duration of bowel habit change",
    "unintentional_weight_loss": "Unintentional weight loss",
    "abdominal_pain": "Abdominal pain",
    "iron_deficiency_anemia": "Iron deficiency anemia",
    "fit_result": "FIT result",
    "family_history_crc": "Family history of colorectal cancer",
    "abdominal_or_rectal_mass": "Abdominal or rectal mass on exam",
    "prior_colonoscopy_date": "Prior colonoscopy",
}


class Claim:
    """A single fact from the chart, already tied to a trusted source_ref."""

    def __init__(self, field: str, value, source_ref: str):
        self.field = field
        self.value = value
        self.source_ref = source_ref


def _claims_from_features(features: ReferralFeatures) -> tuple[list[Claim], list[str]]:
    claims: list[Claim] = []
    dropped: list[str] = []
    data = features.model_dump(exclude={"source_refs", "extraction_confidence"})
    for field, value in data.items():
        if value is None:
            continue
        source_ref = features.source_refs.get(field)
        if not source_ref:
            # No trusted source for this field — never draft a sentence for it.
            log.warning("claim_dropped_no_source_ref", extra={"field": field})
            dropped.append(f"{field}: no_source_ref")
            continue
        claims.append(Claim(field=field, value=value, source_ref=source_ref))
    return claims, dropped


def _template_sentence(claim: Claim) -> str:
    label = FEATURE_LABELS.get(claim.field, claim.field)
    if isinstance(claim.value, bool):
        state = "present" if claim.value else "absent"
        return f"{label}: {state}."
    return f"{label}: {claim.value}."


def _fireworks_sentence(claim: Claim) -> str | None:
    if not FIREWORKS_API_KEY:
        return None
    label = FEATURE_LABELS.get(claim.field, claim.field)
    prompt = (
        f"Write one short, plain clinical-documentation sentence stating this fact "
        f"for a prior authorization letter. State only the fact given — no diagnosis, "
        f"no interpretation, no likelihood language. Fact: {label} = {claim.value!r}."
    )
    payload = {
        "model": FIREWORKS_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 80,
    }
    headers = {"Authorization": f"Bearer {FIREWORKS_API_KEY}", "Content-Type": "application/json"}
    try:
        resp = httpx.post(FIREWORKS_URL, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        log.exception("fireworks_sentence_generation_failed_falling_back_to_template")
        return None


def _rule_rationale_sentences(verdict: TriageVerdict) -> list[PASentence]:
    from app.rule_engine import load_rules

    cfg = load_rules()
    by_id = {r["id"]: r for r in cfg["rules"]}
    sentences = []
    for rule_id in verdict.rules_fired:
        rule = by_id.get(rule_id)
        if not rule:
            continue
        rationale = rule.get("rationale") or f"Criteria met for rule {rule_id}."
        sentences.append(
            PASentence(
                text=rationale.strip(),
                source_ref=f"rule_engine:{rule_id}:{verdict.rule_version}",
                field=None,
            )
        )
    return sentences


def draft_packet(features: ReferralFeatures, verdict: TriageVerdict) -> tuple[list[PASentence], list[str]]:
    """Returns (sentences, dropped_reasons). Never raises — a generation
    failure for one claim just drops that sentence and falls back to a
    template; a wholesale failure yields an empty packet plus dropped
    reasons rather than a broken packet.
    """
    claims, dropped = _claims_from_features(features)
    sentences: list[PASentence] = []

    for claim in claims:
        text = None
        try:
            text = _fireworks_sentence(claim)
        except Exception:
            log.exception("unexpected_fireworks_error")
        if not text:
            text = _template_sentence(claim)

        try:
            result = check_output(text)
        except Exception:
            dropped.append(f"{claim.field}: filter_error_fail_closed")
            continue
        if not result.allowed:
            dropped.append(f"{claim.field}: blocked_by_output_filter ({result.reasons})")
            continue

        sentences.append(PASentence(text=text, source_ref=claim.source_ref, field=claim.field))

    sentences.extend(_rule_rationale_sentences(verdict))

    return sentences, dropped
