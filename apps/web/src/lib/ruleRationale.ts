// Display-only rationale text for rule IDs, mirroring app/rules.yaml's
// `rationale:` fields (as of rule_version referenced there). This is purely
// UI copy to help a nurse read the audit trail without opening the config
// file — the backend remains the source of truth for rules_fired and
// rule_version. If a rule fires with no entry here, we just show its ID.
export const RULE_RATIONALE: Record<string, string> = {
  MASS_ON_EXAM: "Palpable mass warrants urgent evaluation.",
  POSITIVE_FIT: "Positive FIT meets criteria for diagnostic colonoscopy.",
  BLEEDING_OVER_50: "Rectal bleeding at age 50+ meets criteria for urgent referral.",
  IDA_OVER_60: "Iron deficiency anemia at age 60+ meets criteria for urgent referral.",
  BOWEL_HABIT_OVER_60: "Change in bowel habit at age 60+ meets criteria for urgent referral.",
  WEIGHT_LOSS_PLUS_PAIN_OVER_40:
    "Unintentional weight loss with abdominal pain at age 40+ meets criteria for urgent referral.",
  YOUNG_BLEEDING_PLUS_FEATURE:
    "Early-onset colorectal cancer incidence is rising ~3%/yr in ages 20-49, and most under-50 cases present at advanced stage. Bleeding in a young adult with a second red-flag feature is not assumed benign.",
  ISOLATED_BLEEDING_UNDER_50: "Warrants evaluation; not assumed benign.",
  PERSISTENT_BOWEL_CHANGE: "Bowel habit change persisting 6+ weeks warrants evaluation.",
  SCREENING_AGE_NO_PRIOR: "USPSTF screening age is 45 with no prior colonoscopy on record.",
};
