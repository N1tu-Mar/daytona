"""Extraction model A/B on Fireworks, diffed in Braintrust.

Run: python -m evals.extraction_ab            (both models)
     python -m evals.extraction_ab flash      (one model)

Answers one question with data instead of vibes: which Fireworks model
should run live extraction? Each candidate extracts features from the same
15 synthetic referral texts (data/synthetic/referrals.json — gold features
AND gold verdicts), producing one Braintrust experiment per model that the
UI diffs side by side.

The scorer that matters is verdict_preserved: extraction is only perception,
so the question is never "did the model transcribe every field" but "did
its errors change what happens to the patient." A model can fumble a field
the rules don't need and still score 1.0; missing the one field that turns
an urgent case routine scores 0 on extraction_escalation_safety — the
same non-negotiable as everywhere else.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from braintrust import Eval

from app.rule_engine import evaluate
from app.schemas import ReferralFeatures
from services.referral.extract import EXTRACTION_FEATURES, ExtractionError, extract_features

PROJECT = "meridian"
SEED_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "referrals.json"

MODELS = {
    "flash": "accounts/fireworks/models/deepseek-v4-flash",
    "pro": "accounts/fireworks/models/deepseek-v4-pro",
}


def _load_rows() -> list[dict]:
    cases = json.loads(SEED_PATH.read_text())
    return [
        {
            "input": c["raw_text"],
            "expected": {
                "features": c["features"],
                "urgency": c["expected_urgency"],
                "disposition": c["expected_disposition"],
            },
            "metadata": {"case_id": c["id"], "note": c.get("note", "")},
        }
        for c in cases
        if c.get("raw_text")
    ]


def _make_task(model: str):
    def task(raw_text: str) -> dict:
        try:
            features = extract_features(raw_text, model=model)
        except ExtractionError as e:
            # Extraction failure is a legitimate, scoreable outcome: the
            # pipeline would ESCALATE this referral to a human.
            return {"extracted": None, "urgency": None, "disposition": "ESCALATE", "error": str(e)}
        verdict = evaluate(features, referral_id="extraction-ab")
        return {
            "extracted": features.model_dump(mode="json"),
            "urgency": verdict.urgency,
            "disposition": verdict.disposition,
            "rules_fired": verdict.rules_fired,
        }

    return task


def field_accuracy(input, output, expected):
    """Fraction of the 12 clinical fields matching gold. Known-conservative
    floor: gold encodes full clinical truth (unstated negatives as False),
    while the extractor is instructed to never infer, so "not stated" comes
    back None and scores as a miss here. That gap is absorbed downstream by
    the rule engine's fail-safe missing-data handling — which is why
    verdict_preserved, not this, is the decision metric."""
    if output["extracted"] is None:
        return 0.0
    gold, got = expected["features"], output["extracted"]
    hits = sum(1 for f in EXTRACTION_FEATURES if got.get(f) == gold.get(f))
    return hits / len(EXTRACTION_FEATURES)


def asserted_precision(input, output, expected):
    """Of the fields the model *asserted* (non-null), how many match gold —
    the hallucination detector. A model that only returns what the text
    actually states scores 1.0 even if it leaves many fields null; a model
    that invents values gets caught here and nowhere else."""
    if output["extracted"] is None:
        return None  # nothing asserted; no precision to measure
    gold, got = expected["features"], output["extracted"]
    asserted = [f for f in EXTRACTION_FEATURES if got.get(f) is not None]
    if not asserted:
        return None
    return sum(1 for f in asserted if got[f] == gold.get(f)) / len(asserted)


def verdict_preserved(input, output, expected):
    """Did extraction quality change the clinical outcome? Runs the same
    deterministic rules over the extracted features and compares the verdict
    to gold. This is the metric a clinician would actually ask for."""
    return 1.0 if output["urgency"] == expected["urgency"] and output["disposition"] == expected["disposition"] else 0.0


def extraction_escalation_safety(input, output, expected):
    """Should-be-urgent referrals must come out urgent or with a human in
    the loop, even through a lossy extraction. Failed extraction ESCALATEs,
    which is safe by definition."""
    if expected["urgency"] not in ("urgent", "emergency"):
        return None
    flagged = output["urgency"] in ("urgent", "emergency") or output["disposition"] in ("ESCALATE", "NEEDS_INFO")
    return 1.0 if flagged else 0.0


def run_model(alias: str) -> None:
    model = MODELS[alias]
    Eval(
        PROJECT,
        experiment_name=f"extraction-{alias}",
        data=_load_rows,
        task=_make_task(model),
        scores=[verdict_preserved, extraction_escalation_safety, asserted_precision, field_accuracy],
        metadata={"model": model, "stage": "extraction"},
        max_concurrency=4,
    )


def main() -> None:
    wanted = sys.argv[1:] or list(MODELS)
    unknown = [w for w in wanted if w not in MODELS]
    if unknown:
        sys.exit(f"unknown model alias(es) {unknown}; choose from {list(MODELS)}")
    for alias in wanted:
        run_model(alias)


if __name__ == "__main__":
    main()
