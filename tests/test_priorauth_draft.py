"""Invariant #5: every clinical claim traces to a source; sentences without
one never render."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import ReferralFeatures, TriageVerdict
from services.priorauth.draft import draft_packet


def test_every_sentence_has_a_source_ref():
    features = ReferralFeatures(
        age=42,
        rectal_bleeding=True,
        change_in_bowel_habit=True,
        source_refs={"age": "referral line 1", "rectal_bleeding": "referral line 2", "change_in_bowel_habit": "referral line 3"},
        extraction_confidence={"age": 0.9, "rectal_bleeding": 0.9, "change_in_bowel_habit": 0.9},
    )
    verdict = TriageVerdict(
        referral_id="r1",
        urgency="urgent",
        disposition="BOOK",
        rules_fired=["YOUNG_BLEEDING_PLUS_FEATURE"],
        rule_version="2026.07.24-1",
        missing_features=[],
        created_at=datetime.now(timezone.utc),
    )
    sentences, dropped = draft_packet(features, verdict)
    assert sentences
    for s in sentences:
        assert s.source_ref
    assert not dropped


def test_field_without_source_ref_is_dropped_not_rendered():
    # weight_loss is populated but has no source_ref — must not appear.
    features = ReferralFeatures(
        age=42,
        unintentional_weight_loss=True,
        source_refs={"age": "referral line 1"},
        extraction_confidence={"age": 0.9},
    )
    verdict = TriageVerdict(
        referral_id="r2",
        urgency="routine",
        disposition="ESCALATE",
        rules_fired=[],
        rule_version="2026.07.24-1",
        missing_features=[],
        created_at=datetime.now(timezone.utc),
    )
    sentences, dropped = draft_packet(features, verdict)
    fields = [s.field for s in sentences]
    assert "unintentional_weight_loss" not in fields
    assert any("unintentional_weight_loss" in d for d in dropped)


def test_rule_rationale_sentences_carry_rule_engine_source_ref():
    features = ReferralFeatures(
        abdominal_or_rectal_mass=True,
        source_refs={"abdominal_or_rectal_mass": "referral line 1"},
        extraction_confidence={"abdominal_or_rectal_mass": 0.9},
    )
    verdict = TriageVerdict(
        referral_id="r3",
        urgency="urgent",
        disposition="BOOK",
        rules_fired=["MASS_ON_EXAM"],
        rule_version="2026.07.24-1",
        missing_features=[],
        created_at=datetime.now(timezone.utc),
    )
    sentences, _ = draft_packet(features, verdict)
    rule_sentences = [s for s in sentences if s.source_ref.startswith("rule_engine:")]
    assert rule_sentences
    assert rule_sentences[0].source_ref == "rule_engine:MASS_ON_EXAM:2026.07.24-1"
