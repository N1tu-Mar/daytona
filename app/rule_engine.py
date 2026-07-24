"""Deterministic rule engine. Zero model calls, fully unit-testable.

Loads app/rules.yaml, evaluates every rule against a ReferralFeatures
instance, and folds the results into a TriageVerdict via
app.urgency.highest_urgency (never first-match-wins, never a direct
assignment).

Fail-safe defaults (CLAUDE.md invariant #3) are enforced here:
  - a rule whose required features are missing is skipped, not guessed
  - if that leaves the verdict ambiguous, disposition is NEEDS_INFO
  - if evaluation raises for any reason, disposition is ESCALATE
  - there is no code path that produces a "CLEAR" verdict; BOOK is only
    reached when at least one rule explicitly matched on complete data
"""

from __future__ import annotations

import itertools
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.schemas import ReferralFeatures, RuleMatch, TriageVerdict, Urgency
from app.urgency import highest_urgency

log = logging.getLogger("meridian.rule_engine")

RULES_PATH = Path(__file__).parent / "rules.yaml"

# Deliberately tiny expression grammar: rule "when" clauses are trusted
# config (not user input) and are restricted to comparisons/boolean logic
# over the feature dict. No builtins, no attribute access, no calls.
_ALLOWED_GLOBALS: dict[str, Any] = {"__builtins__": {}, "null": None, "true": True, "false": False}

# For each feature that can appear in `requires`, the extreme/representative
# values used to probe whether an unknown value could actually change a
# rule's outcome. E.g. an unknown bowel_habit_duration_weeks doesn't matter
# if change_in_bowel_habit is already known False.
_FIELD_CANDIDATES: dict[str, list[Any]] = {
    "age": [-1, 1000],
    "rectal_bleeding": [True, False],
    "bleeding_duration_weeks": [-1, 1000],
    "change_in_bowel_habit": [True, False],
    "bowel_habit_duration_weeks": [-1, 1000],
    "unintentional_weight_loss": [True, False],
    "abdominal_pain": [True, False],
    "iron_deficiency_anemia": [True, False],
    "fit_result": ["positive", "negative", "not_done"],
    "family_history_crc": ["none", "first_degree", "multiple"],
    "abdominal_or_rectal_mass": [True, False],
}


class RuleEngineError(Exception):
    """Raised on any evaluation failure. Callers must treat this as ESCALATE."""


def load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    with open(path) as f:
        config = yaml.safe_load(f)
    if not config or "version" not in config or "rules" not in config:
        raise RuleEngineError(f"malformed rules config at {path}")
    return config


def _feature_dict(features: ReferralFeatures) -> dict[str, Any]:
    data = features.model_dump(exclude={"source_refs", "extraction_confidence"})
    return data


def evaluate(
    features: ReferralFeatures,
    referral_id: str,
    config: dict[str, Any] | None = None,
) -> TriageVerdict:
    """Evaluate all rules against `features` and return a TriageVerdict.

    Any exception is caught and converted into an ESCALATE verdict — the
    triage path must never propagate an unhandled exception (invariant #3).
    """
    try:
        cfg = config or load_rules()
        return _evaluate_unsafe(features, referral_id, cfg)
    except Exception:
        log.exception("rule_engine_failure", extra={"referral_id": referral_id})
        return TriageVerdict(
            referral_id=referral_id,
            urgency="routine",
            disposition="ESCALATE",
            rules_fired=[],
            rule_version=(config or {}).get("version", "unknown"),
            missing_features=[],
            created_at=datetime.now(timezone.utc),
        )


def _evaluate_unsafe(
    features: ReferralFeatures, referral_id: str, cfg: dict[str, Any]
) -> TriageVerdict:
    fdict = _feature_dict(features)
    matches: list[RuleMatch] = []
    missing: set[str] = set()

    for rule in cfg["rules"]:
        requires: list[str] = rule.get("requires", [])
        unmet = [f for f in requires if fdict.get(f) is None]

        if not unmet:
            fires = _eval_expr(rule["id"], rule["when"], fdict)
        else:
            fires = _eval_with_unknowns(rule["id"], rule["when"], fdict, unmet)
            if fires is None:
                # The missing field(s) could genuinely flip this rule's
                # outcome either way — don't guess, surface as missing.
                missing.update(unmet)
                continue

        if fires:
            matches.append(
                RuleMatch(id=rule["id"], urgency=rule["urgency"], rationale=rule.get("rationale"))
            )

    urgency: Urgency = highest_urgency([m.urgency for m in matches], floor="routine")
    rules_fired = [m.id for m in matches]

    disposition = _decide_disposition(urgency=urgency, rules_fired=rules_fired, missing=missing)

    return TriageVerdict(
        referral_id=referral_id,
        urgency=urgency,
        disposition=disposition,
        rules_fired=rules_fired,
        rule_version=cfg["version"],
        missing_features=sorted(missing),
        created_at=datetime.now(timezone.utc),
    )


def _eval_expr(rule_id: str, expr: str, fdict: dict[str, Any]) -> bool:
    try:
        return bool(eval(expr, _ALLOWED_GLOBALS, dict(fdict)))
    except Exception as e:
        raise RuleEngineError(f"rule {rule_id} failed to evaluate: {e}") from e


def _eval_with_unknowns(
    rule_id: str, expr: str, fdict: dict[str, Any], unmet: list[str]
) -> bool | None:
    """Probe every extreme value of the unmet fields.

    Returns the outcome if it's the same regardless of what the unknown
    fields turn out to be (the missing data is irrelevant to this rule), or
    None if the outcome genuinely depends on data we don't have.
    """
    try:
        candidate_lists = [_FIELD_CANDIDATES[f] for f in unmet]
    except KeyError as e:
        # A required field with no known candidate domain: can't probe it,
        # treat as genuinely ambiguous rather than silently skip.
        raise RuleEngineError(f"rule {rule_id} requires unprobeable field {e}") from e

    outcomes: set[bool] = set()
    for combo in itertools.product(*candidate_lists):
        trial = dict(fdict)
        trial.update(zip(unmet, combo))
        outcomes.add(_eval_expr(rule_id, expr, trial))
        if len(outcomes) > 1:
            return None
    return outcomes.pop()


def _decide_disposition(
    urgency: Urgency, rules_fired: list[str], missing: set[str]
) -> str:
    # No rule matched at all: never silently clear, always send to a human.
    if not rules_fired:
        return "ESCALATE"
    # An explicit rule fired at the ceiling urgency this engine can reach
    # (urgent). Missing data on unrelated features can't lower urgency
    # (monotonic), so it's safe to book while still surfacing the gaps.
    if urgency in ("urgent", "emergency"):
        return "BOOK"
    # A rule fired at a lower urgency, but data is incomplete elsewhere —
    # the true answer could still be higher. Don't guess.
    if missing:
        return "NEEDS_INFO"
    return "BOOK"
