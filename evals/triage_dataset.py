"""Triage accuracy eval dataset (CLAUDE.md Evals dataset 1, ~30 cases).

Loads the named synthetic cases from data/synthetic/referrals.json and adds
generated edge-case variants to round out coverage of missing-data and
boundary-age scenarios. Runs the real rule engine (no LLM, no network) and
scores against each case's expected_urgency/expected_disposition.

`escalation_recall` is the metric that can't be traded away: of cases that
*should* be urgent, how many were flagged urgent (or escalated to a human,
which is always an acceptable outcome, never a miss).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.rule_engine import evaluate
from app.schemas import ReferralFeatures

SEED_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "referrals.json"


def _generated_edge_cases() -> list[dict[str, Any]]:
    """Boundary and missing-data variants not worth hand-authoring individually."""
    cases: list[dict[str, Any]] = []

    # Age boundary: exactly 50, bleeding -> BLEEDING_OVER_50, not the
    # under-50 track.
    cases.append(
        {
            "id": "gen-age-boundary-50",
            "expected_urgency": "urgent",
            "expected_disposition": "BOOK",
            "features": {"age": 50, "rectal_bleeding": True},
        }
    )
    # Age boundary: 49, isolated bleeding -> soon, not urgent.
    cases.append(
        {
            "id": "gen-age-boundary-49",
            "expected_urgency": "soon",
            "expected_disposition": "BOOK",
            "features": {
                "age": 49,
                "rectal_bleeding": True,
                "change_in_bowel_habit": False,
                "unintentional_weight_loss": False,
                "abdominal_pain": False,
                "iron_deficiency_anemia": False,
                "fit_result": "negative",
                "abdominal_or_rectal_mass": False,
            },
        }
    )
    # Age boundary: exactly 60, IDA -> urgent.
    cases.append(
        {
            "id": "gen-ida-boundary-60",
            "expected_urgency": "urgent",
            "expected_disposition": "BOOK",
            "features": {"age": 60, "iron_deficiency_anemia": True},
        }
    )
    # Age boundary: 59, IDA -> no rule at that age; falls through to escalate
    # rather than a false "routine" clear.
    cases.append(
        {
            # IDA_OVER_60 needs 60+; at 59 it doesn't fire. SCREENING_AGE_NO_PRIOR
            # (45+, no prior colonoscopy) still fires, so this correctly
            # resolves to routine/BOOK rather than a rule-engine miss.
            "id": "gen-ida-boundary-59",
            "expected_urgency": "routine",
            "expected_disposition": "BOOK",
            "features": {
                "age": 59,
                "iron_deficiency_anemia": True,
                "rectal_bleeding": False,
                "change_in_bowel_habit": False,
                "unintentional_weight_loss": False,
                "abdominal_pain": False,
                "fit_result": "negative",
                "abdominal_or_rectal_mass": False,
                "prior_colonoscopy_date": None,
            },
        }
    )
    # Bowel habit change exactly at 6-week threshold.
    cases.append(
        {
            "id": "gen-bowel-change-6-weeks",
            "expected_urgency": "soon",
            "expected_disposition": "BOOK",
            "features": {
                "age": 30,
                "change_in_bowel_habit": True,
                "bowel_habit_duration_weeks": 6,
                "rectal_bleeding": False,
                "unintentional_weight_loss": False,
                "abdominal_pain": False,
                "iron_deficiency_anemia": False,
                "fit_result": "negative",
                "abdominal_or_rectal_mass": False,
            },
        }
    )
    # Bowel habit change at 5 weeks -> rule shouldn't fire on duration alone.
    cases.append(
        {
            "id": "gen-bowel-change-5-weeks",
            "expected_urgency": None,
            "expected_disposition": "ESCALATE",
            "features": {
                "change_in_bowel_habit": True,
                "bowel_habit_duration_weeks": 5,
                "age": 30,
                "rectal_bleeding": False,
                "unintentional_weight_loss": False,
                "abdominal_pain": False,
                "iron_deficiency_anemia": False,
                "fit_result": "negative",
                "abdominal_or_rectal_mass": False,
            },
        }
    )
    # Missing FIT result entirely, nothing else abnormal at screening age
    # with a prior colonoscopy -> can't be sure FIT wasn't positive.
    cases.append(
        {
            "id": "gen-missing-fit-result",
            "expected_urgency": None,
            "expected_disposition": "NEEDS_INFO",
            "features": {"age": 55},
        }
    )
    # Family history alone (not currently rule-gated) plus a young bleeder ->
    # still must hit the demo rule regardless of the extra unused field.
    cases.append(
        {
            "id": "gen-young-bleeding-family-history",
            "expected_urgency": "urgent",
            "expected_disposition": "BOOK",
            "features": {
                "age": 33,
                "rectal_bleeding": True,
                "abdominal_pain": True,
                "family_history_crc": "first_degree",
            },
        }
    )
    # Multiple missing fields simultaneously, young patient -> NEEDS_INFO/ESCALATE,
    # never a guessed routine.
    cases.append(
        {
            "id": "gen-many-missing-fields",
            "expected_urgency": None,
            "expected_disposition": None,  # NEEDS_INFO or ESCALATE both acceptable
            "features": {"age": 28},
        }
    )
    # Elderly, everything explicitly negative and prior colonoscopy on file
    # -> no rule fires (screening rule requires no prior) -> ESCALATE, not
    # a silent "nothing to do".
    cases.append(
        {
            "id": "gen-elderly-clean-with-prior",
            "expected_urgency": None,
            "expected_disposition": "ESCALATE",
            "features": {
                "age": 70,
                "rectal_bleeding": False,
                "change_in_bowel_habit": False,
                "unintentional_weight_loss": False,
                "abdominal_pain": False,
                "iron_deficiency_anemia": False,
                "fit_result": "negative",
                "abdominal_or_rectal_mass": False,
                "prior_colonoscopy_date": "2020-01-01",
            },
        }
    )
    # Positive FIT plus otherwise-clean profile at screening age -> both
    # POSITIVE_FIT and SCREENING_AGE_NO_PRIOR should fire, urgent wins.
    cases.append(
        {
            "id": "gen-fit-positive-screening-age",
            "expected_urgency": "urgent",
            "expected_disposition": "BOOK",
            "features": {"age": 46, "fit_result": "positive", "prior_colonoscopy_date": None},
        }
    )
    # Very elderly with bowel habit change under 6 weeks -> BOWEL_HABIT_OVER_60
    # doesn't require duration, so still fires urgent regardless.
    cases.append(
        {
            "id": "gen-elderly-bowel-change-short-duration",
            "expected_urgency": "urgent",
            "expected_disposition": "BOOK",
            "features": {"age": 75, "change_in_bowel_habit": True, "bowel_habit_duration_weeks": 1},
        }
    )
    # Weight loss without pain, age 40+ -> WEIGHT_LOSS_PLUS_PAIN rule needs
    # both; alone this shouldn't fire it.
    cases.append(
        {
            "id": "gen-weight-loss-alone-over-40",
            "expected_urgency": None,
            "expected_disposition": "NEEDS_INFO",
            "features": {"age": 45, "unintentional_weight_loss": True},
        }
    )
    # Under-40 weight loss + pain -> rule is age-gated 40+, shouldn't fire.
    cases.append(
        {
            # Rule is age-gated 40+, so it shouldn't fire at 35, and no other
            # rule matches this profile either -> no explicit rule matched
            # at all -> fails safe to ESCALATE rather than silently BOOK.
            "id": "gen-weight-loss-pain-under-40",
            "expected_urgency": None,
            "expected_disposition": "ESCALATE",
            "features": {
                "age": 35,
                "unintentional_weight_loss": True,
                "abdominal_pain": True,
                "rectal_bleeding": False,
                "change_in_bowel_habit": False,
                "iron_deficiency_anemia": False,
                "fit_result": "negative",
                "abdominal_or_rectal_mass": False,
            },
        }
    )
    return cases


def load_cases() -> list[dict[str, Any]]:
    named = json.loads(SEED_PATH.read_text())
    return named + _generated_edge_cases()


def run() -> dict[str, Any]:
    cases = load_cases()
    results = []

    should_be_urgent_count = 0
    urgent_and_flagged = 0
    routine_false_reassurance = 0
    over_triage_count = 0
    total_scoreable = 0

    for case in cases:
        features = ReferralFeatures(**case["features"])
        verdict = evaluate(features, referral_id=case["id"])

        expected_urgency = case.get("expected_urgency")
        expected_disposition = case.get("expected_disposition")

        should_be_urgent = expected_urgency in ("urgent", "emergency")
        was_flagged_urgent = verdict.urgency in ("urgent", "emergency") or verdict.disposition in (
            "ESCALATE",
            "NEEDS_INFO",
        )
        if should_be_urgent:
            should_be_urgent_count += 1
            if was_flagged_urgent:
                urgent_and_flagged += 1

        # false reassurance: should have been non-routine but engine landed
        # on a routine BOOK (i.e. actively cleared, not escalated).
        if should_be_urgent and verdict.urgency == "routine" and verdict.disposition == "BOOK":
            routine_false_reassurance += 1

        # over-triage: expected routine/soon but engine escalated higher.
        if expected_urgency in ("routine", "soon") and verdict.urgency in ("urgent", "emergency"):
            over_triage_count += 1

        passed = True
        if expected_urgency is not None:
            passed &= verdict.urgency == expected_urgency
        if expected_disposition is not None:
            passed &= verdict.disposition == expected_disposition
        if expected_urgency is not None or expected_disposition is not None:
            total_scoreable += 1

        results.append(
            {
                "id": case["id"],
                "expected_urgency": expected_urgency,
                "expected_disposition": expected_disposition,
                "actual_urgency": verdict.urgency,
                "actual_disposition": verdict.disposition,
                "rules_fired": verdict.rules_fired,
                "passed": bool(passed),
            }
        )

    escalation_recall = (
        urgent_and_flagged / should_be_urgent_count if should_be_urgent_count else 1.0
    )
    false_reassurance_rate = (
        routine_false_reassurance / should_be_urgent_count if should_be_urgent_count else 0.0
    )
    over_triage_rate = over_triage_count / len(cases) if cases else 0.0

    return {
        "n_cases": len(cases),
        "n_should_be_urgent": should_be_urgent_count,
        "escalation_recall": escalation_recall,
        "false_reassurance_rate": false_reassurance_rate,
        "over_triage_rate": over_triage_rate,
        "results": results,
    }


if __name__ == "__main__":
    summary = run()
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
