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

// Published real-patient evidence behind each rule, mirroring the
// `evidence:` blocks in app/rules.yaml. PPVs are from Hamilton et al.'s
// CAPER case-control study (349 colorectal cancer cases + 1,744 matched
// controls in UK primary care, Br J Cancer 2005); referral criteria from
// NICE NG12 and USPSTF 2021. The thresholds are measured epidemiology,
// not invented heuristics — this map lets a nurse see the study behind a
// fired rule without opening the config file.
export const RULE_EVIDENCE: Record<string, { finding: string; source: string; url: string }> = {
  MASS_ON_EXAM: {
    finding: "Abnormal rectal exam: PPV 4.0% (2.4–7.4) for CRC — above the ~3% urgent-referral threshold.",
    source: "CAPER, 2,093 real patients; NICE NG12",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC2361578/",
  },
  POSITIVE_FIT: {
    finding: "Positive faecal occult blood: PPV 7.1% (5.1–10) — strongest single predictor measured.",
    source: "CAPER, 2,093 real patients; NICE NG12/DG30",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC2361578/",
  },
  BLEEDING_OVER_50: {
    finding: "Rectal bleeding: PPV 2.4% (1.9–3.2), rising with age; NG12 refers 50+ urgently.",
    source: "CAPER, 2,093 real patients; NICE NG12 1.3.2",
    url: "https://www.nice.org.uk/guidance/ng12",
  },
  IDA_OVER_60: {
    finding: "Haemoglobin <10 g/dL: PPV 2.3% (1.6–3.1); NG12 refers IDA at 60+ urgently.",
    source: "CAPER, 2,093 real patients; NICE NG12 1.3.1",
    url: "https://www.nice.org.uk/guidance/ng12",
  },
  BOWEL_HABIT_OVER_60: {
    finding: "Bowel-habit change at 60+ meets the NG12 urgent-referral criterion.",
    source: "NICE NG12 1.3.1; CAPER, 2,093 real patients",
    url: "https://www.nice.org.uk/guidance/ng12",
  },
  WEIGHT_LOSS_PLUS_PAIN_OVER_40: {
    finding: "Weight loss (PPV 1.2%) + abdominal pain (PPV 1.1%): each below threshold alone, but any second feature raises risk to the investigation level.",
    source: "CAPER, 2,093 real patients; NICE NG12 1.3.1",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC2361578/",
  },
  YOUNG_BLEEDING_PLUS_FEATURE: {
    finding: "Bleeding alone: PPV 2.4%; CAPER found any second feature pushes CRC risk to the investigation threshold — NG12 1.3.3 encodes exactly this under-50 pattern.",
    source: "CAPER, 2,093 real patients; NICE NG12 1.3.3",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC2361578/",
  },
  ISOLATED_BLEEDING_UNDER_50: {
    finding: "Rectal bleeding carries a measured 2.4% PPV for CRC — below urgent alone under 50, never dismissed as benign.",
    source: "CAPER, 2,093 real patients",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC2361578/",
  },
  PERSISTENT_BOWEL_CHANGE: {
    finding: "6+ weeks is the persistence threshold UK lower-GI referral criteria use to separate transient change from presentations needing evaluation.",
    source: "NICE NG12 / NHS 2-week-wait criteria",
    url: "https://www.nice.org.uk/guidance/ng12",
  },
  SCREENING_AGE_NO_PRIOR: {
    finding: "Screening from age 45: USPSTF Grade B (45–49), Grade A (50–75).",
    source: "USPSTF 2021",
    url: "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/colorectal-cancer-screening",
  },
};
