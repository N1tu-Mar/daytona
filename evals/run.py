"""Run both eval datasets and write data/evals_summary.json for the dashboard.

Run: python -m evals.run

If BRAINTRUST_API_KEY is set, also logs both datasets as Braintrust
experiments (project "meridian"). Without a key, this still produces the real
local summary the dashboard reads — Braintrust is additive, not required to
have a working dashboard.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from evals import redteam_dataset, triage_dataset

OUT_PATH = Path(__file__).parent.parent / "data" / "evals_summary.json"


def _log_to_braintrust(triage: dict, redteam: dict) -> None:
    try:
        import braintrust
    except ImportError:
        print("braintrust not installed; skipping remote logging")
        return

    with braintrust.init(project="meridian", experiment="triage_accuracy") as exp:
        for r in triage["results"]:
            exp.log(
                input={"id": r["id"]},
                output={"urgency": r["actual_urgency"], "disposition": r["actual_disposition"]},
                expected={"urgency": r["expected_urgency"], "disposition": r["expected_disposition"]},
                scores={"passed": 1.0 if r["passed"] else 0.0},
                metadata={"rules_fired": r["rules_fired"]},
            )

    with braintrust.init(project="meridian", experiment="redteam_output_safety") as exp:
        for r in redteam["results"]:
            exp.log(
                input={"bait": r["bait"]},
                output={"unsafe_response_blocked": r["unsafe_response_blocked"]},
                expected={"unsafe_response_blocked": True},
                scores={"blocked_as_expected": 1.0 if r["unsafe_response_blocked"] else 0.0},
            )


def main() -> None:
    triage = triage_dataset.run()
    redteam = redteam_dataset.run()

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "triage": {k: v for k, v in triage.items() if k != "results"},
        "redteam": {k: v for k, v in redteam.items() if k != "results"},
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    failing = [r for r in triage["results"] if not r["passed"]]
    if failing:
        print(f"\n{len(failing)} triage case(s) did not match expected outcome:")
        for r in failing:
            print(f"  {r['id']}: expected {r['expected_urgency']}/{r['expected_disposition']} "
                  f"got {r['actual_urgency']}/{r['actual_disposition']}")

    if os.environ.get("BRAINTRUST_API_KEY"):
        _log_to_braintrust(triage, redteam)


if __name__ == "__main__":
    main()
