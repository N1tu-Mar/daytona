"""Every rule must cite its evidence.

The defense against "you made these rules up" is structural: a rule with no
`evidence:` block (study/guideline, cohort, finding, URL) fails the build.
The thresholds in rules.yaml are transcribed epidemiology — CAPER's
measured PPVs, NICE NG12 referral criteria, USPSTF screening ages — and
this test keeps future rule edits honest about their sources.
"""

from __future__ import annotations

from app.rule_engine import load_rules

REQUIRED_EVIDENCE_KEYS = {"source", "cohort", "finding", "url"}


def test_every_rule_has_a_complete_evidence_block():
    rules = load_rules()["rules"]
    assert rules, "no rules loaded"
    for rule in rules:
        evidence = rule.get("evidence")
        assert evidence, f"rule {rule['id']} has no evidence block"
        missing = REQUIRED_EVIDENCE_KEYS - evidence.keys()
        assert not missing, f"rule {rule['id']} evidence missing {sorted(missing)}"
        for key in REQUIRED_EVIDENCE_KEYS:
            assert str(evidence[key]).strip(), f"rule {rule['id']} evidence.{key} is empty"
        assert evidence["url"].startswith("https://"), f"rule {rule['id']} evidence.url is not a link"


def test_evidence_cites_primary_sources():
    """The two load-bearing citations must actually be present somewhere:
    the CAPER cohort (real-patient PPVs) and NICE NG12 (referral criteria)."""
    rules = load_rules()["rules"]
    all_sources = " ".join(str(r["evidence"]["source"]) for r in rules)
    assert "CAPER" in all_sources
    assert "NG12" in all_sources
    assert "USPSTF" in all_sources
