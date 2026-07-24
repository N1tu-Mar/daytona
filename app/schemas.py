"""Core Pydantic schemas for Meridian.

Every LLM call returns one of these models — no free-form string parsing.
`TriageVerdict` is append-only: corrections create a new verdict linked to
the prior one via `corrects_verdict_id`. Never mutate a signed verdict.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

Urgency = Literal["routine", "soon", "urgent", "emergency"]
Disposition = Literal["BOOK", "ESCALATE", "NEEDS_INFO"]

# Order matters: index position is the urgency's rank. Everything that sets
# urgency must go through apply_urgency() in app/urgency.py — no direct
# assignment anywhere else in the codebase.
URGENCY_ORDER: list[Urgency] = ["routine", "soon", "urgent", "emergency"]


class ReferralFeatures(BaseModel):
    """Structured red-flag features extracted from a referral or call transcript.

    LLM extraction populates this. It never decides urgency — that's the
    rule engine's job. Every populated field must carry a source_ref and an
    extraction_confidence entry so a nurse can trace each fact back to text.
    """

    age: int | None = None
    rectal_bleeding: bool | None = None
    bleeding_duration_weeks: int | None = None
    change_in_bowel_habit: bool | None = None
    bowel_habit_duration_weeks: int | None = None
    unintentional_weight_loss: bool | None = None
    abdominal_pain: bool | None = None
    iron_deficiency_anemia: bool | None = None
    fit_result: Literal["positive", "negative", "not_done"] | None = None
    family_history_crc: Literal["none", "first_degree", "multiple"] | None = None
    abdominal_or_rectal_mass: bool | None = None
    prior_colonoscopy_date: date | None = None

    # every field carries where it came from (chart field name / referral
    # line / transcript turn) and how confident the extractor was
    source_refs: dict[str, str] = Field(default_factory=dict)
    extraction_confidence: dict[str, float] = Field(default_factory=dict)


class TriageVerdict(BaseModel):
    """Result of running ReferralFeatures through the deterministic rule engine.

    Append-only. A correction creates a new TriageVerdict row with
    `corrects_verdict_id` set to the prior verdict's id — never mutate a
    signed verdict in place.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    referral_id: str
    urgency: Urgency
    disposition: Disposition
    rules_fired: list[str] = Field(default_factory=list)
    rule_version: str
    missing_features: list[str] = Field(default_factory=list)
    created_at: datetime
    corrects_verdict_id: str | None = None

    # populated only after a human signs
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_hash: str | None = None


class RuleMatch(BaseModel):
    """One rule that fired during evaluation, for the audit trail."""

    id: str
    urgency: Urgency
    rationale: str | None = None


class PASentence(BaseModel):
    """One sentence in a generated PA packet.

    Invariant #5: every clinical claim traces to a source. A sentence with
    no source_ref must never render — see services/priorauth/draft.py,
    which drops any candidate sentence lacking one before it reaches here.
    """

    text: str
    source_ref: str
    field: str | None = None
