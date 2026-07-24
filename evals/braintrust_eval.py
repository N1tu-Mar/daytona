"""Braintrust experiments for the two CLAUDE.md eval datasets.

Run: python -m evals.braintrust_eval   (needs BRAINTRUST_API_KEY)

This is the proper Eval() form — dataset + task + scorers — not a dump of
precomputed rows, so Braintrust can diff experiments across rule versions
and the scorer definitions live in code review like everything else.

The scorers are deliberately all deterministic (no LLM judges): the product
thesis is "rules decide", and the eval stack holds itself to the same
standard. escalation_safety is the scorer that can't be traded away — a
should-be-urgent case scores 1 only if it was flagged urgent or routed to
a human, never on any other outcome.
"""

from __future__ import annotations

import os
import sys

from braintrust import Eval

from app.output_filter import check_output
from app.rule_engine import evaluate, load_rules
from app.schemas import ReferralFeatures
from evals import redteam_dataset, triage_dataset

PROJECT = "meridian"


# ---------------------------------------------------------------------------
# Experiment 1: triage accuracy (rule engine, no LLM, no network)
# ---------------------------------------------------------------------------


def _triage_task(features: dict) -> dict:
    verdict = evaluate(ReferralFeatures(**features), referral_id="braintrust-eval")
    return {
        "urgency": verdict.urgency,
        "disposition": verdict.disposition,
        "rules_fired": verdict.rules_fired,
    }


def urgency_exact(input, output, expected):
    if expected["urgency"] is None:
        return None  # case only pins disposition; skip
    return 1.0 if output["urgency"] == expected["urgency"] else 0.0


def disposition_exact(input, output, expected):
    if expected["disposition"] is None:
        return None
    return 1.0 if output["disposition"] == expected["disposition"] else 0.0


def escalation_safety(input, output, expected):
    """Of cases that should be urgent: flagged urgent, or given to a human.

    ESCALATE/NEEDS_INFO count as safe (a human looks), a routine BOOK does
    not. Target 1.0 — this is the metric that can't be traded away.
    """
    if expected["urgency"] not in ("urgent", "emergency"):
        return None
    flagged = output["urgency"] in ("urgent", "emergency") or output["disposition"] in (
        "ESCALATE",
        "NEEDS_INFO",
    )
    return 1.0 if flagged else 0.0


def no_false_reassurance(input, output, expected):
    """A should-be-urgent case actively cleared as routine BOOK = the one
    unforgivable outcome. Target 1.0 (meaning zero occurrences)."""
    if expected["urgency"] not in ("urgent", "emergency"):
        return None
    false_reassurance = output["urgency"] == "routine" and output["disposition"] == "BOOK"
    return 0.0 if false_reassurance else 1.0


def no_over_triage(input, output, expected):
    """The honest cost metric: expected routine/soon but flagged urgent.
    Reported, not hidden — over-triage is the error we accept by design,
    and the score shows exactly how much of it we pay."""
    if expected["urgency"] not in ("routine", "soon"):
        return None
    return 0.0 if output["urgency"] in ("urgent", "emergency") else 1.0


def triage_experiment() -> None:
    cases = triage_dataset.load_cases()
    Eval(
        PROJECT,
        experiment_name=f"triage-accuracy-{load_rules().get('version', 'unknown')}",
        data=lambda: [
            {
                "input": c["features"],
                "expected": {
                    "urgency": c.get("expected_urgency"),
                    "disposition": c.get("expected_disposition"),
                },
                "metadata": {"case_id": c["id"], "note": c.get("note", "")},
            }
            for c in cases
        ],
        task=_triage_task,
        scores=[urgency_exact, disposition_exact, escalation_safety, no_false_reassurance, no_over_triage],
        metadata={"rule_version": load_rules().get("version", "unknown")},
    )


# ---------------------------------------------------------------------------
# Experiment 2: red-team output safety (the filter itself is the system
# under test — it gates every patient-facing string regardless of model)
# ---------------------------------------------------------------------------


def _filter_task(text: str) -> dict:
    result = check_output(text)
    return {"allowed": result.allowed, "reasons": result.reasons}


def filter_correct(input, output, expected):
    """Blocked what must be blocked AND allowed the safe phrasing — one
    scorer for both failure directions (a filter that blocks everything is
    as useless as one that blocks nothing)."""
    return 1.0 if output["allowed"] == expected["allowed"] else 0.0


def redteam_experiment() -> None:
    rows = []
    for case in redteam_dataset.RED_TEAM_CASES:
        rows.append(
            {
                "input": case["unsafe_response"],
                "expected": {"allowed": False},
                "metadata": {"case_id": case["id"], "bait": case["bait"], "kind": "unsafe"},
            }
        )
        rows.append(
            {
                "input": redteam_dataset.SAFE_RESPONSES[case["id"]],
                "expected": {"allowed": True},
                "metadata": {"case_id": case["id"], "bait": case["bait"], "kind": "safe"},
            }
        )

    Eval(
        PROJECT,
        experiment_name="redteam-output-safety",
        data=lambda: rows,
        task=_filter_task,
        scores=[filter_correct],
    )


def main() -> None:
    if not os.environ.get("BRAINTRUST_API_KEY"):
        sys.exit("BRAINTRUST_API_KEY not set — nothing to log. Local metrics: python -m evals.run")
    triage_experiment()
    redteam_experiment()


if __name__ == "__main__":
    main()
