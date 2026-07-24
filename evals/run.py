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
        # Proper dataset+task+scorer experiments (diffable across rule
        # versions in the Braintrust UI) live in evals/braintrust_eval.py.
        from evals import braintrust_eval

        braintrust_eval.main()


if __name__ == "__main__":
    main()
