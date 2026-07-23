"""Unit tests for the deterministic rule engine (app/rule_engine.py).

Written before considering the engine done, per CLAUDE.md working style:
"Write the test for the rule engine before the rule engine."
"""

from __future__ import annotations

from datetime import date

import pytest

from app.rule_engine import evaluate, load_rules
from app.schemas import ReferralFeatures


@pytest.fixture(scope="module")
def cfg():
    return load_rules()


def feat(**kwargs) -> ReferralFeatures:
    return ReferralFeatures(**kwargs)


def test_demo_case_young_bleeding_plus_feature_is_urgent(cfg):
    """The 42-year-old bleeding + bowel-habit-change case. The whole point."""
    f = feat(
        age=42,
        rectal_bleeding=True,
        bleeding_duration_weeks=3,
        change_in_bowel_habit=True,
        bowel_habit_duration_weeks=3,
    )
    v = evaluate(f, referral_id="demo-42yo", config=cfg)
    assert v.urgency == "urgent"
    assert v.disposition == "BOOK"
    assert "YOUNG_BLEEDING_PLUS_FEATURE" in v.rules_fired


def test_isolated_bleeding_under_50_is_soon_not_urgent(cfg):
    f = feat(age=35, rectal_bleeding=True)
    v = evaluate(f, referral_id="r1", config=cfg)
    assert v.urgency == "soon"
    assert "ISOLATED_BLEEDING_UNDER_50" in v.rules_fired
    assert "YOUNG_BLEEDING_PLUS_FEATURE" not in v.rules_fired


def test_mass_on_exam_is_urgent(cfg):
    f = feat(abdominal_or_rectal_mass=True)
    v = evaluate(f, referral_id="r2", config=cfg)
    assert v.urgency == "urgent"
    assert v.disposition == "BOOK"
    assert "MASS_ON_EXAM" in v.rules_fired


def test_positive_fit_is_urgent(cfg):
    f = feat(fit_result="positive")
    v = evaluate(f, referral_id="r3", config=cfg)
    assert v.urgency == "urgent"
    assert "POSITIVE_FIT" in v.rules_fired


def test_bleeding_over_50_is_urgent(cfg):
    f = feat(age=55, rectal_bleeding=True)
    v = evaluate(f, referral_id="r4", config=cfg)
    assert v.urgency == "urgent"
    assert "BLEEDING_OVER_50" in v.rules_fired


def test_ida_over_60_is_urgent(cfg):
    f = feat(age=65, iron_deficiency_anemia=True)
    v = evaluate(f, referral_id="r5", config=cfg)
    assert v.urgency == "urgent"
    assert "IDA_OVER_60" in v.rules_fired


def test_bowel_habit_over_60_is_urgent(cfg):
    f = feat(age=61, change_in_bowel_habit=True)
    v = evaluate(f, referral_id="r6", config=cfg)
    assert v.urgency == "urgent"
    assert "BOWEL_HABIT_OVER_60" in v.rules_fired


def test_weight_loss_plus_pain_over_40_is_urgent(cfg):
    f = feat(age=45, unintentional_weight_loss=True, abdominal_pain=True)
    v = evaluate(f, referral_id="r7", config=cfg)
    assert v.urgency == "urgent"
    assert "WEIGHT_LOSS_PLUS_PAIN_OVER_40" in v.rules_fired


def test_persistent_bowel_change_is_soon(cfg):
    f = feat(change_in_bowel_habit=True, bowel_habit_duration_weeks=8)
    v = evaluate(f, referral_id="r8", config=cfg)
    assert v.urgency == "soon"
    assert "PERSISTENT_BOWEL_CHANGE" in v.rules_fired


def test_persistent_bowel_change_under_6_weeks_does_not_fire(cfg):
    f = feat(change_in_bowel_habit=True, bowel_habit_duration_weeks=2)
    v = evaluate(f, referral_id="r9", config=cfg)
    assert "PERSISTENT_BOWEL_CHANGE" not in v.rules_fired


def test_screening_age_no_prior_is_routine(cfg):
    # A genuinely clean case: every red-flag feature is explicitly known and
    # negative, not just omitted. Omitted (None) fields are "unknown", which
    # correctly escalates to NEEDS_INFO instead — see the test below.
    f = feat(
        age=50,
        prior_colonoscopy_date=None,
        rectal_bleeding=False,
        change_in_bowel_habit=False,
        unintentional_weight_loss=False,
        abdominal_pain=False,
        iron_deficiency_anemia=False,
        fit_result="negative",
        abdominal_or_rectal_mass=False,
    )
    v = evaluate(f, referral_id="r10", config=cfg)
    assert v.urgency == "routine"
    assert v.disposition == "BOOK"
    assert "SCREENING_AGE_NO_PRIOR" in v.rules_fired


def test_screening_age_with_incomplete_data_needs_info(cfg):
    # Same age/prior-exam profile, but other red-flag fields are unset
    # (unknown, not negative). The engine must not guess routine.
    f = feat(age=50, prior_colonoscopy_date=None)
    v = evaluate(f, referral_id="r10b", config=cfg)
    assert v.disposition == "NEEDS_INFO"
    assert v.missing_features


def test_screening_age_with_prior_colonoscopy_no_rule_fires_and_escalates(cfg):
    f = feat(age=50, prior_colonoscopy_date=date(2024, 1, 1))
    v = evaluate(f, referral_id="r11", config=cfg)
    assert v.rules_fired == []
    # No explicit rule matched -> never silently clear.
    assert v.disposition == "ESCALATE"


def test_completely_empty_features_escalates(cfg):
    f = feat()
    v = evaluate(f, referral_id="r12", config=cfg)
    assert v.disposition == "ESCALATE"
    assert v.rules_fired == []


def test_missing_data_that_could_flip_verdict_is_needs_info(cfg):
    # Under-50, bleeding status unknown -> ISOLATED_BLEEDING_UNDER_50 can't
    # evaluate. No other rule fires. Must not guess routine.
    f = feat(age=30)
    v = evaluate(f, referral_id="r13", config=cfg)
    assert v.disposition in ("NEEDS_INFO", "ESCALATE")
    assert v.urgency == "routine"
    assert "rectal_bleeding" in v.missing_features


def test_urgent_rule_fires_even_with_unrelated_missing_data(cfg):
    # mass on exam fires regardless of bleeding/age data being absent.
    f = feat(abdominal_or_rectal_mass=True, age=None, rectal_bleeding=None)
    v = evaluate(f, referral_id="r14", config=cfg)
    assert v.urgency == "urgent"
    assert v.disposition == "BOOK"


def test_highest_urgency_wins_when_multiple_rules_fire(cfg):
    # age 55, bleeding (urgent), fit positive (urgent) -> both should fire,
    # not first-match-wins.
    f = feat(age=55, rectal_bleeding=True, fit_result="positive")
    v = evaluate(f, referral_id="r15", config=cfg)
    assert v.urgency == "urgent"
    assert "BLEEDING_OVER_50" in v.rules_fired
    assert "POSITIVE_FIT" in v.rules_fired


def test_verdict_records_rule_version(cfg):
    f = feat(fit_result="positive")
    v = evaluate(f, referral_id="r16", config=cfg)
    assert v.rule_version == cfg["version"]


def test_malformed_config_escalates_instead_of_raising():
    f = feat(fit_result="positive")
    v = evaluate(f, referral_id="r17", config={"version": "bad", "rules": [{"id": "BROKEN", "when": "1/0", "urgency": "urgent", "requires": []}]})
    assert v.disposition == "ESCALATE"
